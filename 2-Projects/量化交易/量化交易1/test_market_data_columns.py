"""
测试市场数据的列名
"""
import sys
from pathlib import Path

# 添加kaipanla_crawler路径
kaipanla_path = Path(__file__).parent / "kaipanla_crawler"
sys.path.insert(0, str(kaipanla_path))

from kaipanla_crawler import KaipanlaCrawler

def test_market_data_columns():
    """测试市场数据的列名"""
    
    crawler = KaipanlaCrawler()
    
    # 获取2026-02-13的市场数据
    date = "2026-02-13"
    print(f"获取 {date} 的市场数据...")
    
    data = crawler.get_daily_data(end_date=date)
    
    print(f"\n数据类型: {type(data)}")
    print(f"数据形状: {data.shape if hasattr(data, 'shape') else 'N/A'}")
    print(f"\n列名: {list(data.columns) if hasattr(data, 'columns') else list(data.index)}")
    
    print("\n前几行数据:")
    print(data.head() if hasattr(data, 'head') else data)

if __name__ == "__main__":
    test_market_data_columns()
