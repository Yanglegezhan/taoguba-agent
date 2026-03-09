"""
量化交易策略集合
包含A股、加密货币、外汇等多种市场策略
"""

import numpy as np
import pandas as pd
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Signal(Enum):
    """交易信号"""
    BUY = 1
    SELL = -1
    HOLD = 0


@dataclass
class TradeSignal:
    """交易信号详情"""
    symbol: str
    signal: Signal
    confidence: float  # 0-1
    entry_price: float
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    reason: str = ""
    timestamp: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "signal": self.signal.name,
            "confidence": self.confidence,
            "entry_price": self.entry_price,
            "stop_loss": self.stop_loss,
            "take_profit": self.take_profit,
            "reason": self.reason,
            "timestamp": self.timestamp
        }


class TechnicalIndicators:
    """技术指标计算"""

    @staticmethod
    def sma(data: pd.Series, window: int) -> pd.Series:
        """简单移动平均"""
        return data.rolling(window=window).mean()

    @staticmethod
    def ema(data: pd.Series, window: int) -> pd.Series:
        """指数移动平均"""
        return data.ewm(span=window, adjust=False).mean()

    @staticmethod
    def macd(data: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """MACD指标"""
        ema_fast = TechnicalIndicators.ema(data, fast)
        ema_slow = TechnicalIndicators.ema(data, slow)
        macd_line = ema_fast - ema_slow
        signal_line = TechnicalIndicators.ema(macd_line, signal)
        histogram = macd_line - signal_line
        return macd_line, signal_line, histogram

    @staticmethod
    def rsi(data: pd.Series, window: int = 14) -> pd.Series:
        """相对强弱指标"""
        delta = data.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

    @staticmethod
    def bollinger_bands(data: pd.Series, window: int = 20, num_std: float = 2) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """布林带"""
        sma = TechnicalIndicators.sma(data, window)
        std = data.rolling(window=window).std()
        upper = sma + (num_std * std)
        lower = sma - (num_std * std)
        return upper, sma, lower

    @staticmethod
    def atr(high: pd.Series, low: pd.Series, close: pd.Series, window: int = 14) -> pd.Series:
        """平均真实波幅"""
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=window).mean()
        return atr

    @staticmethod
    def volume_ratio(volume: pd.Series, window: int = 5) -> pd.Series:
        """量比"""
        avg_volume = volume.rolling(window=window).mean()
        return volume / avg_volume


class MACDStrategy:
    """MACD趋势跟踪策略"""

    def __init__(self, fast: int = 12, slow: int = 26, signal: int = 9):
        self.fast = fast
        self.slow = slow
        self.signal = signal

    def generate_signals(self, df: pd.DataFrame) -> List[TradeSignal]:
        """
        生成交易信号

        Args:
            df: 包含'close'价格的数据框

        Returns:
            交易信号列表
        """
        close = df['close']
        macd_line, signal_line, histogram = TechnicalIndicators.macd(close, self.fast, self.slow, self.signal)

        signals = []

        # 检测MACD金叉和死叉
        for i in range(1, len(df)):
            prev_hist = histogram.iloc[i-1]
            curr_hist = histogram.iloc[i]

            # 金叉（买入信号）
            if prev_hist < 0 and curr_hist > 0:
                signals.append(TradeSignal(
                    symbol=df.iloc[i].get('symbol', 'UNKNOWN'),
                    signal=Signal.BUY,
                    confidence=0.7,
                    entry_price=close.iloc[i],
                    stop_loss=close.iloc[i] * 0.95,
                    take_profit=close.iloc[i] * 1.1,
                    reason=f"MACD金叉，Histogram从{prev_hist:.4f}转为{curr_hist:.4f}",
                    timestamp=df.index[i].isoformat() if hasattr(df.index[i], 'isoformat') else str(df.index[i])
                ))

            # 死叉（卖出信号）
            elif prev_hist > 0 and curr_hist < 0:
                   signals.append(TradeSignal(
                    symbol=df.iloc[i].get('symbol', 'UNKNOWN'),
                    signal=Signal.SELL,
                    confidence=0.7,
                    entry_price=close.iloc[i],
                    reason=f"MACD死叉，Histogram从{prev_hist:.4f}转为{curr_hist:.4f}",
                    timestamp=df.index[i].isoformat() if hasattr(df.index[i], 'isoformat') else str(df.index[i])
                ))

        return signals


