"""
量化交易主程序
演示如何使用各种策略进行回测
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging

from data_fetcher import AShareDataFetcher, CryptoDataFetcher, ForexDataFetcher
from strategies import (
    MACDStrategy, RSIStrategy, BollingerBandsStrategy,
    CryptoVolumeStrategy, ForexCarryTradeStrategy,
    SignalAggregator, create_strategy
)
from backtester import Backtester

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def generate_sample_data(days: int = 252, price: float = 100.0, volatility: float = 0.02) -> pd.DataFrame:
    """生成示例价格数据用于演示"""
    np.random.seed(42)

    dates = pd.date_range(end=datetime.now(), periods=days, freq='D')
    returns = np.random.normal(0, volatility, days)
    prices = price * np.cumprod(1 + returns)

    # 生成OHLCV数据
    df = pd.DataFrame({
        'open': prices * (1 + np.random.uniform(-0.01, 0.01, days)),
        'high': prices * (1 + np.random.uniform(0, 0.02, days)),
        'low': prices * (1 + np.random.uniform(-0.02, 0, days)),
        'close': prices,
        'volume': np.random.randint(1000000, 10000000, days)
    }, index=dates)

    df['symbol'] = 'DEMO'

    return df


def backtest_strategy(strategy, df: pd.DataFrame, strategy_name: str):
    """回测单个策略"""
    print(f"\n{'='*60}")
    print(f"回测策略: {strategy_name}")
    print(f"{'='*60}")

    # 生成信号
    signals = strategy.generate_signals(df)
    print(f"生成 {len(signals)} 个交易信号")

    if not signals:
        print("没有交易信号，跳过回测")
        return None

    # 回测
    backtester = Backtester(initial_capital=100000)
    result = backtester.run(df, signals)
    result.print_summary()

    return result


def backtest_multiple_strategies(df: pd.DataFrame):
    """回测多个策略"""
    strategies = [
        (MACDStrategy(), "MACD策略"),
        (RSIStrategy(), "RSI策略"),
        (BollingerBandsStrategy(), "布林带策略"),
        (CryptoVolumeStrategy(), "加密货币量价策略"),
    ]

    results = {}

    for strategy, name in strategies:
        try:
            result = backtest_strategy(strategy, df, name)
            if result:
                results[name] = result
        except Exception as e:
            logger.error(f"{name} 回测失败: {e}")

    # 汇总结果
    print("\n" + "="*60)
    print("策略对比汇总".center(60))
    print("="*60)
    print(f"{'策略名称':<20} {'总盈亏%':<12} {'胜率':<10} {'夏普比率':<10}")
    print("-"*60)

    for name, result in results.items():
        print(f"{name:<20} {result.total_profit_percent:>10.2f}%   "
              f"{result.win_rate:>8.2f}%   {result.sharpe_ratio:>8.2f}")

    return results


def main():
    """主函数"""
    print("="*60)
    print("量化交易策略回测系统".center(60))
    print("="*60)

    # 生成示例数据（实际使用时应从data_fetcher获取真实数据）
    df = generate_sample_data(days=500)
    print(f"\n使用示例数据: {len(df)} 天")
    print(f"价格范围: {df['close'].min():.2f} - {df['close'].max():.2f}")

    # 回测多个策略
    results = backtest_multiple_strategies(df)

    # 保存结果
    if results:
        import json

        output_dir = "money_mission/quantitative/results"
        import os
        os.makedirs(output_dir, exist_ok=True)

        for name, result in results.items():
            filename = f"{output_dir}/{name.replace(' ', '_').lower()}_result.json"
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump({
                    'summary': result.to_dict(),
                    'trades': result.trades
                }, f, ensure_ascii=False, indent=2)

        print(f"\n回测结果已保存到 {output_dir}/")


if __name__ == "__main__":
    main()
