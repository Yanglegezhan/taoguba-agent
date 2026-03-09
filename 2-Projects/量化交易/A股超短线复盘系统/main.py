# -*- coding: utf-8 -*-
"""
A股超短线复盘系统 - 主程序
"""

import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
import pandas as pd

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from data.market_data_fetcher import MarketDataFetcher
from data.sector_data_fetcher import SectorDataFetcher
from analysis.sentiment_analyzer import (
    MarketDayData,
    SentimentCalculator,
    CycleDetector
)


class MasterReplaySystem:
    """超短线复盘系统主类"""

    def __init__(self):
        """初始化"""
        self.market_fetcher = MarketDataFetcher()
        self.sector_fetcher = SectorDataFetcher()
        self.output_dir = Path("output")
        self.output_dir.mkdir(exist_ok=True)

    def fetch_market_data(self, date_str: str) -> MarketDayData:
        """
        获取市场数据并封装为MarketDayData对象

        Args:
            date_str: 日期，格式 'YYYY-MM-DD'

        Returns:
            MarketDayData对象
        """
        print(f"[*] 获取市场数据: {date_str}")

        # 1. 基础市场数据
        overview = self.market_fetcher.get_market_overview(date_str)

        # 2. 连板梯队
        date_num = date_str.replace('-', '')
        consecutive_dict = self.market_fetcher.get_consecutive_limit_up(date_num)
        max_board_info = self.market_fetcher.get_max_consecutive(date_num)

        # 3. 百日新高（估算）
        new_high_count = self.market_fetcher.get_new_high_stocks(date_str)

        # 4. 昨日涨停今日表现
        yesterday_performance = self.market_fetcher.get_yesterday_limit_up_performance(date_str)

        # 5. 估算炸板率（如果没有炸板数据）
        # Akshare不提供炸板数据，估算方法：涨停数的10-15%
        blown_rate = 0.12  # 估算12%

        # 6. 大幅回撤数（估算）
        # 统计跌幅 > -7% 的股票
        try:
            stock_data = self.market_fetcher._retry_request(
                self.market_fetcher.market_fetcher._retry_request.__self__.stock_zh_a_spot_em
            )
            pullback_count = len(stock_data[stock_data['涨跌幅'] < -7.0])
        except:
            pullback_count = 20  # 估算值

        # 构建MarketDayData
        market_data = MarketDayData(
            trading_date=datetime.strptime(date_str, '%Y-%m-%d').date(),
            index_change=overview['index_change'],
            all_a_change=overview['all_a_change'],
            up_count=overview['up_count'],
            down_count=overview['down_count'],
            limit_up_count=overview['limit_up_count'],
            limit_down_count=overview['limit_down_count'],
            max_consecutive=max_board_info['max_consecutive'],
            yesterday_limit_up_performance=yesterday_performance,
            new_100day_high_count=new_high_count,
            blown_limit_up_count=int(overview['limit_up_count'] * blown_rate),
            blown_limit_up_rate=blown_rate,
            large_pullback_count=pullback_count,
            yesterday_blown_performance=-1.0  # 估算值
        )

        return market_data

    def analyze_sentiment(self, market_data: MarketDayData) -> dict:
        """分析市场情绪"""
        print("[*] 分析市场情绪...")

        # 计算情绪指标
        calculator = SentimentCalculator()
        metrics = calculator.calculate_all_metrics(market_data)

        # 检测周期阶段
        detector = CycleDetector()
        cycle_phase = detector.detect_cycle_phase(metrics)

        return {
            'metrics': metrics,
            'cycle_phase': cycle_phase,
            'cycle_desc': detector.get_cycle_description(cycle_phase)
        }

    def analyze_sectors(self, top_n: int = 10) -> dict:
        """分析板块"""
        print("[*] 分析板块...")

        # 获取概念板块TOP
        concepts = self.sector_fetcher.get_top_sectors(
            top_n=top_n,
            sector_type='concept'
        )

        # 获取行业板块TOP
        industries = self.sector_fetcher.get_top_sectors(
            top_n=top_n,
            sector_type='industry'
        )

        return {
            'concepts': concepts,
            'industries': industries
        }

    def analyze_stocks(self, date_str: str) -> dict:
        """分析个股"""
        print("[*] 分析个股...")

        date_num = date_str.replace('-', '')

        # 获取连板梯队
        consecutive_dict = self.market_fetcher.get_consecutive_limit_up(date_num)

        # 获取最高板
        max_board_info = self.market_fetcher.get_max_consecutive(date_num)

        # 获取涨停股池
        limit_up_pool = self.market_fetcher.get_limit_up_pool(date_num)

        # 首板股（连板数=1或没有连板数据）
        first_board_stocks = []
        if limit_up_pool is not None:
            for _, row in limit_up_pool.iterrows():
                consecutive = int(row.get('连板数', 1))
                if consecutive == 1:
                    first_board_stocks.append({
                        'name': row.get('名称', ''),
                        'code': row.get('代码', ''),
                        'industry': row.get('所属行业', ''),
                        'turnover': row.get('成交额', 0),
                        'first_limit_time': row.get('首次封板时间', '')
                    })

        return {
            'consecutive_dict': consecutive_dict,
            'max_board': max_board_info,
            'first_board_stocks': first_board_stocks[:20]  # 取前20只
        }

    def generate_html_report(self, date_str: str, data: dict) -> str:
        """生成HTML报告"""
        print("[*] 生成HTML报告...")

        # 从data中提取各部分数据
        market_data = data['market_data']
        sentiment = data['sentiment']
        sectors = data['sectors']
        stocks = data['stocks']

        metrics = sentiment['metrics']
        cycle_phase = sentiment['cycle_phase']

        # HTML模板
        html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>A股超短线复盘报告 - {date_str}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: "Microsoft YaHei", Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            background: #f9f9f9;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            padding: 30px;
            box-shadow: 0 0 30px rgba(0,0,0,0.1);
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px;
            margin: -30px -30px 40px -30px;
            border-bottom: 4px solid #5568d3;
        }}
        .header h1 {{
            font-size: 36px;
            margin-bottom: 10px;
        }}
        .header .subtitle {{
            font-size: 16px;
            opacity: 0.9;
        }}
        .section {{
            margin-bottom: 40px;
            padding: 25px;
            border-left: 5px solid #667eea;
            background: #f8f9fa;
            border-radius: 5px;
        }}
        .section-title {{
            font-size: 24px;
            color: #667eea;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 2px solid #e9ecef;
        }}
        .metrics {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }}
        .metric-card {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
            box-shadow: 0 2px 10px rgba(0,0,0,0.05);
        }}
        .metric-value {{
            font-size: 32px;
            font-weight: bold;
            color: #667eea;
            margin: 10px 0;
        }}
        .metric-label {{
            font-size: 14px;
            color: #666;
        }}
        .phase-ice {{ background: #a8edea; }}
        .phase-repair {{ background: #f6d365; }}
        .phase-division {{ background: #c6ffdd; }}
        .phase-high {{ background: #f857a6; }}
        .phase-neutral {{ background: #a1c4fd; }}

        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }}
        th, td {{
            padding: 12px 15px;
            text-align: left;
            border-bottom: 1px solid #dee2e6;
        }}
        th {{
            background: #667eea;
            color: white;
            font-weight: bold;
        }}
        tr:hover {{
            background: #f8f9fa;
        }}
        .positive {{ color: #28a745; }}
        .negative {{ color: #dc3545; }}
        .footer {{
            margin-top: 40px;
            padding: 20px;
            text-align: center;
            color: #666;
            font-size: 14px;
            border-top: 1px solid #dee2e6;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>A股超短线复盘报告</h1>
            <p class="subtitle">数据截止: {date_str} | 数据来源: Akshare</p>
        </div>

        <!-- 一、大盘分析 -->
        <div class="section">
            <h2 class="section-title">一、大盘分析</h2>
            <div class="metrics">
                <div class="metric-card">
                    <div class="metric-label">上证指数</div>
                    <div class="metric-value { 'positive' if market_data.index_change > 0 else 'negative' }">
                        {market_data.index_change:+.2f}%
                    </div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">上涨家数</div>
                    <div class="metric-value">{market_data.up_count}</div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">下跌家数</div>
                    <div class="metric-value">{market_data.down_count}</div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">涨停数</div>
                    <div class="metric-value positive">{market_data.limit_up_count}</div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">跌停数</div>
                    <div class="metric-value negative">{market_data.limit_down_count}</div>
                </div>
            </div>
        </div>

        <!-- 二、情绪分析 -->
        <div class="section">
            <h2 class="section-title">二、情绪分析</h2>
            <div class="metrics">
                <div class="metric-card">
                    <div class="metric-label">大盘系数</div>
                    <div class="metric-value">{metrics.market_coefficient:.2f}</div>
                    <div class="metric-label">
                        { '强势' if metrics.market_coefficient > 150 else '弱势' if metrics.market_coefficient < 30 else '震荡' }
                    </div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">超短情绪</div>
                    <div class="metric-value">{metrics.ultra_short_sentiment:.2f}</div>
                    <div class="metric-label">
                        { '高' if metrics.ultra_short_sentiment > 150 else '低' if metrics.ultra_short_sentiment < 50 else '中等' }
                    </div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">亏钱效应</div>
                    <div class="metric-value { 'negative' if metrics.loss_effect > 100 else 'positive' }">
                        {metrics.loss_effect:.2f}
                    </div>
                    <div class="metric-label">
                        { '高' if metrics.loss_effect > 100 else '低' if metrics.loss_effect < 40 else '中等' }
                    </div>
                </div>
            </div>

            <div style="background: white; padding: 20px; border-radius: 8px; margin-top: 20px;">
                <h3 style="color: #667eea; margin-bottom: 15px;">当前周期阶段</h3>
                <div style="font-size: 24px; font-weight: bold; margin-bottom: 10px;"
                     class="{ 'phase-ice' if cycle_phase == '冰点' else 'phase-repair' if cycle_phase == '修复' else 'phase-division' if cycle_phase == '分歧' else 'phase-high' if cycle_phase == '高潮' else 'phase-neutral' }"
                     style="padding: 15px; border-radius: 8px; color: white;">
                    {cycle_phase}
                </div>
                <p style="color: #666; margin-top: 10px;">{sentiment['cycle_desc']}</p>
            </div>
        </div>

        <!-- 三、板块分析 -->
        <div class="section">
            <h2 class="section-title">三、板块分析</h2>

            <h3 style="color: #667eea; margin: 20px 0 10px 0;">🔥 概念板块 TOP 5</h3>
            <table>
                <thead>
                    <tr>
                        <th>排名</th>
                        <th>板块名称</th>
                        <th>涨幅</th>
                        <th>涨停数</th>
                    </tr>
                </thead>
                <tbody>
"""

        # 添加概念板块数据
        for i, concept in enumerate(sectors['concepts'][:5], 1):
            change_class = "positive" if concept['change_pct'] > 0 else "negative"
            html += f"""
                    <tr>
                        <td><strong>{i}</strong></td>
                        <td>{concept['name']}</td>
                        <td class="{change_class}">{concept['change_pct']:+.2f}%</td>
                        <td>{concept.get('limit_up_count', 0)}</td>
                    </tr>
"""

        html += """
                </tbody>
            </table>

            <h3 style="color: #667eea; margin: 20px 0 10px 0;">📊 行业板块 TOP 5</h3>
            <table>
                <thead>
                    <tr>
                        <th>排名</th>
                        <th>板块名称</th>
                        <th>涨幅</th>
                        <th>涨停数</th>
                    </tr>
                </thead>
                <tbody>
"""

        # 添加行业板块数据
        for i, industry in enumerate(sectors['industries'][:5], 1):
            change_class = "positive" if industry['change_pct'] > 0 else "negative"
            html += f"""
                    <tr>
                        <td><strong>{i}</strong></td>
                        <td>{industry['name']}</td>
                        <td class="{change_class}">{industry['change_pct']:+.2f}%</td>
                        <td>{industry.get('limit_up_count', 0)}</td>
                    </tr>
"""

        html += """
                </tbody>
            </table>
        </div>

        <!-- 四、个股分析 -->
        <div class="section">
            <h2 class="section-title">四、个股分析</h2>

            <h3 style="color: #667eea; margin: 20px 0 10px 0;">🏆 连板梯队</h3>
"""

        # 连板梯队
        consecutive_dict = stocks['consecutive_dict']
        if consecutive_dict:
            html += '<table><thead><tr><th>连板数</th><th>股票数量</th><th>代表个股</th></tr></thead><tbody>'
            for board in sorted(consecutive_dict.keys(), reverse=True)[:5]:
                stocks_list = consecutive_dict[board]
                html += f"""
                    <tr>
                        <td><strong>{board}{'板' if board > 1 else '首板'}</strong></td>
                        <td>{len(stocks_list)}只</td>
                        <td>{', '.join([s['name'] for s in stocks_list[:3]])}</td>
                    </tr>
"""
            html += '</tbody></table>'

        # 最高板
        html += f"""
            <h3 style="color: #667eea; margin: 20px 0 10px 0;">👑 最高板</h3>
            <div style="background: white; padding: 20px; border-radius: 8px;">
                <p><strong>{stocks['max_board']['max_consecutive']}{'连板' if stocks['max_board']['max_consecutive'] > 1 else '首板'}</strong></p>
                <p><strong>个股:</strong> {', '.join(stocks['max_board']['stocks'][:5])}</p>
                <p><strong>概念:</strong> {', '.join(stocks['max_board']['concepts'][:5])}</p>
            </div>
"""

        # 首板股
        html += """
            <h3 style="color: #667eea; margin: 20px 0 10px 0;">🚀 首板股精选</h3>
            <table>
                <thead>
                    <tr>
                        <th>股票名称</th>
                        <th>所属行业</th>
                        <th>成交额</th>
                        <th>首封时间</th>
                    </tr>
                </thead>
                <tbody>
"""

        for stock in stocks['first_board_stocks'][:10]:
            html += f"""
                    <tr>
                        <td>{stock['name']}</td>
                        <td>{stock['industry']}</td>
                        <td>{stock['turnover']:.2f}亿</td>
                        <td>{stock['first_limit_time']}</td>
                    </tr>
"""

        html += """
                </tbody>
            </table>
        </div>

        <!-- 五、操作建议 -->
        <div class="section">
            <h2 class="section-title">五、操作建议</h2>
            <div style="background: white; padding: 25px; border-radius: 8px;">
"""

        # 根据周期阶段给出建议
        advice_map = {
            "冰点": """
                <h3>❄️ 冰点期操作策略</h3>
                <ul style="margin-left: 20px; margin-top: 15px;">
                    <li style="margin-bottom: 10px;">✅ <strong>仓位:</strong> 1-3成，轻仓试错</li>
                    <li style="margin-bottom: 10px;">✅ <strong>策略:</strong> 观望为主，可关注逆势抗跌个股</li>
                    <li style="margin-bottom: 10px;">⚠️ <strong>风险:</strong> 亏钱效应明显，避免追高</li>
                    <li>🎯 <strong>机会:</strong> 关注率先反弹的板块和个股</li>
                </ul>
""",
            "修复": """
                <h3>🌱 修复期操作策略</h3>
                <ul style="margin-left: 20px; margin-top: 15px;">
                    <li style="margin-bottom: 10px;">✅ <strong>仓位:</strong> 3-5成，逐步加仓</li>
                    <li style="margin-bottom: 10px;">✅ <strong>策略:</strong> 关注主流板块，低吸核心个股</li>
                    <li style="margin-bottom: 10px;">⚠️ <strong>风险:</strong> 防止修复失败再次回落</li>
                    <li>🎯 <strong>机会:</strong> 修复初期的龙头股有较好收益</li>
                </ul>
""",
            "分歧": """
                <h3>⚖️ 分歧期操作策略</h3>
                <ul style="margin-left: 20px; margin-top: 15px;">
                    <li style="margin-bottom: 10px;">✅ <strong>仓位:</strong> 3-5成，灵活调整</li>
                    <li style="margin-bottom: 10px;">✅ <strong>策略:</strong> 高抛低吸，关注强势股回调机会</li>
                    <li style="margin-bottom: 10px;">⚠️ <strong>风险:</strong> 波动剧烈，避免追涨杀跌</li>
                    <li>🎯 <strong>机会:</strong> 分歧转一致时的介入机会</li>
                </ul>
""",
            "高潮": """
                <h3>🔥 高潮期操作策略</h3>
                <ul style="margin-left: 20px; margin-top: 15px;">
                    <li style="margin-bottom: 10px;">✅ <strong>仓位:</strong> 5-8成，积极参与</li>
                    <li style="margin-bottom: 10px;">✅ <strong>策略:</strong> 追涨杀跌，聚焦主线龙头</li>
                    <li style="margin-bottom: 10px;">⚠️ <strong>风险:</strong> 防止高潮后退潮，控制回撤</li>
                    <li>🎯 <strong>机会:</strong> 情绪高涨期赚钱效应最强</li>
                </ul>
""",
            "震荡": """
                <h3>🔄 震荡期操作策略</h3>
                <ul style="margin-left: 20px; margin-top: 15px;">
                    <li style="margin-bottom: 10px;">✅ <strong>仓位:</strong> 3-5成，均衡配置</li>
                    <li style="margin-bottom: 10px;">✅ <strong>策略:</strong> 高抛低吸，关注轮动机会</li>
                    <li style="margin-bottom: 10px;">⚠️ <strong>风险:</strong> 缺乏主线，避免频繁换股</li>
                    <li>🎯 <strong>机会:</strong> 板块轮动中的补涨机会</li>
                </ul>
"""
        }

        html += advice_map.get(cycle_phase, advice_map["震荡"])

        html += """
            </div>
        </div>

        <div class="footer">
            <p>报告生成时间: {}</p>
            <p>数据来源: Akshare | 本报告仅供参考，不构成投资建议</p>
        </div>
    </div>
</body>
</html>""".format(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

        # 保存HTML文件
        output_file = self.output_dir / f"复盘报告_{date_str}.html"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html)

        return str(output_file)

    def generate_report(self, date: str = None) -> str:
        """
        生成复盘报告

        Args:
            date: 日期，格式 'YYYY-MM-DD'，默认为今日

        Returns:
            报告文件路径
        """
        if date is None:
            date = datetime.now().strftime('%Y-%m-%d')

        print(f"\n{'='*60}")
        print(f"A股超短线复盘系统 - {date}")
        print(f"{'='*60}\n")

        # 1. 获取市场数据
        market_data = self.fetch_market_data(date)

        # 2. 情绪分析
        sentiment = self.analyze_sentiment(market_data)

        # 3. 板块分析
        sectors = self.analyze_sectors(top_n=10)

        # 4. 个股分析
        stocks = self.analyze_stocks(date)

        # 5. 生成报告
        data = {
            'market_data': market_data,
            'sentiment': sentiment,
            'sectors': sectors,
            'stocks': stocks
        }

        report_path = self.generate_html_report(date, data)

        print(f"\n{'='*60}")
        print(f"✅ 复盘报告生成成功: {report_path}")
        print(f"{'='*60}\n")

        return report_path


def main():
    """主函数"""
    system = MasterReplaySystem()

    # 生成今日复盘报告
    report_path = system.generate_report()

    print(f"📊 报告路径: {report_path}")
    print("💡 提示: 可在浏览器中打开HTML文件查看完整报告")


if __name__ == "__main__":
    main()
