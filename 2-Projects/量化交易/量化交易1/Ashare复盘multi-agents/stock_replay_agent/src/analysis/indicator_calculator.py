"""
指标计算器

计算连板和趋势股的各项技术指标
"""
from typing import Dict, Any, List, Optional, Tuple
import pandas as pd
import numpy as np


class IndicatorCalculator:
    """指标计算器"""

    # ========== 连板指标计算 ==========

    @staticmethod
    def calculate_consecutive_height(consecutive_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        计算连板高度分析

        Args:
            consecutive_data: 连板数据，包含 ladder 信息

        Returns:
            连板高度分析结果
                - max_height: 最高连板天数
                - total_stocks: 总股票数
                - height_distribution: 各高度股票分布
                -梯队的健康度: 0-1之间，越高越健康
        """
        ladder = consecutive_data.get("ladder", {})
        max_height = consecutive_data.get("max_consecutive", 0)

        # 统计各高度股票数
        height_distribution = {}
        total_stocks = 0
        weighted_height = 0

        for days, stocks in ladder.items():
            count = len(stocks)
            height_distribution[days] = count
            total_stocks += count
            weighted_height += days * count

        # 计算平均连板天数
        avg_height = weighted_height / total_stocks if total_stocks > 0 else 0

        # 计算梯队健康度
        # 健康度 = (平均连板高度 / 最高连板高度) * (梯队数量 / 期望梯队数量)
        ladder_count = len(ladder)
        expected_ladder_count = min(max_height, 5)  # 期望的梯队数量
        health_score = 0
        if max_height > 0:
            height_ratio = avg_height / max_height
            ladder_ratio = min(ladder_count / expected_ladder_count, 1.0) if expected_ladder_count > 0 else 0
            health_score = height_ratio * ladder_ratio

        return {
            "max_height": max_height,
            "total_stocks": total_stocks,
            "avg_height": round(avg_height, 2),
            "height_distribution": height_distribution,
            "ladder_count": ladder_count,
            "health_score": round(health_score, 2),
            "health_rating": IndicatorCalculator._get_health_rating(health_score),
        }

    @staticmethod
    def _get_health_rating(score: float) -> str:
        """获取健康度评级"""
        if score >= 0.7:
            return "优秀"
        elif score >= 0.5:
            return "良好"
        elif score >= 0.3:
            return "一般"
        else:
            return "较差"

    @staticmethod
    def calculate_turnover_strength(
        board_stocks: List[Dict[str, Any]], market_cap: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        计算成交额强度

        Args:
            board_stocks: 涨停板股票列表
            market_cap: 流通市值（亿元），可选

        Returns:
            成交额强度分析
                - total_turnover: 总成交额
                - avg_turnover: 平均成交额
                - max_turnover: 最大成交额
                - turnover_to_cap: 换手率（成交额/流通市值）
                - turnover_rating: 评级
        """
        if not board_stocks:
            return {
                "total_turnover": 0,
                "avg_turnover": 0,
                "max_turnover": 0,
                "turnover_to_cap": 0,
                "turnover_rating": "无数据",
            }

        # 提取成交额
        turnovers = []
        for stock in board_stocks:
            turnover = stock.get("turnover", 0)
            turnovers.append(turnover)

        total_turnover = sum(turnovers)
        avg_turnover = total_turnover / len(turnovers)
        max_turnover = max(turnovers)

        # 计算换手率（成交额/流通市值）
        turnover_to_cap = 0
        turnover_rating = "一般"
        if market_cap and market_cap > 0:
            turnover_to_cap = total_turnover / market_cap
            turnover_rating = IndicatorCalculator._get_turnover_rating(turnover_to_cap)

        return {
            "total_turnover": round(total_turnover, 2),
            "avg_turnover": round(avg_turnover, 2),
            "max_turnover": round(max_turnover, 2),
            "turnover_to_cap": round(turnover_to_cap, 2),
            "turnover_rating": turnover_rating,
        }

    @staticmethod
    def _get_turnover_rating(ratio: float) -> str:
        """获取成交额评级"""
        if ratio >= 0.2:
            return "极高（人气火爆）"
        elif ratio >= 0.1:
            return "高（人气旺盛）"
        elif ratio >= 0.05:
            return "中（人气一般）"
        else:
            return "低（人气清淡）"

    @staticmethod
    def calculate_fund_flow(intraday_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        计算主力资金流向

        Args:
            intraday_data: 个股分时数据

        Returns:
            资金流向分析
                - total_inflow: 总流入（万元）
                - total_outflow: 总流出（万元）
                - net_flow: 净流入（万元）
                - flow_ratio: 流入/流出比率
                - flow_trend: 资金趋势
                - key_inflow_points: 关键流入点
        """
        df = intraday_data.get("data")
        if df is None or df.empty:
            return {
                "total_inflow": 0,
                "total_outflow": 0,
                "net_flow": 0,
                "flow_ratio": 0,
                "flow_trend": "无数据",
            }

        # 获取主力净流入
        if "main_net_inflow" in df.columns:
            main_flow = df["main_net_inflow"]
            total_inflow = main_flow[main_flow > 0].sum()
            total_outflow = abs(main_flow[main_flow < 0].sum())
        else:
            total_inflow = 0
            total_outflow = 0

        net_flow = total_inflow - total_outflow

        # 计算流入比率
        flow_ratio = 0
        if total_outflow > 0:
            flow_ratio = total_inflow / total_outflow

        # 判断资金趋势
        flow_trend = IndicatorCalculator._get_flow_trend(net_flow, flow_ratio)

        # 识别关键流入点（大幅流入点）
        key_inflow_points = []
        if "main_net_inflow" in df.columns and not df.empty:
            # 计算流入标准差
            inflow_values = df["main_net_inflow"][df["main_net_inflow"] > 0]
            if not inflow_values.empty:
                threshold = inflow_values.mean() + inflow_values.std() * 2
                key_points = df[
                    (df["main_net_inflow"] > threshold)
                    & (df["main_net_inflow"] > 0)
                ]
                for _, row in key_points.iterrows():
                    key_inflow_points.append(
                        {
                            "time": row.get("time"),
                            "price": row.get("price"),
                            "main_net_inflow": row.get("main_net_inflow"),
                        }
                    )

        return {
            "total_inflow": round(total_inflow, 2),
            "total_outflow": round(total_outflow, 2),
            "net_flow": round(net_flow, 2),
            "flow_ratio": round(flow_ratio, 2),
            "flow_trend": flow_trend,
            "key_inflow_points": key_inflow_points,
        }

    @staticmethod
    def _get_flow_trend(net_flow: float, flow_ratio: float) -> str:
        """获取资金趋势"""
        if net_flow > 0 and flow_ratio > 1.5:
            return "大幅流入（强）"
        elif net_flow > 0 and flow_ratio > 1.1:
            return "流入（中）"
        elif net_flow > 0:
            return "小幅流入（弱）"
        elif net_flow < 0 and flow_ratio < 0.5:
            return "大幅流出（弱）"
        elif net_flow < 0 and flow_ratio < 0.9:
            return "流出（中）"
        elif net_flow < 0:
            return "小幅流出（弱）"
        else:
            return "平衡"

    @staticmethod
    def calculate_board_stability(
        intraday_data: Dict[str, Any], limit_up_price: float
    ) -> Dict[str, Any]:
        """
        计算封板稳定性

        Args:
            intraday_data: 个股分时数据
            limit_up_price: 涨停价

        Returns:
            稳定性分析
                - open_count: 开板次数
                - duration_at_limit: 封板持续时长（分钟）
                - break_ratio: 炸板率
                - stability_rating: 稳定性评级
        """
        df = intraday_data.get("data")
        if df is None or df.empty:
            return {
                "open_count": 0,
                "duration_at_limit": 0,
                "break_ratio": 0,
                "stability_rating": "无数据",
            }

        # 假设涨停价为最高价
        if limit_up_price <= 0:
            limit_up_price = df["price"].max()

        # 计算涨停比例（允许小误差）
        tolerance = 0.001  # 0.1%误差
        is_limit = (df["price"] >= limit_up_price * (1 - tolerance)).values

        # 统计开板次数（从涨停状态变为非涨停状态）
        open_count = 0
        prev_state = True
        for state in is_limit:
            if prev_state and not state:
                open_count += 1
            prev_state = state

        # 计算封板持续时长
        duration_at_limit = sum(is_limit)  # 每条记录代表约1分钟

        # 计算炸板率
        total_points = len(df)
        break_ratio = (total_points - duration_at_limit) / total_points if total_points > 0 else 0

        # 评级
        stability_rating = IndicatorCalculator._get_stability_rating(break_ratio, open_count)

        return {
            "open_count": open_count,
            "duration_at_limit": duration_at_limit,
            "break_ratio": round(break_ratio, 2),
            "stability_rating": stability_rating,
        }

    @staticmethod
    def _get_stability_rating(break_ratio: float, open_count: int) -> str:
        """获取稳性评级"""
        if break_ratio <= 0.05 and open_count <= 1:
            return "超强（一封到底）"
        elif break_ratio <= 0.15 and open_count <= 2:
            return "强（多次封板）"
        elif break_ratio <= 0.3:
            return "中等（多次炸板）"
        elif break_ratio <= 0.5:
            return "弱（频繁炸板）"
        else:
            return "极弱（烂板）"

    @staticmethod
    def analyze_turnover_board(
        turnover_data: Dict[str, Any], board_stability: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        分析换手板

        Args:
            turnover_data: 成交额数据
            board_stability: 板稳定性数据

        Returns:
            换手板分析
                - is_turnover_board: 是否为换手板
                - turnover_level: 换手程度
                - estimated_participants: 估算参与人数
                - recommendation: 操作建议
        """
        turnover_ratio = turnover_data.get("turnover_to_cap", 0)
        stability = board_stability.get("stability_rating", "")
        open_count = board_stability.get("open_count", 0)

        # 判断是否为换手板
        is_turnover_board = turnover_ratio >= 0.1 and open_count >= 2

        # 换手程度
        if turnover_ratio >= 0.2:
            turnover_level = "巨量换手"
        elif turnover_ratio >= 0.1:
            turnover_level = "大换手"
        elif turnover_ratio >= 0.05:
            turnover_level = "适中换手"
        else:
            turnover_level = "低换手"

        # 操作建议
        recommendation = "观望"
        if is_turnover_board:
            if "强" in stability:
                recommendation = "换手板，关注回封机会"
            else:
                recommendation = "换手失败，风险较高"
        else:
            if "超强" in stability:
                recommendation = "硬板，可考虑排板"
            elif "强" in stability:
                recommendation = "稳定板，关注上板机会"

        return {
            "is_turnover_board": is_turnover_board,
            "turnover_level": turnover_level,
            "estimated_participants": IndicatorCalculator._estimate_participants(turnover_ratio),
            "recommendation": recommendation,
        }

    @staticmethod
    def _estimate_participants(turnover_ratio: float) -> str:
        """估算参与人数等级"""
        if turnover_ratio >= 0.3:
            return "极多（游资云集）"
        elif turnover_ratio >= 0.2:
            return "多（机构参与）"
        elif turnover_ratio >= 0.1:
            return "中（混合资金）"
        elif turnover_ratio >= 0.05:
            return "少（散户为主）"
        else:
            return "极少（自然封板）"

    # ========== 趋势股指标计算 ==========

    @staticmethod
    def identify_trend_pattern(
        prices: List[float], volumes: Optional[List[float]] = None
    ) -> Dict[str, Any]:
        """
        识别趋势形态

        Args:
            prices: 价格序列
            volumes: 成交量序列，可选

        Returns:
            趋势形态分析
                - pattern_type: 主升浪/反弹/震荡/筑底/下跌
                - stage: 当前阶段（初期/中期/后期）
                - strength: 趋势强度
                - duration_days: 持续天数
                - key_points: 关键点位
        """
        if len(prices) < 5:
            return {
                "pattern_type": "数据不足",
                "stage": "未知",
                "strength": 0,
                "duration_days": len(prices),
            }

        prices_array = np.array(prices)

        # 计算趋势斜率（线性回归）
        x = np.arange(len(prices))
        coeffs = np.polyfit(x, prices_array, 1)
        slope = coeffs[0]
        intercept = coeffs[1]

        # 计算R²（拟合优度）
        y_pred = np.polyval(coeffs, x)
        ss_res = np.sum((prices_array - y_pred) ** 2)
        ss_tot = np.sum((prices_array - np.mean(prices_array)) ** 2)
        r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0

        # 判断趋势类型
        pattern_type = ""
        stage = ""

        if slope > 0 and r_squared > 0.6:
            pattern_type = "主升浪"
            # 根据价格位置判断阶段
            price_range = max(prices) - min(prices)
            current_price = prices[-1]
            progress = (current_price - min(prices)) / price_range if price_range > 0 else 0.5
            if progress < 0.3:
                stage = "初期"
            elif progress < 0.7:
                stage = "中期"
            else:
                stage = "后期"
        elif slope > 0 and r_squared > 0.3:
            pattern_type = "反弹"
            stage = "进行中"
        elif abs(slope) < np.std(prices_array) * 0.1:
            pattern_type = "震荡"
            stage = "平台整理"
        elif slope < 0 and r_squared > 0.5:
            pattern_type = "下跌"
            stage = "进行中"
        else:
            # 检查是否为筑底
            if IndicatorCalculator._is_bottoming(prices):
                pattern_type = "筑底"
                stage = "构筑中"
            else:
                pattern_type = "震荡"
                stage = "不确定"

        # 计算趋势强度
        strength = abs(slope) / np.std(prices_array) if np.std(prices_array) > 0 else 0
        strength = min(max(strength, 0), 1)  # 归一化到0-1

        # 识别关键点位（局部极值点）
        key_points = IndicatorCalculator._find_key_points(prices)

        return {
            "pattern_type": pattern_type,
            "stage": stage,
            "strength": round(strength, 2),
            "strength_rating": IndicatorCalculator._get_strength_rating(strength),
            "duration_days": len(prices),
            "slope": round(slope, 4),
            "r_squared": round(r_squared, 4),
            "key_points": key_points,
        }

    @staticmethod
    def _is_bottoming(prices: List[float]) -> bool:
        """判断是否为筑底形态"""
        if len(prices) < 5:
            return False

        # 检查是否有明显的底部特征：先下跌后横盘
        prices_array = np.array(prices)
        mid_point = len(prices) // 2
        first_half = prices_array[:mid_point]
        second_half = prices_array[mid_point:]

        # 前半段下跌
        first_trend = np.polyfit(np.arange(len(first_half)), first_half, 1)[0]

        # 后半段波动小（横盘）
        second_std = np.std(second_half)
        first_std = np.std(first_half)

        return first_trend < 0 and second_std < first_std * 0.5

    @staticmethod
    def _find_key_points(prices: List[float]) -> List[Dict[str, Any]]:
        """找出关键点位（局部极值点）"""
        if len(prices) < 5:
            return []

        key_points = []
        window = 3  # 窗口大小

        for i in range(window, len(prices) - window):
            window_prices = prices[i - window : i + window + 1]
            current = prices[i]

            # 检查是否为局部最高点
            if current == max(window_prices):
                key_points.append(
                    {"index": i, "price": current, "type": "local_high"}
                )
            # 检查是否为局部最低点
            elif current == min(window_prices):
                key_points.append(
                    {"index": i, "price": current, "type": "local_low"}
                )

        return key_points

    @staticmethod
    def _get_strength_rating(strength: float) -> str:
        """获取趋势强度评级"""
        if strength >= 0.7:
            return "强"
        elif strength >= 0.4:
            return "中"
        else:
            return "弱"

    @staticmethod
    def analyze_volume_price_relation(
        prices: List[float], volumes: List[float]
    ) -> Dict[str, Any]:
        """
        分析量价关系

        Args:
            prices: 价格序列
            volumes: 成交量序列

        Returns:
            量价关系分析
                - relationship: 量价齐升/量价背离/缩量上涨/放量下跌/无规律
                - price_trend: 价格趋势
                - volume_trend: 成交量趋势
                - correlation: 价格和成交量的相关系数
        """
        if len(prices) != len(volumes) or len(prices) < 3:
            return {
                "relationship": "数据不足",
                "price_trend": "未知",
                "volume_trend": "未知",
                "correlation": 0,
            }

        prices_array = np.array(prices)
        volumes_array = np.array(volumes)

        # 计算价格趋势
        price_slope = np.polyfit(np.arange(len(prices)), prices_array, 1)[0]
        price_trend = "上涨" if price_slope > 0 else "下跌"

        # 计算成交量趋势
        volume_slope = np.polyfit(np.arange(len(volumes)), volumes_array, 1)[0]
        if volume_slope > 0:
            volume_trend = "放量"
        elif volume_slope < 0:
            volume_trend = "缩量"
        else:
            volume_trend = "平稳"

        # 计算相关系数
        correlation = np.corrcoef(prices_array, volumes_array)[0, 1]

        # 判断量价关系
        relationship = ""
        if correlation > 0.5:
            relationship = "量价齐升（健康）"
        elif correlation < -0.5:
            relationship = "量价背离（注意）"
        elif price_slope > 0 and volume_slope < 0:
            relationship = "缩量上涨（动能减弱）"
        elif price_slope < 0 and volume_slope > 0:
            relationship = "放量下跌（恐慌出逃）"
        else:
            relationship = "无规律（震荡）"

        return {
            "relationship": relationship,
            "price_trend": price_trend,
            "volume_trend": volume_trend,
            "correlation": round(correlation, 3),
            "relationship_rating": IndicatorCalculator._get_relation_rating(correlation),
        }

    @staticmethod
    def _get_relation_rating(correlation: float) -> str:
        """获取量价关系评级"""
        abs_corr = abs(correlation)
        if abs_corr >= 0.7:
            return "高度相关"
        elif abs_corr >= 0.4:
            return "中度相关"
        elif abs_corr >= 0.2:
            return "低度相关"
        else:
            return "无明显相关"

    @staticmethod
    def calculate_moving_average_bias(
        prices: List[float],
        periods: List[int] = [5, 10, 20, 60],
    ) -> Dict[str, Any]:
        """
        计算均线乖离率

        Args:
            prices: 价格序列
            periods: 均线周期列表

        Returns:
            均线分析结果
                - mas: 各周期均线值
                - biases: 各周期乖离率
                - alignment: 均线排列状态（多头/空头/缠绕/发散）
                - support_level: 支撑位
                - resistance_level: 压力位
        """
        if len(prices) < max(periods):
            return {
                "mas": {},
                "biases": {},
                "alignment": "数据不足",
            }

        prices_array = np.array(prices)
        current_price = prices[-1]
        result = {}

        # 计算各周期均线
        mas = {}
        biases = {}
        for period in periods:
            if len(prices) >= period:
                ma = np.mean(prices_array[-period:])
                mas[f"ma{period}"] = round(ma, 2)
                bias = ((current_price - ma) / ma) * 100 if ma > 0 else 0
                biases[f"bias{period}"] = round(bias, 2)

        result["mas"] = mas
        result["biases"] = biases

        # 判断均线排列
        if len(prices) >= 60:
            alignment = IndicatorCalculator._determine_ma_alignment(prices)
            result["alignment"] = alignment
        else:
            result["alignment"] = "数据不足"

        # 支撑位和压力位
        if "ma20" in mas:
            result["support_level"] = mas["ma20"]
        if "ma5" in mas:
            result["resistance_level"] = mas["ma5"]

        return result

    @staticmethod
    def _determine_ma_alignment(prices: List[float]) -> str:
        """判断均线排列"""
        prices_array = np.array(prices)
        current_price = prices[-1]

        ma5 = np.mean(prices_array[-5:])
        ma10 = np.mean(prices_array[-10:])
        ma20 = np.mean(prices_array[-20:])
        ma60 = np.mean(prices_array[-60:])

        # 检查多头排列：MA5 > MA10 > MA20 > MA60
        if ma5 > ma10 > ma20 > ma60:
            # 检查价格是否在均线上方
            if current_price > ma5:
                return "多头排列（强势）"
            else:
                return "多头排列（价格回调）"

        # 检查空头排列：MA5 < MA10 < MA20 < MA60
        elif ma5 < ma10 < ma20 < ma60:
            if current_price < ma5:
                return "空头排列（弱势）"
            else:
                return "空头排列（价格反弹）"

        # 检查缠绕
        elif ma20 / ma60 > 0.95 and ma20 / ma60 < 1.05:
            return "缠绕（变盘点）"

        # 检查发散
        elif (ma5 - ma60) / ma60 > 0.1:
            return "发散（方向不明）"
        else:
            return "混合"

    @staticmethod
    def calculate_relative_strength(
        stock_prices: List[float],
        index_prices: List[float],
    ) -> Dict[str, Any]:
        """
        计算相对强度（个股相对于大盘）

        Args:
            stock_prices: 个股价格序列
            index_prices: 指数价格序列

        Returns:
            相对强度分析
                - relative_strength: 相对强度值
                - beta: Beta系数
               ression: 超额收益序列
                - outperformance: 是否跑赢大盘
                - outperformance_pct: 跑赢百分比
        """
        if len(stock_prices) != len(index_prices) or len(stock_prices) < 3:
            return {
                "relative_strength": 0,
                "beta": 0,
                "outperformance": False,
                "outperformance_pct": 0,
            }

        stock_array = np.array(stock_prices)
        index_array = np.array(index_prices)

        # 计算收益率
        stock_returns = np.diff(stock_array) / stock_array[:-1]
        index_returns = np.diff(index_array) / index_array[:-1]

        # 计算相对强度（超额收益总和）
        excess_returns = stock_returns - index_returns
        relative_strength = np.mean(excess_returns)

        # 计算Beta系数
        if np.var(index_returns) > 0:
            beta = np.cov(stock_returns, index_returns)[0, 1] / np.var(
                index_returns
            )
        else:
            beta = 1.0

        # 计算整体跑赢情况
        stock_total_return = (stock_array[-1] - stock_array[0]) / stock_array[0]
        index_total_return = (index_array[-1] - index_array[0]) / index_array[0]
        outperformance = stock_total_return > index_total_return
        outperformance_pct = stock_total_return - index_total_return

        return {
            "relative_strength": round(relative_strength, 4),
            "beta": round(beta, 2),
            "excess_returns": [round(x, 4) for x in excess_returns.tolist()],
            "outperformance": outperformance,
            "outperformance_pct": round(outperformance_pct * 100, 2),
            "strength_rating": IndicatorCalculator._get_rs_rating(relative_strength),
        }

    @staticmethod
    def _get_rs_rating(rs: float) -> str:
        """获取相对强度评级"""
        if rs > 0.01:
            return "远强于大盘"
        elif rs > 0.003:
            return "强于大盘"
        elif rs > 0:
            return "略强于大盘"
        elif rs > -0.003:
            return "略弱于大盘"
        elif rs > -0.01:
            return "弱于大盘"
        else:
            return "远弱于大盘"