class RSIStrategy:
    """RSI超买超卖策略"""

    def __init__(self, window: int = 14, overbought: float = 70, oversold: float = 30):
        self.window = window
        self.overbought = overbought
        self.oversold = oversold

    def generate_signals(self, df: pd.DataFrame) -> List[TradeSignal]:
        close = df['close']
        rsi = TechnicalIndicators.rsi(close, self.window)

        signals = []

        for i in range(1, len(df)):
            curr_rsi = rsi.iloc[i]
            prev_rsi = rsi.iloc[i-1]

            # 超卖反弹（买入）
            if prev_rsi < self.oversold and curr_rsi >= self.oversold:
                signals.append(TradeSignal(
                    symbol=df.iloc[i].get('symbol', 'UNKNOWN'),
                    signal=Signal.BUY,
                    confidence=0.6,
                    entry_price=close.iloc[i],
                    stop_loss=close.iloc[i] * 0.93,
                    take_profit=close.iloc[i] * 1.1,
                    reason=f"RSI从超卖区域反弹，RSI={curr_rsi:.2f}",
                    timestamp=df.index[i].isoformat() if hasattr(df.index[i], 'isoformat') else str(df.index[i])
                ))

            # 超买回调（卖出）
            elif prev_rsi > self.overbought and curr_rsi <= self.overbought:
                signals.append(TradeSignal(
                    symbol=df.iloc[i].get('symbol', 'UNKNOWN'),
                    signal=Signal.SELL,
                    confidence=0.6,
                    entry_price=close.iloc[i],
                    reason=f"RSI从超买区域回调，RSI={curr_rsi:.2f}",
                    timestamp=df.index[i].isoformat() if hasattr(df.index[i], 'isoformat') else str(df.index[i])
                ))

        return signals


class BollingerBandsStrategy:
    """布林带突破策略"""

    def __init__(self, window: int = 20, num_std: float = 2):
        self.window = window
        self.num_std = num_std

    def generate_signals(self, df: pd.DataFrame) -> List[TradeSignal]:
        close = df['close']
        upper, middle, lower = TechnicalIndicators.bollinger_bands(close, self.window, self.num_std)

        signals = []

        for i in range(1, len(df)):
            curr_price = close.iloc[i]
            prev_price = close.iloc[i-1]
            curr_lower = lower.iloc[i]

            # 触及下轨反弹（买入）
            if prev_price <= curr_lower and curr_price > curr_lower:
                signals.append(TradeSignal(
                    symbol=df.iloc[i].get('symbol', 'UNKNOWN'),
                    signal=Signal.BUY,
                    confidence=0.65,
                    entry_price=curr_price,
                    stop_loss=curr_price * 0.92,
                    take_profit=middle.iloc[i],
                    reason=f"价格触及布林带下轨后反弹",
                    timestamp=df.index[i].isoformat() if hasattr(df.index[i], 'isoformat') else str(df.index[i])
                ))

        return signals


class CryptoVolumeStrategy:
    """加密货币量价配合策略"""

    def __init__(self, volume_window: int = 20, volume_multiplier: float = 2.0):
        self.volume_window = volume_window
        self.volume_multiplier = volume_multiplier

    def generate_signals(self, df: pd.DataFrame) -> List[TradeSignal]:
        close = df['close']
        volume = df['volume']

        # 计算MACD和量比
        macd_line, signal_line, histogram = TechnicalIndicators.macd(close)
        volume_ratio = TechnicalIndicators.volume_ratio(volume, self.volume_window)

        signals = []

        for i in range(1, len(df)):
            # 放量且MACD金叉
            if (histogram.iloc[i-1] < 0 and histogram.iloc[i] > 0 and
                volume_ratio.iloc[i] >= self.volume_multiplier):

                signals.append(TradeSignal(
                    symbol=df.iloc[i].get('symbol', 'UNKNOWN'),
                    signal=Signal.BUY,
                    confidence=0.8,
                    entry_price=close.iloc[i],
                    stop_loss=close.iloc[i] * 0.95,
                    take_profit=close.iloc[i] * 1.2,
                    reason=f"放量MACD金叉，量比={volume_ratio.iloc[i]:.2f}",
                    timestamp=df.index[i].isoformat() if hasattr(df.index[i], 'isoformat') else str(df.index[i])
                ))

        return signals


