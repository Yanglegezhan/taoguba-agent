# -*- coding: utf-8 -*-
"""
数据获取层测试脚本
"""

import sys
import os
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
print("数据获取层测试")
print("=" * 80)

# 测试配置管理器
print("\n[1] 测试配置管理器...")
try:
    from config.config_manager import ConfigManager
    config_manager = ConfigManager()
    print("  [OK] 配置管理器加载成功")

    ds_config = config_manager.get_data_source_config()
    print(f"  - TuShare Token: {'已设置' if ds_config.tushare_token else '未设置'}")
    print(f"  - 开盘啦超时: {ds_config.kaipanla_timeout}秒")
    print(f"  - TuShare超时: {ds_config.tushare_timeout}秒")

except Exception as e:
    print(f"  [FAIL] 配置管理器加载失败: {e}")
    import traceback
    traceback.print_exc()

# 测试开盘啦数据源
print("\n[2] 测试开盘啦数据源...")
try:
    from src.data.kaipanla_source import KaipanlaSource
    from datetime import datetime, timedelta

    kaipanla = KaipanlaSource(max_retries=3, timeout=60)
    print("  [OK] 开盘啦数据源初始化成功")

    # 测试获取涨停列表
    test_date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    print(f"  - 测试日期: {test_date}")

    limit_up_stocks = kaipanla.get_limit_up_stocks(test_date)
    print(f"  - 获取到 {len(limit_up_stocks)} 只涨停股票")

    if limit_up_stocks:
        print(f"\n[OK] 涨停股票示例:")
        for i, stock in enumerate(limit_up_stocks[:3], 1):
            print(f"    {i}. {stock.get('stock_name')} ({stock.get('stock_code')}) "
                  f"- {stock.get('consecutive_days')}板 - {stock.get('turnover_amount', 0):.2f}亿")

except ImportError as e:
    print(f"  [FAIL] 导入失败: {e}")
except Exception as e:
    print(f"  [FAIL] 测试失败: {e}")
    import traceback
    traceback.print_exc()

# 测试TuShare数据源
print("\n[3] 测试TuShare数据源...")
try:
    from src.data.tushare_source import TushareSource

    try:
        tushare_token = os.getenv('TUSHARE_TOKEN') or ds_config.tushare_token
    except NameError:
        tushare_token = os.getenv('TUSHARE_TOKEN') or ''
    if not tushare_token:
        print("  [SKIP] TuShare Token 未设置，跳过测试")
    else:
        tushare = TushareSource(api_token=tushare_token, timeout=30)
        print("  [OK] TuShare数据源初始化成功")

        # 测试获取基础信息
        test_codes = ['600000.SH', '000001.SZ']
        basic_info = tushare.get_stock_basic_info(test_codes)
        print(f"  - 获取到 {len(basic_info)} 只股票的基础信息")

        for code, info in basic_info.items():
            if info:
                print(f"    * {info.get('name', code)}: {info.get('area', '未知')} - {info.get('industry', '未知')}")

except ImportError as e:
    print(f"  [FAIL] 导入失败: {e}")
except Exception as e:
    print(f"  [FAIL] 测试失败: {e}")
    import traceback
    traceback.print_exc()

# 测试AkShare数据源
print("\n[4] 测试AkShare数据源...")
try:
    from src.data.akshare_source import AkshareSource

    akshare = AkshareSource(timeout=30)
    print("  [OK] AkShare数据源初始化成功")

    # 测试获取概念
    print("  - 获取概念板块名称...")
    concepts = akshare.get_all_concept_names()
    print(f"  - 共有 {len(concepts)} 个概念板块")

    if concepts:
        print(f"  - 前5个概念: {concepts[:5]}")

    # 测试获取股票概念
    print("\n  - 获取股票概念...")
    stock_concepts = akshare.get_stock_concepts('600000')
    print(f"  - 600000 的概念: {stock_concepts}")

except ImportError as e:
    print(f"  [FAIL] 导入失败: {e}")
except Exception as e:
    print(f"  [FAIL] 测试失败: {e}")
    import traceback
    traceback.print_exc()

# 测试技术指标计算器
print("\n[5] 测试技术指标计算器...")
try:
    from src.data.technical_calculator import TechnicalCalculator
    import pandas as pd

    calculator = TechnicalCalculator(ma_periods=[5, 10, 20, 60])
    print("  [OK] 技术指标计算器初始化成功")

    # 创建测试数据
    test_prices = pd.Series([15.5, 15.3, 15.0, 14.8, 14.5, 14.2, 14.0, 13.8, 13.5, 13.2])
    print(f"  - 测试价格序列: {test_prices.tolist()}")

    # 计算均线偏离度
    ma_deviation = calculator.calculate_ma_deviation(test_prices)
    print(f"  - 均线偏离度: {ma_deviation}")

    # 计算最高价距离
    high_distance = calculator.calculate_high_250d_distance(test_prices, 15.5)
    print(f"  - 最高价距离: {high_distance:.2f}%")

    print("  [OK] 技术指标计算正常")

except Exception as e:
    print(f"  [FAIL] 测试失败: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 80)
print("数据获取层测试完成")
print("=" * 80)
