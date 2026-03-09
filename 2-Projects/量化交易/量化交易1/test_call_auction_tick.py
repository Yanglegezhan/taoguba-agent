# -*- coding: utf-8 -*-
"""
测试个股竞价tick数据接口
"""

import sys
sys.path.append('kaipanla_crawler')

from kaipanla_crawler import KaipanlaCrawler
from datetime import datetime


def test_realtime_call_auction():
    """测试实时竞价tick数据"""
    print("=" * 100)
    print("测试：实时竞价tick数据")
    print("=" * 100)
    
    crawler = KaipanlaCrawler()
    
    # 测试股票代码（万科A）
    stock_code = "000002"
    
    print(f"\n获取 {stock_code} 的实时竞价tick数据...")
    data = crawler.get_stock_call_auction_tick(stock_code)
    
    if data:
        print(f"\n股票代码: {data['stock_code']}")
        print(f"日期: {data['date']}")
        print(f"数据类型: {'实时' if data['is_realtime'] else '历史'}")
        
        df = data['data']
        print(f"\n竞价tick数据: {len(df)} 条")
        
        if not df.empty:
            print("\n前5条数据:")
            print(df.head())
            
            # 查看9:15:00的数据
            first_tick = df[df['time'] == '09:15:00']
            if not first_tick.empty:
                print(f"\n9:15:00 数据:")
                print(f"  匹配价: {first_tick['price'].values[0]:.2f} 元")
                print(f"  累计成交量: {first_tick['volume'].values[0]} 手")
            
            # 查看9:25:00的数据
            last_tick = df[df['time'] == '09:25:00']
            if not last_tick.empty:
                print(f"\n9:25:00 数据:")
                print(f"  匹配价: {last_tick['price'].values[0]:.2f} 元")
                print(f"  累计成交量: {last_tick['volume'].values[0]} 手")
            
            # 统计信息
            print(f"\n统计信息:")
            print(f"  最高匹配价: {df['price'].max():.2f} 元")
            print(f"  最低匹配价: {df['price'].min():.2f} 元")
            print(f"  最终成交量: {df['volume'].max()} 手")
    else:
        print("未获取到数据")


def test_historical_call_auction():
    """测试历史竞价tick数据"""
    print("\n" + "=" * 100)
    print("测试：历史竞价tick数据")
    print("=" * 100)
    
    crawler = KaipanlaCrawler()
    
    # 测试股票代码和日期
    stock_code = "000002"
    date = "2026-02-20"
    
    print(f"\n获取 {stock_code} 在 {date} 的竞价tick数据...")
    data = crawler.get_stock_call_auction_tick(stock_code, date)
    
    if data:
        print(f"\n股票代码: {data['stock_code']}")
        print(f"日期: {data['date']}")
        print(f"数据类型: {'实时' if data['is_realtime'] else '历史'}")
        
        df = data['data']
        print(f"\n竞价tick数据: {len(df)} 条")
        
        if not df.empty:
            print("\n所有数据:")
            print(df.to_string())
            
            # 查看9:15:00的数据
            first_tick = df[df['time'] == '09:15:00']
            if not first_tick.empty:
                print(f"\n9:15:00 数据:")
                print(f"  匹配价: {first_tick['price'].values[0]:.2f} 元")
                print(f"  累计成交量: {first_tick['volume'].values[0]} 手")
    else:
        print("未获取到数据")


def test_multiple_stocks():
    """测试多个股票的竞价数据"""
    print("\n" + "=" * 100)
    print("测试：多个股票的竞价tick数据")
    print("=" * 100)
    
    crawler = KaipanlaCrawler()
    
    # 测试多个股票
    stock_codes = ["000002", "600519", "000001"]
    
    for stock_code in stock_codes:
        print(f"\n{'=' * 50}")
        print(f"股票: {stock_code}")
        print(f"{'=' * 50}")
        
        data = crawler.get_stock_call_auction_tick(stock_code)
        
        if data and not data['data'].empty:
            df = data['data']
            
            # 查看9:15:00的数据
            first_tick = df[df['time'] == '09:15:00']
            if not first_tick.empty:
                print(f"9:15:00 匹配价: {first_tick['price'].values[0]:.2f} 元")
                print(f"9:15:00 累计成交量: {first_tick['volume'].values[0]} 手")
            
            # 查看9:25:00的数据
            last_tick = df[df['time'] == '09:25:00']
            if not last_tick.empty:
                print(f"9:25:00 匹配价: {last_tick['price'].values[0]:.2f} 元")
                print(f"9:25:00 累计成交量: {last_tick['volume'].values[0]} 手")
        else:
            print("未获取到数据")


if __name__ == "__main__":
    # 测试实时竞价数据
    test_realtime_call_auction()
    
    # 测试历史竞价数据（注意：东方财富网API可能不支持历史竞价数据）
    # test_historical_call_auction()
    
    # 测试多个股票
    test_multiple_stocks()
