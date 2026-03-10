"""
LLM 干货提取器
使用大语言模型智能提取评论中的干货和预案
基于 OpenAI 兼容接口（与 index_replay_agent 相同）
"""
import os
import json
import ssl
import urllib3
from typing import List, Dict
from urllib3.exceptions import InsecureRequestWarning
from datetime import datetime

from openai import OpenAI
import httpx

# 修复网络问题
urllib3.disable_warnings(InsecureRequestWarning)


# 预设的 base_url 配置
PROVIDER_BASE_URLS = {
    "minimax": "https://api.minimaxi.com/v1",  # OpenAI 兼容接口
    "zhipu": "https://open.bigmodel.cn/api/paas/v4",
    "deepseek": "https://api.deepseek.com/v1",
    "qwen": "https://dashscope.aliyuncs.com/compatible-mode/v1",
    "kimi": "https://api.moonshot.cn/v1",
}


class LLMExtractor:
    """使用 LLM 提取干货 - OpenAI 兼容接口"""

    def __init__(self):
        self.provider = os.getenv("LLM_PROVIDER", "minimax")
        self.api_key = os.getenv("LLM_API_KEY", "")
        self.model = os.getenv("LLM_MODEL", "MiniMax-M2.5")
        self.base_url = PROVIDER_BASE_URLS.get(self.provider, "https://api.minimaxi.com/v1")
        self.max_tokens = int(os.getenv("LLM_MAX_TOKENS", "190000"))  # 默认190000

        # 创建 httpx 客户端（禁用 SSL 验证，无超时限制）
        self.http_client = httpx.Client(verify=False, timeout=None)

        # 创建 OpenAI 客户端
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            timeout=60,
            http_client=self.http_client,
        )

    def extract_ganhuo(self, blogger_name: str, post_title: str, comments: List[Dict],
                       time_range: str, batch_size: int = 30) -> Dict:
        """
        提取单个博主的干货

        Args:
            blogger_name: 博主名
            post_title: 帖子标题
            comments: 评论列表
            time_range: 时间范围
            batch_size: 每批处理的评论数量，默认30条

        Returns:
            提取结果
        """
        if not comments:
            return {"ganhuo_points": [], "yuan_points": [], "summary": "无评论内容"}

        # 如果评论数量不多，直接处理
        if len(comments) <= batch_size:
            return self._extract_single_batch(blogger_name, post_title, comments, time_range)

        # 分批处理
        print(f"      评论较多({len(comments)}条)，分批处理...")
        all_ganhuo = []
        all_yuan = []
        summaries = []

        for i in range(0, len(comments), batch_size):
            batch = comments[i:i + batch_size]
            batch_num = i // batch_size + 1
            total_batches = (len(comments) + batch_size - 1) // batch_size
            print(f"        处理第 {batch_num}/{total_batches} 批({len(batch)}条)...")

            result = self._extract_single_batch(
                blogger_name, post_title, batch, time_range,
                batch_info=f"第{batch_num}/{total_batches}批"
            )

            all_ganhuo.extend(result.get("ganhuo_points", []))
            all_yuan.extend(result.get("yuan_points", []))
            if result.get("summary"):
                summaries.append(result["summary"])

        # 合并总结
        final_summary = self._merge_summaries(summaries, blogger_name) if summaries else ""

        return {
            "ganhuo_points": all_ganhuo,
            "yuan_points": all_yuan,
            "summary": final_summary
        }

    def extract_post_ganhuo(self, blogger_name: str, post_title: str,
                            post_content: str, time_range: str) -> Dict:
        """
        提取主贴内容的干货

        Args:
            blogger_name: 博主名
            post_title: 帖子标题
            post_content: 主贴内容
            time_range: 时间范围

        Returns:
            提取结果
        """
        if not post_content or len(post_content.strip()) < 10:
            return {"ganhuo_points": [], "yuan_points": [], "summary": ""}

        # 构建输入文本
        input_text = f"""博主: {blogger_name}
帖子标题: {post_title}
时间范围: {time_range}

主贴内容:
{"=" * 50}

{post_content}
"""

        # 构建 system prompt
        system_prompt = f"""你是一位专业的股票短线交易分析助手，擅长从淘股吧博主的主贴中提取有价值的"干货"和"预案"。

## 任务
请深入分析 {blogger_name} 在 {time_range} 发布的主贴内容，提取详细内容。

重要原则：
- **不要限制条数** - 有多少有价值的干货就提取多少，无上限
- **宁多勿少** - 只要是有价值的观点都要提取，不要遗漏
- **全面覆盖** - 覆盖交易逻辑、买卖点、情绪、板块、风控等所有方面

### 1. 干货要点 (ganhuo_points)
每条干货需要包含：
- **核心观点**：具体是什么交易逻辑或思路
- **详细解释**：为什么会有这个判断，依据是什么
- **适用场景**：在什么情况下可以使用这个思路
- **具体例子**：如果有具体个股或案例，要详细说明

干货类型（但不限于）：
- 交易核心逻辑和思路（详细阐述）
- 买卖点判断依据（具体条件）
- 情绪周期分析（当前阶段特征）
- 板块和个股分析（详细理由）
- 风险控制原则（具体操作）
- 预期管理（符合/超预期/不及预期的处理）

要求：
- 只提取有实质内容的观点，去掉客套话、问候、表情
- 每条干货要具体、有深度、有操作性
- 保持原文的核心意思，但用自己的话详细表达
- **不要限制条数，有多少提取多少**

### 2. 预案要点 (yuan_points)
每条预案需要包含：
- **策略名称**：这是什么策略
- **适用条件**：什么情况下执行
- **具体操作**：买入/卖出/持仓的具体动作
- **目标标的**：具体关注哪些个股或板块
- **风险控制**：止损位、仓位控制、失败应对方案
- **预期收益**：合理预期是什么

要求：
- **不要限制条数，有多少提取多少**
- 每条预案都要完整、可执行

### 3. 总结 (summary)
用 2-3 句话简要概括主贴的核心观点。

## 输出格式
必须以 JSON 格式输出，全部使用中文：

{{
    "ganhuo_points": [
        "【核心观点】详细阐述...",
        ...
    ],
    "yuan_points": [
        "【策略名称】详细说明...",
        ...
    ],
    "summary": "总结文本"
}}

## 注意事项
- 只提取该时间段内的内容
- 干货要具体、详细、有深度、有操作性
- 预案要明确，有条件、有动作、有风控
- 如果某类内容没有，对应数组留空
- **全部使用中文输出，不要出现英文**
"""

        # 调用 LLM
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": input_text}
                ],
                temperature=0.3
            )

            content = response.choices[0].message.content
            return self._parse_response(content)

        except Exception as e:
            print(f"  主贴 LLM 调用失败: {e}")
            return {
                "ganhuo_points": [],
                "yuan_points": [],
                "summary": ""
            }

    def _extract_single_batch(self, blogger_name: str, post_title: str,
                              comments: List[Dict], time_range: str,
                              batch_info: str = "") -> Dict:
        """处理单批评论"""
        # 构建输入文本
        input_text = self._build_input_text(blogger_name, post_title, comments, time_range, batch_info)

        # 构建 system prompt（批次模式）
        if batch_info:
            system_prompt = self._build_batch_prompt(blogger_name, time_range, batch_info)
        else:
            system_prompt = self._build_system_prompt(blogger_name, time_range)

        # 调用 LLM
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": input_text}
                ],
                temperature=0.3
                # 不设置max_tokens，让模型自己决定输出长度
                # 不设置timeout，等待模型完成
            )

            content = response.choices[0].message.content
            return self._parse_response(content)

        except Exception as e:
            print(f"  LLM 调用失败 ({batch_info}): {e}")
            return {
                "ganhuo_points": [],
                "yuan_points": [],
                "summary": f""
            }

    def _merge_summaries(self, summaries: List[str], blogger_name: str) -> str:
        """合并多个批次的总结"""
        if not summaries:
            return ""
        if len(summaries) == 1:
            return summaries[0]

        # 过滤掉提取失败的总结
        valid_summaries = [s for s in summaries if s and s != "提取失败"]
        if not valid_summaries:
            return ""
        if len(valid_summaries) == 1:
            return valid_summaries[0]

        # 使用 LLM 合并总结
        merge_prompt = f"""请将以下关于 {blogger_name} 的多个时段分析总结合并成一个连贯的总结：

{'\n\n'.join([f"总结{i+1}: {s}" for i, s in enumerate(valid_summaries)])}

请用 3-5 句话概括核心观点，去除重复内容。全部使用中文输出。"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": merge_prompt}],
                temperature=0.3,
                max_tokens=500
            )
            return response.choices[0].message.content
        except:
            # 如果合并失败，返回第一个有效总结
            return valid_summaries[0]

    def _build_batch_prompt(self, blogger_name: str, time_range: str, batch_info: str) -> str:
        """构建批次处理的 prompt"""
        return f"""你是一位专业的股票短线交易分析助手。这是 {blogger_name} 在 {time_range} 的评论中的 {batch_info}。

