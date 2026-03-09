# -*- coding: utf-8 -*-
"""
情绪指标计算器

基于市场数据计算三线指标：大盘系数、超短情绪、亏钱效应。
"""

from typing import Dict, List
from dataclasses import dataclass
from datetime import date


@dataclass
class MarketDayData:
    """单日市场数据"""
    trading_date: date
    index_change: float  # 指数涨跌幅
    all_a_change: float  # 全A涨跌幅
    up_count: int  # 上涨家数
    down_count: int  # 下跌家数
    limit_up_count: int  # 涨停数
    limit_down_count: int  # 跌停数
    max_consecutive: int  # 最高板
    yesterday_limit_up_performance: float  # 昨日涨停今表现
    new_100day_high_count: int  # 百日新高数
    blown_limit_up_count: int  # 炸板数
    blown_limit_up_rate: float  # 炸板率
    large_pullback_count: int  # 大幅回撤数
    yesterday_blown_performance: float  # 昨日炸板今表现


@dataclass
class SentimentMetrics:
    """情绪指标"""
    market_coefficient: float  # 大盘系数
    ultra_short_sentiment: float  # 超短情绪
    loss_effect: float  # 亏钱效应


class SentimentCalculator:
    """情绪指标计算器"""

    @staticmethod
    def calculate_market_coefficient(data: MarketDayData) -> float:
        """
        计算大盘系数

        公式: (上涨家数 - 下跌家数) / (上涨家数 + 下跌家数) × 100 + 指数涨跌幅 × 10

        判断标准:
        - < 30: 弱势
        - 30-150: 震荡
        - > 150: 强势
        """
        total_count = data.up_count + data.down_count
        if total_count == 0:
            return 0.0

        up_down_ratio = (data.up_count - data.down_count) / total_count
        market_coeff = up_down_ratio * 100 + data.index_change * 10

        return market_coeff

    @staticmethod
    def calculate_ultra_short_sentiment(data: MarketDayData) -> float:
        """
        计算超短情绪

        公式: 涨停数 × 2 + 百日新高数 × 0.5 - 跌停数 × 3 - 炸板率 × 50

        判断标准:
        - < 50: 情绪低
        - 50-150: 情绪中等
        - > 150: 情绪高
        """
        sentiment = (
            data.limit_up_count * 2 +
            data.new_100day_high_count * 0.5 -
            data.limit_down_count * 3 -
            data.blown_limit_up_rate * 50
        )

        return sentiment

    @staticmethod
    def calculate_loss_effect(data: MarketDayData) -> float:
        """
        计算亏钱效应

        公式: 跌停数 × 2 + 大幅回撤数 + |昨日涨停今表现| × 10

        判断标准:
        - < 40: 亏钱效应低
        - 40-100: 亏钱效应中等
        - > 100: 亏钱效应高
        """
        loss_effect = (
            data.limit_down_count * 2 +
            data.large_pullback_count +
            abs(data.yesterday_limit_up_performance) * 10
        )

        return loss_effect

    @staticmethod
    def calculate_all_metrics(data: MarketDayData) -> SentimentMetrics:
        """
        计算所有情绪指标

        Args:
            data: 市场数据

        Returns:
            情绪指标对象
        """
        market_coeff = SentimentCalculator.calculate_market_coefficient(data)
        ultra_short = SentimentCalculator.calculate_ultra_short_sentiment(data)
        loss_effect = SentimentCalculator.calculate_loss_effect(data)

        return SentimentMetrics(
            market_coefficient=market_coeff,
            ultra_short_sentiment=ultra_short,
            loss_effect=loss_effect
        )


class CycleDetector:
    """情绪周期检测器"""

    @staticmethod
    def detect_cycle_phase(
        current_metrics: SentimentMetrics,
        previous_metrics: SentimentMetrics = None
    ) -> str:
        """
        检测当前情绪周期阶段

        Args:
            current_metrics: 当前指标
            previous_metrics: 昨日指标（可选）

        Returns:
            周期阶段: "冰点" | "修复" | "分歧" | "高潮" | "震荡"
        """
        # 冰点判断
        if (current_metrics.market_coefficient < 30 and
            current_metrics.ultra_short_sentiment < 50 and
            current_metrics.loss_effect > 100):
            return "冰点"

        # 高潮判断
        if (current_metrics.market_coefficient > 150 and
            current_metrics.ultra_short_sentiment > 150 and
            current_metrics.loss_effect < 40):
            return "高潮"

        # 如果有昨日数据，判断修复/分歧
        if previous_metrics:
            # 计算变化幅度
            market_change = abs(current_metrics.market_coefficient - previous_metrics.market_coefficient)
            sentiment_change = abs(current_metrics.ultra_short_sentiment - previous_metrics.ultra_short_sentiment)

            # 分歧判断（指标波动大）
            if market_change > 50 or sentiment_change > 50:
                return "分歧"

            # 修复判断（指标上升）
            if (current_metrics.market_coefficient > previous_metrics.market_coefficient and
                current_metrics.ultra_short_sentiment > previous_metrics.ultra_short_sentiment and
                current_metrics.loss_effect < previous_metrics.loss_effect):
                return "修复"

        # 默认震荡
        return "震荡"

    @staticmethod
    def get_cycle_description(phase: str) -> str:
        """获取周期阶段描述"""
        descriptions = {
            "冰点": "市场情绪极低，亏钱效应明显，适合观望或轻仓试错",
            "修复": "情绪开始回暖，亏钱效应减弱，可逐步加仓",
            "分歧": "情绪波动剧烈，资金分歧大，需谨慎操作",
            "高潮": "情绪高涨，赚钱效应明显，可积极参与",
            "震荡": "情绪平稳，缺乏方向，适合高抛低吸"
        }
        return descriptions.get(phase, "未知阶段")


if __name__ == "__main__":
    # 测试数据
    from datetime import date

    test_data = MarketDayData(
        trading_date=date(2026, 3, 5),
        index_change=1.25,
        all_a_change=1.10,
        up_count=4079,
        down_count=1306,
        limit_up_count=80,
        limit_down_count=5,
        max_consecutive=2,
        yesterday_limit_up_performance=2.5,
        new_100day_high_count=150,
        blown_limit_up_count=12,
        blown_limit_up_rate=0.13,
        large_pullback_count=20,
        yesterday_blown_performance=-1.5
    )

    # 计算指标
    calculator = SentimentCalculator()
    metrics = calculator.calculate_all_metrics(test_data)

    print("=== 情绪指标 ===")
    print(f"大盘系数: {metrics.market_coefficient:.2f}")
    print(f"超短情绪: {metrics.ultra_short_sentiment:.2f}")
    print(f"亏钱效应: {metrics.loss_effect:.2f}")

    # 检测周期
    detector = CycleDetector()
    phase = detector.detect_cycle_phase(metrics)
    print(f"\n当前周期: {phase}")
    print(f"周期描述: {detector.get_cycle_description(phase)}")
