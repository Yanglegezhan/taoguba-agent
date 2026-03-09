"""
回测模块
用于测试量化策略的历史表现
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Optional
from dataclasses import dataclass
from enum import Enum
import logging

from strategies import TradeSignal, Signal

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Position:
    """持仓"""

    def __init__(
        self,
        symbol: str,
        entry_price: float,
        quantity: float,
        entry_time: str,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None
    ):
        self.symbol = symbol
        self.entry_price = entry_price
        self.quantity = quantity
        self.entry_time = entry_time
        self.stop_loss = stop_loss
        self.take_profit = take_profit
        self.exit_price = None
        self.exit_time = None
        self.exit_reason = None

    @property
    def current_value(self, current_price: float) -> float:
        """当前价值"""
        return current_price * self.quantity

    @property
    def profit(self) -> float:
        """已实现盈亏"""
        if self.exit_price is None:
            return 0.0
        return (self.exit_price - self.entry_price) * self.quantity

    @property
    def profit_percent(self) -> float:
        """盈亏百分比"""
        if self.exit_price is None or self.entry_price == 0:
            return 0.0
        return ((self.exit_price - self.entry_price) / self.entry_price) * 100

    @property
    def is_open(self) -> bool:
        """是否持仓中"""
        return self.exit_price is None


@dataclass
class BacktestResult:
    """回测结果"""
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    total_profit: float
    total_profit_percent: float
    max_drawdown: float
    sharpe_ratio: float
    final_equity: float
    equity_curve: List[float]
    trades: List[Dict]

    def to_dict(self) -> dict:
        return {
            "total_trades": self.total_trades,
            "winning_trades": self.winning_trades,
            "losing_trades": self.losing_trades,
            "win_rate": self.win_rate,
            "total_profit": self.total_profit,
            "total_profit_percent": self.total_profit_percent,
            "max_drawdown": self.max_drawdown,
            "sharpe_ratio": self.sharpe_ratio,
            "final_equity": self.final_equity,
        }

    def print_summary(self):
        """打印回测摘要"""
        print("\n" + "="*50)
        print("回测结果摘要".center(50))
        print("="*50)
        print(f"总交易次数: {self.total_trades}")
        print(f"盈利交易: {self.winning_trades}")
        print(f"亏损交易: {self.losing_trades}")
        print(f"胜率: {self.win_rate:.2f}%")
        print(f"总盈亏: {self.total_profit:.2f}")
        print(f"总盈亏百分比: {self.total_profit_percent:.2f}%")
        print(f"最大回撤: {self.max_drawdown:.2f}%")
        print(f"夏普比率: {self.sharpe_ratio:.2f}")
        print(f"最终资金: {self.final_equity:.2f}")
        print("="*50 + "\n")


class Backtester:
    """回测器"""

    def __init__(
        self,
        initial_capital: float = 100000,
        commission: float = 0.001,
        slippage: float = 0.0001
    ):
        """
        初始化回测器

        Args:
            initial_capital: 初始资金
            commission: 手续费率（默认0.1%）
            slippage: 滑点（默认0.01%）
        """
        self.initial_capital = initial_capital
        self.commission = commission
        self.slippage = slippage

        self.equity = initial_capital
        self.positions: Dict[str, Position] = {}
        self.equity_curve = [initial_capital]
        self.trades: List[Dict] = []
        self.trade_history = []

    def run(
        self,
        df: pd.DataFrame,
        signals: List[TradeSignal],
        price_col: str = 'close'
    ) -> BacktestResult:
        """
        运行回测

        Args:
            df: 价格数据
            signals: 交易信号
            price_col: 价格列名

        Returns:
            回测结果
        """
        # 按时间排序信号
        signals_sorted = sorted(signals, key=lambda x: x.timestamp or '')

        # 逐条执行信号
        for signal in signals_sorted:
            # 找到对应的价格
            idx = df.index.get_loc(signal.timestamp) if signal.timestamp in df.index else None

        if idx is not None:
                current_price = df.iloc[idx][price_col]

            # 执行信号
            if signal.signal == Signal.BUY:
                self._execute_buy(signal, current_price)
            elif signal.signal == Signal.SELL:
                self._execute_sell(signal, current_price)

        # 清算所有持仓
        self._close_all_positions(df[price_col].iloc[-1])

        # 计算结果
        return self._calculate_result()

    def _execute_buy(self, signal: TradeSignal, price: float):
        """执行买入"""
        if signal.symbol in self.positions:
            logger.warning(f"已持有 {signal.symbol}，跳过买入信号")
            return

        # 计算滑点
        execution_price = price * (1 + self.slippage)

        # 计算可买入数量（简化：全仓买入）
        quantity = self.equity / execution_price

        # 扣除手续费
        commission_cost = quantity * execution_price * self.commission
        self.equity -= commission_cost

        # 创建持仓
        position = Position(
            symbol=signal.symbol,
            entry_price=execution_price,
            quantity=quantity,
            entry_time=signal.timestamp or '',
            stop_loss=signal.stop_loss,
            take_profit=signal.take_profit
        )

        self.positions[signal.symbol] = position

        logger.info(f"买入 {signal.symbol} @ {execution_price:.2f}, 数量: {quantity:.2f}")

    def _execute_sell(self, signal: TradeSignal, price: float):
        """执行卖出"""
        if signal.symbol not in self.positions:
            return

        position = self.positions[signal.symbol]

        # 计算滑点
        execution_price = price * (1 - self.slippage)

        # 平仓
        profit = (execution_price - position.entry_price) * position.quantity
        commission_cost = execution_price * position.quantity * self.commission

        self.equity += profit - commission_cost

        # 记录交易
        position.exit_price = execution_price
        position.exit_time = signal.timestamp or ''
        position.exit_reason = signal.reason or "卖出信号"

        self.trades.append({
            "symbol": position.symbol,
            "entry_price": position.entry_price,
            "exit_price": execution_price,
            "quantity": position.quantity,
            "profit": profit,
            "profit_percent": position.profit_percent,
            "entry_time": position.entry_time,
            "exit_time": position.exit_time,
            "exit_reason": position.exit_reason
        })

        del self.positions[signal.symbol]
        self.equity_curve.append(self.equity)

        logger.info(f"卖出 {signal.symbol} @ {execution_price:.2f}, 盈亏: {profit:.2f}")

    def _close_all_positions(self, last_price: float):
        """平仓所有持仓"""
        for symbol in list(self.positions.keys()):
            position = self.positions[symbol]

            execution_price = last_price
            profit = (execution_price - position.entry_price) * position.quantity
            commission_cost = execution_price * position.quantity * self.commission

            self.equity += profit - commission_cost

            position.exit_price = execution_price
            position.exit_time = "回测结束"
            position.exit_reason = "强制平仓"

            self.trades.append({
                "symbol": position.symbol,
                "entry_price": position.entry_price,
                "exit_price": execution_price,
                "quantity": position.quantity,
                "profit": profit,
                "profit_percent": position.profit_percent,
                "entry_time": position.entry_time,
                "exit_time": position.exit_time,
                "exit_reason": position.exit_reason
            })

            del self.positions[symbol]
            self.equity_curve.append(self.equity)

    def _calculate_result(self) -> BacktestResult:
        """计算回测结果"""
        total_trades = len(self.trades)
        winning_trades = len([t for t in self.trades if t['profit'] > 0])
        losing_trades = len([t for t in self.trades if t['profit'] <= 0])

        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0

        total_profit = sum(t['profit'] for t in self.trades)
        total_profit_percent = (total_profit / self.initial_capital * 100)

        # 计算最大回撤
        equity_values = self.equity_curve
        peak = equity_values[0]
        max_drawdown = 0

        for value in equity_values:
            if value > peak:
                peak = value
            else:
                drawdown = (peak - value) / peak * 100
                if drawdown > max_drawdown:
                    max_drawdown = drawdown

        # 计算夏普比率（简化版）
        if len(equity_values) > 1:
            returns = pd.Series(equity_values).pct_change().dropna()
            sharpe_ratio = returns.mean() / returns.std() * np.sqrt(252) if returns.std() > 0 else 0
        else:
            sharpe_ratio = 0

        return BacktestResult(
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            win_rate=win_rate,
            total_profit=total_profit,
            total_profit_percent=total_profit_percent,
            max_drawdown=max_drawdown,
            sharpe_ratio=sharpe_ratio,
            final_equity=self.equity,
            equity_curve=self.equity_curve,
            trades=self.trades
        )
