"""
Analyst Agent (Agent 1): 项目分析智能体
负责深入分析项目需求，生成结构化的项目规格说明书
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from .base_agent import BaseAgent

logger = logging.getLogger(__name__)


class AnalystAgent(BaseAgent):
    """
    Analyst Agent - 项目分析智能体
    
    核心功能:
    - 深入理解项目需求
    - 识别模糊点和潜在风险
    - 生成结构化的项目规格说明书
    - 提供技术方案建议
    - 评估工作量和时间
    """

    def __init__(self, config: Dict[str, Any], llm_provider=None):
        # 设置系统提示
        system_prompt = """你是 Auto-Freelance Swarm 的 Analyst Agent (项目分析师)。

你的主要职责是:
1. 深入分析客户提供的项目需求
2. 识别需求中的模糊点和不确定之处
3. 生成结构化、详细的项目规格说明书
4. 提供技术方案建议和技术栈选择
5. 评估项目工作量和合理工期
6. 识别潜在风险和注意事项

项目规格说明书应当包含:
- 项目概述 (背景、目标、范围)
- 功能需求清单 (详细的功能点列表)
- 非功能需求 (性能、安全、兼容性等)
- 技术方案建议 (推荐的技术栈)
- 工作量评估 (人/天或工时)
- 风险评估 (潜在问题和应对措施)
- 验收标准 (如何判断项目完成)

重要原则:
- 需求不明确时，明确指出并建议澄清问题
- 考虑技术的可行性和复杂度
- 提供多种技术方案选择（如果适用）
- 实事求是地评估工作量和工期
"""
        
        config["system_prompt"] = system_prompt
        super().__init__("AnalystAgent", config, llm_provider)

    async def execute(self, input_data: Any, context: Optional[Dict] = None) -> Dict[str, Any]:
        """
        执行项目分析任务
        
        Args:
            input_data: 项目信息或需求描述
            context: 上下文信息
            
        Returns:
            项目分析报告
        """
        logger.info("开始执行项目分析任务")
        
        # 提取项目信息
        if isinstance(input_data, dict):
            project_info = input_data
        else:
            project_info = {"description": str(input_data)}
        
        # 生成项目分析报告
        report = await self.analyze_project(project_info, context)
        
        # 提取关键信息
        extracted_info = await self.extract_key_info(report)
        
        logger.info("项目分析完成")
        
        return {
            "status": "success",
            "project_info": project_info,
            "analysis_report": report,
            "extracted_info": extracted_info,
            "analyzed_at": datetime.now().isoformat()
        }

    async def analyze_project(
        self,
        project_info: Dict[str, Any],
        context: Optional[Dict] = None
    ) -> str:
        """
        分析项目并生成规格说明书
        
        Args:
            project_info: 项目基本信息
            context: 上下文信息
            
        Returns:
            Markdown 格式的项目规格说明书
        """
        
        description = project_info.get("description", "")
        title = project_info.get("title", "未命名项目")
        budget = project_info.get("budget", "未标注")
        
        prompt = f"""请为以下项目生成详细的项目规格说明书:

项目名称: {title}
项目预算: {budget}
项目描述:
{description}

请按照以下格式生成项目规格说明书:

---

# {title} - 项目规格说明书

## 1. 项目概述

### 1.1 项目背景
(项目是如何产生的，解决了什么痛点)

### 1.2 项目目标
(项目要达成的主要目标)

### 1.3 项目范围
(明确项目包含和不包含的内容)

---

## 2. 功能需求

### 2.1 核心功能列表
| 功能编号 | 功能名称 | 功能描述 | 优先级 |
|---------|---------|---------|--------|
| F01 | | | P0 |
| F02 | | | P1 |

### 2.2 功能详细描述
(每个核心功能的详细描述，包括输入、处理、输出)

---

## 3. 非功能需求

### 3.1 性能需求
- 响应时间:
- 并发用户:
- 数据处理量:

### 3.2 安全需求
- 认证授权:
- 数据加密:
- 防护措施:

### 3.3 兼容性需求
- 浏览器兼容:
- 移动端适配:
- 第三方集成:

---

## 4. 技术方案

### 4.1 推荐技术栈
| 层级 | 技术选择 | 理由 |
|-----|---------|------|
| 前端 | | |
| 后端 | | |
| 数据库 | | |
| 部署 | | |

### 4.2 系统架构
(简化的架构图或描述)

---

## 5. 工作量评估

