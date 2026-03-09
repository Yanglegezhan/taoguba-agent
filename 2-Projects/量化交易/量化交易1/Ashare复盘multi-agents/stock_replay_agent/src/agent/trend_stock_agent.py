"""
趋势核心复盘智能体

分析趋势上升个股
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

# 导入项目模块
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(project_root))

from src.data.kaipanla_stock_source import KaipanlaStockSource
from src.analysis.indicator_calculator import IndicatorCalculator
from src.llm.client import LLMClient
from src.llm.prompt_engine import PromptEngine
from src.models.stock_models import (
    TrendStockAnalysis,
    TrendPattern,
    VolumePriceAnalysis,
    MovingAverageAnalysis,
    BreakthroughPoint,
)


logger = logging.getLogger(__name__)


class TrendStockAgent:
    """趋势核心复盘智能体"""

    def __init__(
        self,
        data_source: Optional[KaipanlaStockSource] = None,
        llm_client: Optional[LLMClient] = None,
        prompt_engine: Optional[PromptEngine] = None,
        config: Optional[Dict[str, Any]] = None,
    ):
        """
        初始化趋势核心复盘智能体

        Args:
            data_source: 数据源实例
            llm_client: LLM客户端实例
            prompt_engine: 提示词引擎实例
            config: 配置参数
        """
        self.data_source = data_source if data_source is not None else KaipanlaStockSource()
        self.llm_client = llm_client
        self.prompt_engine = prompt_engine if prompt_engine is not None else PromptEngine()

        self.config = config if config is not None else {}

        # 初始化分析器
        self.indicator_calculator = IndicatorCalculator()

        # 默认配置
        self.default_config = {
            "trend_period": 20,  # 趋势分析周期（天）
            "min_trend_days": 5,  # 最小趋势天数
            "relative_index": "SH000001",  # 对比指数
            "use_llm": True,
        }

    def analyze(
        self,
        stock_code: str,
        date: str,
        index_code: Optional[str] = None,
        historical_days: int = 20,
    ) -> TrendStockAnalysis:
        """
        分析指定股票的趋势

        Args:
            stock_code: 股票代码
            date: 分析日期
            index_code: 对比指数代码，默认使用上证指数
            historical_days: 历史数据天数

        Returns:
            趋势分析结果
        """
        logger.info(f"开始分析趋势股票: {stock_code}, 日期: {date}")

        # 1. 获取股票基本信息
        stock_info = self._get_stock_info(stock_code, date)
        if not stock_info:
            logger.error(f"无法获取股票信息: {stock_code}")
            return self._create_empty_analysis(stock_code, date, error="无法获取数据")

        # 2. 获取历史价格数据
        historical_prices = self._get_historical_prices(
            stock_code, date, historical_days
        )
        historical_volumes = self._get_historical_volumes(
            stock_code, date, historical_days
        )

        if not historical_prices or len(historical_prices) < 5:
            return self._create_empty_analysis(
                stock_code, date, error="历史数据不足"
            )

        # 3. 识别趋势形态
        trend_pattern_data = self.indicator_calculator.identify_trend_pattern(
            historical_prices, historical_volumes
        )
        trend_pattern = TrendPattern(
            pattern_type=trend_pattern_data["pattern_type"],
            stage=trend_pattern_data["stage"],
            duration_days=trend_pattern_data["duration_days"],
            strength=trend_pattern_data["strength"],
        )

        # 4. 分析量价关系
        volume_price_data = self.indicator_calculator.analyze_volume_price_relation(
            historical_prices, historical_volumes
        )
        volume_price = VolumePriceAnalysis(
            relationship=volume_price_data["relationship"],
            description=volume_price_data.get("description", ""),
            volume_trend=volume_price_data["volume_trend"],
            price_trend=volume_price_data["price_trend"],
        )

        # 5. 计算均线系统
        ma_data = self.indicator_calculator.calculate_moving_average_bias(
            historical_prices
        )
        moving_average = MovingAverageAnalysis(
            ma5=ma_data["mas"].get("ma5"),
            ma10=ma_data["mas"].get("ma10"),
            ma20=ma_data["mas"].get("ma20"),
            ma60=ma_data["mas"].get("ma60"),
            ma5_bias=ma_data["biases"].get("bias5"),
            ma20_bias=ma_data["biases"].get("bias20"),
            alignment=ma_data["alignment"],
            support_level=ma_data.get("support_level"),
            resistance_level=ma_data.get("resistance_level"),
        )

        # 6. 识别突破/回踩点
        breakthrough_points = self._identify_breakthrough_points(
            historical_prices, historical_volumes
        )

        # 7. 计算相对强度
        index_code = index_code or self.config.get(
            "relative_index", self.default_config["relative_index"]
        )
        relative_strength = 0.0
        if historical_prices:
            index_prices = self._get_index_prices(index_code, date, historical_days)
            if index_prices and len(index_prices) == len(historical_prices):
                rs_data = self.indicator_calculator.calculate_relative_strength(
                    historical_prices, index_prices
                )
                relative_strength = rs_data.get("relative_strength", 0.0)

        # 8. 持续性预判
        sustainability, sustainability_reason = self._judge_sustainability(
            trend_pattern, volume_price, moving_average
        )

        # 9. 风险评估
        risk_level, key_risk_points = self._assess_risk(
            trend_pattern, volume_price, breakthrough_points
        )

        # 10. 机会判断
        opportunity_level, entry_point, target_price, stop_loss = (
            self._assess_opportunity(
                stock_info, trend_pattern, moving_average, breakthrough_points
            )
        )

        # 11. 计算置信度
        confidence = self._calculate_confidence(
            trend_pattern, volume_price, sustainability
        )

        # 12. 构建分析结果
        analysis = TrendStockAnalysis(
            stock_code=stock_code,
            stock_name=stock_info.get("stock_name", ""),
            analysis_date=date,
            trend_pattern=trend_pattern,
            volume_price=volume_price,
            moving_average=moving_average,
            breakthrough_points=[BreakthroughPoint(**bp) for bp in breakthrough_points],
            relative_strength=relative_strength,
            relative_index=index_code,
            sustainability=sustainability,
            sustainability_reason=sustainability_reason,
            risk_level=risk_level,
            key_risk_points=key_risk_points,
            opportunity_level=opportunity_level,
            entry_point=entry_point,
            target_price=target_price,
            stop_loss=stop_loss,
            confidence=confidence,
            reasoning=self._build_reasoning(
                stock_info,
                trend_pattern,
                volume_price,
                moving_average,
            ),
        )

        logger.info(f"完成趋势分析: {stock_code}")

        return analysis

    def _get_stock_info(self, stock_code: str, date: str) -> Dict[str, Any]:
        """获取股票基本信息"""
        # 从实时涨停板数据中查找
        realtime_data = self.data_source.get_realtime_all_boards_stocks()
        for board_name in ["first_board", "second_board", "third_board", "fourth_board", "fifth_board_plus"]:
            for stock in realtime_data.get(board_name, []):
                if stock.get("stock_code") == stock_code:
                    return stock

        return {"stock_code": stock_code, "stock_name": stock_code}

    def _get_historical_prices(
        self, stock_code: str, date: str, days: int
    ) -> List[float]:
        """获取历史价格数据"""
        # 这里应该从数据源获取历史K线数据
        # 暂时返回模拟数据
        import random
        base_price = random.uniform(10, 50)
        trend = random.uniform(-0.5, 1.0)
        return [
            base_price + trend * i + random.uniform(-0.5, 0.5)
            for i in range(days)
        ]

    def _get_historical_volumes(
        self, stock_code: str, date: str, days: int
    ) -> List[float]:
        """获取历史成交量数据"""
        import random
        base_volume = random.uniform(100000, 1000000)
        return [
            base_volume * (1 + random.uniform(-0.3, 0.3))
            for i in range(days)
        ]

    def _get_index_prices(
        self, index_code: str, date: str, days: int
    ) -> List[float]:
        """获取指数历史价格"""
        import random
        base_price = random.uniform(3000, 3500)
        trend = random.uniform(-2.0, 2.0)
        return [
            base_price + trend * i + random.uniform(-20, 20) for i in range(days)
        ]

    def _identify_breakthrough_points(
        self, prices: List[float], volumes: List[float]
    ) -> List[Dict[str, Any]]:
        """识别突破/回踩点"""
        points = []
        if len(prices) < 10:
            return points

        # 计算20日均线
        if len(prices) >= 20:
            import numpy as np
            ma20 = []
            for i in range(20, len(prices)):
                ma = np.mean(prices[i - 20 : i])
                ma20.append(ma)

            # 找出突破点
            for i in range(20, len(prices)):
                prev_ma = ma20[i - 20 - 1]
                curr_ma = ma20[i - 20]
                prev_price = prices[i - 1]
                curr_price = prices[i]

                # 向上突破
                if prev_price < prev_ma and curr_price > curr_ma:
                    points.append(
                        {
                            "point_type": "突破",
                            "level": curr_ma,
                            "level_type": "均线",
                            "timestamp": f"第{i}天",
                            "volume": volumes[i] if i < len(volumes) else 0,
                            "valid": True,
                        }
                    )
                # 向下破位
                elif prev_price > prev_ma and curr_price < curr_ma:
                    points.append(
                        {
                            "point_type": "破位",
                            "level": curr_ma,
                            "level_type": "均线",
                            "timestamp": f"第{i}天",
                            "volume": volumes[i] if i < len(volumes) else 0,
                            "valid": True,
                        }
                    )

        return points

    def _judge_sustainability(
        self,
        trend_pattern: TrendPattern,
        volume_price: VolumePriceAnalysis,
        moving_average: MovingAverageAnalysis,
    ) -> tuple:
        """判断趋势持续性"""
        sustainability = "中"

        # 主升浪且量价齐升
        if "主升浪" in trend_pattern.pattern_type and "齐升" in volume_price.relationship:
            sustainability = "强"
            reason = "主升浪形态且量价齐升，趋势健康"
        # 主升浪但量价背离
        elif "主升浪" in trend_pattern.pattern_type and "背离" in volume_price.relationship:
            sustainability = "弱"
            reason = "主升浪形态但量价背离，动能减弱"
        # 多头排列
        elif "多头" in moving_average.alignment:
            sustainability = "中"
            reason = "均线多头排列，趋势尚可"
        # 空头排列
        elif "空头" in moving_average.alignment:
            sustainability = "弱"
            reason = "均线空头排列，趋势转弱"
        else:
            sustainability = "中"
            reason = "趋势方向不明确，需观察"

        return sustainability, reason

    def _assess_risk(
        self,
        trend_pattern: TrendPattern,
        volume_price: VolumePriceAnalysis,
        breakthrough_points: List[Dict[str, Any]],
    ) -> tuple:
        """评估风险"""
        risk_points = []
        risk_level = "中"

        # 检查风险点
        if "下跌" in trend_pattern.pattern_type:
            risk_level = "高"
            risk_points.append("趋势下跌")

        if "背离" in volume_price.relationship:
            risk_points.append("量价背离")

        if "放量下跌" in volume_price.relationship:
            risk_points.append("放量出逃")
            risk_level = "高"

        # 检查近期是否破位
        if breakthrough_points:
            recent_breaks = [
                bp for bp in breakthrough_points[-3:]
                if bp.get("point_type") == "破位"
            ]
            if recent_breaks:
                risk_points.append("近期破位")
                risk_level = "高" if risk_level != "高" else "中"

        if not risk_points:
            risk_level = "低"

        return risk_level, risk_points

    def _assess_opportunity(
        self,
        stock_info: Dict[str, Any],
        trend_pattern: TrendPattern,
        moving_average: MovingAverageAnalysis,
        breakthrough_points: List[Dict[str, Any]],
    ) -> tuple:
        """评估机会"""
        opportunity_level = "中"
        entry_point = None
        target_price = None
        stop_loss = None

        # 主升浪且均线多头排列
        if "主升浪" in trend_pattern.pattern_type and "多头" in moving_average.alignment:
            opportunity_level = "高"

            # 建议入场点：20日均线附近
            entry_point = moving_average.ma20

            # 目标价：5日均线延伸
            if moving_average.ma5:
                target_price = moving_average.ma5 * 1.1

            # 止损位：破20日均线
            stop_loss = moving_average.ma20 * 0.95

        # 筑底阶段
        elif "筑底" in trend_pattern.pattern_type:
            opportunity_level = "中"
            entry_point = moving_average.ma20
            target_price = moving_average.ma20 * 1.2
            stop_loss = moving_average.ma20 * 0.9

        return opportunity_level, entry_point, target_price, stop_loss

    def _calculate_confidence(
        self,
        trend_pattern: TrendPattern,
        volume_price: VolumePriceAnalysis,
        sustainability: str,
    ) -> str:
        """计算置信度"""
        score = 0

        # 趋势形态得分
        if "主升" in trend_pattern.pattern_type:
            score += 30
        elif "反弹" in trend_pattern.pattern_type:
            score += 20
        elif "筑底" in trend_pattern.pattern_type:
            score += 15

        # 量价关系得分
        if "齐升" in volume_price.relationship:
            score += 30
        elif "缩量上涨" in volume_price.relationship:
            score += 10
        elif "背离" in volume_price.relationship:
            score -= 10

        # 持续性得分
        if sustainability == "强":
            score += 40
        elif sustainability == "中":
            score += 20

        # 归一化
        confidence = "高"
        if score < 40:
            confidence = "低"
        elif score < 60:
            confidence = "中"

        return confidence

    def _build_reasoning(
        self,
        stock_info: Dict[str, Any],
        trend_pattern: TrendPattern,
        volume_price: VolumePriceAnalysis,
        moving_average: MovingAverageAnalysis,
    ) -> str:
        """构建分析推理过程"""
        parts = [
            f"股票：{stock_info.get('stock_name')}（{stock_info.get('stock_code')}）",
            f"趋势形态：{trend_pattern.pattern_type}（{trend_pattern.stage}）",
            f"趋势强度：{trend_pattern.strength:.2f}",
            f"量价关系：{volume_price.relationship}",
            f"均线排列：{moving_average.alignment}",
        ]

        return "；".join(parts) + "。"

    def _create_empty_analysis(
        self, stock_code: str, date: str, error: str = ""
    ) -> TrendStockAnalysis:
        """创建空分析结果"""
        return TrendStockAnalysis(
            stock_code=stock_code,
            stock_name="",
            analysis_date=date,
            trend_pattern=TrendPattern(
                pattern_type="未知", stage="", duration_days=0, strength=0
            ),
            volume_price=VolumePriceAnalysis(
                relationship="无数据",
                description="",
                volume_trend="平稳",
                price_trend="震荡",
            ),
            moving_average=MovingAverageAnalysis(alignment="缠绕"),
            risk_level="中",
            opportunity_level="低",
            confidence="低",
            reasoning=error,
        )

    def batch_analyze(
        self,
        stock_codes: List[str],
        date: str,
        index_code: Optional[str] = None,
    ) -> List[TrendStockAnalysis]:
        """
        批量分析股票

        Args:
            stock_codes: 股票代码列表
            date: 分析日期
            index_code: 对比指数代码

        Returns:
            分析结果列表
        """
        results = []
        for stock_code in stock_codes:
            try:
                analysis = self.analyze(stock_code, date, index_code)
                results.append(analysis)
            except Exception as e:
                logger.error(f"分析股票 {stock_code} 失败: {e}")
                results.append(
                    self._create_empty_analysis(
                        stock_code, date, f"分析失败: {str(e)}"
                    )
                )

        return results
