# -*- coding: utf-8 -*-
"""正确检查2板股票（排除前7行）"""
import pandas as pd

df = pd.read_csv('output/连板溢价表_测试.csv', encoding='utf-8-sig')
last_col = df.columns[-1]

# 排除前7行，只看第8行之后的
df_main = df.iloc[7:]

# 找出显示2板的行（精确匹配"2板"，不包括"12板"等）
board_2 = df_main[df_main[last_col].astype(str).str.match(r'^2板', na=False)]

print(f"主表中显示2板的行（共{len(board_2)}行）:")
print("\n序号 | 概念 | 股票名称 | 12-26 | 12-29")
print("-" * 80)

for idx, row in board_2.iterrows():
    print(f"{row['序号']} | {row['概念']} | {row['股票名称']} | {row['2025-12-26']} | {row[last_col]}")

# 加载实际数据对比
board_df = pd.read_csv('output/board_analysis.csv', encoding='utf-8-sig')
board_df['日期'] = pd.to_datetime(board_df['日期'])

actual_date = pd.to_datetime(last_col)
actual_data = board_df[board_df['日期'] == actual_date]
actual_board_2 = actual_data[actual_data['连板数'] == 2]

print(f"\n实际数据中的2板股票: {len(actual_board_2)}只")
print(f"溢价表中的2板股票: {len(board_2)}只")
print(f"差异: {len(board_2) - len(actual_board_2)}")

if len(board_2) == len(actual_board_2):
    print("\n✓ 数据匹配！")
else:
    print(f"\n⚠️ 数据不匹配")
