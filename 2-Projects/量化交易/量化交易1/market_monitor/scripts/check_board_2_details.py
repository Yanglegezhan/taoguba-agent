# -*- coding: utf-8 -*-
"""检查2板股票的详细信息"""
import pandas as pd

df = pd.read_csv('output/连板溢价表_测试.csv', encoding='utf-8-sig')
last_col = df.columns[-1]

# 找出显示2板的行
board_2 = df[df[last_col].astype(str).str.contains('2板', na=False)]

print(f"显示2板的行（共{len(board_2)}行）:")
print("\n序号 | 概念 | 股票名称 | 12-26 | 12-29")
print("-" * 80)

for idx, row in board_2.iterrows():
    print(f"{row['序号']} | {row['概念']} | {row['股票名称']} | {row['2025-12-26']} | {row[last_col]}")
