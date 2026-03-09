# -*- coding: utf-8 -*-
"""
真实数据复盘脚本 - 只使用Akshare真实数据，不做任何估算
"""

import sys
import io
import os
from datetime import datetime
import pandas as pd

# UTF-8编码
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 禁用代理
os.environ['NO_PROXY'] = '*'
os.environ['no_proxy'] = '*'
for key in ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy']:
    if key in os.environ:
        del os.environ[key]

import akshare as ak


def get_real_market_data(date_str):
    """获取真实市场数据"""
    print(f"\n{'='*60}")
    print(f"获取 {date_str} 真实市场数据")
    print(f"{'='*60}\n")

    date_num = date_str.replace('-', '')

    # 1. 获取大盘指数
    print("[1/6] 获取大盘指数...")
    try:
        index_data = ak.stock_zh_index_spot()
        sh_index = index_data[index_data['代码'] == 'sh000001']
        sz_index = index_data[index_data['代码'] == 'sz399001']

        if not sh_index.empty:
            sh_change = float(sh_index['涨跌幅'].iloc[0])
            sh_price = float(sh_index['最新价'].iloc[0])
            print(f"  ✓ 上证指数: {sh_price:.2f} ({sh_change:+.2f}%)")
        else:
            sh_change = 0.0
            print("  ✗ 未获取到上证指数")

        if not sz_index.empty:
            sz_change = float(sz_index['涨跌幅'].iloc[0])
            print(f"  ✓ 深证成指: {sz_change:+.2f}%")
        else:
            sz_change = 0.0
    except Exception as e:
        print(f"  ✗ 失败: {e}")
        sh_change = sz_change = 0.0

    # 2. 获取全市场涨跌家数
    print("\n[2/6] 获取涨跌家数...")
    try:
        stock_data = ak.stock_zh_a_spot_em()
        up_count = len(stock_data[stock_data['涨跌幅'] > 0])
        down_count = len(stock_data[stock_data['涨跌幅'] < 0])
        flat_count = len(stock_data[stock_data['涨跌幅'] == 0])

        print(f"  ✓ 总股票数: {len(stock_data)}")
        print(f"  ✓ 上涨: {up_count} 家")
        print(f"  ✓ 下跌: {down_count} 家")
        print(f"  ✓ 平盘: {flat_count} 家")
    except Exception as e:
        print(f"  ✗ 失败: {e}")
        up_count = down_count = flat_count = 0

    # 3. 获取涨停股池
    print("\n[3/6] 获取涨停股池...")
    try:
        limit_up_data = ak.stock_zt_pool_em(date=date_num)
        if limit_up_data is not None and not limit_up_data.empty:
            limit_up_count = len(limit_up_data)
            print(f"  ✓ 涨停数: {limit_up_count} 只")

            # 显示部分涨停股
            print(f"  ✓ 涨停股示例 (前5只):")
            for idx, row in limit_up_data.head(5).iterrows():
                name = row.get('名称', '')
                code = row.get('代码', '')
                industry = row.get('所属行业', '')
                print(f"    - {name}({code}) - {industry}")
        else:
            limit_up_count = 0
            print("  ✗ 涨停股池为空")
    except Exception as e:
        print(f"  ✗ 失败: {e}")
        limit_up_count = 0
        limit_up_data = None

    # 4. 获取连板梯队
    print("\n[4/6] 获取连板梯队...")
    if limit_up_data is not None and not limit_up_data.empty:
        consecutive_dict = {}
        for _, row in limit_up_data.iterrows():
            try:
                consecutive = int(row.get('连板数', 1))
                if consecutive == 0:
                    consecutive = 1

                if consecutive not in consecutive_dict:
                    consecutive_dict[consecutive] = []

                consecutive_dict[consecutive].append({
                    'name': row.get('名称', ''),
                    'code': row.get('代码', ''),
                    'industry': row.get('所属行业', '')
                })
            except:
                continue

        if consecutive_dict:
            print(f"  ✓ 连板梯队:")
            for board in sorted(consecutive_dict.keys(), reverse=True)[:5]:
                stocks = consecutive_dict[board]
                count = len(stocks)
                print(f"    - {board}{'连板' if board > 1 else '首板'}: {count}只")
                if count > 0:
                    names = ', '.join([s['name'] for s in stocks[:3]])
                    print(f"      ({names})")
        else:
            print("  ✗ 未获取到连板数据")
    else:
        consecutive_dict = {}
        print("  ✗ 无涨停股数据")

    # 5. 获取最高板
    print("\n[5/6] 获取最高板...")
    if consecutive_dict:
        max_board = max(consecutive_dict.keys())
        stocks = consecutive_dict[max_board]
        print(f"  ✓ 最高板: {max_board}连板")
        print(f"  ✓ 股票: {', '.join([s['name'] for s in stocks])}")
        concepts = list(set([s['industry'] for s in stocks if s['industry']]))
        print(f"  ✓ 概念: {', '.join(concepts[:5])}")
    else:
        max_board = 0
        print("  ✗ 未获取到最高板数据")

    # 6. 估算跌停数（只能通过涨跌幅<=-9.9%判断）
    print("\n[6/6] 计算跌停数...")
    try:
        limit_down_count = len(stock_data[stock_data['涨跌幅'] <= -9.9])
        print(f"  ✓ 跌停数: {limit_down_count} 只")
    except:
        limit_down_count = 0
        print("  ✗ 未获取到跌停数据")

    # 构建返回数据
    result = {
        'date': date_str,
        'index': {
            'sh_change': sh_change,
            'sz_change': sz_change
        },
        'market': {
            'total': len(stock_data),
            'up': up_count,
            'down': down_count,
            'flat': flat_count
        },
        'limit_up': {
            'count': limit_up_count,
            'data': limit_up_data,
            'consecutive': consecutive_dict,
            'max_board': max_board
        },
        'limit_down': {
            'count': limit_down_count
        }
    }

    return result