## 任务
请分析这批评论，提取干货要点和预案要点。

### 1. 干货要点 (ganhuo_points)
提取有价值的交易观点、逻辑、判断依据等。宁多勿少。

### 2. 预案要点 (yuan_points)
提取具体的操作策略、买入卖出条件、风险控制方案等。

### 3. 总结 (summary)
简要概括这批评论的核心观点（2-3句话）。

## 输出格式
必须以 JSON 格式输出，全部使用中文：

{{
    "ganhuo_points": ["干货1", "干货2", ...],
    "yuan_points": ["预案1", "预案2", ...],
    "summary": "总结文本"
}}

注意：这只是整体评论的一部分，所以总结只针对这批评论。"""

    def _build_input_text(self, blogger_name: str, post_title: str,
                          comments: List[Dict], time_range: str, batch_info: str = "") -> str:
        """构建输入文本"""
        lines = [
            f"博主: {blogger_name}",
            f"帖子标题: {post_title}",
            f"时间范围: {time_range}",
        ]
        if batch_info:
            lines.append(f"批次: {batch_info}")
        lines.extend([
            "",
            "评论内容:",
            "=" * 50,
            ""
        ])

        for i, comment in enumerate(comments, 1):
            author = comment.get('author', '未知')
            content = comment.get('content', '')
            time_str = comment.get('time_str', '')

            # 清理内容
            content = content.strip()
            if len(content) < 5:
                continue

            lines.append(f"[{i}] 作者: {author}")
            if time_str:
                lines.append(f"    时间: {time_str}")
            lines.append(f"    内容: {content}")
            lines.append("")

        return '\n'.join(lines)

    def _build_system_prompt(self, blogger_name: str, time_range: str) -> str:
        """构建 system prompt"""
        return f"""你是一位专业的股票短线交易分析助手，擅长从淘股吧博主的评论中提取有价值的"干货"和"预案"。

