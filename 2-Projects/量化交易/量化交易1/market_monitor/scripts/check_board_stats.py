# -*- coding: utf-8 -*-
"""检查连板统计"""
import pandas as pd

df = pd.read_csv('output/board_analysis.csv', encoding='utf-8-sig')
df['日期'] = pd.to_datetime(df['日期'])

# 检查最近几天的数据
recent_dates = sorted(df['日期'].unique())[-5:]

for date in recent_dates:
    date_data = df[df['日期'] == date]
    print(f"\n{'='*60}")
    print(f"{date.date()} 数据统计:")
    print(f"{'='*60}")
    print(f"总股票数: {date_data['股票代码'].nunique()}")
    print(f"涨停股票数: {date_data[date_data['是否涨停'] == True].shape[0]}")
    print(f"2板股票数: {date_data[date_data['连板数'] == 2].shape[0]}")
    print(f"3板股票数: {date_data[date_data['连板数'] == 3].shape[0]}")
    print(f"4板及以上: {date_data[date_data['连板数'] >= 4].shape[0]}")
    
    # 显示2板股票
    board_2 = date_data[date_data['连板数'] == 2][['股票名称', '连板数', '涨跌幅', '是否涨停']].head(10)
    if not board_2.empty:
        print(f"\n2板股票示例（前10只）:")
        print(board_2.to_string(index=False))
