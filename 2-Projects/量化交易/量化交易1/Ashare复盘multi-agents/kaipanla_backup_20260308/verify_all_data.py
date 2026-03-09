# -*- coding: utf-8 -*-
"""
数据验证脚本 - 检查多个数据源的一致性
"""

import sys
sys.path.insert(0, '..')
sys.path.insert(0, '../../kaipanla_crawler')

from kaipanla_crawler import KaipanlaCrawler
import pandas as pd

def test_sector_ranking():
    """测试板块排名数据"""
    print("=" * 70)
    print("测试1: get_sector_ranking (涨停板块数据)")
    print("=" * 70)

    crawler = KaipanlaCrawler()
    result = crawler.get_sector_ranking(date='2026-03-06')

    summary = result.get('summary', {})
    sectors = result.get('sectors', [])

    print(f"\n市场概况:")
    print(f"  日期: {summary.get('日期')}")
    print(f"  涨停数: {summary.get('涨停数')}")
    print(f"  跌停数: {summary.get('跌停数')}")
    print(f"  上涨家数: {summary.get('上涨家数')}")
    print(f"  下跌家数: {summary.get('下跌家数')}")

    print(f"\n前5板块:")
    for sector in sectors[:5]:
        print(f"  - {sector['sector_name']}: {sector['stock_count']}只涨停")

    # 查找算力板块
    for sector in sectors:
        if sector['sector_name'] == '算力':
            print(f"\n算力板块详情:")
            print(f"  板块代码: {sector['sector_code']}")
            print(f"  涨停数: {sector['stock_count']}")
            print(f"  涨停股票:")
            for stock in sector['stocks'][:5]:
                print(f"    - {stock['股票名称']} ({stock['股票代码']}): {stock['连板天数']}")
            break

    return result

def test_limit_up_ladder():
    """测试涨停梯队数据"""
    print("\n" + "=" * 70)
    print("测试2: get_limit_up_ladder (连板梯队)")
    print("=" * 70)

    crawler = KaipanlaCrawler()
    result = crawler.get_limit_up_ladder(date='2026-03-06')

    if result is not None and not result.empty:
        print(f"\n连板梯队数据:")
        print(f"  一板: {result['一板'].iloc[0]}家")
        print(f"  二板: {result['二板'].iloc[0]}家")
        print(f"  三板: {result['三板'].iloc[0]}家")
        print(f"  高度板: {result['高度板'].iloc[0]}家")
        print(f"  连板率: {result['连板率(%)'].iloc[0]}%")
        print(f"  今日涨停破板率: {result['今日涨停破板率(%)'].iloc[0]}%")
        print(f"  昨日涨停今表现: {result['昨日涨停今表现(%)'].iloc[0]}%")
    else:
        print("  未获取到数据")

    return result

def test_consecutive_limit_up():
    """测试连板梯队详细数据"""
    print("\n" + "=" * 70)
    print("测试3: get_consecutive_limit_up (详细连板梯队)")
    print("=" * 70)

    crawler = KaipanlaCrawler()
    result = crawler.get_consecutive_limit_up(date='2026-03-06')

    print(f"\n最高连板: {result['max_consecutive']}板")
    print(f"  个股: {result['max_consecutive_stocks']}")
    print(f"  概念: {result['max_consecutive_concepts']}")

    ladder = result.get('ladder', {})
    print(f"\n连板分布:")
    for board_num in sorted(ladder.keys(), reverse=True):
        stocks = ladder[board_num]
        stock_names = [s['股票名称'] for s in stocks]
        print(f"  {board_num}板: {len(stocks)}只 - {'/'.join(stock_names[:5])}")

    return result