## 任务
请深入分析 {blogger_name} 在 {time_range} 的评论内容，提取详细内容。

重要原则：
- **不要限制条数** - 有多少有价值的干货就提取多少，无上限
- **宁多勿少** - 只要是有价值的观点都要提取，不要遗漏
- **全面覆盖** - 覆盖交易逻辑、买卖点、情绪、板块、风控等所有方面

### 1. 干货要点 (ganhuo_points)
每条干货需要包含：
- **核心观点**：具体是什么交易逻辑或思路
- **详细解释**：为什么会有这个判断，依据是什么
- **适用场景**：在什么情况下可以使用这个思路
- **具体例子**：如果有具体个股或案例，要详细说明

干货类型（但不限于）：
- 交易核心逻辑和思路（详细阐述）
- 买卖点判断依据（具体条件）
- 情绪周期分析（当前阶段特征）
- 板块和个股分析（详细理由）
- 风险控制原则（具体操作）
- 盘口语言解读（主力行为分析）
- 预期管理（符合/超预期/不及预期的处理）
- 辨识度判断标准（如何区分龙头杂毛）
- 资金流向分析
- 时间节点判断（变盘日、回暖日等）
- 仓位管理策略
- 套利模式总结

要求：
- 只提取有实质内容的观点，去掉客套话、问候、表情
- 每条干货要具体、有深度、有操作性
- 保持原文的核心意思，但用自己的话详细表达
- 如有具体个股，要说明逻辑和预期
- **不要限制条数，有多少提取多少**

### 2. 预案要点 (yuan_points)
每条预案需要包含：
- **策略名称**：这是什么策略
- **适用条件**：什么情况下执行
- **具体操作**：买入/卖出/持仓的具体动作
- **目标标的**：具体关注哪些个股或板块
- **风险控制**：止损位、仓位控制、失败应对方案
- **预期收益**：合理预期是什么