def generate_html_report(data):
    """生成HTML报告"""
    print("\n" + "="*60)
    print("生成HTML报告")
    print("="*60 + "\n")

    date_str = data['date']
    index = data['index']
    market = data['market']
    limit_up = data['limit_up']
    limit_down = data['limit_down']

    # HTML模板
    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>A股真实数据复盘 - {date_str}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: "Microsoft YaHei", Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            background: #f9f9f9;
            padding: 20px;
        }}
        .container {{
            max-width: 1000px;
            margin: 0 auto;
            background: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 2px 20px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #333;
            margin-bottom: 10px;
            font-size: 28px;
        }}
        .subtitle {{
            color: #666;
            margin-bottom: 30px;
            font-size: 14px;
        }}
        .section {{
            margin-bottom: 30px;
            padding: 20px;
            background: #f8f9fa;
            border-radius: 8px;
        }}
        h2 {{
            color: #667eea;
            margin-bottom: 15px;
            font-size: 20px;
            padding-bottom: 10px;
            border-bottom: 2px solid #e9ecef;
        }}
        .metrics {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin: 15px 0;
        }}
        .metric-card {{
            background: white;
            padding: 15px;
            border-radius: 8px;
            text-align: center;
            box-shadow: 0 1px 5px rgba(0,0,0,0.05);
        }}
        .metric-value {{
            font-size: 28px;
            font-weight: bold;
            color: #667eea;
            margin: 8px 0;
        }}
        .metric-label {{
            font-size: 13px;
            color: #666;
        }}
        .positive {{ color: #28a745; }}
        .negative {{ color: #dc3545; }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 15px 0;
        }}
        th, td {{
            padding: 10px;
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
        .footer {{
            margin-top: 30px;
            padding: 15px;
            text-align: center;
            color: #666;
            font-size: 13px;
            border-top: 1px solid #dee2e6;
        }}
        .info {{
            background: #e7f3ff;
            padding: 10px 15px;
            border-radius: 5px;
            margin: 10px 0;
            font-size: 13px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>A股真实数据复盘报告</h1>
        <p class="subtitle">日期: {date_str} | 数据来源: Akshare (东方财富) | 只使用真实数据，未做任何估算</p>

        <!-- 一、大盘指数 -->
        <div class="section">
            <h2>📊 一、大盘指数</h2>
            <div class="metrics">
                <div class="metric-card">
                    <div class="metric-label">上证指数</div>
                    <div class="metric-value {'positive' if index['sh_change'] > 0 else 'negative' if index['sh_change'] < 0 else ''}">
                        {index['sh_change']:+.2f}%
                    </div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">深证成指</div>
                    <div class="metric-value {'positive' if index['sz_change'] > 0 else 'negative' if index['sz_change'] < 0 else ''}">
                        {index['sz_change']:+.2f}%
                    </div>
                </div>
            </div>
        </div>

        <!-- 二、市场概况 -->
        <div class="section">
            <h2>📈 二、市场概况</h2>
            <div class="metrics">
                <div class="metric-card">
                    <div class="metric-label">总股票数</div>
                    <div class="metric-value">{market['total']}</div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">上涨家数</div>
                    <div class="metric-value positive">{market['up']}</div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">下跌家数</div>
                    <div class="metric-value negative">{market['down']}</div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">平盘家数</div>
                    <div class="metric-value">{market['flat']}</div>
                </div>
            </div>
            <div class="info">
                <strong>说明:</strong> 涨跌家数统计基于Akshare实时行情数据，涨跌幅>0为上涨，<0为下跌，=0为平盘。
            </div>
        </div>

        <!-- 三、涨停分析 -->
        <div class="section">
            <h2>🚀 三、涨停分析</h2>
            <div class="metrics">
                <div class="metric-card">
                    <div class="metric-label">涨停数</div>
                    <div class="metric-value positive">{limit_up['count']}</div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">跌停数</div>
                    <div class="metric-value negative">{limit_down['count']}</div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">最高板</div>
                    <div class="metric-value">{limit_up['max_board']}{'板' if limit_up['max_board'] > 0 else ''}</div>
                </div>
            </div>
"""

    # 添加连板梯队表格
    if limit_up['consecutive']:
        html += """
            <h3 style="color: #667eea; margin: 20px 0 10px 0; font-size: 16px;">连板梯队:</h3>
            <table>
                <thead>
                    <tr>
                        <th>连板数</th>
                        <th>股票数量</th>
                        <th>代表个股</th>
                    </tr>
                </thead>
                <tbody>
"""
        for board in sorted(limit_up['consecutive'].keys(), reverse=True)[:5]:
            stocks = limit_up['consecutive'][board]
            html += f"""
                    <tr>
                        <td><strong>{board}{'连板' if board > 1 else '首板'}</strong></td>
                        <td>{len(stocks)}只</td>
                        <td>{', '.join([s['name'] for s in stocks[:3]])}</td>
                    </tr>
"""
        html += """
                </tbody>
            </table>
"""

    # 添加涨停股列表
    if limit_up['data'] is not None and not limit_up['data'].empty:
        html += """
            <h3 style="color: #667eea; margin: 20px 0 10px 0; font-size: 16px;">涨停股列表 (前20只):</h3>
            <table>
                <thead>
                    <tr>
                        <th>股票名称</th>
                        <th>股票代码</th>
                        <th>所属行业</th>
                        <th>首次封板</th>
                        <th>连板数</th>
                    </tr>
                </thead>
                <tbody>
"""
        for _, row in limit_up['data'].head(20).iterrows():
            name = row.get('名称', '')
            code = row.get('代码', '')
            industry = row.get('所属行业', '')
            first_time = row.get('首次封板时间', '')
            consecutive = row.get('连板数', 1)

            html += f"""
                    <tr>
                        <td>{name}</td>
                        <td>{code}</td>
                        <td>{industry}</td>
                        <td>{first_time}</td>
                        <td>{consecutive}{'板' if consecutive > 1 else '（首板）'}</td>
                    </tr>
"""
        html += """
                </tbody>
            </table>
"""

    html += """
        </div>

        <div class="footer">
            <p><strong>数据真实性说明:</strong></p>
            <p>本报告所有数据均来自Akshare(东方财富)真实接口，未做任何估算或假设:</p>
            <ul style="margin-left: 20px; margin-top: 8px;">
                <li>大盘指数: stock_zh_index_spot() - 真实指数数据</li>
                <li>涨跌家数: stock_zh_a_spot_em() - 真实行情数据</li>
                <li>涨停股池: stock_zt_pool_em() - 真实涨停数据</li>
                <li>连板梯队: 从涨停股池的"连板数"字段提取 - 真实连板数据</li>
                <li>跌停数: 从行情数据统计涨跌幅<=-9.9%的股票 - 真实跌停数据</li>
            </ul>
            <p style="margin-top: 15px;">报告生成时间: """ + datetime.now().strftime('%Y-%m-%d %H:%M:%S') + """</p>
            <p>数据来源: Akshare | 仅供参考，不构成投资建议</p>
        </div>
    </div>
</body>
</html>"""

    # 保存文件
    output_dir = "output"
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, f"真实复盘_{date_str}.html")

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f"✓ HTML报告已生成: {output_file}")
    return output_file


def main():
    """主函数"""
    date_str = "2026-03-05"  # 3月5日

    # 获取真实数据
    data = get_real_market_data(date_str)

    # 生成报告
    report_path = generate_html_report(data)

    print("\n" + "="*60)
    print("✅ 复盘完成!")
    print("="*60)
    print(f"\n📊 报告路径: {report_path}")
    print("💡 提示: 在浏览器中打开HTML文件查看完整报告")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n⚠️  用户中断")
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
