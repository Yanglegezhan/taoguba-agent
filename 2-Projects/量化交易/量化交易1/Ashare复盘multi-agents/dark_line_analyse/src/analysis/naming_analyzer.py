# -*- coding: utf-8 -*-
"""命名语义分析器"""

import logging
from typing import List, Dict, Any
from collections import Counter
from difflib import SequenceMatcher

from ..models.data_models import LimitUpStockBasic, NamingAnalysisSummary


class NamingAnalyzer:
    """命名语义分析器"""

    # 命名特征关键词
    KEYWORD_PATTERNS = {
        '东方系': ['东方', '东风'],
        '数字系': ['一', '二', '三', '四', '五', '六', '七', '八', '九', '十',
                  '壹', '贰', '叁', '肆', '伍', '陆', '柒', '捌', '玖', '拾'],
        '龙凤系': ['龙', '凤', '凰'],
        '上升系': ['升', '涨', '腾', '飞', '翔'],
        '神圣系': ['圣', '神', '仙', '佛'],
        '中字头': ['中'],
        '国字号': ['国'],
        '华字头': ['华'],
        '科技系': ['科技', '智能', '智'],
        '能源系': ['能源', '电', '力'],
        '健康系': ['健康', '医疗', '药', '生物'],
        '新经济': ['新', '创'],
        '消费系': ['消费', '商贸', '商'],
    }

    def __init__(self, config):
        """初始化分析器"""
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.similarity_threshold = config.naming_similarity_threshold

    def analyze_batch(self, stocks: List[LimitUpStockBasic]) -> NamingAnalysisSummary:
        """批量分析命名特征"""
        self.logger.info(f"Analyzing naming patterns for {len(stocks)} stocks")

        all_features = []
        name_to_stock = {}

        for stock in stocks:
            stock_name = stock.name if hasattr(stock, 'name') else ''
            name_to_stock[stock_name] = stock.code if hasattr(stock, 'code') else stock_name

            features = self.analyze(stock_name)
            all_features.extend(features)

        # 汇总特征统计
        feature_counter = Counter(all_features)
        feature_summary = dict(feature_counter)
        feature_ratio = {k: v / len(stocks) * 100 for k, v in feature_counter.items()}

        # 查找相似名称
        similar_names = self._find_similar_names(list(name_to_stock.keys()))

        # 前缀模式分析
        prefix_patterns = self._analyze_prefix_patterns(name_to_stock.keys())

        return NamingAnalysisSummary(
            feature_summary=feature_summary,
            feature_ratio=feature_ratio,
            similar_names=similar_names,
            prefix_patterns=prefix_patterns
        )

    def analyze(self, name: str) -> List[str]:
        """分析单个股票名称的命名特征"""
        features = []

        if not name:
            return features

        for pattern_name, keywords in self.KEYWORD_PATTERNS.items():
            for keyword in keywords:
                if keyword in name:
                    features.append(pattern_name)
                    break  # 避免重复添加同一模式

        # 阿拉伯数字检测
        if any(c.isdigit() for c in name):
            features.append('阿拉伯数字')

        return features

    def _find_similar_names(self, names: List[str]) -> List[Dict[str, Any]]:
        """查找高相似度名称"""
        similar_pairs = []

        for i, name1 in enumerate(names):
            for name2 in names[i+1:]:
                similarity = SequenceMatcher(None, name1, name2).ratio()
                if similarity >= self.similarity_threshold:
                    similar_pairs.append({
                        'name1': name1,
                        'name2': name2,
                        'similarity': round(similarity, 2)
                    })

        return similar_pairs

    def _analyze_prefix_patterns(self, names: List[str]) -> Dict[str, List[str]]:
        """分析前缀模式"""
        prefixes = {}

        for name in names:
            if not name:
                continue

            # 常见前缀
            common_prefixes = ['中国', '中华', '华夏', '南方', '北方', '东方',
                            '西部', '中部', '华东', '华南', '华北']

            for prefix in common_prefixes:
                if name.startswith(prefix):
                    if prefix not in prefixes:
                        prefixes[prefix] = []
                    prefixes[prefix].append(name)
                    break

        return prefixes
