# -*- coding: utf-8 -*-
"""
测试日期输入功能
"""

import pandas as pd

# 模拟加载数据
print("加载数据...")
board_df = pd.read_csv('output/board_analysis.csv', encoding='utf-8-sig')
board_df['日期'] = pd.to_datetime(board_df['日期'])

latest_date = board_df['日期'].max()
earliest_date = board_df['日期'].min()

print(f"数据日期范围: {earliest_date.date()} 至 {latest_date.date()}")

# 测试日期输入
print("\n" + "=" * 60)
print("请输入结束日期（格式：YYYY-MM-DD）")
print(f"直接回车使用最新日期: {latest_date.date()}")
print("=" * 60)

user_input = input("结束日期: ").strip()

end_date = None
if user_input:
    try:
        # 验证日期格式
        end_date = pd.to_datetime(user_input)
        print(f"✓ 使用指定日期: {end_date.date()}")
    except:
        print(f"✗ 日期格式错误，使用最新日期: {latest_date.date()}")
        end_date = None
else:
    print(f"✓ 使用最新日期: {latest_date.date()}")

# 显示结果
if end_date is None:
    print(f"\n将使用最新日期: {latest_date.date()}")
else:
    print(f"\n将使用指定日期: {end_date.date()}")
