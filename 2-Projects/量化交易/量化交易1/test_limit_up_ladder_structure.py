"""
测试连板梯队数据结构
"""
import sys
from pathlib import Path

# 添加kaipanla_crawler路径
kaipanla_path = Path(__file__).parent / "kaipanla_crawler"
sys.path.insert(0, str(kaipanla_path))

from kaipanla_crawler import KaipanlaCrawler
import json

def test_limit_up_ladder_structure():
    """测试连板梯队数据结构"""
    
    crawler = KaipanlaCrawler()
    
    # 获取2026-02-13的连板梯队数据
    date = "2026-02-13"
    print(f"获取 {date} 的连板梯队数据...")
    
    data = crawler.get_market_limit_up_ladder(date=date)
    
    print("\n" + "=" * 80)
    print("连板梯队数据结构:")
    print("=" * 80)
    
    # 显示数据的键
    print(f"\n顶层键: {list(data.keys())}")
    
    # 显示ladder数据
    if 'ladder' in data:
        print(f"\nladder键: {list(data['ladder'].keys())}")
        
        # 显示第一只连板股的详细信息
        for consecutive_days, stocks in data['ladder'].items():
            if stocks:
                print(f"\n{consecutive_days}板股票示例:")
                first_stock = stocks[0]
                print(json.dumps(first_stock, indent=2, ensure_ascii=False))
                break
    
    # 保存完整数据到文件
    output_file = "limit_up_ladder_structure_20260213.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"\n完整数据已保存到: {output_file}")

if __name__ == "__main__":
    test_limit_up_ladder_structure()
