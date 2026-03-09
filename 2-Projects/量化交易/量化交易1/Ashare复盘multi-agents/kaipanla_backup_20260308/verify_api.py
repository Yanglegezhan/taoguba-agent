# -*- coding: utf-8 -*-
"""
开盘啦数据接口验证脚本

验证内容：
1. 数据接口是否正常返回数据
2. 涨停数是否正确
3. 数据字段是否完整
"""

import sys
sys.path.insert(0, '..')
sys.path.insert(0, '../../kaipanla_crawler')

from src.data.kaipanla_source import KaipanlaDataSource


def test_sector_detailed_data():
    """测试板块详细数据接口"""
    print("=" * 60)
    print("测试 get_sector_detailed_data 接口")
    print("=" * 60)

    # 创建数据源
    source = KaipanlaDataSource(max_retries=3, retry_delay=1.0)

    # 测试算力板块
    sector_code = '803023'
    sector_name = '算力'
    date = '2026-03-06'

    print(f"\n测试板块: {sector_name}")
    print(f"板块代码: {sector_code}")
    print(f"日期: {date}")
    print("-" * 60)

    try:
        detailed_data = source.get_sector_detailed_data(
            sector_code=sector_code,
            sector_name=sector_name,
            date=date
        )

        # 验证返回字段
        required_fields = [
            'limit_up_count', 'limit_up_stocks', 'consecutive_boards',
            'capital_inflow', 'capital_inflow_rate', 'turnover', 'change_pct'
        ]

        print("\n1. 字段完整性检查:")
        all_fields_present = True
        for field in required_fields:
            present = field in detailed_data
            status = "✓" if present else "✗"
            print(f"   {status} {field}: {present}")
            if not present:
                all_fields_present = False

        # 验证涨停数
        limit_up_count = detailed_data.get('limit_up_count', 0)
        limit_up_stocks = detailed_data.get('limit_up_stocks', [])
        actual_count = len(limit_up_stocks)

        print(f"\n2. 涨停数检查:")
        print(f"   返回的 limit_up_count: {limit_up_count}")
        print(f"   实际的 stocks 数量: {actual_count}")
        count_match = limit_up_count == actual_count
        print(f"   是否一致: {'✓ 是' if count_match else '✗ 否'}")

        # 显示涨停股票列表
        print(f"\n3. 涨停股票列表 (共{actual_count}只):")
        for i, stock in enumerate(limit_up_stocks, 1):
            stock_code = stock.get('股票代码', '')
            stock_name = stock.get('股票名称', '')
            consecutive = stock.get('连板天数', '')
            print(f"   {i}. {stock_name} ({stock_code}) - {consecutive}")

        # 验证连板梯队
        consecutive_boards = detailed_data.get('consecutive_boards', {})
        print(f"\n4. 连板梯队分布:")
        if consecutive_boards:
            for board_num in sorted(consecutive_boards.keys(), reverse=True):
                count = consecutive_boards[board_num]
                print(f"   {board_num}板: {count}只")
        else:
            print("   无连板数据")

        # 验证资金数据
        print(f"\n5. 资金数据:")
        print(f"   主力资金净流入: {detailed_data.get('capital_inflow', 0):.2f} 亿元")
        print(f"   主力资金净流入率: {detailed_data.get('capital_inflow_rate', 0):.2f}%")
        print(f"   成交额: {detailed_data.get('turnover', 0):.2f} 亿元")
        print(f"   涨跌幅: {detailed_data.get('change_pct', 0):.2f}%")

        # 验证龙头股
        leading_stock = detailed_data.get('leading_stock')
        print(f"\n6. 龙头股信息:")
        if leading_stock:
            print(f"   名称: {leading_stock.get('name', '')}")
            print(f"   代码: {leading_stock.get('code', '')}")
            print(f"   连板: {leading_stock.get('consecutive_days', '')}")
            print(f"   成交额: {leading_stock.get('turnover', 0):.2f} 亿元")
        else:
            print("   无龙头股数据")

        # 总结
        print("\n" + "=" * 60)
        print("测试结果总结")
        print("=" * 60)
        print(f"字段完整性: {'✓ 通过' if all_fields_present else '✗ 失败'}")
        print(f"涨停数一致性: {'✓ 通过' if count_match else '✗ 失败'}")
        print(f"数据完整性: {'✓ 通过' if actual_count > 0 else '✗ 失败'}")

        return {
            'success': all_fields_present and count_match and actual_count > 0,
            'limit_up_count': limit_up_count,
            'actual_count': actual_count,
            'fields_present': all_fields_present
        }

    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return {'success': False, 'error': str(e)}


def test_sector_ranking():
    """测试板块排名接口"""
    print("\n" + "=" * 60)
    print("测试 get_sector_ranking 接口 (直接调用 crawler)")
    print("=" * 60)

    from kaipanla_crawler import KaipanlaCrawler
    crawler = KaipanlaCrawler()

    try:
        result = crawler.get_sector_ranking(date='2026-03-06')

        summary = result.get('summary', {})
        sectors = result.get('sectors', [])

        print(f"\n市场概况:")
        print(f"   日期: {summary.get('日期', '')}")
        print(f"   上涨家数: {summary.get('上涨家数', 0)}")
        print(f"   下跌家数: {summary.get('下跌家数', 0)}")
        print(f"   涨停数: {summary.get('涨停数', 0)}")
        print(f"   跌停数: {summary.get('跌停数', 0)}")
        print(f"   涨跌比: {summary.get('涨跌比', 0)}")

        print(f"\n板块数量: {len(sectors)}")

        # 查找算力板块
        for sector in sectors:
            if sector.get('sector_name') == '算力':
                print(f"\n算力板块数据:")
                print(f"   板块代码: {sector.get('sector_code', '')}")
                print(f"   涨停数: {sector.get('stock_count', 0)}")
                print(f"   涨停股票:")
                for stock in sector.get('stocks', []):
                    print(f"      - {stock.get('股票名称')} ({stock.get('股票代码')}): {stock.get('连板天数')}")
                break

        return {'success': True, 'sector_count': len(sectors)}

    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return {'success': False, 'error': str(e)}


if __name__ == "__main__":
    print("\n开盘啦数据接口验证")
    print("=" * 60)
    print()

    # 运行测试
    result1 = test_sector_detailed_data()
    result2 = test_sector_ranking()

    # 最终总结
    print("\n" + "=" * 60)
    print("最终测试总结")
    print("=" * 60)
    print(f"get_sector_detailed_data: {'✓ 通过' if result1.get('success') else '✗ 失败'}")
    print(f"get_sector_ranking: {'✓ 通过' if result2.get('success') else '✗ 失败'}")

    if result1.get('success') and result2.get('success'):
        print("\n✓ 所有测试通过！数据接口工作正常。")
    else:
        print("\n✗ 部分测试失败，请检查配置或网络连接。")
