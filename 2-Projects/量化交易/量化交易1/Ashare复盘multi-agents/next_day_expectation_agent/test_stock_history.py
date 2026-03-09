"""
测试个股历史数据获取功能
"""
import sys
from pathlib import Path
from datetime import datetime

# 添加项目路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

from src.data_sources.akshare_client import AKShareClient
from src.common.logger import get_logger

logger = get_logger(__name__)


def test_stock_history():
    """测试获取个股历史数据"""
    
    print("=" * 80)
    print("测试个股历史数据获取功能")
    print("=" * 80)
    
    # 初始化AKShare客户端
    client = AKShareClient()
    
    # 测试股票代码
    test_stocks = [
        "002498",  # 汉缆股份
        "603533",  # 掌阅科技
        "300369",  # 绿盟科技
    ]
    
    # 测试日期
    end_date = "20260213"
    start_date = "20250913"  # 5个月前
    
    print(f"\n测试参数:")
    print(f"  开始日期: {start_date}")
    print(f"  结束日期: {end_date}")
    print(f"  测试股票: {len(test_stocks)} 只")
    print("-" * 80)
    
    for stock_code in test_stocks:
        print(f"\n测试股票: {stock_code}")
        
        try:
            # 获取历史数据
            hist_data = client.get_stock_hist(
                stock_code=stock_code,
                start_date=start_date,
                end_date=end_date,
                period="daily",
                adjust="qfq"
            )
            
            if not hist_data.empty:
                print(f"  ✓ 成功获取 {len(hist_data)} 条历史数据")
                print(f"  列名: {list(hist_data.columns)}")
                print(f"  日期范围: {hist_data['日期'].iloc[0]} 到 {hist_data['日期'].iloc[-1]}")
                print(f"  收盘价范围: {hist_data['收盘'].min():.2f} - {hist_data['收盘'].max():.2f}")
                print(f"  成交量范围: {hist_data['成交量'].min():.0f} - {hist_data['成交量'].max():.0f}")
                
                # 显示最近5天的数据
                print(f"\n  最近5天数据:")
                recent_data = hist_data.tail(5)[['日期', '收盘', '成交量', '涨跌幅']]
                for _, row in recent_data.iterrows():
                    print(f"    {row['日期']}: 收盘={row['收盘']:.2f}, 成交量={row['成交量']:.0f}, 涨跌幅={row['涨跌幅']:.2f}%")
            else:
                print(f"  ✗ 未获取到历史数据")
                
        except Exception as e:
            print(f"  ✗ 获取失败: {e}")
    
    print("\n" + "=" * 80)
    print("测试完成")
    print("=" * 80)


if __name__ == "__main__":
    test_stock_history()
