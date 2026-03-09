"""运行 Stage1 Agent 测试 - 使用 wencai 获取热门股"""

import sys
from pathlib import Path
import json

# 添加 src 到路径
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from stage1.stage1_agent import Stage1Agent

def run_stage1_test(date: str = "2026-02-13"):
    """运行 Stage1 Agent 测试"""
    
    print("=" * 70)
    print(f"运行 Stage1 Agent 测试 - 日期: {date}")
    print("=" * 70)
    
    try:
        # 创建配置 - 使用 wencai 获取热门股
        config = {
            'use_wencai': True,        # 优先使用问财
            'wencai_fallback': True    # kaipanla失败时回退到问财
        }
        
        print("\n配置:")
        print(f"  use_wencai: {config['use_wencai']}")
        print(f"  wencai_fallback: {config['wencai_fallback']}")
        
        # 创建 Stage1 Agent
        print("\n正在初始化 Stage1 Agent...")
        agent = Stage1Agent(config=config)
        
        # 运行分析
        print(f"\n正在运行 Stage1 分析 (日期: {date})...")
        print("-" * 70)
        
        result = agent.run(date=date)
        
        # 输出结果
        print("\n" + "=" * 70)
        print("分析结果")
        print("=" * 70)
        
        gene_pool = result.get('gene_pool', {})
        
        print(f"\n基因池统计:")
        print(f"  连板股: {len(gene_pool.get('continuous_limit_up', []))} 只")
        print(f"  炸板股: {len(gene_pool.get('failed_limit_up', []))} 只")
        print(f"  辨识度个股: {len(gene_pool.get('recognition_stocks', []))} 只")
        print(f"  趋势股: {len(gene_pool.get('trend_stocks', []))} 只")
        print(f"  总计: {len(gene_pool.get('all_stocks', {}))} 只")
        
        # 显示辨识度个股详情
        recognition_stocks = gene_pool.get('recognition_stocks', [])
        if recognition_stocks:
            print(f"\n辨识度个股前10名:")
            for i, stock in enumerate(recognition_stocks[:10], 1):
                name = stock.get('name', '未知')
                hot_rank = stock.get('hot_rank', i)
                print(f"  {hot_rank}. {name}")
        
        # 显示趋势股详情
        trend_stocks = gene_pool.get('trend_stocks', [])
        if trend_stocks:
            print(f"\n趋势股详情:")
            for stock in trend_stocks:
                code = stock.get('code', '')
                name = stock.get('name', '')
                price = stock.get('price', 0)
                technical = stock.get('technical_levels', {})
                ma5_dist = technical.get('distance_to_ma5_pct', 0)
                print(f"  {code} {name}: 价格={price:.2f}, MA5距离={ma5_dist:.2f}%")
        else:
            print(f"\n未识别到趋势股")
            
            # 显示连板股技术位分析
            continuous = gene_pool.get('continuous_limit_up', [])
            if continuous:
                print(f"\n连板股技术位分析（前3只）:")
                for stock in continuous[:3]:
                    code = stock.get('code', '')
                    name = stock.get('name', '')
                    price = stock.get('price', 0)
                    technical = stock.get('technical_levels', {})
                    if technical:
                        ma5 = technical.get('ma5', 0)
                        ma10 = technical.get('ma10', 0)
                        ma20 = technical.get('ma20', 0)
                        ma5_dist = technical.get('distance_to_ma5_pct', 0)
                        print(f"  {code} {name}: 价格={price:.2f}, MA5距离={ma5_dist:.2f}%")
                        print(f"    MA5={ma5:.2f}, MA10={ma10:.2f}, MA20={ma20:.2f}")
        
        # 保存结果到文件
        output_file = Path(__file__).parent / "data" / "stage1_output" / f"gene_pool_{date}.json"
        print(f"\n结果已保存到: {output_file}")
        
        print("\n" + "=" * 70)
        print("测试完成")
        print("=" * 70)
        
        return True
        
    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    import sys
    
    # 从命令行参数获取日期，默认为 2026-02-13
    date = sys.argv[1] if len(sys.argv) > 1 else "2026-02-13"
    
    success = run_stage1_test(date=date)
    
    if success:
        print("\n✓ Stage1 Agent 测试成功！")
    else:
        print("\n✗ Stage1 Agent 测试失败")
        sys.exit(1)
