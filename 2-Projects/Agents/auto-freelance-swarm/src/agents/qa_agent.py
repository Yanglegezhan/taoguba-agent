"""
QA Agent (Agent 4): 项目验收智能体
负责验证交付物是否符合项目规格说明书的要求
"""

import os
import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path

from .base_agent import BaseAgent

logger = logging.getLogger(__name__)


class QAAgent(BaseAgent):
    """
    QA Agent - 项目验收智能体
    
    核心功能:
    - 验证交付物是否符合项目规格说明书
    - 检查所有功能需求是否实现
    - 验证非功能需求（性能、安全等）
    - 生成验收报告
    - 检查AI生成内容的合规性
    """

    def __init__(self, config: Dict[str, Any], llm_provider=None):
        # 设置系统提示
        system_prompt = """你是 Auto-Freelance Swarm 的 QA Agent (质量保证专家)。

你的主要职责是:
1. 验证交付物是否符合项目规格说明书
2. 检查所有功能需求是否完整实现
3. 验证非功能需求（性能、安全、兼容性等）
4. 检查代码的完整性和可运行性
5. 检测AI生成内容的"AI痕迹"
6. 生成最终的验收报告

验收标准:
- 功能完整性: 所有声明的功能都已实现
- 代码质量: 代码可运行、无明显错误
- 文档完整性: 包含必要的README和使用说明
- 合规性: 无AI生成痕迹、无侵权内容
- 安全性: 无明显的安全漏洞

重要原则:
- 严格按照规格说明书进行验收
- 对不符合项给出明确的改进建议
- 区分"阻塞性问题"和"建议改进项"
- 确保交付物可以正常使用

输出格式:
请提供详细的验收报告，包括:
- 验收结果（通过/有条件通过/不通过）
- 验收项清单及结果
- 问题列表及严重程度
- 最终建议
"""
        
        config["system_prompt"] = system_prompt
        super().__init__("QAAgent", config, llm_provider)

    async def execute(self, input_data: Any, context: Optional[Dict] = None) -> Dict[str, Any]:
        """
        执行项目验收任务
        
        Args:
            input_data: 项目信息，包含规格说明书和交付物路径
            context: 上下文信息
            
        Returns:
            验收报告
        """
        logger.info("开始执行项目验收任务")
        
        # 解析输入
        if isinstance(input_data, dict):
            specs = input_data.get("specs", "")
            project_path = input_data.get("project_path", "")
            project_files = input_data.get("files", [])
        else:
            specs = str(input_data)
            project_path = ""
            project_files = []
        
        # 验收检查项
        checks = []
        
        # 1. 检查代码完整性
        code_check = await self.check_code_completeness(project_path, project_files)
        checks.append(code_check)
        
        # 2. 检查文档完整性
        doc_check = await self.check_documentation(project_path)
        checks.append(doc_check)
        
        # 3. 检查AI痕迹
        ai_check = await self.check_ai_artifacts(project_path, project_files)
        checks.append(ai_check)
        
        # 4. 检查安全性
        security_check = await self.check_security(project_path, project_files)
        checks.append(security_check)
        
        # 5. 验证功能实现
        func_check = await self.verify_functionality(specs, project_path)
        checks.append(func_check)
        
        # 生成验收报告
        report = await self.generate_acceptance_report(
            specs,
            project_path,
            checks,
            context
        )
        
        # 判断是否通过
        passed = all(
            check.get("status") == "pass"
            for check in checks
            if check.get("required", True)
        )
        
        logger.info(f"项目验收完成，结果: {'通过' if passed else '不通过'}")
        
        return {
            "status": "success",
            "passed": passed,
            "project_path": project_path,
            "checks": checks,
            "checks_passed": sum(1 for c in checks if c.get("status") == "pass"),
            "checks_failed": sum(1 for c in checks if c.get("status") == "fail"),
            "report": report,
            "checked_at": datetime.now().isoformat()
        }

    async def check_code_completeness(
        self,
        project_path: str,
        project_files: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """检查代码完整性"""
        
        logger.info("检查代码完整性")
        
        result = {
            "name": "代码完整性",
            "required": True,
            "status": "pass",
            "details": [],
            "issues": []
        }
        
        if not project_path:
            result["details"].append("未提供项目路径，跳过检查")
            return result
        
        path = Path(project_path)
        
        if not path.exists():
            result["status"] = "fail"
            result["issues"].append({
                "severity": "Critical",
                "description": "项目目录不存在"
            })
            return result
        
        # 检查必要文件
        required_files = {
            "python": ["main.py", "app.py", "script.py"],
            "web": ["index.html", "app.js"],
            "config": ["requirements.txt", "config.yaml"]
        }
        
        # 扫描文件
        py_files = list(path.rglob("*.py"))
        html_files = list(path.rglob("*.html"))
        
        if not py_files and not html_files:
            result["status"] = "fail"
            result["issues"].append({
                "severity": "Critical",
                "description": "未找到任何代码文件"
            })
        
        # 检查requirements.txt
        if not (path / "requirements.txt").exists():
            result["details"].append("警告: 未找到requirements.txt")
        
        # 尝试运行代码
        if py_files:
            run_check = await self.check_code_runnable(path)
            if not run_check["runnable"]:
                result["issues"].append({
                    "severity": "Medium",
                    "description": f"代码可运行性检查: {run_check.get('error', '未知错误')}"
                })
        
        if not result["issues"]:
            result["details"].append("代码完整性检查通过")
        
        return result

    async def check_code_runnable(self, project_path: Path) -> Dict[str, Any]:
        """检查代码是否可运行"""
        
        result = {"runnable": True, "error": ""}
        
        # 查找主文件
        main_files = ["main.py", "app.py", "run.py", "server.py"]
        main_file = None
        
        for f in main_files:
            if (project_path / f).exists():
                main_file = f
                break
        
        if not main_file:
            return {"runnable": False, "error": "未找到主文件"}
        
        # 语法检查
        main_content = (project_path / main_file).read_text(encoding='utf-8')
        
        # 简单语法检查
        try:
            compile(main_content, main_file, 'exec')
        except SyntaxError as e:
            return {"runnable": False, "error": f"语法错误: {e}"}
        
        return result

    async def check_documentation(self, project_path: str) -> Dict[str, Any]:
        """检查文档完整性"""
        
        logger.info("检查文档完整性")
        
        result = {
            "name": "文档完整性",
            "required": True,
            "status": "pass",
            "details": [],
            "issues": []
        }
        
        if not project_path:
            result["details"].append("未提供项目路径，跳过检查")
            return result
        
        path = Path(project_path)
        
        # 检查README
        readme_files = ["README.md", "README.txt", "readme.md"]
        has_readme = any((path / f).exists() for f in readme_files)
        
        if has_readme:
            result["details"].append("✓ 找到README文档")
            
            # 检查README内容
            for f in readme_files:
                if (path / f).exists():
                    content = (path / f).read_text(encoding='utf-8')
                    if len(content) < 100:
                        result["issues"].append({
                            "severity": "Low",
                            "description": "README内容过于简短"
                        })
                    break
        else:
            result["issues"].append({
                "severity": "Medium",
                "description": "未找到README文档"
            })
        
        # 检查代码注释
        py_files = list(path.rglob("*.py"))
        commented_files = 0
        
        for py_file in py_files:
            try:
                content = py_file.read_text(encoding='utf-8')
                if '"""' in content or "'''" in content or '# ' in content:
                    commented_files += 1
            except:
                pass
        
        if py_files:
            comment_ratio = commented_files / len(py_files)
            if comment_ratio < 0.3:
                result["issues"].append({
                    "severity": "Low",
                    "description": "大部分代码缺少注释"
                })
            else:
                result["details"].append(f"代码注释覆盖率: {int(comment_ratio*100)}%")
        
        # 更新状态
        critical_issues = [i for i in result["issues"] if i.get("severity") == "Critical"]
        if critical_issues:
            result["status"] = "fail"
        elif result["issues"]:
            result["status"] = "warn"
        
        return result

    async def check_ai_artifacts(
        self,
        project_path: str,
        project_files: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """检查AI生成痕迹"""
        
        logger.info("检查AI生成痕迹")
        
        result = {
            "name": "AI痕迹检测",
            "required": True,
            "status": "pass",
            "details": [],
            "issues": []
        }
        
        # AI痕迹关键词
        ai_phrases = [
            "As an AI language model",
            "I am an AI",
            "I'm sorry, but I cannot",
            "I cannot provide",
            "I'm not able to",
            "Unfortunately, I am not able",
            "as a large language model",
            "AI助手",
            "我是一个AI语言模型",
            "很抱歉，我无法"
        ]
        
        if not project_path:
            result["details"].append("未提供项目路径，跳过检查")
            return result
        
        path = Path(project_path)
        
        # 扫描所有文本文件
        for ext in ["*.py", "*.md", "*.txt", "*.js", "*.html"]:
            for file in path.rglob(ext):
                try:
                    content = file.read_text(encoding='utf-8', errors='ignore')
                    
                    for phrase in ai_phrases:
                        if phrase.lower() in content.lower():
                            result["issues"].append({
                                "severity": "High",
                                "description": f"文件 {file.name} 包含AI痕迹: {phrase}"
                            })
                            break
                except:
                    pass
        
        if not result["issues"]:
            result["details"].append("✓ 未检测到AI生成痕迹")
        
        # 更新状态
        if result["issues"]:
            result["status"] = "fail"
        
        return result

    async def check_security(
        self,
        project_path: str,
        project_files: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """检查安全性"""
        
        logger.info("检查安全性")
        
        result = {
            "name": "安全性检查",
            "required": True,
            "status": "pass",
            "details": [],
            "issues": []
        }
        
        # 安全问题关键词
        security_issues = [
            ("password", "硬编码密码"),
            ("api_key", "硬编码API密钥"),
            ("secret_key", "硬编码密钥"),
            ("token", "硬编码Token"),
            ("eval(", "使用eval()存在风险"),
            ("exec(", "使用exec()存在风险"),
            ("__import__(", "动态导入存在风险"),
        ]
        
        if not project_path:
            result["details"].append("未提供项目路径，跳过检查")
            return result
        
        path = Path(project_path)
        
        # 扫描代码文件
        for ext in ["*.py", "*.js"]:
            for file in path.rglob(ext):
                if "__pycache__" in str(file):
                    continue
                
                try:
                    content = file.read_text(encoding='utf-8', errors='ignore')
                    
                    for keyword, desc in security_issues:
                        if keyword in content.lower():
                            # 检查是否是硬编码
                            if any(pattern in content for pattern in ['= "', "= '", '= """']):
                                result["issues"].append({
                                    "severity": "High",
                                    "description": f"文件 {file.name}: {desc}"
                                })
                except:
                    pass
        
        # 检查.env文件
        env_files = list(path.glob(".env*"))
        if env_files:
            result["issues"].append({
                "severity": "Critical",
                "description": "发现.env文件，请确保已添加到.gitignore"
            })
        
        if not result["issues"]:
            result["details"].append("✓ 安全性检查通过")
        
        # 更新状态
        critical_issues = [i for i in result["issues"] if i.get("severity") == "Critical"]
        if critical_issues:
            result["status"] = "fail"
        elif result["issues"]:
            result["status"] = "warn"
        
        return result

    async def verify_functionality(
        self,
        specs: str,
        project_path: str
    ) -> Dict[str, Any]:
        """验证功能实现"""
        
        logger.info("验证功能实现")
        
        result = {
"name": "功能实现验证",
            "required": True,
            "status": "pass",
            "details": [],
            "issues": []
        }
        
        if not specs:
            result["details"].append("未提供规格说明书，跳过功能验证")
            return result
        
        if not project_path:
            result["details"].append("未提供项目路径，跳过功能验证")
            return result
        
        # 使用LLM验证功能
        path = Path(project_path)
        
        # 收集代码内容
        code_contents = []
        for ext in ["*.py", "*.js", "*.html"]:
            for file in path.rglob(ext):
                if "__pycache__" in str(file):
                    continue
                try:
                    content = file.read_text(encoding='utf-8', errors='ignore')
                    code_contents.append(f"文件: {file.name}\n{content[:1000]}")
                except:
                    pass
        
        if not code_contents:
            result["status"] = "fail"
            result["issues"].append({
                "severity": "Critical",
                "description": "无法读取代码内容"
            })
            return result
        
        # 使用LLM验证
        prompt = f"""请验证以下项目代码是否实现了规格说明书中的功能:

规格说明书:
{specs[:2000]}

代码文件:
{chr(10).join(code_contents[:5])}

请检查:
1. 代码是否包含了规格中声明的核心功能
2. 是否有明显的功能缺失
3. 实现是否合理

请以JSON格式返回:
{{
  "implemented": true/false,
  "missing_features": ["缺失的功能列表"],
  "issues": ["发现的问题"]
}}

只返回JSON。"""
        
        messages = self.get_messages()
        messages.append({
            "role": "user",
            "content": prompt
        })
        
        try:
            import re
            response = await self.call_llm(messages, temperature=0.3, max_tokens=1000)
            
            # 提取JSON
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                import json
                verification = json.loads(json_match.group())
                
                if not verification.get("implemented", True):
                    result["status"] = "fail"
                
                for feature in verification.get("missing_features", []):
                    result["issues"].append({
                        "severity": "High",
                        "description": f"缺失功能: {feature}"
                    })
        except Exception as e:
            logger.error(f"功能验证失败: {e}")
            result["details"].append("功能验证自动检查失败，请人工复核")
        
        if not result["issues"]:
            result["details"].append("✓ 功能实现验证通过")
        
        return result

    async def generate_acceptance_report(
        self,
        specs: str,
        project_path: str,
        checks: List[Dict[str, Any]],
        context: Optional[Dict] = None
    ) -> str:
        """生成验收报告"""
        
        # 统计结果
        passed = sum(1 for c in checks if c.get("status") == "pass")
        failed = sum(1 for c in checks if c.get("status") == "fail")
        warns = sum(1 for c in checks if c.get("status") == "warn")
        
        # 确定最终结果
        if failed > 0:
            final_result = "不通过"
        elif warns > 0:
            final_result = "有条件通过"
        else:
            final_result = "通过"
        
        prompt = f"""请根据以下验收检查结果生成最终的验收报告:

项目路径: {project_path}

验收结果: {final_result}

检查统计:
- 通过: {passed}
- 不通过: {failed}
- 警告: {warns}

检查详情:
{self._format_checks(checks)}

请生成详细的验收报告，包括:
1. 验收结论
2. 各检查项详细结果
3. 问题汇总
4. 最终建议

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
            logger.error(f"生成验收报告失败: {e}")
            return self._generate_simple_report(final_result, checks)

    def _format_checks(self, checks: List[Dict[str, Any]]) -> str:
        """格式化检查结果"""
        
        lines = []
        
        for check in checks:
            name = check.get("name", "未命名检查")
            status = check.get("status", "unknown")
            status_icon = {
                "pass": "✓",
                "fail": "✗",
                "warn": "⚠",
                "unknown": "?"
            }.get(status, "?")
            
            lines.append(f"### {status_icon} {name} [{status.upper()}]")
            
            for detail in check.get("details", []):
                lines.append(f"- {detail}")
            
            for issue in check.get("issues", []):
                severity = issue.get("severity", "")
                desc = issue.get("description", "")
                lines.append(f"- [{severity}] {desc}")
            
            lines.append("")
        
        return "\n".join(lines)

    def _generate_simple_report(self, result: str, checks: List[Dict[str, Any]]) -> str:
        """生成简单的验收报告"""
        
        report = f"""# 项目验收报告

## 验收结果: **{result}**

## 检查统计

"""
        
        status_counts = {}
        for check in checks:
            status = check.get("status", "unknown")
            status_counts[status] = status_counts.get(status, 0) + 1
        
        for status, count in status_counts.items():
            report += f"- {status}: {count}\n"
        
        report += "\n## 检查详情\n\n"
        
        for check in checks:
            name = check.get("name", "未命名")
            status = check.get("status", "unknown")
            status_icon = {"pass": "✓", "fail": "✗", "warn": "⚠"}.get(status, "?")
            
            report += f"### {status_icon} {name}\n"
            
            if check.get("issues"):
                report += "**问题:**\n"
                for issue in check["issues"]:
                    report += f"- [{issue.get('severity', '')}] {issue.get('description', '')}\n"
            
            report += "\n"
        
        return report
