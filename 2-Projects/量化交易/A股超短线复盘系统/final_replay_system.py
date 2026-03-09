# -*- coding: utf-8 -*-
"""
完整版超短线复盘系统 - 修复版

使用正确的开盘啦接口获取真实数据
"""

import sys
import io
import os
import json
from datetime import datetime

# UTF-8编码
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 禁用代理
os.environ['NO_PROXY'] = '*'
os.environ['no_proxy'] = '*'
for key in ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy']:
    if key in os.environ:
        del os.environ[key]

# 添加开盘啦路径
kaipanla_path = os.path.join(os.path.dirname(__file__), '..', '量化交易1', 'kaipanla_crawler')
if kaipanla_path not in sys.path:
    sys.path.insert(0, kaipanla_path)

from kaipanla_crawler import KaipanlaCrawler


class MasterReplaySystemFixed:
    """修复版复盘系统"""

    def __init__(self):
        self.kp = KaipanlaCrawler()

    def get_market_data(self, date_str):
        """获取市场数据"""
        data = {
            'date': date_str,
            'index': {},
            'market': {},
            'limit_up': {},
            'sectors': {},
            'consecutive': {},
            'stocks': {}
        }

        # 1. 基础数据
        try:
            daily_data = self.kp.get_daily_data(date_str)
            data['market'] = {
                'up_count': int(daily_data.get('上涨家数', 0)),
                'down_count': int(daily_data.get('下跌家数', 0))
            }
        except:
            data['market'] = {'up_count': 0, 'down_count': 0}

        # 2. 涨停数据
        try:
            rise_fall = self.kp.get_realtime_rise_fall_analysis()
            data['limit_up'] = {
                'count': int(rise_fall.get('limit_up_count', 0)),
                'down_count': int(rise_fall.get('limit_down_count', 0)),
                'blown_rate': float(rise_fall.get('blown_limit_up_rate', 0)) / 100.0,
                'yesterday_performance': float(rise_fall.get('yesterday_limit_up_performance', 0))
            }
        except:
            data['limit_up'] = {
                'count': 0, 'down_count': 0, 'blown_rate': 0.0,
                'yesterday_performance': 0.0
            }

        # 3. 板块数据
        try:
            sector_data = self.kp.get_sector_ranking(date_str)
            if sector_data and 'sectors' in sector_data:
                top_sectors = sector_data['sectors'][:10]
                sectors_list = []
                for sector in top_sectors:
                    sectors_list.append({
                        'name': sector.get('sector_name', ''),
                        'change': float(sector.get('change_pct', 0)),
                        'limit_up_count': len(sector.get('stocks', []))
                    })
                data['sectors']['top'] = sectors_list

                # 收集所有涨停股
                all_stocks = []
                for sector in sector_data['sectors']:
                    stocks = sector.get('stocks', [])
                    for stock in stocks:
                        all_stocks.append({
                            'name': stock.get('股票名称', ''),
                            'code': stock.get('股票代码', ''),
                            'sector': sector.get('sector_name', ''),
                            'consecutive': self._parse_consecutive(stock.get('连板天数', '')),
                            'industry': stock.get('概念标签', '')
                        })
                data['stocks']['limit_up'] = all_stocks
        except:
            data['sectors']['top'] = []
            data['stocks']['limit_up'] = []

        # 4. 连板梯队
        try:
            consecutive_dict = {}
            for board in range(1, 6):
                try:
                    stocks = self.kp.get_realtime_board_stocks(board_type=board)
                    if stocks:
                        stock_list = []
                        for s in stocks:
                            stock_list.append({
                                'name': s.get('stock_name', ''),
                                'code': s.get('stock_code', ''),
                                'concepts': s.get('concepts', '')
                            })
                        consecutive_dict[board] = stock_list
                except:
                    pass

            data['consecutive'] = consecutive_dict
            if consecutive_dict:
                data['consecutive']['max_board'] = max(consecutive_dict.keys())
        except:
            data['consecutive'] = {'max_board': 0}

        # 5. 指数数据
        try:
            index_list = self.kp.get_realtime_index_list()
            if index_list and 'indexes' in index_list:
                sh_index = None
                for idx in index_list['indexes']:
                    if idx.get('index_code') == '000001':
                        sh_index = idx
                        break
                if sh_index:
                    data['index'] = {
                        'sh': float(sh_index.get('change_pct', 0)),
                        'name': sh_index.get('name', '上证指数')
                    }
        except:
            data['index'] = {'sh': 0.0, 'name': '上证指数'}

        return data

    def _parse_consecutive(self, s):
        """解析连板数"""
        import re
        if not s:
            return 1
        match = re.search(r'\d+', str(s))
        return int(match.group()) if match else 1

    def analyze_sentiment(self, data):
        """情绪分析"""
        market = data['market']
        limit_up = data['limit_up']

        # 晋级率估算（基于连板数据）
        consecutive = data['consecutive']
        max_board = consecutive.get('max_board', 0)

        # 情绪周期判断
        if max_board <= 2 and limit_up['blown_rate'] > 0.3:
            cycle = "【退潮末期】高位股集体补跌，资金切换低位"
        elif max_board >= 3 and limit_up['count'] > 60:
            cycle = "【主升初期】连板高度提升，涨停数量增加"
        else:
            cycle = "【震荡过渡】新旧周期交替中"

        return {
            'cycle': cycle,
            'max_board': max_board,
            'advance_rate': "估算中（需要历史数据）"
        }

    def identify_main_themes(self, data):
        """识别主线题材"""
        sectors = data['sectors'].get('top', [])
        limit_up_stocks = data['stocks'].get('limit_up', [])

        # 按涨停数和涨幅排序
        main_themes = []
        for sector in sectors[:5]:
            if sector['limit_up_count'] >= 5:
                # 收集板块内的涨停股
                sector_stocks = [s for s in limit_up_stocks if s.get('sector') == sector['name']]
                main_themes.append({
                    'name': sector['name'],
                    'change': sector['change'],
                    'count': sector['limit_up_count'],
                    'stocks': sector_stocks[:5]  # 前5只
                })

        return main_themes

    def generate_report(self, data):
        """生成报告"""
        date_str = data['date']
        sentiment = self.analyze_sentiment(data)
        main_themes = self.identify_main_themes(data)

        # 构建报告文本
        report = f"""
{'='*70}
📊 A股超短线复盘报告 - {date_str}
{'='*70}

一、大盘总结
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
指数：{data['index'].get('name', '上证指数')} {data['index'].get('sh', 0):+.2f}%

市场情绪：
  • 上涨家数：{data['market'].get('up_count', 0)}
  • 下跌家数：{data['market'].get('down_count', 0)}
  • 涨停数量：{data['limit_up'].get('count', 0)}
  • 跌停数量：{data['limit_up'].get('down_count', 0)}
  • 炸板率：{data['limit_up'].get('blown_rate', 0)*100:.2f}%

【定性判断】
当前处于{sentiment['cycle']}

二、板块与主线分析
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
强势板块（涨幅前5）：
"""
        for i, sector in enumerate(data['sectors'].get('top', [])[:5], 1):
            report += f"\n{i}. {sector['name']}：{sector['change']:+.2f}% ({sector['limit_up_count']}只涨停)"

        report += f"""

【主线题材】
"""
        for theme in main_themes:
            report += f"\n• {theme['name']}（{theme['count']}只涨停）："
            report += f"\n  代表股：{', '.join([s['name'] for s in theme['stocks'][:3]])}"

        report += f"""

三、情绪周期判断
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
最高板：{sentiment['max_board']}连板

情绪周期定位：
{sentiment['cycle']}

四、连板梯队
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        consecutive = data['consecutive']
        if consecutive:
            for board in sorted([k for k in consecutive.keys() if k != 'max_board'], reverse=True)[:5]:
                stocks = consecutive.get(board, [])
                report += f"\n{board}{'连板' if board > 1 else '首板'}：{len(stocks)}只"
                if stocks:
                    report += f"（{', '.join([s['name'] for s in stocks[:3]])}）"

        report += f"""

