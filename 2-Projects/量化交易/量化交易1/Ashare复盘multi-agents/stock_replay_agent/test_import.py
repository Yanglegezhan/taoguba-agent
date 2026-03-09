#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试导入 - 验证所有模块可以正常导入
"""
import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

def test_imports():
    """测试所有模块导入"""
    print("=" * 60)
    print("测试模块导入")
    print("=" * 60)

    tests = []

    # 测试1: models 模块
    try:
        from src.models.stock_models import (
            ConsecutiveBoardAnalysis,
            TrendStockAnalysis,
            CriticEvaluation,
            SynthesisReport,
        )
        tests.append(("models.stock_models", True))
        print("✓ models.stock_models 导入成功")
    except Exception as e:
        tests.append(("models.stock_models", False))
        print(f"✗ models.stock_models 导入失败: {e}")

    # 测试2: llm 模块
    try:
        from src.llm.base import LLMConfig, LLMMessage
        from src.llm.client import LLMClient, create_client
        from src.llm.prompt_engine import PromptEngine
        tests.append(("llm", True))
        print("✓ llm 模块导入成功")
    except Exception as e:
        tests.append(("llm", False))
        print(f"✗ llm 模块导入失败: {e}")

    # 测试3: data 模块
    try:
        from src.data.kaipanla_stock_source import KaipanlaStockSource
        tests.append(("data.kaipanla_stock_source", True))
        print("✓ data.kaipanla_stock_source 导入成功")
    except Exception as e:
        tests.append(("data.kaipanla_stock_source", False))
        print(f"✗ data.kaipanla_stock_source 导入失败: {e}")

    # 测试4: analysis 模块
    try:
        from src.analysis.indicator_calculator import IndicatorCalculator
        from src.analysis.special_action_detector import SpecialActionDetector
        from src.analysis.sector_comparator import SectorComparator
        tests.append(("analysis", True))
        print("✓ analysis 模块导入成功")
    except Exception as e:
        tests.append(("analysis", False))
        print(f"✗ analysis 模块导入失败: {e}")

    # 测试5: agent 模块
    try:
        from src.agent.consecutive_board_agent import ConsecutiveBoardStockAgent
        from src.agent.trend_stock_agent import TrendStockAgent
        from src.agent.critic_agent import (
            CriticAgent,
            ConsecutiveBoardCritic,
            TrendStockCritic,
        )
        from src.agent.synthesis_agent import StockSynthesisAgent
        tests.append(("agent", True))
        print("✓ agent 模块导入成功")
    except Exception as e:
        tests.append(("agent", False))
        print(f"✗ agent 模块导入失败: {e}")

    # 测试6: output 模块
    try:
        from src.output.report_generator import ReportGenerator
        from src.output.json_exporter import JsonExporter
        tests.append(("output", True))
        print("✓ output 模块导入成功")
    except Exception as e:
        tests.append(("output", False))
        print(f"✗ output 模块导入失败: {e}")

    # 总结
    print("")
    print("=" * 60)
    print("导入测试总结")
    print("=" * 60)
    passed = sum(1 for _, success in tests if success)
    total = len(tests)
    print(f"通过: {passed}/{total}")
    for name, success in tests:
        status = "✓" if success else "✗"
        print(f"  {status} {name}")

    return all(success for _, success in tests)


if __name__ == "__main__":
    success = test_imports()
    sys.exit(0 if success else 1)
