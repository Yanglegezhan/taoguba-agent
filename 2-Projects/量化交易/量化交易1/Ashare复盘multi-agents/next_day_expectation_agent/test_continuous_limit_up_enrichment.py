"""
测试连板股量价数据补充功能
"""
import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

from src.stage1.gene_pool_builder import GenePoolBuilder
from src.common.logger import get_logger

logger = get_logger(__name__)


def test_continuous_limit_up_enrichment():
    """测试连板股量价数据补充"""
    
    print("=" * 80)
    print("测试连板股量价数据补充功能")
    print("=" * 80)
    
    # 初始化基因池构建器
    builder = GenePoolBuilder()
    
    # 测试日期
    test_date = "2026-02-13"
    
    print(f"\n测试日期: {test_date}")
    print("-" * 80)
    
    # 扫描连板梯队
    print("\n1. 扫描连板梯队...")
    continuous_stocks = builder.scan_continuous_limit_up(test_date)
    
    print(f"\n找到 {len(continuous_stocks)} 只连板股")
    print("-" * 80)
    
    # 显示每只连板股的详细信息
    for i, stock in enumerate(continuous_stocks, 1):
        print(f"\n{i}. {stock.code} {stock.name}")
        print(f"   连板高度: {stock.board_height}板")
        print(f"   价格: {stock.price:.2f}元")
        print(f"   涨跌幅: {stock.change_pct:.2f}%")
        print(f"   成交量: {stock.volume:.0f}手")
        print(f"   成交额: {stock.amount:.2f}万元")
        print(f"   换手率: {stock.turnover_rate:.2f}%")
        print(f"   市值: {stock.market_cap:.2f}亿元")
        print(f"   题材: {', '.join(stock.themes) if stock.themes else '无'}")
    
    print("\n" + "=" * 80)
    print("测试完成")
    print("=" * 80)
    
    # 验证数据完整性
    print("\n数据完整性检查:")
    print("-" * 80)
    
    has_price = sum(1 for s in continuous_stocks if s.price > 0)
    has_change_pct = sum(1 for s in continuous_stocks if s.change_pct != 0)
    has_volume = sum(1 for s in continuous_stocks if s.volume > 0)
    has_amount = sum(1 for s in continuous_stocks if s.amount > 0)
    
    print(f"有价格数据: {has_price}/{len(continuous_stocks)}")
    print(f"有涨跌幅数据: {has_change_pct}/{len(continuous_stocks)}")
    print(f"有成交量数据: {has_volume}/{len(continuous_stocks)}")
    print(f"有成交额数据: {has_amount}/{len(continuous_stocks)}")
    
    if has_price == len(continuous_stocks) and has_amount == len(continuous_stocks):
        print("\n✅ 数据补充成功！所有连板股都有完整的量价数据")
    else:
        print("\n⚠️ 部分连板股缺少量价数据")


if __name__ == "__main__":
    test_continuous_limit_up_enrichment()
