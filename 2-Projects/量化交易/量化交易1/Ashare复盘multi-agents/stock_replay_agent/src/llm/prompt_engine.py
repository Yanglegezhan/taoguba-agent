"""
提示词引擎

管理和组装 LLM 提示词
"""
import os
from typing import Dict, Any, List, Optional
from pathlib import Path


class PromptEngine:
    """提示词引擎"""

    def __init__(self, prompts_dir: Optional[str] = None):
        """
        初始化提示词引擎

        Args:
            prompts_dir: 提示词模板目录，默认为项目根目录下的prompts
        """
        if prompts_dir is None:
            # 默认使用项目根目录下的prompts目录
            current_dir = Path(__file__).resolve().parent.parent.parent
            prompts_dir = current_dir / "prompts"

        self.prompts_dir = Path(prompts_dir)
        self._cache: Dict[str, str] = {}

    def load_prompt(self, category: str, name: str = "system") -> str:
        """
        加载提示词模板

        Args:
            category: 类别目录，如 "consecutive_board", "trend_stock"
            name: 提示词文件名，默认为 "system"

        Returns:
            提示词内容
        """
        cache_key = f"{category}/{name}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        prompt_file = self.prompts_dir / category / f"{name}.txt"

        if not prompt_file.exists():
            # 尝试不加.txt后缀
            prompt_file = self.prompts_dir / category / name

        if not prompt_file.exists():
            raise FileNotFoundError(
                f"提示词文件不存在: {prompt_file}"
            )

        content = prompt_file.read_text(encoding="utf-8").strip()
        self._cache[cache_key] = content

        return content

    def load_example(self, category: str, example_name: str) -> str:
        """
        加载示例数据

        Args:
            category: 类别目录
            example_name: 示例文件名

        Returns:
            示例内容
        """
        cache_key = f"{category}/examples/{example_name}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        example_file = self.prompts_dir / category / "examples" / example_name

        if not example_file.exists():
            raise FileNotFoundError(
                f"示例文件不存在: {example_file}"
            )

        content = example_file.read_text(encoding="utf-8").strip()
        self._cache[cache_key] = content

        return content

    def format_prompt(
        self,
        category: str,
        name: str,
        variables: Dict[str, Any]
    ) -> str:
        """
        格式化提示词模板

        Args:
            category: 类别目录
            name: 提示词文件名
            variables: 变量字典

        Returns:
            格式化后的提示词
        """
        template = self.load_prompt(category, name)
        return template.format(**variables)

    def build_consecutive_board_analysis(
        self,
        stock_info: Dict[str, Any],
        consecutive_data: Dict[str, Any],
        special_actions: Dict[str, Any],
        sector_comparison: Optional[Dict[str, Any]] = None,
    ) -> List[str]:
        """
        构建连板分析提示词

        Args:
            stock_info: 个股信息
            consecutive_data: 连板数据
            special_actions: 特殊动作检测结果
            sector_comparison: 同题材对比（可选）

        Returns:
            提示词消息列表
        """
        # 加载系统提示词
        system_prompt = self.load_prompt("consecutive_board", "system")

        # 加载分析提示词
        analysis_template = self.load_prompt("consecutive_board", "analysis")

        # 格式化分析提示词
        variables = {
            "stock_code": stock_info.get("stock_code", ""),
            "stock_name": stock_info.get("stock_name", ""),
            "consecutive_days": stock_info.get("consecutive_days", 0),
            "turnover": stock_info.get("turnover", 0),
            "main_net_inflow": stock_info.get("main_net_inflow", 0),
            "concepts": ", ".join(stock_info.get("concepts", [])),
        }

        # 添加连板梯队信息
        if "ladder" in consecutive_data:
            variables["max_consecutive"] = consecutive_data.get("max_consecutive", 0)
            variables["max_consecutive_stocks"] = consecutive_data.get("max_consecutive_stocks", "")

        # 添加特殊动作
        special_actions_text = []
        for action_type, action_data in special_actions.items():
            if action_data.get("detected"):
                special_actions_text.append(
                    f"{action_type}: {action_data.get('description', '')}"
                )
        variables["special_actions"] = "\n".join(special_actions_text) if special_actions_text else "无"

        # 添加同题材对比
        if sector_comparison:
            variables["sector"] = sector_comparison.get("sector", "未知")
            variables["same_concept_count"] = sector_comparison.get("same_concept_count", 0)
            variables["is_leader"] = "是" if sector_comparison.get("is_leader") else "否"
            variables["premium_level"] = sector_comparison.get("premium_level", "持平")

        analysis_prompt = analysis_template.format(**variables)

        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": analysis_prompt},
        ]

    def build_trend_stock_analysis(
        self,
        stock_info: Dict[str, Any],
        trend_pattern: Dict[str, Any],
        volume_price: Dict[str, Any],
        moving_average: Dict[str, Any],
    ) -> List[str]:
        """
        构建趋势股分析提示词

        Args:
            stock_info: 个股信息
            trend_pattern: 趋势形态
            volume_price: 量价关系
            moving_average: 均线系统

        Returns:
            提示词消息列表
        """
        # 加载系统提示词
        system_prompt = self.load_prompt("trend_stock", "system")

        # 加载分析提示词
        analysis_template = self.load_prompt("trend_stock", "analysis")

        # 格式化分析提示词
        variables = {
            "stock_code": stock_info.get("stock_code", ""),
            "stock_name": stock_info.get("stock_name", ""),
            "pattern_type": trend_pattern.get("pattern_type", "未知"),
            "pattern_stage": trend_pattern.get("stage", ""),
            "pattern_strength": trend_pattern.get("strength", 0),
            "volume_price_relation": volume_price.get("relationship", "未知"),
            "volume_trend": volume_price.get("volume_trend", ""),
            "price_trend": volume_price.get("price_trend", ""),
        }

        # 添加均线信息
        if "mas" in moving_average:
            variables["ma_alignment"] = moving_average.get("alignment", "")
            variables["ma5"] = moving_average["mas"].get("ma5", 0)
            variables["ma20"] = moving_average["mas"].get("ma20", 0)

        analysis_prompt = analysis_template.format(**variables)

        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": analysis_prompt},
        ]

    def build_critic_evaluation(
        self,
        agent_type: str,
        stock_info: Dict[str, Any],
        analysis_result: Dict[str, Any],
    ) -> List[str]:
        """
        构建Critic评估提示词

        Args:
            agent_type: 被评估的Agent类型
            stock_info: 个股信息
            analysis_result: 分析结果

        Returns:
            提示词消息列表
        """
        # 加载系统提示词
        system_prompt = self.load_prompt("critic", "system")

        # 加载分析提示词
        analysis_template = self.load_prompt("critic", "analysis")

        # 格式化分析提示词
        variables = {
            "agent_type": agent_type,
            "stock_code": stock_info.get("stock_code", ""),
            "stock_name": stock_info.get("stock_name", ""),
            "analysis_result": str(analysis_result),
        }

        analysis_prompt = analysis_template.format(**variables)

        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": analysis_prompt},
        ]

    def build_synthesis_analysis(
        self,
        consecutive_board_results: List[Dict[str, Any]],
        trend_stock_results: List[Dict[str, Any]],
        critic_evaluations: List[Dict[str, Any]],
        external_context: Optional[Dict[str, Any]] = None,
    ) -> List[str]:
        """
        构建综合分析提示词

        Args:
            consecutive_board_results: 连板分析结果
            trend_stock_results: 趋势股分析结果
            critic_evaluations: Critic评估结果
            external_context: 外部报告上下文（可选）

        Returns:
            提示词消息列表
        """
        # 加载系统提示词
        system_prompt = self.load_prompt("synthesis", "system")

        # 加载分析提示词
        analysis_template = self.load_prompt("synthesis", "analysis")

        # 格式化分析提示词
        variables = {
            "consecutive_board_count": len(consecutive_board_results),
            "trend_stock_count": len(trend_stock_results),
            "critic_evaluation_count": len(critic_evaluations),
        }

        # 添加连板分析摘要
        if consecutive_board_results:
            variables["consecutive_board_summary"] = "\n".join([
                f"- {r.get('stock_name')} ({r.get('stock_code')}): {r.get('role', '')}"
                for r in consecutive_board_results[:5]
            ])
        else:
            variables["consecutive_board_summary"] = "无"

        # 添加趋势股分析摘要
        if trend_stock_results:
            variables["trend_stock_summary"] = "\n".join([
                f"- {r.get('stock_name')} ({r.get('stock_code')}): {r.get('trend_pattern', {}).get('pattern_type', '')}"
                for r in trend_stock_results[:5]
            ])
        else:
            variables["trend_stock_summary"] = "无"

        # 添加外部上下文
        if external_context:
            variables["external_context"] = str(external_context)
        else:
            variables["external_context"] = "无"

        analysis_prompt = analysis_template.format(**variables)

        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": analysis_prompt},
        ]

    def clear_cache(self) -> None:
        """清空缓存"""
        self._cache.clear()

    def get_available_prompts(self, category: Optional[str] = None) -> List[str]:
        """
        获取可用的提示词列表

        Args:
            category: 类别目录，None表示获取所有

        Returns:
            提示词文件列表
        """
        if category:
            category_dir = self.prompts_dir / category
            if not category_dir.exists():
                return []
            return [f.stem for f in category_dir.glob("*.txt") if f.is_file()]
        else:
            prompts = []
            for cat_dir in self.prompts_dir.iterdir():
                if cat_dir.is_dir():
                    prompts.extend([
                        f"{cat_dir.name}/{f.stem}"
                        for f in cat_dir.glob("*.txt")
                        if f.is_file()
                    ])
            return prompts
