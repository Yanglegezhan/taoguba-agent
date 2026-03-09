# -*- coding: utf-8 -*-
"""
清理重复数据
"""

import pandas as pd
import os

print("=" * 60)
print("清理重复数据")
print("=" * 60)

# 加载数据
data_file = 'data/raw_stock_data.csv'
if not os.path.exists(data_file):
    print(f"错误: 找不到数据文件 {data_file}")
    exit(1)

print(f"\n加载数据: {data_file}")
df = pd.read_csv(data_file, encoding='utf-8-sig')
print(f"原始数据形状: {df.shape}")

# 检查重复
print("\n检查重复记录...")
df['日期'] = pd.to_datetime(df['日期'])
duplicates_before = df.duplicated(subset=['股票代码', '日期'], keep=False).sum()
print(f"重复记录数: {duplicates_before}")

# 确保股票代码是字符串并补齐6位
print("\n标准化股票代码...")
df['股票代码'] = df['股票代码'].astype(str).str.zfill(6)

# 标准化日期格式
print("标准化日期格式...")
df['日期'] = df['日期'].dt.strftime('%Y-%m-%d')

# 去重
print("\n去重...")
df_clean = df.drop_duplicates(subset=['股票代码', '日期'], keep='last')

print(f"清理后数据形状: {df_clean.shape}")
print(f"删除了 {len(df) - len(df_clean)} 条重复记录")

# 保存
print(f"\n保存清理后的数据...")
df_clean.to_csv(data_file, index=False, encoding='utf-8-sig')
print(f"✓ 数据已保存: {data_file}")

# 验证
print("\n验证...")
df_verify = pd.read_csv(data_file, encoding='utf-8-sig')
df_verify['日期'] = pd.to_datetime(df_verify['日期'])
duplicates_after = df_verify.duplicated(subset=['股票代码', '日期'], keep=False).sum()
print(f"剩余重复记录数: {duplicates_after}")

if duplicates_after == 0:
    print("\n✓ 数据清理成功！")
else:
    print(f"\n⚠️ 仍有 {duplicates_after} 条重复记录")

print("\n" + "=" * 60)
print("完成！")
print("=" * 60)
