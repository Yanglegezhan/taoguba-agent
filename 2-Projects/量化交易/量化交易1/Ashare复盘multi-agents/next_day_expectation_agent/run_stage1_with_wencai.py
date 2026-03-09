"""
运行Stage1 Agent测试 - 使用 wencai 获取热门股

测试日期：2026-02-13
使用真实数据
"""

import sys
from pathlib import Path
import json

# 不需要手动添加路径，因为包已经安装
from stage1.stage1_agent import Stage1Agent
from common.logger import get_logger

logger = get_logger(__name__)


def main():
    """运行Stage1 Agent测试"""
    print("=" * 80)
    print("Stage1 Agent 测试运行 - 使用 wencai 获取热门股")
    print("测试日期: 2026-02-13")
    print("=" * 80)
    print()
    
    # 创建配置 - 启用 wencai
    config = {
        'base_dir': 'data',
        'db_path': 'data/historical/gene_pool_history.db',
        'enable_database': False,  # 禁用数据库以简化测试
        'use_wencai': True,        # 优先使用问财获取热门股
        'wencai_fallback': True    # kaipanla失败时回退到问财
    }
    
    print("配置:")
    print(f"  use_wencai: {config['use_wencai']}")
    print(f"  wencai_fallback: {config['wencai_fallback']}")
    print()
    
    # 创建Stage1 Agent实例
    print("1. 初始化Stage1 Agent...")
    try:
        agent = Stage1Agent(config)
        print("   ✓ Agent初始化成功")
        print()
    except Exception as e:
        print(f"   ✗ Agent初始化失败: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # 运行Stage1 Agent
    print("2. 运行Stage1 Agent (日期: 2026-02-13)...")
    print("   注意: 这将调用真实的数据接口")
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
                    
                    # 显示辨识度个股（使用 wencai 获取）
                    recognition_stocks = gene_pool_data.get('recognition_stocks', [])
                    if recognition_stocks:
                        print("辨识度个股（使用 wencai 获取）:")
                        for i, stock in enumerate(recognition_stocks[:10], 1):
                            name = stock.get('name', '未知')
                            hot_rank = stock.get('hot_rank', i)
                            print(f"  {hot_rank}. {name}")
                        print()
                    
                    # 显示连板梯队详情
                    continuous = gene_pool_data.get('continuous_limit_up', [])
                    if continuous:
                        print("连板梯队详情:")
                        for i, stock in enumerate(continuous[:5], 1):  # 只显示前5只
                            code = stock.get('code', '')
                            name = stock.get('name', '')
                            board_height = stock.get('board_height', 0)
                            change_pct = stock.get('change_pct', 0)
                            amount = stock.get('amount', 0)
                            themes = stock.get('themes', [])
                            
                            print(f"  {i}. {code} {name}")
                            print(f"     连板高度: {board_height}板, 涨跌幅: {change_pct:.2f}%")
                            print(f"     成交额: {amount:.0f}万元")
                            print(f"     题材: {', '.join(themes) if themes else '无'}")
                            
                            # 显示技术位
                            tech = stock.get('technical_levels')
                            if tech:
                                ma5_dist = tech.get('distance_to_ma5_pct', 0)
                                ma5 = tech.get('ma5', 0)
                                ma10 = tech.get('ma10', 0)
                                ma20 = tech.get('ma20', 0)
                                print(f"     技术位: MA5={ma5:.2f}, MA10={ma10:.2f}, MA20={ma20:.2f}")
                                print(f"     距MA5: {ma5_dist:.2f}%")
                            print()
                    
                    # 显示趋势股详情
                    trend_stocks = gene_pool_data.get('trend_stocks', [])
                    if trend_stocks:
                        print("趋势股详情:")
                        for stock in trend_stocks:
                            code = stock.get('code', '')
                            name = stock.get('name', '')
                            price = stock.get('price', 0)
                            tech = stock.get('technical_levels', {})
                            ma5_dist = tech.get('distance_to_ma5_pct', 0)
                            print(f"  {code} {name}: 价格={price:.2f}, MA5距离={ma5_dist:.2f}%")
                        print()
                    else:
                        print("未识别到趋势股")
                        print("(连板股通常距离MA5较远，不符合趋势股标准)")
                        print()
                    
                except Exception as e:
                    print(f"  读取基因池文件失败: {e}")
                    import traceback
                    traceback.print_exc()
            
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
