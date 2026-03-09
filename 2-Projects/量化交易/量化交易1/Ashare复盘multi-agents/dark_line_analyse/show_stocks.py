#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""显示涨停个股列表"""

import json
from pathlib import Path

# 读取报告
report_file = Path('output/reports/dark_line_analysis_20260205.json')
data = json.load(open(report_file, 'r', encoding='utf-8'))

stocks = data.get('stock_details', [])

print(f"\n2026-02-05 涨停个股列表（共{len(stocks)}只）")
print("=" * 80)
print(f"{'序号':<6}{'股票代码':<12}{'股票名称':<12}{'市值(亿)':<12}{'连板':<8}{'涨停原因':<30}")
print("-" * 80)

for i, stock in enumerate(stocks, 1):
    code = stock.get('stock_code', '')
    name = stock.get('stock_name', '')
    market_cap = stock.get('total_market_cap', 0)
    # 市值单位已经是亿元
    market_cap_str = f"{market_cap:.2f}" if market_cap else "N/A"
    consecutive = stock.get('consecutive_days', 0)
    consecutive_str = f"{consecutive}板" if consecutive else "首板"
    reason = stock.get('limit_up_reason', '')[:28]
    
    print(f"{i:<6}{code:<12}{name:<12}{market_cap_str:<12}{consecutive_str:<8}{reason:<30}")

print("=" * 80)

# 统计信息
total_market_cap = sum([s.get('total_market_cap', 0) for s in stocks if s.get('total_market_cap')])
avg_market_cap = total_market_cap / len(stocks) if stocks else 0

print(f"\n统计信息:")
print(f"  - 总市值: {total_market_cap:.2f} 亿")
print(f"  - 平均市值: {avg_market_cap:.2f} 亿")
print(f"  - 首板数量: {sum([1 for s in stocks if s.get('consecutive_days', 0) <= 1])} 只")
print(f"  - 连板数量: {sum([1 for s in stocks if s.get('consecutive_days', 0) >= 2])} 只")