### 5.1 功能点评估
| 模块 | 功能点 | 预估工时 |
|-----|-------|---------|
| 合计 | | |

### 5.2 总工作量
- 预估总工时: 
- 建议工期: 

---

## 6. 风险评估

### 6.1 潜在风险
| 风险描述 | 可能性 | 影响 | 应对措施 |
|---------|-------|-----|---------|
| | 高/中/低 | 高/中/低 | |

---

## 7. 验收标准

### 7.1 功能验收
- [ ] 
- [ ] 

### 7.2 交付物
- 源代码
- 文档
- 部署说明

---

请根据实际项目情况进行详细分析和填写。"""
        
        messages = self.get_messages()
        messages.append({
            "role": "user",
            "content": prompt
        })
        
        try:
            report = await self.call_llm(messages)
            return report
        except Exception as e:
            logger.error(f"生成项目分析报告失败: {e}")
            return self._generate_simple_report(project_info)

    async def extract_key_info(self, report: str) -> Dict[str, Any]:
        """从分析报告中提取关键信息"""
        
        prompt = f"""请从以下项目分析报告中提取关键信息，以JSON格式返回:

{report}

请提取以下字段并以JSON格式返回:
- estimated_hours: 预估工时（数字）
- suggested_duration: 建议工期（天）
- tech_stack: 技术栈（数组）
- key_risks: 主要风险（数组）
- core_features: 核心功能列表（数组）
- budget_estimate: 预算建议（字符串）

只返回JSON，不要其他内容。"""
        
        messages = self.get_messages()
        messages.append({
            "role": "user",
            "content": prompt
        })
        
        try:
            import re
            response = await self.call_llm(messages)
            
            # 提取JSON
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                import json
                return json.loads(json_match.group())
        except Exception as e:
            logger.error(f"提取关键信息失败: {e}")
        
        # 返回默认值
        return {
            "estimated_hours": 0,
            "suggested_duration": 0,
            "tech_stack": [],
            "key_risks": [],
            "core_features": [],
            "budget_estimate": "待评估"
        }

    async def clarify_requirements(
        self,
        unclear_points: List[str]
    ) -> List[Dict[str, Any]]:
        """
        生成需求澄清问题列表
        
        Args:
            unclear_points: 不明确的问题点
            
        Returns:
            澄清问题列表
        """
        
        prompt = f"""以下项目需求存在不明确之处，请生成专业的澄清问题列表:

不明确的问题点:
{chr(10).join([f"- {point}" for point in unclear_points])}

请为每个问题点生成1-2个具体的澄清问题，问题要专业、具体，有助于明确项目范围。"""
        
        messages = self.get_messages()
        messages.append({
            "role": "user",
            "content": prompt
        })
        
        try:
            response = await self.call_llm(messages)
            return response
        except Exception as e:
            logger.error(f"生成澄清问题失败: {e}")
            return []

    def _generate_simple_report(self, project_info: Dict[str, Any]) -> str:
        """生成简单的项目分析报告（当LLM调用失败时）"""
        
        return f"""# {project_info.get('title', '项目')} - 项目分析报告

## 项目概述

项目描述: {project_info.get('description', '无描述')}

## 初步评估

由于无法获取详细的项目信息，以下是初步评估:

- 预算范围: {project_info.get('budget', '待确定')}
- 项目复杂度: 待评估
- 建议工期: 需进一步沟通

## 待处理

需要进一步了解以下信息:
1. 详细的功能需求
2. 技术栈偏好
3. 交付时间要求
4. 验收标准

## 建议

请提供更详细的项目需求文档，以便进行准确的分析和评估。
"""

    async def compare_technologies(
        self,
        options: List[Dict[str, str]]
    ) -> str:
        """
        比较技术方案
        
        Args:
            options: 技术方案选项列表
            
        Returns:
            技术对比分析
        """
        
        prompt = f"""请对比分析以下技术方案:

{chr(10).join([f"- {opt.get('name', '方案')}: {opt.get('description', '')}" for opt in options])}

请从以下维度进行对比:
1. 学习成本
2. 开发效率
3. 性能表现
4. 维护成本
5. 社区生态

并给出最终推荐。"""
        
        messages = self.get_messages()
        messages.append({
            "role": "user",
            "content": prompt
        })
        
        try:
            return await self.call_llm(messages)
        except Exception as e:
            logger.error(f"技术对比失败: {e}")
            return "技术对比分析失败"
