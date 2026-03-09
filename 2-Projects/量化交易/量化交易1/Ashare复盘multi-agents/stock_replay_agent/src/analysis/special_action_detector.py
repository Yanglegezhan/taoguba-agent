"""
特殊动作检测器

检测个股的特殊动作：领涨、逆跌、反核
"""
from typing import Dict, Any, List, Optional, Tuple
import pandas as pd
import numpy as np


class SpecialActionDetector:
    """特殊动作检测器"""

    # 配置参数
    DEFAULT_CONFIG = {
        # 领涨检测
        "leading": {
            "time_window": 30,  # 开盘后30分钟内检测
            "min_price_change": 0.01,  # 价格变化至少1%
            "min_flow_ratio": 1.5,  # 流入/流出比率至少1.5
            "min_flow_threshold": 100_000,  # 最小流入金额（10万元）
        },
        # 逆跌检测
        "reverse_fall": {
            "min_index_drop": -0.015,  # 大盘跌幅至少至少-1.5%
            "max_stock_drop": -0.01,  # 个股跌幅不超过-1%
            "min_hold_time": 10,  # 至少承接10分钟
        },
        # 反核检测
        "anti_nuclear": {
            "min_open_drop": -0.08,  # 开盘跌幅至少-8%
            "max_open_drop": -0.099,  # 跌停开或接近跌停
            "min_rebound_high": 0.05,  # 盘中拉升至+5%以上
            "min_flow_amount": 100_000,  # 最小流入金额（10万元）
        },
    }

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化检测器

        Args:
            config: 检测配置，可选
        """
        self.config = config if config is None else self.DEFAULT_CONFIG.copy()

    def detect_leading_action(
        self, stock_intraday: Dict[str, Any], market_cap: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        检测领涨动作（早盘第一笔大单进攻点）

        Args:
            stock_intraday: 个股分时数据
            market_cap: 流通市值（亿元），可选

        Returns:
            领涨动作检测结果
                - detected: 是否检测到领涨
                - timestamp: 检测时间点
                - price: 检测时刻价格
                - volume: 检测时刻成交量
                - main_net_inflow: 检测时刻主力净流入
                - description: 动作描述
                - confidence: 置信度（0-1）
        """
        df = stock_intraday.get("data")
        if df is None or df.empty:
            return self._no_detection("no_data")

        config = self.config["leading"]
        time_window = config["time_window"]
        min_price_change = config["min_price_change"]
        min_flow_ratio = config["min_flow_ratio"]
        min_flow_threshold = config["min_flow_threshold"]

        # 获取开盘价
        open_price = stock_intraday.get("begin_px")
        if open_price is None or open_price <= 0:
            open_price = df.iloc[0]["price"] if len(df) > 0 else 0

        if open_price <= 0:
            return self._no_detection("no_open_price")

        # 筛选早盘时间窗口内的数据
        df["time_num"] = df["time"].apply(self._time_to_minutes)
        early_df = df[df["time_num"] <= time_window]

        if early_df.empty:
            return self._no_detection("no_early_data")

        # 寻找大单流入点
        if "main_net_inflow" not in df.columns:
            return self._no_detection("no_flow_data")

        # 计算流入比率
        inflow_mask = early_df["main_net_inflow"] > min_flow_threshold
        inflow_points = early_df[inflow_mask]

        if inflow_points.empty:
            return self._no_detection("no_inflow")

        # 找到流入最大的点
        max_inflow_idx = inflow_points["main_net_inflow"].idxmax()
        max_inflow_row = inflow_points.loc[max_inflow_idx]

        # 检查价格是否突破
        price_change = (max_inflow_row["price"] - open_price) / open_price

        if abs(price_change) < min_price_change:
            return self._no_detection("price_no_change")

        # 计算流入/流出比率
        total_inflow = early_df[early_df["main_net_inflow"] > 0][
            "main_net_inflow"
        ].sum()
        total_outflow = abs(
            early_df[early_df["main_net_inflow"] < 0][
                "main_net_inflow"
            ].sum()
        )
        flow_ratio = total_inflow / total_outflow if total_outflow > 0 else 0

        # 判断是否为领涨
        is_leading = flow_ratio >= min_flow_ratio and price_change > 0

        confidence = self._calculate_leading_confidence(
            flow_ratio, price_change, max_inflow_row["main_net_inflow"]
        )

        description = self._generate_leading_description(
            max_inflow_row, open_price, price_change, flow_ratio, market_cap
        )

        return {
            "detected": is_leading,
            "timestamp": max_inflow_row["time"],
            "price": max_inflow_row["price"],
            "volume": max_inflow_row.get("volume", 0),
            "main_net_inflow": max_inflow_row["main_net_inflow"],
            "open_price": open_price,
            "price_change": round(price_change * 100, 2),
            "flow_ratio": round(flow_ratio, 2),
            "description": description,
            "confidence": round(confidence, 2),
        }

    def _time_to_minutes(self, time_str: str) -> int:
        """将时间字符串转换为分钟数"""
        try:
            parts = time_str.split(":")
            hours = int(parts[0]) if len(parts) > 0 else 0
            minutes = int(parts[1]) if len(parts) > 1 else 0
            return hours * 60 + minutes
        except:
            return 0

    def _no_detection(self, reason: str) -> Dict[str, Any]:
        """返回未检测到结果"""
        return {
            "detected": False,
            "timestamp": None,
            "price": None,
            "volume": None,
            "main_net_inflow": None,
            "description": f"未检测到: {reason}",
            "confidence": 0.0,
        }

    def _calculate_leading_confidence(
        self, flow_ratio: float, price_change: float, flow_amount: float
    ) -> float:
        """计算领涨检测的置信度"""
        # 流入比率权重
        flow_ratio_score = min(flow_ratio / 2.0, 1.0)  # 归一化
        # 价格变化权重
        price_change_score = min(abs(price_change) / 0.05, 1.0)  # 5%变化为满分
        # 流入金额权重
        flow_amount_score = min(flow_amount / 500_000, 1.0)  # 50万元流入为满分

        # 加权平均
        confidence = (
            flow_ratio_score * 0.4
            + price_change_score * 0.4
            + flow_amount_score * 0.2
        )
        return confidence

    def _generate_leading_description(
        self,
        row: pd.Series,
        open_price: float,
        price_change: float,
        flow_ratio: float,
        market_cap: Optional[float],
    ) -> str:
        """生成领涨动作描述"""
        time_desc = row["time"]
        price_desc = f"{row['price']:.2f}"
        change_desc = f"{price_change * 100:+.2f}%"
        flow_desc = f"{row['main_net_inflow'] / 10000:.1f}万"

        parts = [
            f"{time_desc}时，",
            f"价格{price_desc}（{change_desc}），",
            f"主力净流入{flow_desc}，",
            f"流入比{flow_ratio:.1f}倍。",
        ]

        if market_cap and market_cap > 0:
            parts.append(f"流通市值{market_cap:.1f}亿。")

        return "".join(parts)

    def detect_reverse_fall_action(
        self,
        stock_intraday: Dict[str, Any],
        index_intraday: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        检测逆跌动作（大盘跳水期间的个股表现）

        Args:
            stock_intraday: 个股分时数据
            index_intraday: 大盘指数分时数据

        Returns:
            逆跌动作检测结果
                - detected: 是否检测到逆跌
                - timestamp: 检测时间点
                - description: 动作描述
                - confidence: 置信度（0-1）
                - stock_during_index_drop: 大盘下跌期间个股表现
        """
        stock_df = stock_intraday.get("data")
        index_df = index_intraday.get("data")

        if stock_df is None or stock_df.empty or index_df is None or index_df.empty:
            return self._no_detection("no_data")

        config = self.config["reverse_fall"]
        min_index_drop = config["min_index_drop"]
        max_stock_drop = config["max_stock_drop"]
        min_hold_time = config["min_hold_time"]

        # 找出大盘下跌时段
        index_df["pct_change_raw"] = index_df["pct_change"]
        drop_periods = self._find_drop_periods(index_df, min_index_drop)

        if not drop_periods:
            return self._.no_detection("no_index_drop")

        # 分析个股在大盘下跌期间的表现
        stock_during_drops = []
        for start_idx, end_idx in drop_periods:
            if start_idx < len(stock_df) and end_idx < len(stock_df):
                stock_period = stock_df.iloc[start_idx : end_idx + 1]
                stock_during_drops.append(stock_period)

        if not stock_during_drops:
            return self._.no_detection("stock_data_not_aligned")

        # 分析表现：横盘承接或逆势拉升
        is_reverse_fall = False
        best_period = None
        best_confidence = 0

        for i, period in enumerate(stock_during_drops):
            if period.empty:
                continue

            # 计算个股在该期间的表现
            start_price = period.iloc[0]["price"]
            end_price = period.iloc[-1]["price"]
            period_return = (end_price - start_price) / start_price

            # 判断是否为逆跌（横盘或上涨）
            if period_return >= max_stock_drop:
                is_reverse_fall = True

                # 计算置信度
                period_duration = len(period)
                confidence = self._calculate_reverse_confidence(
                    period_return, period_duration, min_hold_time
                )

                if confidence > best_confidence:
                    best_confidence = confidence
                    best_period = {
                        "index": i,
                        "start_time": period.iloc[0]["time"],
                        "end_time": period.iloc[-1]["time"],
                        "duration": period_duration,
                        "start_price": start_price,
                        "end_price": end_price,
                        "return": period_return,
                    }

        if not is_reverse_fall or best_period is None:
            return self._no_detection("no_reverse_behavior")

        description = self._generate_reverse_description(best_period)

        return {
            "detected": is_reverse_fall,
            "timestamp": best_period["start_time"],
            "description": description,
            "confidence": round(best_confidence, 2),
            "stock_during_index_drop": best_period,
        }

    def _find_drop_periods(
        self, index_df: pd.DataFrame, min_drop: float
    ) -> List[Tuple[int, int]]:
        """找出大盘下跌时段"""
        drop_periods = []
        in_drop = False
        start_idx = 0

        for idx, row in index_df.iterrows():
            pct_change = row.get("pct_change", 0)
            raw_change = row.get("pct_change_raw", 0)

            # 使用原始数据（如果有的话）
            drop_value = raw_change if raw_change != 0 else pct_change

            if drop_value <= min_drop and not in_drop:
                # 开始下跌
                in_drop = True
                start_idx = idx
            elif drop_value > min_drop / 2 and in_drop:
                # 结束下跌（反弹到阈值一半以上）
                in_drop = False
                if idx - start_idx >= 5:  # 至少5分钟
                    drop_periods.append((start_idx, idx))

        # 处理最后一个下跌时段
        if in_drop:
            if len(index_df) - start_idx >= 5:
                drop_periods.append((start_idx, len(index_df) - 1))

        return drop_periods

    def _calculate_reverse_confidence(
        self, period_return: float, period_duration: int, min_hold_time: int
    ) -> float:
        """计算逆跌检测的置信度"""
        # 收益率评分
        return_score = min(max(period_return, 0) / 0.02, 1.0)  # +2%为满分

        # 持续时间评分
        duration_score = min(period_duration / min_hold_time, 1.0)

        # 加权平均
        confidence = return_score * 0.7 + duration_score * 0.3
        return confidence

    def _generate_reverse_description(self, period: Dict[str, Any]) -> str:
        """生成逆跌动作描述"""
        return_str = period["return"] * 100
        return (
            f"大盘跳水期间（{period['start_time']}-{period['end_time']}），"
            f"个股横盘承接，期间涨幅{return_str:+.2f}%，"
            f"持续时间{period['duration']}分钟。"
        )

    def detect_anti_nuclear_action(
        self,
        stock_intraday: Dict[str, Any],
        prev_day_limit_down: bool = False,
    ) -> Dict[str, Any]:
        """
        检测反核动作（昨日跌停或深开后的反弹）

        Args:
            stock_intraday: 个股分时数据
            prev_day_limit_down: 昨日是否跌停

        Returns:
            反核动作检测结果
                - detected: 是否检测到反核
                - timestamp: 检测时间点
                - description: 动作描述
                - confidence: 置信度（0-1）
        """
        df = stock_intraday.get("data")
        if df is None or df.empty:
            return self._no_detection("no_data")

        config = self.config["anti_nuclear"]
        min_open_drop = config["min_open_drop"]
        max_open_drop = config["max_open_drop"]
        min_rebound_high = config["min_rebound_high"]
        min_flow_amount = config["min_flow_amount"]

        # 获取昨收价
        preclose_px = stock_intraday.get("preclose_px")
        open_price = stock_intraday.get("begin_px")

        if preclose_px is None or open_price is None or preclose_px <= 0:
            return self._no_detection("no_preopen_data")

        # 计算开盘跌幅
        open_drop = (open_price - preclose_px) / preclose_px

        # 判断是否深开（接近跌停）
        is_deep_open = (
            open_drop >= min_open_drop
            or prev_day_limit_down
            or open_drop <= max_open_drop
        )

        if not is_deep_open:
            return self._no_detection("not_deep_open")

        # 寻找盘中高点
        df["pct_change_from_open"] = (
            (df["price"] - open_price) / open_price * 100
        )

        # 找到最大涨幅时刻
        max_rebound_row = df.loc[df["pct_change_from_open"].idxmax()]
        max_rebound_pct = max_rebound_row["pct_change_from_open"]

        # 判断是否反核（拉升至+5%以上）
        if max_rebound_pct < min_rebound_high:
            return self._no_detection("no_rebound")

        # 检查是否有大量资金点火
        detected = True
        flow_amount = 0
        if "main_net_inflow" in df.columns:
            # 计算反弹期间的总流入
            rebound_mask = df["pct_change_from_open"] > 0
            flow_amount = df[rebound_mask]["main_net_inflow"].sum()

            if flow_amount < min_flow_amount:
                detected = False

        # 计算置信度
        confidence = self._calculate_anti_nuclear_confidence(
            open_drop, max_rebound_pct, flow_amount
        )

        description = self._generate_anti_nuclear_description(
            open_price,
            preclose_px,
            max_rebound_row["price"],
            open_drop,
            max_rebound_pct,
            flow_amount,
        )

        return {
            "detected": detected,
            "timestamp": max_rebound_row["time"],
            "price": max_rebound_row["price"],
            "volume": max_rebound_row.get("volume", 0),
            "main_net_inflow": flow_amount,
            "open_price": open_price,
            "preclose_price": preclose_px,
            "open_drop": round(open_drop * 100, 2),
            "max_rebound_pct": round(max_rebound_pct, 2),
            "description": description,
            "confidence": round(confidence, 2),
        }

    def _calculate_anti_nuclear_confidence(
        self, open_drop: float, max_rebound_pct: float, flow_amount: float
    ) -> float:
        """计算反核检测的置信度"""
        # 开盘跌幅评分
        drop_score = min(abs(open_drop) / 0.1, 1.0)  # 10%跌幅为满分

        # 反弹幅度评分
        rebound_score = min(max_rebound_pct / 0.1, 1.0)  # 10%反弹为满分

        # 资金点火评分
        flow_score = min(flow_amount / 500_000, 1.0)  # 50万元为满分

        # 加权平均
        confidence = drop_score * 0.3 + rebound_score * 0.5 + flow_score * 0.2
        return confidence

    def _generate_anti_nuclear_description(
        self,
        open_price: float,
        preclose_px: float,
        high_price: float,
        open_drop: float,
        max_rebound_pct: float,
        flow_amount: float,
    ) -> str:
        """生成反核动作描述"""
        open_drop_str = open_drop * 100

        parts = [
            f"昨收{preclose_px:.2f}，",
            f"今开{open_price:.2f}（{open_drop_str:+.2f}%），",
            f"盘中拉升至{high_price:.2f}（+{max_rebound_pct:.2f}%），",
        ]

        if flow_amount > 0:
            parts.append(f"主力净流入{flow_amount / 10000:.1f}万，")

        parts.append("呈现反核形态。")

        return "".join(parts)

    def detect_all_special_actions(
        self,
        stock_intraday: Dict[str, Any],
        index_intraday: Optional[Dict[str, Any]] = None,
        market_cap: Optional[float] = None,
        prev_day_limit_down: bool = False,
    ) -> Dict[str, Dict[str, Any]]:
        """
        检测所有特殊动作

        Args:
            stock_intraday: 个股分时数据
            index_intraday: 大盘指数分时数据（可选）
            market_cap: 流通市值（可选）
            prev_day_limit_down: 昨日是否跌停（可选）

        Returns:
            所有检测结果
                - leading: 领涨检测
                - reverse_fall: 逆跌检测
                - anti_nuclear: 反核检测
        """
        results = {}

        # 领涨检测
        results["leading"] = self.detect_leading_action(stock_intraday, market_cap)

        # 逆跌检测（需要大盘数据）
        if index_intraday:
            results["reverse_fall"] = self.detect_reverse_fall_action(
                stock_intraday, index_intraday
            )
        else:
            results["reverse"] = self._no_detection("no_index_data")

        # 反核检测
        results["anti_nuclear"] = self.detect_anti_nuclear_action(
            stock_intraday, prev_day_limit_down
        )

        return results
