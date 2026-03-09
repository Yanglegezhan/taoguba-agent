"""
运行Stage1 Agent测试脚本 - 使用预先生成的报告

测试日期：2026-02-13
使用已保存的报告文件，跳过报告生成步骤
"""

import sys
from pathlib import Path
import json
from unittest.mock import Mock, patch

# 添加src目录到Python路径
src_path = Path(__file__).parent / 'src'
sys.path.insert(0, str(src_path))

from src.stage1.stage1_agent import Stage1Agent
from src.common.models import MarketReport, EmotionReport, ThemeReport
from src.common.logger import get_logger

logger = get_logger(__name__)


def load_market_report_from_file(file_path: str) -> MarketReport:
    """从文件加载大盘报告"""
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # 提取关键信息
    current_price = data.get('current_price', 0.0)
    
    # 提取支撑压力位
    daily_levels = data.get('daily_levels', {})
    support_levels = daily_levels.get('support', [])
    resistance_levels = daily_levels.get('resistance', [])
    
    # 提取短期预期
    opening_scenarios = data.get('opening_scenarios', [])
    short_term_scenario = opening_scenarios[0].get('scenario', '') if opening_scenarios else ''
    short_term_target = opening_scenarios[0].get('target_levels', []) if opening_scenarios else []
    
    # 提取长期预期
    current_trend = data.get('current_trend', '')
    
    # 构建MarketReport对象
    report = MarketReport(
        date='2026-02-13',
        current_price=current_price,
        change_pct=-1.26,  # 从之前的输出中获取
        support_levels=support_levels,
        resistance_levels=resistance_levels,
        short_term_scenario=short_term_scenario,
        short_term_target=short_term_target,
        long_term_trend=current_trend,
        raw_data=data
    )
    
    return report


def create_mock_emotion_report():
    """创建模拟的情绪报告"""
    return EmotionReport(
        date='2026-02-13',
        market_coefficient=120.0,
        ultra_short_emotion=35.5,
        loss_effect=45.3,
        cycle_node="分歧转一致",
        profit_score=45,
        position_suggestion="轻仓"
    )


def create_mock_theme_report():
    """创建模拟的题材报告"""
    return ThemeReport(
        date='2026-02-13',
        hot_themes=[
            {
                "name": "AI",
                "strength": 75,
                "cycle_stage": "分歧期",
                "capacity": "大容量",
                "leading_stocks": ["002810", "300XXX"]
            },
            {
                "name": "数字经济",
                "strength": 68,
                "cycle_stage": "启动期",
                "capacity": "中容量",
                "leading_stocks": ["600XXX"]
            }
        ],
        market_summary="市场整体偏弱，题材分化明显"
    )


def main():
    """运行Stage1 Agent测试"""
    print("=" * 80)
    print("Stage1 Agent 测试运行 (使用预生成报告)")
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
    
    # 加载预生成的大盘报告
    print("2. 加载预生成的报告...")
    market_report_path = Path(__file__).parent.parent / "index_replay_agent" / "output" / "market_report_20260213.json"
    
    if not market_report_path.exists():
        print(f"   ✗ 大盘报告文件不存在: {market_report_path}")
        print("   请先运行: python -m src.cli --date 2026-02-13 --output-format json --output output/market_report_20260213.json")
        print("   在 index_replay_agent 目录下")
        return
    
    market_report = load_market_report_from_file(str(market_report_path))
    emotion_report = create_mock_emotion_report()
    theme_report = create_mock_theme_report()
    
    print(f"   ✓ 大盘报告加载成功 (价格: {market_report.current_price})")
    print(f"   ✓ 情绪报告创建成功 (市场系数: {emotion_report.market_coefficient})")
    print(f"   ✓ 题材报告创建成功 ({len(theme_report.hot_themes)}个热门题材)")
    print()
    
    # Mock报告生成器
    print("3. 配置Mock报告生成器...")
    with patch.object(agent.report_generator, 'generate_market_report', return_value=market_report):
        with patch.object(agent.report_generator, 'generate_emotion_report', return_value=emotion_report):
            with patch.object(agent.report_generator, 'generate_theme_report', return_value=theme_report):
                
                print("   ✓ Mock配置完成")
                print()
                
                # 运行Stage1 Agent
                print("4. 运行Stage1 Agent (日期: 2026-02-13)...")
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
                                    print("连板梯队示例 (前5只):")
                                    for i, stock in enumerate(gene_pool_data['continuous_limit_up'][:5]):
                                        print(f"  {i+1}. {stock['code']} {stock['name']}")
                                        print(f"     连板高度: {stock['board_height']}板")
                                        print(f"     涨跌幅: {stock['change_pct']:.2f}%")
                                        print(f"     成交额: {stock['amount']:.0f}万元")
                                        print(f"     题材: {', '.join(stock['themes'])}")
                                        if stock.get('technical_levels'):
                                            tech = stock['technical_levels']
                                            print(f"     技术位: 距MA5={tech.get('distance_to_ma5_pct', 0):.2f}%, 距前高={tech.get('distance_to_high_pct', 0):.2f}%")
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