预案类型（但不限于）：
- 明日操作策略（详细计划）
- 具体个股预案（买入卖出条件）
- 开仓/平仓条件（触发条件）
- 风险应对方案（各种情况的预案）
- 板块轮动预案（轮动时的应对）
- 情绪周期应对（不同周期的策略）
- 大盘环境应对（不同大盘位置的策略）

要求：
- **不要限制条数，有多少提取多少**
- 每条预案都要完整、可执行

### 3. 总结 (summary)
用 3-5 句话详细概括：
- 该时段市场整体情绪如何
- 博主的核心观点是什么
- 关键个股/板块有哪些
- 明日操作的关键点是什么
- 风险提示

## 输出格式
必须以 JSON 格式输出：

{{
    "ganhuo_points": [
        "【核心观点】详细阐述这个干货点，包括判断依据、适用场景、具体例子等，内容要充实详细...",
        "【核心观点】详细阐述...",
        ...
        // 继续添加，无上限
    ],
    "yuan_points": [
        "【策略名称】详细说明适用条件、具体操作、目标标的、风险控制、预期收益等内容...",
        "【策略名称】详细说明...",
        ...
        // 继续添加，无上限
    ],
    "summary": "详细总结文本（3-5句话），涵盖市场情绪、核心观点、关键标的、明日要点和风险提示"
}}

