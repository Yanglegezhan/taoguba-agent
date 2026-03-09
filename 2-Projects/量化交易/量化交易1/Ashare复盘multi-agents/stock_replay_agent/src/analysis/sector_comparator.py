"""
同题材对比分析器

分析同题材股票的溢价水平，判断"头狼"还是"羊群"
"""
from typing import Dict, Any, List, Optional, Tuple
import pandas as pd
import numpy as np


class SectorComparator:
    """同题材对比分析器"""

    def __init__(self, data_source=None):
        """
        初始化同题材对比分析器

        Args:
            data_source: 数据源实例（可选）
        """
        self.data_source = data_source

    def compare_same_concept_stocks(
        self,
        target_stock: Dict[str, Any],
        all_stocks: List[Dict[str, Any]],
        ladder_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        比较同题材股票的溢价水平

        Args:
            target_stock: 目标个股信息
            all_stocks: 所有涨停板股票列表
            ladder_data: 连板梯队数据（可选）

        Returns:
            同题材对比分析
                - sector: 题材名称
                - same_concept_stocks: 同题材股票列表
                - target_premium: 目标个股次日溢价
                - sector_avg_premium: 同题材平均溢价
                - premium_level: 溢价水平对比（优于/持平/弱于）
                - is_leader: 是否为题材龙头（头狼）
                - sector_avg_turnover: 同题材平均成交额
                - sector_avg_consecutive: 同题材平均连板天数
        """
        # 提取目标个股概念
        target_concepts = self._extract_concepts(target_stock)

        if not target_concepts:
            return {
                "sector": "未知",
                "same_concept_stocks": [],
                "target_premium": "未开盘",
                "sector_avg_premium": "未开盘",
                "premium_level": "无数据",
                "is_leader": False,
            }

        # 找出同题材股票
        same_concept_stocks = []
        for stock in all_stocks:
            stock_concepts = self._extract_concepts(stock)
            # 检查是否有交集
            if target_concepts & stock_concepts:
                same_concept_stocks.append(stock)

        # 如果没有找到同题材股票
        if not same_concept_stocks:
            return {
                "sector": list(target_concepts)[0],
                "same_concept_stocks": [],
                "target_premium": "未开盘",
                "sector_avg_premium": "未开盘",
                "premium_level": "无同题材",
                "is_leader": True,  # 唯一的成员，默认为龙头
            }

        # 计算目标个股的次日溢价（这里使用当前数据模拟）
        target_premium = self._calculate_premium(target_stock)

        # 计算同题材平均溢价
        sector_premiums = []
        for stock in same_concept_stocks:
            premium = self._calculate_premium(stock)
            if premium is not None:
                sector_premiums.append(premium)

        if not sector_premiums:
            sector_avg_premium = 0
        else:
            sector_avg_premium = np.mean(sector_premiums)

        # 判断溢价水平
        premium_level = self._compare_premium(target_premium, sector_avg_premium)

        # 判断是否为龙头
        is_leader = self._is_leader(
            target_stock, same_concept_stocks, premium_level
        )

        # 计算同题材统计数据
        sector_stats = self._calculate_sector_stats(same_concept_stocks)

        # 确定主要题材名称（使用目标个股的第一个概念）
        primary_sector = list(target_concepts)[0] if target_concepts else "未知"

        return {
            "sector": primary_sector,
            "same_concept_stocks": same_concept_stocks,
            "same_concept_count": len(same_concept_stocks),
            "target_premium": self._premium_to_label(target_premium),
            "target_premium_value": target_premium,
            "sector_avg_premium": self._premium_to_label(sector_avg_premium),
            "sector_avg_premium_value": sector_avg_premium,
            "premium_level": premium_level,
            "is_leader": is_leader,
            "role": self._determine_role(is_leader, premium_level),
            **sector_stats,
        }

    def _extract_concepts(self, stock: Dict[str, Any]) -> set:
        """
        提取股票概念

        Args:
            stock: 股票信息字典

        Returns:
            概念集合
        """
        concepts = set()

        # 尝试不同的字段名
        concept_fields = [
            "concepts",
            "concept",
            "concepts_list",
            "概念",
            "题材",
            "sector",
        ]

        for field in concept_fields:
            value = stock.get(field)
            if value:
                if isinstance(value, list):
                    concepts.update(value)
                elif isinstance(value, str):
                    # 分割字符串
                    parts = [p.strip() for p in value.replace("/", "、").split("、") if p.strip()]
                    concepts.update(parts)

        return concepts

    def _calculate_premium(self, stock: Dict[str, Any]) -> Optional[float]:
        """
        计算个股溢价（模拟）

        实际应用中应该从次日数据计算，这里使用当前数据模拟

        Args:
            stock: 股票信息

        Returns:
            溢价百分比，None表示未开盘
        """
        # 获取开盘价和昨收价
        open_price = stock.get("open_price", stock.get("begin_px", 0))
        preclose_px = stock.get("preclose_px", 0)

        if preclose_px is None or preclose_px <= 0:
            return None

        if open_price is None or open_price <= 0:
            return None

        premium = (open_price - preclose_px) / preclose_px
        return premium

    def _premium_to_label(self, premium: Optional[float]) -> str:
        """将溢价值转换为标签"""
        if premium is None:
            return "未开盘"
        elif premium >= 0.02:
            return "高开"
        elif premium >= 0.005:
            return "平开"
        elif premium >= -0.005:
            return "低开"
        else:
            return "大幅低开"

    def _compare_premium(
        self, target_premium: Optional[float], sector_avg_premium: float
    ) -> str:
        """
        比较溢价水平

        Args:
            target_premium: 目标个股溢价
            sector_avg_premium: 同题材平均溢价

        Returns:
            溢价水平对比
        """
        if target_premium is None:
            return "未知"

        diff = target_premium - sector_avg_premium
        threshold = 0.01  # 1%差异阈值

        if diff > threshold:
            return "优于"
        elif diff < -threshold:
            return "弱于"
        else:
            return "持平"

    def _is_leader(
        self,
        target_stock: Dict[str, Any],
        same_concept_stocks: List[Dict[str, Any]],
        premium_level: str,
    ) -> bool:
        """
        判断是否为题材龙头

        Args:
            target_stock: 目标个股
            same_concept_stocks: 同题材股票列表
            premium_level: 溢价水平

        Returns:
            是否为龙头
        """
        if not same_concept_stocks:
            return True

        # 判断标准：
        # 1. 溢价优于同题材
        # 2. 成交额领先
        # 3. 连板天数最高

        target_turnover = target_stock.get("turnover", 0)
        target_consecutive = target_stock.get("consecutive_days", 1)

        # 计算同题材平均成交额
        sector_turnovers = [s.get("turnover", 0) for s in same_concept_stocks]
        sector_avg_turnover = np.mean(sector_turnovers) if sector_turnovers else 0

        # 计算同题材最大连板天数
        sector_consecutives = [s.get("consecutive_days", 1) for s in same_concept_stocks]
        sector_max_consecutive = max(sector_consecutives) if sector_consecutives else 1

        # 综合判断
        score = 0
        if premium_level == "优于":
            score += 1
        if target_turnover > sector_avg_turnover:
            score += 1
        if target_consecutive >= sector_max_consecutive:
            score += 1

        # 满足2个条件则认为是龙头
        return score >= 2

    def _determine_role(self, is_leader: bool, premium_level: str) -> str:
        """确定个股在题材中的角色"""
        if is_leader:
            if premium_level == "优于":
                return "头狼（核心领涨）"
            else:
                return "中军（题材支撑）"
        else:
            if premium_level == "弱于":
                return "跟风（滞涨跟风）"
            else:
                return "羊群（题材跟随）"

    def _calculate_sector_stats(self, stocks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        计算同题材统计数据

        Args:
            stocks: 同题材股票列表

        Returns:
            统计数据
                - sector_avg_turnover: 平均成交额
                - sector_max_turnover: 最大成交额
                - sector_avg_consecutive: 平均连板天数
                - sector_max_consecutive: 最大连板天数
                - sector_avg_cap: 平均流通市值
        """
        if not stocks:
            return {}

        # 提取各项指标
        turnovers = [s.get("turnover", 0) for s in stocks]
        consecutives = [s.get("consecutive_days", 1) for s in stocks]
        caps = [s.get("circulating_market_cap", 0) for s in stocks]

        return {
            "sector_avg_turnover": round(np.mean(turnovers), 2) if turnovers else 0,
            "sector_max_turnover": round(max(turnovers), 2) if turnovers else 0,
            "sector_avg_consecutive": round(np.mean(consecutives), 1) if consecutives else 1,
            "sector_max_consecutive": max(consecutives) if consecutives else 1,
            "sector_avg_cap": round(np.mean(caps), 2) if caps else 0,
        }

    def analyze_ladder_role(
        self,
        stock_code: str,
        consecutive_days: int,
        ladder_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        分析个股在连板梯队中的角色

        Args:
            stock_code: 股票代码
            consecutive_days: 连板天数
            ladder_data: 连板梯队数据

        Returns:
            角色分析
                - role: 角色类型（头狼/中军/先锋/补涨/羊群/跟风）
                - position_in_ladder: 在梯队中的位置
                - ladder_info: 梯队信息
        """
        ladder = ladder_data.get("ladder", {})
        max_consecutive = ladder_data.get("max_consecutive", 0)

        # 确定角色
        role = ""
        role_description = ""

        if consecutive_days == max_consecutive:
            # 最高板，可能是头狼
            stocks_at_max = ladder.get(max_consecutive, [])
            if len(stocks_at_max) <= 2:
                role = "头狼"
                role_description = "最高板且数量少，可能是核心领涨"
            else:
                role = "中军"
                role_description = "最高板但数量较多，属于题材中军"
        elif consecutive_days >= max_consecutive - 1:
            # 次高板，可能是先锋或补涨
            if consecutive_days == max_consecutive:
                role = "中军"
                role_description = "同处最高板，题材中军"
            else:
                role = "先锋"
                role_description = "次高板，可能是上板先锋"
        elif consecutive_days >= 3:
            role = "中军"
            role_description = "中等高度，题材中坚力量"
        elif consecutive_days == 2:
            role = "补涨"
            role_description = "二板，题材补涨跟随"
        else:
            role = "首板"
            role_description = "首板启动，可能是新题材爆发"

        # 获取该高度的股票数量
        stocks_at_height = ladder.get(consecutive_days, [])
        position_in_ladder = {
            "height": consecutive_days,
            "count": len(stocks_at_height),
            "is_highest": consecutive_days == max_consecutive,
            "is_lowest": consecutive_days == 1,
        }

        return {
            "role": role,
            "role_description": role_description,
            "position_in_ladder": position_in_ladder,
            "ladder_max_height": max_consecutive,
        }

    def compare_with_previous_day(
        self,
        current_stocks: List[Dict[str, Any]],
        previous_stocks: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        与前一日的同题材股票对比

        Args:
            current_stocks: 当前日涨停股票
            previous_stocks: 前一日涨停股票

        Returns:
            对比结果
                - continued: 继续涨停的股票列表
                - new_added: 新涨停的股票列表
                - dropped: 消失的股票列表
                - continuation_rate: 延续率
        """
        current_codes = {s.get("stock_code") for s in current_stocks}
        previous_codes = {s.get("stock_code") for s in previous_stocks}

        continued = [
            s for s in current_stocks if s.get("stock_code") in previous_codes
        ]
        new_added = [
            s for s in current_stocks if s.get("stock_code") not in previous_codes
        ]
        dropped = [
            s for s in previous_stocks if s.get("stock_code") not in current_codes
        ]

        continuation_rate = len(continued) / len(previous_codes) if previous_codes else 0

        return {
            "continued": continued,
            "continued_count": len(continued),
            "new_added": new_added,
            "new_added_count": len(new_added),
            "dropped": dropped,
            "dropped_count": len(dropped),
            "continuation_rate": round(continuation_rate * 100, 2),
        }

    def analyze_sector_momentum(
        self, same_concept_stocks: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        分析题材动量

        Args:
            same_concept_stocks: 同题材股票列表

        Returns:
            动量分析
                - momentum_score: 动量得分（0-1）
                - momentum_rating: 动量评级
                - spread_rating: 梯队分布评级
                - consistency_rating: 一致性评级
        """
        if not same_concept_stocks:
            return {
                "momentum_score": 0,
                "momentum_rating": "无数据",
            }

        # 提取连板天数
        consecutives = [s.get("consecutive_days", 1) for s in same_concept_stocks]
        max_consecutive = max(consecutives) if consecutives else 1
        avg_consecutive = np.mean(consecutives) if consecutives else 1

        # 提取成交额
        turnovers = [s.get("turnover", 0) for s in same_concept_stocks]
        total_turnover = sum(turnovers)

        # 提取主力净流入
        inflows = [s.get("main_net_inflow", 0) for s in same_concept_stocks]
        total_inflow = sum([i for i in inflows if i > 0])

        # 动量得分计算
        # 1. 连板高度得分
        height_score = min(max_consecutive / 10, 1.0)

        # 2. 平均连板天数得分
        avg_height_score = min(avg_consecutive / 5, 1.0)

        # 3. 资金流入得分
        flow_score = min(total_inflow / (total_turnover * 100), 1.0) if total_turnover > 0 else 0

        # 综合得分
        momentum_score = height_score * 0.4 + avg_height_score * 0.4 + flow_score * 0.2

        # 动量评级
        momentum_rating = self._get_momentum_rating(momentum_score)

        # 梯队分布评级
        unique_heights = len(set(consecutives))
        spread_rating = "集中"
        if unique_heights >= 4:
            spread_rating = "梯队完整"
        elif unique_heights >= 3:
            spread_rating = "梯队较好"
        elif unique_heights >= 2:
            spread_rating = "梯队一般"
        else:
            spread_rating = "单一高度"

        # 一致性评级（连板天数的一致性）
        std_consecutive = np.std(consecutives) if len(consecutives) > 1 else 0
        consistency_ratio = 1 - min(std_consecutive / 5, 1.0)  # 标准差越小，一致性越高
        consistency_rating = "高度一致" if consistency_ratio >= 0.7 else "分散"

        return {
            "momentum_score": round(momentum_score, 2),
            "momentum_rating": momentum_rating,
            "spread_rating": spread_rating,
            "consistency_rating": consistency_rating,
            "unique_heights": unique_heights,
            "avg_consecutive": round(avg_consecutive, 1),
            "max_consecutive": max_consecutive,
        }

    def _get_momentum_rating(self, score: float) -> str:
        """获取动量评级"""
        if score >= 0.7:
            return "极强"
        elif score >= 0.5:
            return "强"
        elif score >= 0.3:
            return "中"
        elif score >= 0.1:
            return "弱"
        else:
            return "极弱"
