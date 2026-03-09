"""
测试DataFrame列名
"""

import sys
from pathlib import Path

# 添加src目录到Python路径
src_path = Path(__file__).parent / 'src'
sys.path.insert(0, str(src_path))

from src.data_sources.kaipanla_client import KaipanlaClient

def test_dataframe_columns():
    """测试获取的DataFrame列名"""
    client = KaipanlaClient()
    
    print("测试获取2026-02-13的涨停数据...")
    print()
    
    # 获取涨停股数据
    limit_up_data = client.get_limit_up_stocks("2026-02-13")
    
    print(f"获取到 {len(limit_up_data)} 只涨停股")
    print()
    print("DataFrame列名:")
    for col in limit_up_data.columns:
        print(f"  - {col}")
    
    print()
    print("前3行数据:")
    print(limit_up_data.head(3))
    
    print()
    print("=" * 80)
    
    # 获取连板股数据
    continuous_data = client.get_continuous_limit_up_stocks("2026-02-13")
    
    print(f"获取到 {len(continuous_data)} 只连板股")
    print()
    print("DataFrame列名:")
    for col in continuous_data.columns:
        print(f"  - {col}")
    
    print()
    print("前3行数据:")
    print(continuous_data.head(3))


if __name__ == '__main__':
    test_dataframe_columns()
