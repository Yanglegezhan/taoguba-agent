# -*- coding: utf-8 -*-
"""
A股超短线复盘系统 - 简化测试版

这个版本不使用LLM，直接生成报告
"""

import os
import sys
import io
from datetime import datetime, timedelta
from pathlib import Path

# 强制使用UTF-8编码
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from data.market_data_fetcher import MarketDataFetcher
from data.sector_data_fetcher import SectorDataFetcher
from analysis.sentiment_analyzer import (
    MarketDayData,
    SentimentCalculator,
    CycleDetector
)


def test_system():
    """测试系统"""
    print("\n" + "="*60)
    print("A股超短线复盘系统 - 测试运行")
    print("="*60 + "\n")


if __name__ == "__main__":
    try:
        test_system()
    except KeyboardInterrupt:
        print("\n⚠️  用户中断")
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
