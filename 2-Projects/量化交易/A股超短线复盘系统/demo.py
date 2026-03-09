# -*- coding: utf-8 -*-
"""
演示脚本 - 使用示例数据生成报告
"""

import sys
import io
from datetime import datetime
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 添加路径
sys.path.insert(0, str(Path(__file__).parent))

from analysis.sentiment_analyzer import MarketDayData, SentimentCalculator, CycleDetector


def demo_with_sample_data():
    """使用示例数据生成报告"""
    print("\n" + "="*60)
    print("Demo: Sample Data Report Generation")
    print("="*60 + "\n")

    # 示例数据（模拟2026-03-05的市场数据）
    sample_data = MarketDayData(
        trading_date=datetime(2026, 3, 5).date(),
        index_change=1.25,           # 指数涨幅
        all_a_change=1.10,           # 全A涨幅
        up_count=4079,               # 上涨家数
        down_count=1306,             # 下跌家数
        limit_up_count=80,           # 涨停数
        limit_down_count=5,          # 跌停数
        max_consecutive=2,           # 最高板
        yesterday_limit_up_performance=2.5,   # 昨日涨停今表现
        new_100day_high_count=150,   # 百日新高
        blown_limit_up_count=12,     # 炸板数
        blown_limit_up_rate=0.13,    # 炸板率
        large_pullback_count=20,     # 大幅回撤
        yesterday_blown_performance=-1.5  # 昨日炸板今表现
    )

    print("Sample Market Data:")
    print(f"  Date: {sample_data.trading_date}")
    print(f"  Index: +{sample_data.index_change:.2f}%")
    print(f"  Up/Down: {sample_data.up_count} / {sample_data.down_count}")
    print(f"  Limit Up/Down: {sample_data.limit_up_count} / {sample_data.limit_down_count}")
    print(f"  Max Consecutive: {sample_data.max_consecutive} boards")
    print()

    # 计算情绪指标
    calculator = SentimentCalculator()
    metrics = calculator.calculate_all_metrics(sample_data)

    print("Sentiment Metrics:")
    print(f"  Market Coefficient: {metrics.market_coefficient:.2f}")
    print(f"  Ultra Short Sentiment: {metrics.ultra_short_sentiment:.2f}")
    print(f"  Loss Effect: {metrics.loss_effect:.2f}")
    print()

    # 检测周期
    detector = CycleDetector()
    phase = detector.detect_cycle_phase(metrics)

    print("Cycle Detection:")
    print(f"  Phase: {phase}")
    print(f"  Description: {detector.get_cycle_description(phase)}")
    print()

    # 生成HTML报告
    html_content = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>A股超短线复盘报告 - 演示</title>
    <style>
        body {{ font-family: Arial, sans-serif; padding: 20px; background: #f5f5f5; }}
        .container {{ max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        h1 {{ color: #333; border-bottom: 3px solid #667eea; padding-bottom: 10px; }}
        h2 {{ color: #667eea; margin-top: 30px; }}
        .metric {{ display: inline-block; margin: 10px; padding: 15px; background: #f8f9fa; border-radius: 5px; text-align: center; min-width: 150px; }}
        .metric-value {{ font-size: 24px; font-weight: bold; color: #667eea; }}
        .metric-label {{ font-size: 14px; color: #666; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        th, td {{ padding: 10px; text-align: left; border-bottom: 1px solid #ddd; }}
        th {{ background: #667eea; color: white; }}
        .positive {{ color: #28a745; }}
        .negative {{ color: #dc3545; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>A股超短线复盘报告</h1>
        <p><strong>日期:</strong> 2026-03-05</p>
        <p><strong>状态:</strong> 演示数据（非实时）</p>

        <h2>📊 大盘数据</h2>
        <table>
            <tr><th>指标</th><th>数值</th></tr>
            <tr><td>上证指数</td><td class="positive">+{sample_data.index_change:.2f}%</td></tr>
            <tr><td>上涨家数</td><td>{sample_data.up_count}</td></tr>
            <tr><td>下跌家数</td><td>{sample_data.down_count}</td></tr>
            <tr><td>涨停数</td><td class="positive">{sample_data.limit_up_count}</td></tr>
            <tr><td>跌停数</td><td class="negative">{sample_data.limit_down_count}</td></tr>
            <tr><td>最高板</td><td>{sample_data.max_consecutive}板</td></tr>
        </table>

        <h2>📈 情绪指标</h2>
        <div class="metric">
            <div class="metric-label">大盘系数</div>
            <div class="metric-value">{metrics.market_coefficient:.2f}</div>
        </div>
        <div class="metric">
            <div class="metric-label">超短情绪</div>
            <div class="metric-value">{metrics.ultra_short_sentiment:.2f}</div>
        </div>
        <div class="metric">
            <div class="metric-label">亏钱效应</div>
            <div class="metric-value">{metrics.loss_effect:.2f}</div>
        </div>

        <h2>🔄 情绪周期</h2>
        <div style="padding: 20px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border-radius: 8px;">
            <h3 style="margin: 0;">{phase}</h3>
            <p style="margin: 10px 0 0 0; opacity: 0.9;">{detector.get_cycle_description(phase)}</p>
        </div>

        <h2>💡 说明</h2>
        <p>这是一个演示报告，使用的是示例数据。</p>
        <p>要获取真实数据，请确保：</p>
        <ul>
            <li>已安装 akshare 库</li>
            <li>在交易日运行</li>
            <li>网络连接正常</li>
            <li>未使用代理</li>
        </ul>

        <hr style="margin: 30px 0; border: none; border-top: 1px solid #ddd;">
        <p style="text-align: center; color: #999; font-size: 12px;">
            报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}<br>
            数据来源: 示例数据 | 仅供参考
        </p>
    </div>
</body>
</html>"""

    # 保存报告
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    demo_file = output_dir / "demo_report.html"

    with open(demo_file, 'w', encoding='utf-8') as f:
        f.write(html_content)

    print("="*60)
    print("✅ Demo report generated successfully!")
    print(f"📄 Report path: {demo_file.absolute()}")
    print("="*60)
    print("\n💡 提示: 在浏览器中打开HTML文件查看演示报告")


if __name__ == "__main__":
    demo_with_sample_data()
