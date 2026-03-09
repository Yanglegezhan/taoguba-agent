# -*- coding: utf-8 -*-
"""检查多出来的2只股票"""
import pandas as pd

# 加载溢价表
premium_df = pd.read_csv('output/连板溢价表_测试.csv', encoding='utf-8-sig')

# 获取最后一列中显示2板的股票
last_col = premium_df.columns[-1]
board_2_rows = premium_df[premium_df[last_col].astype(str).str.contains('2板', na=False)]

print(f"溢价表中显示2板的股票（{last_col}）:")
print(board_2_rows[['股票名称', last_col]].to_string(index=False))

# 加载实际数据
board_df = pd.read_csv('output/board_analysis.csv', encoding='utf-8-sig')
board_df['日期'] = pd.to_datetime(board_df['日期'])

actual_date = pd.to_datetime(last_col)
actual_data = board_df[board_df['日期'] == actual_date]
actual_board_2 = actual_data[actual_data['连板数'] == 2]

print(f"\n实际数据中的2板股票（{actual_date.date()}）:")
print(actual_board_2[['股票名称', '连板数', '涨跌幅']].to_string(index=False))

# 找出差异
premium_stocks = set(board_2_rows['股票名称'].dropna())
actual_stocks = set(actual_board_2['股票名称'])

extra_stocks = premium_stocks - actual_stocks
print(f"\n多出来的股票:")
for stock in extra_stocks:
    print(f"  {stock}")
    # 查看这只股票的历史
    stock_history = board_df[board_df['股票名称'] == stock].sort_values('日期').tail(10)
    print(stock_history[['日期', '连板数', '涨跌幅', '是否涨停']])
