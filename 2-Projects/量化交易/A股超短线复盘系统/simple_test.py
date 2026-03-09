# -*- coding: utf-8 -*-
"""
简单测试脚本 - 使用ASCII字符
"""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from data.market_data_fetcher import MarketDataFetcher
from datetime import datetime

def simple_test():
    print("\n" + "="*60)
    print("Simple Test - Market Data")
    print("="*60 + "\n")

    fetcher = MarketDataFetcher()
    today = datetime.now().strftime('%Y-%m-%d')

    print("Fetching market data...")
    overview = fetcher.get_market_overview(today)

    print(f"\nResults:")
    print(f"  Up: {overview['up_count']}")
    print(f"  Down: {overview['down_count']}")
    print(f"  Limit Up: {overview['limit_up_count']}")
    print(f"  Limit Down: {overview['limit_down_count']}")
    print(f"  Index: {overview['index_change']:.2f}%")

    print("\n" + "="*60)

if __name__ == "__main__":
    simple_test()
