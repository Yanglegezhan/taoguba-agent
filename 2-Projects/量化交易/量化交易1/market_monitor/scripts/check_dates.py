# -*- coding: utf-8 -*-
"""检查数据日期"""
import pandas as pd
from datetime import datetime

df = pd.read_csv('output/board_analysis.csv', encoding='utf-8-sig')
df['日期'] = pd.to_datetime(df['日期'])

dates = df['日期'].drop_duplicates().sort_values()

print('最近10个交易日:')
for d in dates.tail(10):
    print(f'  {d.date()} ({d.strftime("%A")})')

print(f'\n今天是: {datetime.now().date()} ({datetime.now().strftime("%A")})')
print(f'数据最新日期: {dates.max().date()}')

# 检查是否需要更新数据
today = datetime.now().date()
latest_data = dates.max().date()

if latest_data < today:
    print(f'\n⚠️ 数据需要更新！最新数据是 {latest_data}，今天是 {today}')
    print('请运行: batch/一键更新.bat')
else:
    print('\n✓ 数据是最新的')
