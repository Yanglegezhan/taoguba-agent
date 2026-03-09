"""
Reviewer Agent (Agent 3): 代码审查智能体
负责审查代码质量、检查问题并提出修复建议
"""

import os
import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path

from .base_agent import BaseAgent

logger = logging.getLogger(__name__)


class ReviewerAgent(BaseAgent):
    """
    Reviewer Agent - 代码审查智能体
    
    核心功能:
    - 静态代码分析
    - 检查代码风格和规范
    - 识别潜在bug和安全问题
    - 提供修复建议
    - 与Coder Agent协作修复问题
    """

    def __init__(self, config: Dict[str, Any], llm_provider=None):
        # 设置系统提示
        system_prompt = """你是 Auto-Freelance Swarm 的 Reviewer Agent (代码审查专家)。

你的主要职责是:
1. 对生成的代码进行全面的静态分析
2. 检查代码风格一致性
3. 识别潜在的bug和逻辑错误
4. 检查安全问题（SQL注入、XSS、敏感信息泄露等）
5. 评估代码性能和优化空间
6. 提供具体的修复建议

审查维度:
- 代码正确性: 代码能否正常运行
- 代码风格: 是否遵循PEP8/语言规范
- 安全性: 是否有安全漏洞
- 性能: 是否有性能问题
- 可维护性: 代码是否易于理解和维护
- 完整性: 是否包含必要的组件（测试、文档等）

重要原则:
- 发现问题时，提供具体的修复建议
- 区分问题的严重程度（Critical/High/Medium/Low）
- 对于不确定的问题，标注为"建议检查"而非直接判定
- 关注代码的整体质量，而非吹毛求疵

输出格式:
请提供结构化的审查报告，包括:
- 问题列表（按严重程度排序）
- 每个问题的详细说明
- 具体的修复建议
- 代码评分
"""
        
        config["system_prompt"] = system_prompt
        super().__init__("ReviewerAgent", config, llm_provider)

    async def execute(self, input_data: Any, context: Optional[Dict] = None) -> Dict[str, Any]:
        """
        执行代码审查任务
        
        Args:
            input_data: 项目路径或代码文件列表
            context: 上下文信息
            
        Returns:
            代码审查报告
        """
        logger.info("开始执行代码审查任务")
        
        # 解析输入
        if isinstance(input_data, dict):
            project_path = input_data.get("project_path", "")
            project_files = input_data.get("files", [])
        else:
            project_path = str(input_data)
            project_files = []
        
        # 扫描项目文件
        if not project_files:
            project_files = await self.scan_project_files(project_path)
        
        # 审查每个文件
        all_issues = []
        file_reviews = []
        
        for file_info in project_files:
            review = await self.review_file(file_info)
            file_reviews.append(review)
            
            if review.get("issues"):
                all_issues.extend(review["issues"])
        
        # 生成总体审查报告
        report = await self.generate_review_report(
            project_path,
            file_reviews,
            all_issues,
            context
        )
        
        # 评估是否需要修复
        needs_fix = any(
            issue.get("severity") in ["Critical", "High"]
            for issue in all_issues
        )
        
        logger.info(f"代码审查完成，发现 {len(all_issues)} 个问题")
        
        return {
            "status": "success",
            "project_path": project_path,
            "files_reviewed": len(file_reviews),
            "total_issues": len(all_issues),
            "issues_by_severity": self._count_by_severity(all_issues),
            "file_reviews": file_reviews,
            "report": report,
            "needs_fix": needs_fix,
            "reviewed_at": datetime.now().isoformat()
        }

    async def scan_project_files(self, project_path: str) -> List[Dict[str, Any]]:
        """扫描项目文件"""
        
        files = []
        path = Path(project_path)
        
        if not path.exists():
            logger.warning(f"项目路径不存在: {project_path}")
            return files
        
        # 扫描Python文件
        for py_file in path.rglob("*.py"):
            if "__pycache__" in str(py_file):
                continue
            
            files.append({
                "name": py_file.name,
                "path": str(py_file),
                "type": "python",
                "relative_path": str(py_file.relative_to(path))
            })
        
        # 扫描其他代码文件
        for ext in ["*.js", "*.ts", "*.html", "*.css", "*.yaml", "*.json"]:
            for file in path.rglob(ext):
                files.append({
                    "name": file.name,
                    "path": str(file),
                    "type": ext.replace("*", ""),
                    "relative_path": str(file.relative_to(path))
                })
        
        return files

    async def review_file(self, file_info: Dict[str, Any]) -> Dict[str, Any]:
        """审查单个文件"""
        
        file_path = file_info.get("path", "")
        file_type = file_info.get("type", "")
        file_name = file_info.get("name", "")
        
        logger.info(f"审查文件: {file_name}")
        
        # 读取文件内容
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            logger.error(f"读取文件失败: {e}")
            return {
                "file": file_name,
                "path": file_path,
                "status": "error",
                "error": str(e)
            }
        
        # 进行代码审查
        issues = await self.analyze_code(content, file_type, file_name)
        
        return {
            "file": file_name,
            "path": file_path,
            "type": file_type,
            "lines": len(content.split('\n')),
            "issues": issues,
            "issue_count": len(issues)
        }

    async def analyze_code(
        self,
        content: str,
        file_type: str,
        file_name: str
    ) -> List[Dict[str, Any]]:
        """分析代码并发现问题"""
        
        # 使用LLM进行代码审查
        prompt = f"""请审查以下{file_type}代码，找出潜在问题:

文件名: {file_name}

```{file_type}
{content[:5000]}  # 限制长度
```

请识别以下类型的问题:
1. 语法错误或潜在运行时错误
2. 安全漏洞（如SQL注入、XSS、敏感信息泄露）
3. 代码风格问题
4. 潜在的bug
5. 性能问题
6. 缺失的错误处理

对于每个问题，请指出:
- 问题描述
- 严重程度 (Critical/High/Medium/Low)
- 具体的行号或位置
- 修复建议

请以JSON数组格式返回，例如:
[
  {{
    "severity": "High",
    "category": "Security",
    "description": "问题描述",
    "line": 42,
    "suggestion": "修复建议"
  }}
]

如果没有问题，请返回空数组 []。"""
        
        messages = self.get_messages()
        messages.append({
            "role": "user",
            "content": prompt
        })
        
        try:
            import re
            response = await self.call_llm(messages, temperature=0.3, max_tokens=3000)
            
            # 提取JSON
            json_match = re.search(r'\[[\s\S]*\]', response)
            if json_match:
                import json
                issues = json.loads(json_match.group())
                return issues
        except Exception as e:
            logger.error(f"代码分析失败: {e}")
        
        return []

    async def generate_review_report(
        self,
        project_path: str,
        file_reviews: List[Dict[str, Any]],
        all_issues: List[Dict[str, Any]],
        context: Optional[Dict] = None
    ) -> str:
        """生成审查报告"""
        
        # 计算整体评分
        score = self.calculate_score(all_issues, len(file_reviews))
        
        prompt = f"""请根据以下代码审查结果生成详细的审查报告:

项目路径: {project_path}

审查文件数: {len(file_reviews)}
发现问题数: {len(all_issues)}

问题统计:
{self._format_issue_stats(all_issues)}

文件审查详情:
{self._format_file_reviews(file_reviews)}

请生成结构化的审查报告，包括:
1. 总体评价
2. 主要问题（Critical和High级别）
3. 建议改进项
4. 整体评分（100分制）
5. 总结建议

Markdown格式输出。"""
        
        messages = self.get_messages()
        messages.append({
            "role": "user",
            "content": prompt
        })
        
        try:
            report = await self.call_llm(messages)
            return report
        except Exception as e:
            logger.error(f"生成审查报告失败: {e}")
            return self._generate_simple_report(score, all_issues)

    def calculate_score(self, issues: List[Dict[str, Any]], file_count: int) -> float:
        """计算代码评分"""
        
        if file_count == 0:
            return 100.0
        
        # 扣分规则
        deductions = {
            "Critical": 15,
            "High": 8,
            "Medium": 3,
            "Low": 1
        }
        
        total_deduction = 0
        for issue in issues:
            severity = issue.get("severity", "Low")
            total_deduction += deductions.get(severity, 1)
        
        # 基础分100，减去扣分
        score = max(0, 100 - total_deduction)
        
        return score

    def _count_by_severity(self, issues: List[Dict[str, Any]]) -> Dict[str, int]:
        """按严重程度统计问题数"""
        
        counts = {
            "Critical": 0,
            "High": 0,
            "Medium": 0,
            "Low": 0
        }
        
        for issue in issues:
            severity = issue.get("severity", "Low")
            if severity in counts:
                counts[severity] += 1
        
        return counts

    def _format_issue_stats(self, issues: List[Dict[str, Any]]) -> str:
        """格式化问题统计"""
        
        counts = self._count_by_severity(issues)
        
        return f"""- Critical: {counts['Critical']}
- High: {counts['High']}
- Medium: {counts['Medium']}
- Low: {counts['Low']}"""

    def _format_file_reviews(self, file_reviews: List[Dict[str, Any]]) -> str:
        """格式化文件审查结果"""
        
        lines = []
        
        for review in file_reviews:
            file_name = review.get("file", "unknown")
            issue_count = review.get("issue_count", 0)
            
            if issue_count > 0:
                lines.append(f"- {file_name}: {issue_count} 个问题")
            else:
                lines.append(f"- {file_name}: ✓ 通过")
        
        return "\n".join(lines) if lines else "无文件"

    def _generate_simple_report(self, score: float, issues: List[Dict[str, Any]]) -> str:
        """生成简单的审查报告"""
        
        severity_counts = self._count_by_severity(issues)
        
        report = f"""# 代码审查报告

## 总体评分
**{score}/100**

## 问题统计
- Critical: {severity_counts['Critical']}
- High: {severity_counts['High']}
- Medium: {severity_counts['Medium']}
- Low: {severity_counts['Low']}

## 审查结果

"""
        
        if not issues:
            report += "✓ 代码审查通过，未发现重大问题。"
        else:
            report += "### 需要关注的问题\n\n"
            
            critical_issues = [i for i in issues if i.get("severity") == "Critical"]
            high_issues = [i for i in issues if i.get("severity") == "High"]
            
            for issue in critical_issues + high_issues[:5]:
                report += f"""**{issue.get('severity', 'Unknown')}**: {issue.get('description', '')}
- 位置: 第 {issue.get('line', 'N/A')} 行
- 建议: {issue.get('suggestion', '')}

"""
        
        return report

    async def suggest_fixes(
        self,
        issues: List[Dict[str, Any]],
        file_content: str,
        file_type: str
    ) -> str:
        """生成修复建议"""
        
        prompt = f"""请针对以下代码问题，提供修复后的代码:

文件类型: {file_type}

原始代码:
```{file_type}
{file_content[:4000]}
```

问题列表:
{self._format_issues_for_llm(issues)}

请提供修复后的完整代码。只返回代码，不要其他解释。"""
        
        messages = self.get_messages()
        messages.append({
            "role": "user",
            "content": prompt
        })
        
        try:
            return await self.call_llm(messages, max_tokens=4000)
        except Exception as e:
            logger.error(f"生成修复建议失败: {e}")
            return ""

    def _format_issues_for_llm(self, issues: List[Dict[str, Any]]) -> str:
        """格式化问题列表供LLM使用"""
        
        lines = []
        for i, issue in enumerate(issues, 1):
            lines.append(f"""{i}. [{issue.get('severity', '')}] {issue.get('description', '')}
   - 位置: 第 {issue.get('line', 'N/A')} 行
   - 修复建议: {issue.get('suggestion', '')}""")
        
        return "\n".join(lines)
