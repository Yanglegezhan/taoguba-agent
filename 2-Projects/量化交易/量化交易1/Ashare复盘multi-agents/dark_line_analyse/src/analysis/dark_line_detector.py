# -*- coding: utf-8 -*-
"""暗线检测器"""

import logging
from typing import List, Dict, Any

from ..models.data_models import (
    DarkLine,
    DarkLineEvidence,
    DarkLineType,
    StatisticalAnalysis,
    NamingAnalysis,
    LimitUpStockBasic
)


class DarkLineDetector:
    """暗线检测器"""

    def __init__(self, config):
        """初始化检测器"""
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.lift_threshold = config.lift_ratio_threshold
        self.min_sample = config.min_sample_size

    def detect(
        self,
        stat_analysis: StatisticalAnalysis,
        naming_analysis: NamingAnalysis,
        stocks: List[LimitUpStockBasic]
    ) -> List[DarkLine]:
        """检测所有暗线"""
        dark_lines = []

        # 1. 地域集聚检测
        regional = self._detect_regional_cluster(stat_analysis, stocks)
        if regional:
            dark_lines.extend(regional)

        # 2. 企业性质检测
        ownership = self._detect_ownership_theme(stat_analysis, stocks)
        if ownership:
            dark_lines.extend(ownership)

        # 3. PB价值主题检测
        pb = self._detect_pb_value_theme(stat_analysis, stocks)
        if pb:
            dark_lines.extend(pb)

        # 4. 命名模式检测
        naming = self._detect_naming_pattern(naming_analysis, stocks)
        if naming:
            dark_lines.extend(naming)

        # 5. 连板梯队检测
        consecutive = self._detect_consecutive_pattern(stat_analysis, stocks)
        if consecutive:
            dark_lines.extend(consecutive)

        # 6. 市值特征检测
        cap = self._detect_market_cap_pattern(stat_analysis, stocks)
        if cap:
            dark_lines.extend(cap)

        return sorted(dark_lines, key=lambda x: x.confidence, reverse=True)

    def _detect_regional_cluster(
        self,
        stat_analysis: StatisticalAnalysis,
        stocks: List[LimitUpStockBasic]
    ) -> List[DarkLine]:
        """检测地域集聚型暗线"""
        dark_lines = []

        if not hasattr(stat_analysis, 'province_analysis'):
            return dark_lines

        province_analysis = stat_analysis.province_analysis
        lift_ratios = getattr(province_analysis, 'lift_ratio', {})
        frequencies = getattr(province_analysis, 'pool_frequency', {})

        for province, lift in lift_ratios.items():
            if lift >= self.lift_threshold:
                count = int(frequencies.get(province, 0) * len(stocks) / 100)
                if count >= self.min_sample:
                    dark_line = DarkLine(
                        title=f"地域集聚: {province}省",
                        description=f"今日{province}省涨停股票占比显著高于市场基准，"
                                   f"提升倍数为{lift:.1f}倍",
                        dark_line_type=DarkLineType.REGIONAL_CLUSTER,
                        confidence=min(lift / 3, count / 5, 1.0),
                        evidences=[DarkLineEvidence(
                            evidence_type="统计显著性",
                            description=f"{province}省涨停占比{frequencies.get(province, 0):.1f}%，提升倍数{lift:.1f}x",
                            strength=min(lift / 5, 1.0),
                            data={
                                "dimension": "地域",
                                "value": province,
                                "lift_ratio": lift,
                                "sample_size": count
                            }
                        )],
                        stock_count=count,
                        related_stocks=[s.stock_code for s in stocks
                                      if hasattr(s, 'province') and s.province == province],
                        is_accidental=count < 5
                    )
                    dark_lines.append(dark_line)

        return dark_lines

    def _detect_ownership_theme(
        self,
        stat_analysis: StatisticalAnalysis,
        stocks: List[LimitUpStockBasic]
    ) -> List[DarkLine]:
        """检测企业性质主题"""
        dark_lines = []

        if not hasattr(stat_analysis, 'ownership_analysis'):
            return dark_lines

        ownership_analysis = stat_analysis.ownership_analysis
        lift_ratios = getattr(ownership_analysis, 'lift_ratio', {})
        frequencies = getattr(ownership_analysis, 'pool_frequency', {})

        for ownership, lift in lift_ratios.items():
            if lift >= self.lift_threshold:
                count = int(frequencies.get(ownership, 0) * len(stocks) / 100)
                if count >= self.min_sample:
                    title_map = {
                        '中央国有企业': '央企重组预期',
                        '地方国有企业': '国企改革主题',
                        '民营企业': '民企活跃',
                        '民企': '民企活跃',
                        '外资': '外资活跃'
                    }
                    title = title_map.get(ownership, f"{ownership}主题")

                    dark_line = DarkLine(
                        title=title,
                        description=f"今日{ownership}涨停股票占比显著，提升倍数{lift:.1f}倍",
                        dark_line_type=DarkLineType.OWNERSHIP_THEME,
                        confidence=min(lift / 3, 0.9),
                        evidences=[DarkLineEvidence(
                            evidence_type="统计显著性",
                            description=f"{ownership}涨停占比{frequencies.get(ownership, 0):.1f}%，提升倍数{lift:.1f}x",
                            strength=min(lift / 5, 1.0),
                            data={
                                "dimension": "企业性质",
                                "value": ownership,
                                "lift_ratio": lift,
                                "sample_size": count
                            }
                        )],
                        stock_count=count,
                        related_stocks=[s.stock_code for s in stocks
                                      if hasattr(s, 'ownership') and s.ownership == ownership],
                        is_accidental=count < 3
                    )
                    dark_lines.append(dark_line)

        return dark_lines

    def _detect_pb_value_theme(
        self,
        stat_analysis: StatisticalAnalysis,
        stocks: List[LimitUpStockBasic]
    ) -> List[DarkLine]:
        """检测PB价值主题"""
        dark_lines = []

        if not hasattr(stat_analysis, 'broken_net_ratio'):
            return dark_lines

        broken_net_ratio = stat_analysis.broken_net_ratio

        # 破净股占比超过15%视为暗线
        if broken_net_ratio >= 15:
            count = int(broken_net_ratio * len(stocks) / 100)

            dark_line = DarkLine(
                title="破净修复主题",
                description=f"今日破净股(PB<1)涨停占比{broken_net_ratio:.1f}%，"
                           f"反映低估值修复逻辑",
                dark_line_type=DarkLineType.PB_VALUE_THEME,
                confidence=min(broken_net_ratio / 30, 0.85),
                evidences=[DarkLineEvidence(
                    evidence_type="统计显著性",
                    description=f"破净股占比{broken_net_ratio:.1f}%",
                    strength=min(broken_net_ratio / 30, 1.0),
                    data={
                        "dimension": "PB估值",
                        "value": "PB<1.0",
                        "lift_ratio": broken_net_ratio / 8.0,
                        "sample_size": count
                    }
                )],
                stock_count=count,
                related_stocks=[s.stock_code for s in stocks
                              if hasattr(s, 'pb') and s.pb and s.pb < 1.0],
                is_accidental=count < 3
            )
            dark_lines.append(dark_line)

        return dark_lines

    def _detect_naming_pattern(
        self,
        naming_analysis: NamingAnalysis,
        stocks: List[LimitUpStockBasic]
    ) -> List[DarkLine]:
        """检测命名模式"""
        dark_lines = []

        feature_ratio = naming_analysis.feature_ratio or {}
        feature_summary = naming_analysis.feature_summary or {}

        # 高占比命名特征
        for feature, ratio in feature_ratio.items():
            if ratio >= 20:  # 占比超过20%
                count = feature_summary.get(feature, 0)
                if count >= self.min_sample:
                    description_map = {
                        '东方系': '近期"东方"系股票活跃',
                        '龙凤系': '龙年或生肖相关概念',
                        '数字系': '数字命名股票聚集',
                        '中字头': '中字头央企/国企活跃',
                        '科技系': '科技题材主线',
                        '能源系': '能源题材活跃'
                    }
                    description = description_map.get(
                        feature, f'"{feature}"命名模式聚集'
                    )

                    dark_line = DarkLine(
                        title=f"命名模式: {feature}",
                        description=description,
                        dark_line_type=DarkLineType.NAMING_PATTERN,
                        confidence=min(ratio / 30, 0.8),
                        evidences=[DarkLineEvidence(
                            evidence_type="命名特征",
                            description=f"{feature}占比{ratio:.1f}%",
                            strength=min(ratio / 30, 1.0),
                            data={
                                "dimension": "命名特征",
                                "value": feature,
                                "lift_ratio": ratio / 10.0,
                                "sample_size": count
                            }
                        )],
                        stock_count=count,
                        is_accidental=count < 3
                    )
                    dark_lines.append(dark_line)

        # 相似名称
        similar_names = naming_analysis.similar_names or []
        if len(similar_names) >= 2:
            # 找出涉及股票最多的相似组
            similar_stocks = set()
            for sim in similar_names:
                similar_stocks.add(sim.get('name1', ''))
                similar_stocks.add(sim.get('name2', ''))

            if len(similar_stocks) >= 3:
                dark_line = DarkLine(
                    title="名称相似性聚集",
                    description=f"涨停池中存在{len(similar_stocks)}只高相似度股票名称",
                    dark_line_type=DarkLineType.NAMING_PATTERN,
                    confidence=0.6,
                    evidences=[],
                    stock_count=len(similar_stocks),
                    is_accidental=False
                )
                dark_lines.append(dark_line)

        return dark_lines

    def _detect_consecutive_pattern(
        self,
        stat_analysis: StatisticalAnalysis,
        stocks: List[LimitUpStockBasic]
    ) -> List[DarkLine]:
        """检测连板梯队"""
        dark_lines = []

        if not hasattr(stat_analysis, 'consecutive_days_analysis'):
            return dark_lines

        cons_analysis = stat_analysis.consecutive_days_analysis
        frequencies = getattr(cons_analysis, 'pool_frequency', {})

        # 检测2板及以上占比
        high_board_ratio = 0
        for key in ['2板', '3板', '4板', '5板及以上']:
            high_board_ratio += frequencies.get(key, 0)

        if high_board_ratio >= 30:  # 连板股占比超过30%
            dark_line = DarkLine(
                title="强势连板梯队",
                description=f"今日连板股(2板及以上)占比{high_board_ratio:.1f}%，"
                           f"反映题材延续性强",
                dark_line_type=DarkLineType.TECHNICAL_PATTERN,
                confidence=min(high_board_ratio / 50, 0.9),
                evidences=[DarkLineEvidence(
                    evidence_type="连板特征",
                    description=f"连板股占比{high_board_ratio:.1f}%",
                    strength=min(high_board_ratio / 50, 1.0),
                    data={
                        "dimension": "连板高度",
                        "value": "2板及以上",
                        "lift_ratio": high_board_ratio / 25.0,
                        "sample_size": int(high_board_ratio * len(stocks) / 100)
                    }
                )],
                stock_count=int(high_board_ratio * len(stocks) / 100),
                related_stocks=[s.stock_code for s in stocks
                              if hasattr(s, 'consecutive_days') and s.consecutive_days and s.consecutive_days >= 2],
                is_accidental=False
            )
            dark_lines.append(dark_line)

        return dark_lines

    def _detect_market_cap_pattern(
        self,
        stat_analysis: StatisticalAnalysis,
        stocks: List[LimitUpStockBasic]
    ) -> List[DarkLine]:
        """检测市值特征"""
        dark_lines = []

        if not hasattr(stat_analysis, 'market_cap_analysis'):
            return dark_lines

        cap_analysis = stat_analysis.market_cap_analysis
        frequencies = getattr(cap_analysis, 'pool_frequency', {})
        lift_ratios = getattr(cap_analysis, 'lift_ratio', {})

        # 小市值主导
        small_cap_ratio = frequencies.get('<30亿', 0)
        if small_cap_ratio >= 50:
            count = int(small_cap_ratio * len(stocks) / 100)
            dark_line = DarkLine(
                title="小市值主导",
                description=f"今日30亿以下小市值涨停占比{small_cap_ratio:.1f}%，"
                           f"反映游资偏好小票风格",
                dark_line_type=DarkLineType.CONCEPT_CLUSTER,
                confidence=min(small_cap_ratio / 70, 0.85),
                evidences=[DarkLineEvidence(
                    evidence_type="市值特征",
                    description=f"小市值(<30亿)占比{small_cap_ratio:.1f}%",
                    strength=min(small_cap_ratio / 70, 1.0),
                    data={
                        "dimension": "市值",
                        "value": "<30亿",
                        "lift_ratio": lift_ratios.get('<30亿', 0),
                        "sample_size": count
                    }
                )],
                stock_count=count,
                related_stocks=[s.stock_code for s in stocks
                              if hasattr(s, 'total_market_cap') and s.total_market_cap
                              and s.total_market_cap < 30],  # 已经是亿元，直接比较
                is_accidental=False
            )
            dark_lines.append(dark_line)

        return dark_lines
