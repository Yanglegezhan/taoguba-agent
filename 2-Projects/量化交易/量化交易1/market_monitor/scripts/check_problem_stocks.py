# -*- coding: utf-8 -*-
"""检查问题股票"""
import pandas as pd

df = pd.read_csv('output/board_analysis.csv', encoding='utf-8-sig')
df['日期'] = pd.to_datetime(df['日期'])

problem_stocks = ['航天工程', '九鼎新材', '天际股份', '华联控股', '集泰股份', '宏盛股份', '火炬电子', '金海高科']

for stock in problem_stocks:
    stock_data = df[df['股票名称'] == stock].sort_values('日期')
    if not stock_data.empty:
        print(f'\n{stock}:')
        print(stock_data[['日期', '连板数', '涨跌幅', '是否涨停']].tail(15))
    else:
        print(f'\n{stock}: 未找到数据')