class ForexCarryTradeStrategy:
    """外汇套利策略"""

    def __init__(self, rate_diff_threshold: float = 0.02):
        self.rate_diff_threshold = rate_diff_threshold

    def generate_signals(self, df: pd.DataFrame, rate_diff: float) -> List[TradeSignal]:
        """
        生成套利信号

        Args:
            df: 汇率数据
            rate_diff: 两国利率差（正数表示目标货币利率更高）
        """
        close = df['close']

        # MACD判断趋势
        macd_line, signal_line, histogram = TechnicalIndicators.macd(close)

        signals = []

        for i in range(1, len(df)):
            # 利差为正且MACD金叉 - 做多高利率货币
            if (rate_diff > self.rate_diff_threshold and
                histogram.iloc[i-1] < 0 and histogram.iloc[i] > 0):

                signals.append(TradeSignal(
                    symbol=df.iloc[i].get('symbol', 'UNKNOWN'),
                    signal=Signal.BUY,
                    confidence=0.75,
                    entry_price=close.iloc[i],
                    stop_loss=close.iloc[i] * 0.97,
                    take_profit=close.iloc[i] * 1.1,
                    reason=f"利率套利：利差{rate_diff:.2%}，MACD金叉",
                    timestamp=df.index[i].isoformat() if hasattr(df.index[i], 'isoformat') else str(df.index[i])
                ))

            # 利差为负且MACD死叉 - 做空高利率货币
            elif (rate_diff < -self.rate_diff_threshold and
                  histogram.iloc[i-1] > 0 and histogram.iloc[i] < 0):

                signals.append(TradeSignal(
                    symbol=df.iloc[i].get('symbol', 'UNKNOWN'),
                    signal=Signal.SELL,
                    confidence=0.75,
                    entry_price=close.iloc[i],
                    reason=f"利率套利：利差{rate_diff:.2%}，MACD死叉",
                    timestamp=df.index[i].isoformat() if hasattr(df.index[i], 'isoformat') else str(df.index[i])
                ))

        return signals


class SignalAggregator:
    """信号聚合器 - 整合多个策略的信号"""

    def __init__(self, strategies: List):
        self.strategies = strategies

    def generate_consensus_signals(self, df: pd.DataFrame, **kwargs) -> List[TradeSignal]:
        """
        生成共识信号（多个策略一致时才发出信号）

        Returns:
            共识信号列表
        """
        all_signals = {}

        # 收集所有策略信号
        for strategy in self.strategies:
            signals = strategy.generate_signals(df, **kwargs)

            for signal in signals:
                key = (signal.signal, signal.timestamp)
                if key not in all_signals:
                    all_signals[key] = []
                all_signals[key].append(signal)

        # 找出共识信号
        consensus_signals = []

        for key, signals_list in all_signals.items():
            if len(signals_list) >= 2:  # 至少2个策略一致
                # 计算平均置信度
                avg_confidence = sum(s.confidence for s in signals_list) / len(signals_list)
                merged_signal = TradeSignal(
                    symbol=signals_list[0].symbol,
                    signal=signals_list[0].signal,
                    confidence=min(avg_confidence * 1.2, 1.0),  # 提升置信度
                    entry_price=signals_list[0].entry_price,
                    stop_loss=signals_list[0].stop_loss,
                    take_profit=signals_list[0].take_profit,
                    reason=f"共识信号: {len(signals_list)}个策略一致",
                    timestamp=signals_list[0].timestamp
                )
                consensus_signals.append(merged_signal)

        return sorted(consensus_signals, key=lambda x: x.timestamp)


# 便捷工厂函数
def create_strategy(strategy_type: str, **params) -> object:
    """创建策略实例"""
    strategies = {
        'macd': MACDStrategy,
        'rsi': RSIStrategy,
        'bollinger': BollingerBandsStrategy,
        'crypto_volume': CryptoVolumeStrategy,
        'forex_carry': ForexCarryTradeStrategy
    }

    if strategy_type not in strategies:
        raise ValueError(f"未知策略类型: {strategy_type}")

    return strategies[strategy_type](**params)
