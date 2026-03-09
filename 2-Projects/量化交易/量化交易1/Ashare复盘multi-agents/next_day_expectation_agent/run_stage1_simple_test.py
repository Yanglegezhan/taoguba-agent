"""
运行Stage1 Agent简化测试脚本

测试日期：2026-02-13
使用mock数据避免实际调用复盘agents
"""

import sys
from pathlib import Path
from unittest.mock import Mock, patch
import json

# 添加src目录到Python路径
src_path = Path(__file__).parent / 'src'
sys.path.insert(0, str(src_path))

from src.stage1.stage1_agent import Stage1Agent
from src.common.models import MarketReport, EmotionReport, ThemeReport, Stock, GenePool, TechnicalLevels
from src.common.logger import get_logger

logger = get_logger(__name__)


def create_mock_market_report():
    """创建模拟的大盘报告"""
    return MarketReport(
        date='2026-02-13',
        current_price=3018.56,
        change_pct=0.62,
        support_levels=[
            {"price": 3000.0, "strength": "强"},
            {"price": 2990.0, "strength": "中"}
        ],
        resistance_levels=[
            {"price": 3050.0, "strength": "强"},
            {"price": 3030.0, "strength": "中"}
        ],
        short_term_scenario="震荡修复",
        short_term_target=[3030, 3050],
        long_term_trend="震荡趋势"
    )


def create_mock_emotion_report():
    """创建模拟的情绪报告"""
    return EmotionReport(
        date='2026-02-13',
        market_coefficient=150.0,
        ultra_short_emotion=45.5,
        loss_effect=28.3,
        cycle_node="修复后分歧",
        profit_score=65,
        position_suggestion="半仓"
    )


def create_mock_theme_report():
    """创建模拟的题材报告"""
    return ThemeReport(
        date='2026-02-13',
        hot_themes=[
            {
                "name": "AI",
                "strength": 85,
                "cycle_stage": "主升期",
                "capacity": "大容量",
                "leading_stocks": ["002810", "300XXX"]
            },
            {
                "name": "数字经济",
                "strength": 72,
                "cycle_stage": "启动期",
                "capacity": "中容量",
                "leading_stocks": ["600XXX"]
            }
        ],
        market_summary="市场整体强势，AI题材持续活跃"
    )


def create_mock_gene_pool():
    """创建模拟的基因池"""
    # 创建测试股票
    stock1 = Stock(
        code='002810',
        name='韩建河山',
        market_cap=45.2,
        price=15.68,
        change_pct=10.0,
        volume=1250000,
        amount=19600,
        turnover_rate=4.2,
        board_height=5,
        themes=['AI', '数字经济']
    )
    
    stock2 = Stock(
        code='300XXX',
        name='测试股A',
        market_cap=30.0,
        price=20.50,
        change_pct=10.0,
        volume=800000,
        amount=16400,
        turnover_rate=3.5,
        board_height=3,
        themes=['新能源']
    )
    
    stock3 = Stock(
        code='600XXX',
        name='炸板股B',
        market_cap=25.0,
        price=12.50,
        change_pct=8.5,
        volume=2000000,
        amount=25000,
        turnover_rate=8.5,
        board_height=0,
        themes=['医药']
    )
    
    return GenePool(
        date='2026-02-13',
        continuous_limit_up=[stock1, stock2],
        failed_limit_up=[stock3],
        recognition_stocks=[],
        trend_stocks=[],
        all_stocks={
            '002810': stock1,
            '300XXX': stock2,
            '600XXX': stock3
        }
    )


def create_mock_technical_levels():
    """创建模拟的技术位"""
    return TechnicalLevels(
        ma5=14.5,
        ma10=13.8,
        ma20=13.0,
        previous_high=16.0,
        chip_zone_low=13.5,
        chip_zone_high=14.5,
        distance_to_ma5_pct=8.1,
        distance_to_high_pct=-2.0
    )


