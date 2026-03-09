"""
测试获取涨停数据
"""

import sys
from pathlib import Path

# 添加kaipanla_crawler到路径
crawler_path = Path(__file__).parent.parent.parent / 'kaipanla_crawler'
sys.path.insert(0, str(crawler_path))

from kaipanla_crawler import KaipanlaCrawler

def test_limit_up_data():
    """测试获取2026-02-13的涨停数据"""
    crawler = KaipanlaCrawler()
    
    print("测试获取2026-02-13的涨停数据...")
    print()
    
    # 获取历史连板梯队数据
    data = crawler.get_market_limit_up_ladder(date="2026-02-13")
    
    print(f"日期: {data.get('date')}")
    print(f"是否实时: {data.get('is_realtime')}")
    print()
    
    ladder = data.get('ladder', {})
    print(f"连板梯队数据: {len(ladder)} 个梯队")
    
    total_stocks = 0
    for consecutive, stocks in sorted(ladder.items(), key=lambda x: int(x[0]), reverse=True):
        print(f"  {consecutive}连板: {len(stocks)} 只")
        total_stocks += len(stocks)
        
        # 显示前3只
        for i, stock in enumerate(stocks[:3]):
            print(f"    {i+1}. {stock.get('stock_code')} {stock.get('stock_name')}")
    
    print()
    print(f"总涨停数: {total_stocks}")
    print()
    
    # 炸板股
    broken_stocks = data.get('broken_stocks', [])
    print(f"炸板股: {len(broken_stocks)} 只")
    for i, stock in enumerate(broken_stocks[:5]):
        print(f"  {i+1}. {stock.get('stock_code')} {stock.get('stock_name')}")
    
    print()
    print("统计信息:")
    stats = data.get('statistics', {})
    for key, value in stats.items():
        print(f"  {key}: {value}")


if __name__ == '__main__':
    test_limit_up_data()
