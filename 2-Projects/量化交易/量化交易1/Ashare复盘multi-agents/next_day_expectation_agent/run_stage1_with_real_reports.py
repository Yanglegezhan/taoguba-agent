"""
运行Stage1 Agent测试脚本 - 使用真实的报告生成

测试日期：2026-02-13
调用真实的报告生成Agent，不使用mock
"""

import sys
from pathlib import Path
import json

# 添加src目录到Python路径
src_path = Path(__file__).parent / 'src'
sys.path.insert(0, str(src_path))

from src.stage1.stage1_agent import Stage1Agent
from src.common.logger import get_logger

logger = get_logger(__name__)


def main():
    """运行Stage1 Agent测试"""
    print("=" * 80)
    print("Stage1 Agent 测试运行 (使用真实报告生成)")
    print("测试日期: 2026-02-13")
    print("=" * 80)
    print()
    
    # 创建配置
    config = {
        'base_dir': 'data',
        'db_path': 'data/historical/gene_pool_history.db',
        'enable_database': True
    }
    
    # 创建Stage1 Agent实例
    print("1. 初始化Stage1 Agent...")
    agent = Stage1Agent(config)
    print("   ✓ Agent初始化成功")
    print()
    
    # 运行Stage1 Agent（使用真实的报告生成）
    print("2. 运行Stage1 Agent (日期: 2026-02-13)...")
    print("   注意：将调用真实的报告生成Agent")
    print()
    
    try:
        result = agent.run('2026-02-13')
        
        print()
        print("=" * 80)
        print("运行结果")
        print("=" * 80)
        
        if result['success']:
            print("✓ Stage1 Agent运行成功!")
            print()
            print("输出文件:")
            print(f"  - 基因池: {result.get('gene_pool_path', 'N/A')}")
            print(f"  - 大盘报告: {result.get('market_report_path', 'N/A')}")
            print(f"  - 情绪报告: {result.get('emotion_report_path', 'N/A')}")
            print(f"  - 题材报告: {result.get('theme_report_path', 'N/A')}")
            print()
            
            # 读取并显示基因池摘要
            if result.get('gene_pool_path'):
                try:
                    with open(result['gene_pool_path'], 'r', encoding='utf-8') as f:
                        gene_pool_data = json.load(f)
                    
                    print("基因池摘要:")
                    print(f"  - 日期: {gene_pool_data.get('date', 'N/A')}")
                    print(f"  - 连板梯队: {len(gene_pool_data.get('continuous_limit_up', []))} 只")
                    print(f"  - 炸板股: {len(gene_pool_data.get('failed_limit_up', []))} 只")
                    print(f"  - 辨识度个股: {len(gene_pool_data.get('recognition_stocks', []))} 只")
                    print(f"  - 趋势股: {len(gene_pool_data.get('trend_stocks', []))} 只")
                    print(f"  - 总计: {len(gene_pool_data.get('all_stocks', {}))} 只")
                    print()
                    
                    # 显示部分个股信息
                    if gene_pool_data.get('continuous_limit_up'):
                        print("连板梯队详情 (前5只):")
                        for i, stock in enumerate(gene_pool_data['continuous_limit_up'][:5]):
                            print(f"  {i+1}. {stock['code']} {stock['name']}")
                            print(f"     连板高度: {stock['board_height']}板")
                            print(f"     涨跌幅: {stock['change_pct']:.2f}%")
                            print(f"     成交额: {stock['amount']:.0f}万元")
                            if stock.get('themes'):
                                print(f"     题材: {', '.join(stock['themes'])}")
                            if stock.get('technical_levels'):
                                tech = stock['technical_levels']
                                print(f"     技术位: 距MA5={tech.get('distance_to_ma5_pct', 0):.2f}%, 距前高={tech.get('distance_to_high_pct', 0):.2f}%")
                            print()
                    
                    # 显示炸板股信息
                    if gene_pool_data.get('failed_limit_up'):
                        print("炸板股详情:")
                        for i, stock in enumerate(gene_pool_data['failed_limit_up'][:5]):
                            print(f"  {i+1}. {stock['code']} {stock['name']}")
                            print(f"     连板高度: {stock['board_height']}板")
                            print()
                    
                except Exception as e:
                    print(f"  读取基因池文件失败: {e}")
        else:
            print("✗ Stage1 Agent运行失败")
            print(f"错误信息: {result.get('error', 'Unknown error')}")
        
        print("=" * 80)
        
    except Exception as e:
        print()
        print("=" * 80)
        print("✗ 运行过程中发生异常")
        print(f"错误: {e}")
        print("=" * 80)
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