def test_new_high_data():
    """测试百日新高数据"""
    print("\n" + "=" * 70)
    print("测试4: get_new_high_data (百日新高)")
    print("=" * 70)

    crawler = KaipanlaCrawler()
    result = crawler.get_new_high_data(end_date='2026-03-06')

    print(f"\n百日新高数据:")
    if isinstance(result, pd.Series):
        if '2026-03-06' in result.index:
            print(f"  2026-03-06 新增百日新高: {result['2026-03-06']}家")
        else:
            print(f"  可用日期: {list(result.index[:5])}")
            print(f"  最新数据: {result.iloc[0]}家 ({result.index[0]})")
    else:
        print(f"  结果: {result}")

    return result

def test_daily_data():
    """测试每日市场数据"""
    print("\n" + "=" * 70)
    print("测试5: get_daily_data (市场汇总数据)")
    print("=" * 70)

    crawler = KaipanlaCrawler()
    result = crawler.get_daily_data(end_date='2026-03-06')

    if isinstance(result, pd.Series):
        print(f"\n市场数据 (2026-03-06):")
        print(f"  涨停数: {result.get('涨停数', 'N/A')}")
        print(f"  实际涨停: {result.get('实际涨停', 'N/A')}")
        print(f"  跌停数: {result.get('跌停数', 'N/A')}")
        print(f"  首板数量: {result.get('首板数量', 'N/A')}")
        print(f"  2连板数量: {result.get('2连板数量', 'N/A')}")
        print(f"  3连板数量: {result.get('3连板数量', 'N/A')}")
        print(f"  4连板以上数量: {result.get('4连板以上数量', 'N/A')}")
        print(f"  连板率: {result.get('连板率', 'N/A')}%")
        print(f"  大幅回撤家数: {result.get('大幅回撤家数', 'N/A')}")
    else:
        print(f"  结果类型: {type(result)}")
        print(f"  结果: {result}")

    return result

def compare_data_sources():
    """对比多个数据源的一致性"""
    print("\n" + "=" * 70)
    print("测试6: 数据源一致性对比")
    print("=" * 70)

    crawler = KaipanlaCrawler()

    # 获取不同来源的涨停数据
    daily = crawler.get_daily_data(end_date='2026-03-06')
    ladder = crawler.get_limit_up_ladder(date='2026-03-06')
    consecutive = crawler.get_consecutive_limit_up(date='2026-03-06')

    print("\n不同数据源的涨停统计:")

    # 来源1: daily_data
    if isinstance(daily, pd.Series):
        print(f"\n来源1 - get_daily_data:")
        print(f"  涨停数: {daily.get('涨停数', 'N/A')}")
        print(f"  首板: {daily.get('首板数量', 'N/A')}")
        print(f"  2连板: {daily.get('2连板数量', 'N/A')}")
        print(f"  3连板: {daily.get('3连板数量', 'N/A')}")
        print(f"  4连板+: {daily.get('4连板以上数量', 'N/A')}")

    # 来源2: limit_up_ladder
    if ladder is not None and not ladder.empty:
        print(f"\n来源2 - get_limit_up_ladder:")
        print(f"  一板: {ladder['一板'].iloc[0]}家")
        print(f"  二板: {ladder['二板'].iloc[0]}家")
        print(f"  三板: {ladder['三板'].iloc[0]}家")
        print(f"  高度板: {ladder['高度板'].iloc[0]}家")

    # 来源3: consecutive_limit_up
    print(f"\n来源3 - get_consecutive_limit_up:")
    ladder_data = consecutive.get('ladder', {})
    total = 0
    for board_num in sorted(ladder_data.keys(), reverse=True):
        count = len(ladder_data[board_num])
        total += count
        print(f"  {board_num}板: {count}家")
    print(f"  总计: {total}家")

if __name__ == "__main__":
    print("\n开盘啦数据源验证")
    print("=" * 70)
    print("验证日期: 2026-03-06")
    print()

    # 运行所有测试
    test_sector_ranking()
    test_limit_up_ladder()
    test_consecutive_limit_up()
    test_new_high_data()
    test_daily_data()
    compare_data_sources()

    print("\n" + "=" * 70)
    print("验证完成")
    print("=" * 70)