五、涨停股逻辑（部分）
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        # 按连板数排序
        limit_up_stocks = data['stocks'].get('limit_up', [])
        limit_up_stocks.sort(key=lambda x: x.get('consecutive', 1), reverse=True)

        # 最高板股
        max_board = data['consecutive'].get('max_board', 0)
        if max_board > 0:
            max_board_stocks = [s for s in limit_up_stocks if s.get('consecutive', 1) == max_board]
            report += f"\n【{max_board}连板（最高板）】"
            for stock in max_board_stocks[:5]:
                report += f"\n• {stock['name']}（{stock['sector']}）：{stock.get('industry', '')}"

        # 首板股
        first_board_stocks = [s for s in limit_up_stocks if s.get('consecutive', 1) == 1]
        report += f"\n\n【首板股（部分）】"
        for stock in first_board_stocks[:10]:
            report += f"\n• {stock['name']} - {stock['sector']}"

        report += f"""

{'='*70}
数据来源：开盘啦真实数据
{'='*70}
"""
        return report

    def save_report(self, report, date_str):
        """保存报告"""
        output_dir = "output"
        os.makedirs(output_dir, exist_ok=True)
        output_file = os.path.join(output_dir, f"复盘报告_{date_str}.txt")

        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(report)

        return output_file


def main():
    date_str = "2026-03-05"

    print("="*70)
    print("【修复版】A股超短线复盘系统")
    print("="*70)

    system = MasterReplaySystemFixed()

    # 获取数据
    print("\n[*] 正在获取市场数据...")
    data = system.get_market_data(date_str)

    # 生成报告
    print("[*] 正在生成复盘报告...")
    report = system.generate_report(data)

    # 保存报告
    output_file = system.save_report(report, date_str)

    # 显示报告
    print(report)
    print(f"\n✅ 报告已保存到: {output_file}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n⚠️  用户中断")
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
