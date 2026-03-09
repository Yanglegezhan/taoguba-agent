# -*- coding: utf-8 -*-
"""统计学分析器"""

import logging
from typing import List, Dict, Any, Optional
from collections import Counter

from ..models.data_models import (
    LimitUpStockBasic,
    FrequencyAnalysis,
    StatisticalAnalysis
)


class StatisticalAnalyzer:
    """统计学对比分析器"""

    def __init__(self, config):
        """初始化分析器"""
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.lift_threshold = config.lift_ratio_threshold
        self.min_sample = config.min_sample_size

    def full_analyze(self, stocks: List[LimitUpStockBasic]) -> StatisticalAnalysis:
        """执行完整的统计学分析"""
        self.logger.info(f"Running full statistical analysis on {len(stocks)} stocks")

        # 各维度频率分析
        province_analysis = self.analyze_province(stocks)
        ownership_analysis = self.analyze_ownership(stocks)
        pb_analysis = self.analyze_pb(stocks)
        market_cap_analysis = self.analyze_market_cap(stocks)
        price_analysis = self.analyze_price_range(stocks)
        consecutive_analysis = self.analyze_consecutive_days(stocks)

        # 计算破净比例
        broken_net_stocks = [s for s in stocks if hasattr(s, 'pb_ratio') and s.pb_ratio and s.pb_ratio < 1.0]
        broken_net_ratio = len(broken_net_stocks) / len(stocks) * 100 if stocks else 0

        return StatisticalAnalysis(
            analysis_date="",
            limit_up_count=len(stocks),
            province_analysis=province_analysis,
            ownership_analysis=ownership_analysis,
            pb_analysis=pb_analysis,
            market_cap_analysis=market_cap_analysis,
            price_range_analysis=price_analysis,
            broken_net_ratio=broken_net_ratio,
            consecutive_days_analysis=consecutive_analysis,
            naming_feature_summary={
                'total_stocks': len(stocks)
            }
        )

    def analyze_province(self, stocks: List[LimitUpStockBasic]) -> FrequencyAnalysis:
        """地域分布分析"""
        provinces = [s.province for s in stocks if hasattr(s, 'province') and s.province]
        counter = Counter(provinces)

        return self._calculate_frequency_analysis(
            counter,
            total_count=len(stocks),
            dimension_name="province"
        )

    def analyze_ownership(self, stocks: List[LimitUpStockBasic]) -> FrequencyAnalysis:
        """企业性质分析"""
        ownerships = [s.ownership for s in stocks if hasattr(s, 'ownership') and s.ownership]
        counter = Counter(ownerships)

        return self._calculate_frequency_analysis(
            counter,
            total_count=len(stocks),
            dimension_name="ownership"
        )

    def analyze_pb(self, stocks: List[LimitUpStockBasic]) -> FrequencyAnalysis:
        """PB分布分析"""
        pb_ranges = []
        for s in stocks:
            if hasattr(s, 'pb_ratio') and s.pb_ratio is not None:
                if s.pb_ratio < 1.0:
                    pb_ranges.append('PB<1.0')
                elif s.pb_ratio < 2.0:
                    pb_ranges.append('1.0<=PB<2.0')
                elif s.pb_ratio < 5.0:
                    pb_ranges.append('2.0<=PB<5.0')
                else:
                    pb_ranges.append('PB>=5.0')

        counter = Counter(pb_ranges)

        return self._calculate_frequency_analysis(
            counter,
            total_count=len(stocks),
            dimension_name="pb_range"
        )

    def analyze_market_cap(self, stocks: List[LimitUpStockBasic]) -> FrequencyAnalysis:
        """市值分布分析"""
        cap_ranges = []
        for s in stocks:
            if hasattr(s, 'total_market_cap') and s.total_market_cap is not None:
                cap = s.total_market_cap  # 已经是亿元，不需要再转换
                if cap < 30:
                    cap_ranges.append('<30亿')
                elif cap < 100:
                    cap_ranges.append('30-100亿')
                elif cap < 500:
                    cap_ranges.append('100-500亿')
                else:
                    cap_ranges.append('>=500亿')

        counter = Counter(cap_ranges)

        return self._calculate_frequency_analysis(
            counter,
            total_count=len(stocks),
            dimension_name="market_cap"
        )

    def analyze_price_range(self, stocks: List[LimitUpStockBasic]) -> FrequencyAnalysis:
        """股价区间分析"""
        price_ranges = []
        for s in stocks:
            if hasattr(s, 'price') and s.price is not None:
                if s.price < 10:
                    price_ranges.append('<10元')
                elif s.price < 20:
                    price_ranges.append('10-20元')
                elif s.price < 50:
                    price_ranges.append('20-50元')
                else:
                    price_ranges.append('>=50元')

        counter = Counter(price_ranges)

        return self._calculate_frequency_analysis(
            counter,
            total_count=len(stocks),
            dimension_name="price"
        )

    def analyze_consecutive_days(self, stocks: List[LimitUpStockBasic]) -> FrequencyAnalysis:
        """连板高度分析"""
        consecutive_counts = []
        for s in stocks:
            if hasattr(s, 'consecutive_days') and s.consecutive_days is not None:
                if s.consecutive_days == 1:
                    consecutive_counts.append('首板')
                elif s.consecutive_days == 2:
                    consecutive_counts.append('2板')
                elif s.consecutive_days == 3:
                    consecutive_counts.append('3板')
                elif s.consecutive_days == 4:
                    consecutive_counts.append('4板')
                else:
                    consecutive_counts.append('5板及以上')

        counter = Counter(consecutive_counts)

        return self._calculate_frequency_analysis(
            counter,
            total_count=len(stocks),
            dimension_name="consecutive_days"
        )

    def _calculate_frequency_analysis(
        self,
        counter: Counter,
        total_count: int,
        dimension_name: str
    ) -> FrequencyAnalysis:
        """计算频率分析"""
        if total_count == 0:
            return FrequencyAnalysis(
                category=dimension_name,
                items_in_pool={},
                total_in_pool=0,
                pool_frequency={},
                items_in_market={},
                total_in_market=0,
                market_frequency={},
                lift_ratio={},
                significant_items=[]
            )

        pool_frequencies = {k: v for k, v in counter.items()}
        pool_freq_percent = {k: v / total_count * 100 for k, v in counter.items()}
        baseline_frequencies = self._get_baseline_frequencies(dimension_name)

        significant_items = []
        lift_ratios = {}
        for item, freq_percent in pool_freq_percent.items():
            baseline = baseline_frequencies.get(item, 1.0)  # 默认基准1%
            lift_ratio = freq_percent / baseline if baseline > 0 else 0
            lift_ratios[item] = lift_ratio

            if lift_ratio >= self.lift_threshold and counter[item] >= self.min_sample:
                significant_items.append(f"{item}({counter[item]},{lift_ratio:.1f}x)")

        return FrequencyAnalysis(
            category=dimension_name,
            items_in_pool=pool_frequencies,
            total_in_pool=total_count,
            pool_frequency=pool_freq_percent,
            items_in_market={},  # 暂时为空
            total_in_market=0,
            market_frequency=baseline_frequencies,
            lift_ratio=lift_ratios,
            significant_items=significant_items
        )

    def _get_baseline_frequencies(self, dimension_name: str) -> Dict[str, float]:
        """获取市场基准频率"""
        baselines = {
            'province': {
                '广东': 8.0, '浙江': 6.0, '江苏': 6.0, '北京': 4.0,
                '上海': 4.0, '山东': 4.0, '福建': 3.0, '四川': 3.0,
                '湖北': 2.5, '湖南': 2.5, '安徽': 2.0, '河南': 2.0
            },
            'ownership': {
                '民营企业': 65.0, '地方国有企业': 18.0,
                '中央国有企业': 8.0, '其他企业': 9.0
            },
            'pb_range': {
                'PB<1.0': 8.0, '1.0<=PB<2.0': 35.0,
                '2.0<=PB<5.0': 45.0, 'PB>=5.0': 12.0
            },
            'market_cap': {
                '<30亿': 30.0, '30-100亿': 40.0,
                '100-500亿': 25.0, '>=500亿': 5.0
            },
            'price': {
                '<10元': 25.0, '10-20元': 35.0,
                '20-50元': 30.0, '>=50元': 10.0
            },
            'consecutive_days': {
                '首板': 70.0, '2板': 18.0, '3板': 7.0,
                '4板': 3.0, '5板及以上': 2.0
            }
        }
        return baselines.get(dimension_name, {})
