# -*- coding: utf-8 -*-
"""分析层测试脚本"""

import sys
import io
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 设置UTF-8输出
if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

print("=" * 80)
print("分析层测试")
print("=" * 80)

# 测试配置管理器
print("\n[1] 测试配置管理器...")
try:
    from config.config_manager import ConfigManager
    config_manager = ConfigManager()
    print("  [OK] 配置管理器加载成功")

    analysis_config = config_manager.get_analysis_config()
    print(f"  - 提升倍数阈值: {analysis_config.lift_ratio_threshold}")
    print(f"  - 最小样本量: {analysis_config.min_sample_size}")

except Exception as e:
    print(f"  [FAIL] 配置管理器加载失败: {e}")
    import traceback
    traceback.print_exc()

# 测试命名语义分析器
print("\n[2] 测试命名语义分析器...")
try:
    from src.analysis.naming_analyzer import NamingAnalyzer

    analyzer = NamingAnalyzer(similarity_threshold=0.7)
    print("  [OK] 命名语义分析器初始化成功")

    # 测试股票名称
    test_names = [
        "东方财富", "数字政通", "龙腾科技", "凤凰传媒",
        "圣农发展", "中国银行", "万科A"
    ]

    test_codes = ["000001.SZ", "002574.SZ", "300912.SZ", "002415.SZ",
                "000876.SZ", "601988.SH", "000002.SZ"]

    print(f"\n  分析测试股票:")
    for name, code in zip(test_names, test_codes):
        analysis = analyzer.analyze(name, code, test_names)
        print(f"    * {name} ({code}):")
        print(f"      东方: {analysis.has_dongfang}, 数字: {analysis.has_chinese_num or analysis.has_arabic_num}")
        print(f"      龙: {analysis.has_long}, 凤: {analysis.has_phoenix}")

except Exception as e:
    print(f"  [FAIL] 命名语义分析器测试失败: {e}")
    import traceback
    traceback.print_exc()

# 测试统计学分析器
print("\n[3] 测试统计学分析器...")
try:
    from src.analysis.statistical_analyzer import StatisticalAnalyzer
    from src.models.data_models import (
        LimitUpStockBasic,
        OwnershipType,
        PriceRange,
        MarketCapRange
    )

    analyzer = StatisticalAnalyzer(lift_ratio_threshold=2.0)
    print("  [OK] 统计学分析器初始化成功")

    # 创建测试数据
    test_stocks = [
        LimitUpStockBasic(
            stock_code="600000.SH",
            stock_name="浦发银行",
            province="上海",
            ownership=OwnershipType.LOCAL_STATE,
            pb_ratio=0.8,
            is_broken_net=True,
            price_range=PriceRange.MEDIUM,
            market_cap_range=MarketCapRange.LARGE,
            consecutive_days=2
        ),
        LimitUpStockBasic(
            stock_code="601988.SH",
            stock_name="中国银行",
            province="北京",
            ownership=OwnershipType.CENTRAL,
            pb_ratio=0.6,
            is_broken_net=True,
            price_range=PriceRange.MEDIUM,
            market_cap_range=MarketCapRange.LARGE,
            consecutive_days=3
        ),
        LimitUpStockBasic(
            stock_code="000876.SZ",
            stock_name="圣农发展",
            province="广东",
            ownership=OwnershipType.PRIVATE,
            pb_ratio=2.5,
            is_broken_net=False,
            price_range=PriceRange.LOW,
            market_cap_range=MarketCapRange.MICRO,
            consecutive_days=1
        )
    ]

    # 测试分析
    result = analyzer.full_analyze(test_stocks, "2026-02-04")
    print(f"  [OK] 统计学分析执行成功")
    print(f"    涨停数量: {result.limit_up_count}")
    print(f"    破净比例: {result.broken_net_ratio:.1f}%")
    print(f"    融资融券比例: {result.margin_trading_ratio:.1f}%")

    # 显示显著项目
    if result.province_analysis.significant_items:
        print(f"    显著省份: {result.province_analysis.significant_items}")

    if result.ownership_analysis.significant_items:
        print(f"    显著企业性质: {result.ownership_analysis.significant_items}")

except Exception as e:
    print(f"  [FAIL] 统计学分析器测试失败: {e}")
    import traceback
    traceback.print_exc()

# 测试暗线识别器
print("\n[4] 测试暗线识别器...")
try:
    from src.analysis.dark_line_detector import DarkLineDetector

    detector = DarkLineDetector(min_sample_size=3)
    print("  [OK] 暗线识别器初始化成功")

    # 检测暗线
    dark_lines = detector.detect(
        statistical_analysis=result,
        naming_analyses=[],
        limit_up_stocks=test_stocks
    )

    print(f"  [OK] 暗线识别成功")
    print(f"    识别出 {len(dark_lines)} 条暗线")

    for i, dark_line in enumerate(dark_lines, 1):
        print(f"\n    暗线{i}: {dark_line.title}")
        print(f"      类型: {dark_line.dark_line_type.value}")
        print(f"      置信度: {dark_line.confidence:.2f}")
        print(f"      涉及股票: {dark_line.stock_count}只")
        if dark_line.is_accidental:
            print(f"      [注意] 标记为偶然因素")

except Exception as e:
    print(f"  [FAIL] 暗线识别器测试失败: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 80)
print("分析层测试完成")
print("=" * 80)
