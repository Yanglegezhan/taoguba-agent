# -*- coding: utf-8 -*-
"""
修复版开盘啦数据获取 - 完整市场数据获取器

解决原接口问题，使用正确的开盘啦API组合
"""

import sys
import io
import os
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


class FixedKaipanlaFetcher:
    """修复版开盘啦数据获取器"""

    def __init__(self):
        self.kp = KaipanlaCrawler()

    def get_complete_data(self, date_str):
        """
        获取完整市场数据

        使用正确的接口组合：
        1. get_daily_data() - 基础数据（涨跌家数）
        2. get_realtime_rise_fall_analysis() - 涨停跌停数、炸板率
        3. get_sector_ranking() - 板块排名和涨停股
        4. get_realtime_board_stocks() - 连板股
        5. get_market_mood() - 市场情绪（涨跌家数）
        """
        print(f"\n{'='*70}")
        print(f"获取 {date_str} 完整市场数据（修复版）")
        print(f"{'='*70}\n")

        data = {
            'date': date_str,
            'index': {},
            'market': {},
            'limit_up': {},
            'sectors': {},
            'consecutive': {},
            'stocks': {}
        }

        # 1. 获取基础数据（涨跌家数、指数）
        print("[1/6] 【基础数据】")
        try:
            daily_data = self.kp.get_daily_data(date_str)

            # 提取关键数据
            data['market'] = {
                'up_count': int(daily_data.get('上涨家数', 0)),
                'down_count': int(daily_data.get('下跌家数', 0)),
                'flat_count': int(daily_data.get('平盘家数', 0)),
                'limit_up_count': int(daily_data.get('涨停数', 0)),
                'limit_down_count': int(daily_data.get('跌停数', 0))
            }

            # 计算指数涨跌幅（从涨停数字段估算）
            # 这里使用实时数据接口获取准确指数
            print(f"  ✓ 总股票: {data['market']['up_count'] + data['market']['down_count']}")
            print(f"  ✓ 涨跌: {data['market']['up_count']}/{data['market']['down_count']}")
            print(f"  ✓ 涨停: {data['market']['limit_up_count']}, 跌停: {data['market']['limit_down_count']}")
        except Exception as e:
            print(f"  ✗ 失败: {e}")

        # 2. 获取实时涨跌分析（准确的涨停跌停、炸板率）
        print("\n[2/6] 【实时涨跌分析】")
        try:
            rise_fall = self.kp.get_realtime_rise_fall_analysis()

            data['limit_up'] = {
                'count': int(rise_fall.get('limit_up_count', 0)),
                'down_count': int(rise_fall.get('limit_down_count', 0)),
                'blown_count': int(rise_fall.get('blown_limit_up_count', 0)),
                'blown_rate': float(rise_fall.get('blown_limit_up_rate', 0)) / 100.0,  # 转换为小数
                'yesterday_performance': float(rise_fall.get('yesterday_limit_up_performance', 0))
            }

            print(f"  ✓ 涨停: {data['limit_up']['count']}")
            print(f"  ✓ 跌停: {data['limit_up']['down_count']}")
            print(f"  ✓ 炸板: {data['limit_up']['blown_count']} (炸板率: {data['limit_up']['blown_rate']*100:.2f}%)")
            print(f"  ✓ 昨日涨停表现: {data['limit_up']['yesterday_performance']:+.2f}%")
        except Exception as e:
            print(f"  ✗ 失败: {e}")
            data['limit_up'] = {
                'count': 0, 'down_count': 0, 'blown_count': 0, 'blown_rate': 0.0,
                'yesterday_performance': 0.0
            }

        # 3. 获取板块排名
        print("\n[3/6] 【板块排名】")
        try:
            sector_data = self.kp.get_sector_ranking(date_str)

            if sector_data and 'sectors' in sector_data:
                # 提取涨幅前10的板块
                top_sectors = sector_data['sectors'][:10]

                sectors_list = []
                for sector in top_sectors:
                    sectors_list.append({
                        'name': sector.get('sector_name', ''),
                        'change': float(sector.get('change_pct', 0)),
                        'limit_up_count': len(sector.get('stocks', []))
                    })

                data['sectors']['top'] = sectors_list
                print(f"  ✓ 概念板块TOP10: {sectors_list[0]['name']} (+{sectors_list[0]['change']:.2f}%)")

                # 统计所有板块的涨停股
                all_limit_up_stocks = []
                for sector in sector_data['sectors']:
                    stocks = sector.get('stocks', [])
                    for stock in stocks:
                        all_limit_up_stocks.append({
                            'name': stock.get('股票名称', ''),
                            'code': stock.get('股票代码', ''),
                            'sector': sector.get('sector_name', ''),
                            'consecutive': self._parse_consecutive(stock.get('连板天数', '')),
                            'first_time': stock.get('首次封板时间', ''),
                            'turnover': stock.get('成交额', 0),
                            'industry': stock.get('概念标签', '')
                        })

                data['stocks']['limit_up'] = all_limit_up_stocks
                print(f"  ✓ 涨停股总数: {len(all_limit_up_stocks)}")
            else:
                data['sectors']['top'] = []
                data['stocks']['limit_up'] = []
        except Exception as e:
            print(f"  ✗ 失败: {e}")
            data['sectors']['top'] = []
            data['stocks']['limit_up'] = []

        # 4. 获取连板梯队
        print("\n[4/6] 【连板梯队】")
        try:
            consecutive_dict = {}

            # 测试获取1-10连板的股票
            for board in range(1, 11):
                try:
                    stocks = self.kp.get_realtime_board_stocks(board_type=board)
                    if stocks and len(stocks) > 0:
                        # 转换为统一格式
                        stock_list = []
                        for s in stocks:
                            stock_list.append({
                                'name': s.get('stock_name', ''),
                                'code': s.get('stock_code', ''),
                                'concepts': s.get('concepts', ''),
                                'turnover': s.get('turnover', 0),
                                'seal_amount': s.get('seal_amount', 0)
                            })

                        consecutive_dict[board] = stock_list
                        print(f"    - {board}{'连板' if board > 1 else '首板'}: {len(stock_list)}只")
                except Exception:
                    pass

            data['consecutive'] = consecutive_dict

            if consecutive_dict:
                max_board = max(consecutive_dict.keys())
                data['consecutive']['max_board'] = max_board
                print(f"  ✓ 连板梯队: {len(consecutive_dict)}个梯队")
                print(f"  ✓ 最高板: {max_board}连板")
            else:
                data['consecutive']['max_board'] = 0
        except Exception as e:
            print(f"  ✗ 失败: {e}")
            data['consecutive'] = {'max_board': 0}

        # 5. 获取市场情绪（实时）
        print("\n[5/6] 【市场情绪】")
        try:
            mood_data = self.kp.get_realtime_market_mood()

            data['market']['up_count'] = int(mood_data.get('上涨家数', data['market'].get('up_count', 0)))
            data['market']['down_count'] = int(mood_data.get('下跌家数', data['market'].get('down_count', 0)))

            print(f"  ✓ 涨跌家数: {data['market']['up_count']}/{data['market']['down_count']}")
        except Exception as e:
            print(f"  ✗ 失败: {e}")

        # 6. 获取指数数据
        print("\n[6/6] 【指数数据】")
        try:
            index_list = self.kp.get_realtime_index_list()

            if index_list and 'indexes' in index_list:
                # 取上证指数
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
                    print(f"  ✓ {data['index']['name']}: {data['index']['sh']:+.2f}%")
                else:
                    data['index'] = {'sh': 0.0, 'name': '上证指数'}
        except Exception as e:
            print(f"  ✗ 失败: {e}")
            data['index'] = {'sh': 0.0, 'name': '上证指数'}

        print("\n" + "="*70)
        print("✅ 完整数据获取完成！")
        print("="*70)

        return data

    def _parse_consecutive(self, consecutive_str):
        """解析连板天数字符串"""
        import re

        if not consecutive_str:
            return 1

        # 尝试提取数字
        match = re.search(r'\d+', str(consecutive_str))
        if match:
            return int(match.group())
        else:
            return 1

    def print_summary(self, data):
        """打印数据摘要"""
        print("\n" + "="*70)
        print("📊 市场数据摘要")
        print("="*70)

        # 指数
        print(f"\n【指数】")
        print(f"  {data['index'].get('name', '指数')}: {data['index'].get('sh', 0):+.2f}%")

        # 市场概况
        print(f"\n【市场概况】")
        print(f"  总股票: {data['market'].get('up_count', 0) + data['market'].get('down_count', 0)}")
        print(f"  涨跌: {data['market'].get('up_count', 0)} / {data['market'].get('down_count', 0)}")

        # 涨停数据
        print(f"\n【涨停数据】")
        print(f"  涨停数: {data['limit_up'].get('count', 0)}")
        print(f"  跌停数: {data['limit_up'].get('down_count', 0)}")
        print(f"  炸板率: {data['limit_up'].get('blown_rate', 0)*100:.2f}%")
        print(f"  昨日涨停表现: {data['limit_up'].get('yesterday_performance', 0):+.2f}%")

        # 连板梯队
        print(f"\n【连板梯队】")
        consecutive = data['consecutive']
        if consecutive:
            max_board = consecutive.get('max_board', 0)
            print(f"  最高板: {max_board}连板")
            for board in sorted([k for k in consecutive.keys() if k != 'max_board'], reverse=True)[:5]:
                count = len(consecutive[board])
                print(f"  {board}连板: {count}只")

        # 板块
        print(f"\n【强势板块】")
        sectors = data['sectors'].get('top', [])[:5]
        for i, sector in enumerate(sectors, 1):
            print(f"  {i}. {sector['name']}: {sector['change']:+.2f}% ({sector['limit_up_count']}只涨停)")

        print("\n" + "="*70)


def main():
    """主函数"""
    date_str = "2026-03-05"

    print("="*70)
    print("【修复版】开盘啦数据获取测试")
    print("="*70)

    fetcher = FixedKaipanlaFetcher()
    data = fetcher.get_complete_data(date_str)

    # 打印摘要
    fetcher.print_summary(data)

    # 保存到文件
    import json
    output_file = f"开盘啦数据_{date_str}.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"\n✓ 数据已保存到: {output_file}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n⚠️  用户中断")
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
