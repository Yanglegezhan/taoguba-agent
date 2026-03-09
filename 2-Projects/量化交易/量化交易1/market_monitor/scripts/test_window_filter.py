# -*- coding: utf-8 -*-
"""
测试窗口过滤功能
"""

import pandas as pd
import sys
sys.path.append('.')

from premium_table_v3 import PremiumTableV3

print("=" * 60)
print("测试窗口过滤功能")
print("=" * 60)

# 加载数据
board_df = pd.read_csv('output/board_analysis.csv', encoding='utf-8-sig')
board_df['日期'] = pd.to_datetime(board_df['日期'])

# 加载概念
concept_dict = {}
try:
    concept_cache = pd.read_csv('output/concept_cache.csv', encoding='utf-8-sig', dtype={'股票代码': str})
    concept_cache['股票代码'] = concept_cache['股票代码'].str.zfill(6)
    concept_dict = dict(zip(concept_cache['股票代码'], concept_cache['概念']))
except:
    pass

print(f"\n数据加载完成")
print(f"数据日期范围: {board_df['日期'].min().date()} 至 {board_df['日期'].max().date()}")

# 生成溢价表
print(f"\n生成溢价表...")
generator = PremiumTableV3(board_df, concept_dict, use_correlation=True)
premium_table = generator.generate_table(days=20)

# 统计结果
print(f"\n溢价表统计:")
print(f"总行数: {len(premium_table)}")
print(f"总列数: {len(premium_table.columns)}")

# 检查最后一列
last_col = premium_table.columns[-1]
print(f"\n最后一列（{last_col}）统计:")
values = premium_table[last_col].dropna()
print(f"非空值数量: {len(values)}")

# 统计包含"板"的
board_values = values[values.astype(str).str.contains('板', na=False)]
print(f"包含'板'的数量: {len(board_values)}")

# 统计2板
board_2 = values[values.astype(str).str.contains('2板', na=False)]
print(f"2板数量: {len(board_2)}")

# 对比实际数据
actual_date = pd.to_datetime(last_col)
actual_data = board_df[board_df['日期'] == actual_date]
actual_board_2 = actual_data[actual_data['连板数'] == 2]
print(f"\n实际数据对比:")
print(f"实际2板股票数: {len(actual_board_2)}")
print(f"溢价表2板数量: {len(board_2)}")
print(f"差异: {len(board_2) - len(actual_board_2)}")

if len(board_2) > len(actual_board_2):
    print(f"\n⚠️ 溢价表中2板数量多于实际数据！")
    print(f"可能原因：追踪了窗口外的股票")
else:
    print(f"\n✓ 溢价表数据正常")

# 保存测试结果
premium_table.to_csv('output/连板溢价表_测试.csv', index=False, encoding='utf-8-sig')
print(f"\n测试结果已保存: output/连板溢价表_测试.csv")