def main():
    """运行Stage1 Agent简化测试"""
    print("=" * 80)
    print("Stage1 Agent 简化测试运行 (使用Mock数据)")
    print("测试日期: 2026-02-13")
    print("=" * 80)
    print()
    
    # 创建配置
    config = {
        'base_dir': 'data',
        'db_path': 'data/historical/gene_pool_history.db',
        'enable_database': False  # 禁用数据库以简化测试
    }
    
    # 创建Stage1 Agent实例
    print("1. 初始化Stage1 Agent...")
    agent = Stage1Agent(config)
    print("   ✓ Agent初始化成功")
    print()
    
    # Mock报告生成器
    print("2. 配置Mock数据...")
    with patch.object(agent.report_generator, 'generate_market_report', return_value=create_mock_market_report()):
        with patch.object(agent.report_generator, 'generate_emotion_report', return_value=create_mock_emotion_report()):
            with patch.object(agent.report_generator, 'generate_theme_report', return_value=create_mock_theme_report()):
                with patch.object(agent.gene_pool_builder, 'build_gene_pool', return_value=create_mock_gene_pool()):
                    with patch.object(agent.technical_calculator, 'calculate_technical_levels', return_value=create_mock_technical_levels()):
                        
                        print("   ✓ Mock数据配置完成")
                        print()
                        
                        # 运行Stage1 Agent
                        print("3. 运行Stage1 Agent (日期: 2026-02-13)...")
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
                                        
                                        # 显示个股详情
                                        print("连板梯队详情:")
                                        for i, stock in enumerate(gene_pool_data['continuous_limit_up']):
                                            print(f"  {i+1}. {stock['code']} {stock['name']}")
                                            print(f"     连板高度: {stock['board_height']}板")
                                            print(f"     涨跌幅: {stock['change_pct']:.2f}%")
                                            print(f"     成交额: {stock['amount']:.0f}万元")
                                            print(f"     换手率: {stock['turnover_rate']:.2f}%")
                                            print(f"     题材: {', '.join(stock['themes'])}")
                                            if stock.get('technical_levels'):
                                                tech = stock['technical_levels']
                                                print(f"     技术位:")
                                                print(f"       MA5={tech['ma5']:.2f}, MA10={tech['ma10']:.2f}, MA20={tech['ma20']:.2f}")
                                                print(f"       前高={tech['previous_high']:.2f}")
                                                print(f"       筹码区=[{tech['chip_zone_low']:.2f}, {tech['chip_zone_high']:.2f}]")
                                                print(f"       距MA5={tech['distance_to_ma5_pct']:.2f}%")
                                                print(f"       距前高={tech['distance_to_high_pct']:.2f}%")
                                            print()
                                        
                                        print("炸板股详情:")
                                        for i, stock in enumerate(gene_pool_data['failed_limit_up']):
                                            print(f"  {i+1}. {stock['code']} {stock['name']}")
                                            print(f"     涨跌幅: {stock['change_pct']:.2f}%")
                                            print(f"     成交额: {stock['amount']:.0f}万元")
                                            print(f"     题材: {', '.join(stock['themes'])}")
                                            print()
                                        
                                    except Exception as e:
                                        print(f"  读取基因池文件失败: {e}")
                                
                                # 读取并显示大盘报告
                                if result.get('market_report_path'):
                                    try:
                                        with open(result['market_report_path'], 'r', encoding='utf-8') as f:
                                            market_data = json.load(f)
                                        
                                        print("大盘报告摘要:")
                                        print(f"  - 当前价格: {market_data.get('current_price', 'N/A')}")
                                        print(f"  - 涨跌幅: {market_data.get('change_pct', 'N/A')}%")
                                        print(f"  - 短期场景: {market_data.get('short_term_scenario', 'N/A')}")
                                        print(f"  - 长期趋势: {market_data.get('long_term_trend', 'N/A')}")
                                        print()
                                    except Exception as e:
                                        print(f"  读取大盘报告失败: {e}")
                                
                                # 读取并显示情绪报告
                                if result.get('emotion_report_path'):
                                    try:
                                        with open(result['emotion_report_path'], 'r', encoding='utf-8') as f:
                                            emotion_data = json.load(f)
                                        
                                        print("情绪报告摘要:")
                                        print(f"  - 市场系数: {emotion_data.get('market_coefficient', 'N/A')}")
                                        print(f"  - 超短情绪: {emotion_data.get('ultra_short_emotion', 'N/A')}")
                                        print(f"  - 周期节点: {emotion_data.get('cycle_node', 'N/A')}")
                                        print(f"  - 盈利分数: {emotion_data.get('profit_score', 'N/A')}")
                                        print(f"  - 仓位建议: {emotion_data.get('position_suggestion', 'N/A')}")
                                        print()
                                    except Exception as e:
                                        print(f"  读取情绪报告失败: {e}")
                                
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