## 注意事项
- 只提取该时间段内的内容
- 干货要具体、详细、有深度、有操作性
- 预案要明确，有条件、有动作、有风控
- 如果某类内容没有，对应数组留空
- 保持原文的核心意思，用自己的话详细表达
- **不要省略细节，越详细越好**
- **不要限制条数，有多少提取多少**
- 如有具体个股，必须说明完整逻辑
- **全部使用中文输出，不要出现英文**
"""

    def _parse_response(self, response: str) -> Dict:
        """解析 LLM 响应"""
        # 清理响应内容
        response = response.strip()

        # 如果响应为空
        if not response:
            print("  LLM 返回为空")
            return {"ganhuo_points": [], "yuan_points": [], "summary": "提取失败"}

        try:
            # 尝试直接解析 JSON
            result = json.loads(response)
            return {
                "ganhuo_points": result.get("ganhuo_points", []),
                "yuan_points": result.get("yuan_points", []),
                "summary": result.get("summary", "")
            }
        except json.JSONDecodeError as e:
            # 如果直接解析失败，尝试提取 JSON 部分
            try:
                import re
                # 查找 JSON 代码块
                json_match = re.search(r'```(?:json)?\s*(.*?)\s*```', response, re.DOTALL)
                if json_match:
                    json_str = json_match.group(1).strip()
                    result = json.loads(json_str)
                    return {
                        "ganhuo_points": result.get("ganhuo_points", []),
                        "yuan_points": result.get("yuan_points", []),
                        "summary": result.get("summary", "")
                    }

                # 尝试直接找 JSON 对象（匹配最外层的大括号）
                # 使用更智能的方式找到匹配的括号
                start = response.find('{')
                if start != -1:
                    brace_count = 0
                    for i, char in enumerate(response[start:], start):
                        if char == '{':
                            brace_count += 1
                        elif char == '}':
                            brace_count -= 1
                            if brace_count == 0:
                                # 找到匹配的闭合括号
                                json_str = response[start:i+1]
                                result = json.loads(json_str)
                                return {
                                    "ganhuo_points": result.get("ganhuo_points", []),
                                    "yuan_points": result.get("yuan_points", []),
                                    "summary": result.get("summary", "")
                                }
            except Exception as e2:
                print(f"  解析 LLM 响应失败: {e2}")
                # 打印前200字符用于调试
                preview = response[:200].replace('\n', ' ')
                print(f"  响应预览: {preview}...")

        # 解析失败，返回空结果
        return {
            "ganhuo_points": [],
            "yuan_points": [],
            "summary": "提取失败"
        }

    def merge_blogger_reports(self, blogger_reports: Dict[str, Dict],
                              time_range: str) -> str:
        """整合所有博主的报告"""
        lines = [
            f"# 淘股吧 {time_range} 干货汇总",
            "",
            f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "",
            "---",
            ""
        ]

        # 统计
        total_ganhuo = sum(len(r["ganhuo_points"]) for r in blogger_reports.values())
        total_yuan = sum(len(r["yuan_points"]) for r in blogger_reports.values())

        lines.extend([
            "## 统计",
            "",
            f"- 博主数: {len(blogger_reports)}",
            f"- 干货要点: {total_ganhuo}条",
            f"- 预案要点: {total_yuan}条",
            "",
            "---",
            ""
        ])

        # 各博主详情
        for blogger_name, report in blogger_reports.items():
            lines.extend([
                f"## {blogger_name}",
                ""
            ])

            if report["summary"]:
                lines.extend([
                    f"**总结**: {report['summary']}",
                    ""
                ])

            if report["ganhuo_points"]:
                lines.extend([
                    "### 干货要点",
                    ""
                ])
                for i, point in enumerate(report["ganhuo_points"], 1):
                    lines.append(f"{i}. {point}")
                lines.append("")

            if report["yuan_points"]:
                lines.extend([
                    "### 预案要点",
                    ""
                ])
                for i, point in enumerate(report["yuan_points"], 1):
                    lines.append(f"{i}. {point}")
                lines.append("")

            lines.extend([
                "---",
                ""
            ])

        return '\n'.join(lines)

    def merge_blogger_reports_v2(self, blogger_reports: Dict[str, Dict],
                                  time_range: str) -> str:
        """整合所有博主的报告（V2版本 - 分开显示主贴和评论）"""
        lines = [
            f"# 淘股吧 {time_range} 干货汇总",
            "",
            f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "",
            "---",
            ""
        ]

        # 统计
        total_post_ganhuo = sum(len(r.get("post_ganhuo_points", [])) for r in blogger_reports.values())
        total_post_yuan = sum(len(r.get("post_yuan_points", [])) for r in blogger_reports.values())
        total_comment_ganhuo = sum(len(r.get("comment_ganhuo_points", [])) for r in blogger_reports.values())
        total_comment_yuan = sum(len(r.get("comment_yuan_points", [])) for r in blogger_reports.values())

        lines.extend([
            "## 统计",
            "",
            f"- 博主数: {len(blogger_reports)}",
            f"- 主贴干货: {total_post_ganhuo}条",
            f"- 主贴预案: {total_post_yuan}条",
            f"- 评论干货: {total_comment_ganhuo}条",
            f"- 评论预案: {total_comment_yuan}条",
            "",
            "---",
            ""
        ])

        # 各博主详情
        for blogger_name, report in blogger_reports.items():
            lines.extend([
                f"## {blogger_name}",
                ""
            ])

            if report.get("summary"):
                lines.extend([
                    f"**总结**: {report['summary']}",
                    ""
                ])

            # 1. 主贴干货
            post_ganhuo = report.get("post_ganhuo_points", [])
            post_yuan = report.get("post_yuan_points", [])

            if post_ganhuo or post_yuan:
                lines.extend([
                    "### 📄 主贴干货",
                    ""
                ])

                if post_ganhuo:
                    lines.extend([
                        "**核心观点**",
                        ""
                    ])
                    for i, point in enumerate(post_ganhuo, 1):
                        lines.append(f"{i}. {point}")
                    lines.append("")

                if post_yuan:
                    lines.extend([
                        "**操作策略**",
                        ""
                    ])
                    for i, point in enumerate(post_yuan, 1):
                        lines.append(f"{i}. {point}")
                    lines.append("")

            # 2. 评论干货
            comment_ganhuo = report.get("comment_ganhuo_points", [])
            comment_yuan = report.get("comment_yuan_points", [])

            if comment_ganhuo or comment_yuan:
                lines.extend([
                    "### 💬 评论干货",
                    ""
                ])

                if comment_ganhuo:
                    lines.extend([
                        "**核心观点**",
                        ""
                    ])
                    for i, point in enumerate(comment_ganhuo, 1):
                        lines.append(f"{i}. {point}")
                    lines.append("")

                if comment_yuan:
                    lines.extend([
                        "**操作策略**",
                        ""
                    ])
                    for i, point in enumerate(comment_yuan, 1):
                        lines.append(f"{i}. {point}")
                    lines.append("")

            lines.extend([
                "---",
                ""
            ])

        return '\n'.join(lines)
