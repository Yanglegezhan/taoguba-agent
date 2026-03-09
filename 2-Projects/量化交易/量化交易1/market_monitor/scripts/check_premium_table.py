# -*- coding: utf-8 -*-
"""检查溢价表"""
import pandas as pd

df = pd.read_csv('output/连板溢价表_最终版.csv', encoding='utf-8-sig')

print(f"溢价表形状: {df.shape}")
print(f"列名: {list(df.columns)}")

# 检查最后一列（12-29）
last_col = df.columns[-1]
print(f"\n最后一列: {last_col}")

# 统计各种值
values = df[last_col].dropna()
print(f"非空值数量: {len(values)}")

# 统计包含"板"的
board_values = values[values.astype(str).str.contains('板', na=False)]
print(f"\n包含'板'的数量: {len(board_values)}")

# 统计2板
board_2 = values[values.astype(str).str.contains('2板', na=False)]
print(f"2板数量: {len(board_2)}")

# 统计3板
board_3 = values[values.astype(str).str.contains('3板', na=False)]
print(f"3板数量: {len(board_3)}")

# 统计4板及以上
board_4plus = values[values.astype(str).str.contains(r'[4-9]板|[1-9][0-9]板', na=False, regex=True)]
print(f"4板及以上: {len(board_4plus)}")

# 显示前20行的最后一列
print(f"\n前20行的{last_col}列:")
print(df[[last_col]].head(20))

# 显示100-120行的最后一列
print(f"\n100-120行的{last_col}列:")
print(df.iloc[99:120][[last_col]])
