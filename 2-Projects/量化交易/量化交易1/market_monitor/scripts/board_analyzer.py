# -*- coding: utf-8 -*-
"""
连板分析模块 - 识别连板个股及其溢价情况
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from config import *


class BoardAnalyzer:
    """连板分析类"""
    
    def __init__(self, data_df):
        """
        初始化
        
        Args:
            data_df: 包含所有股票日线数据的DataFrame
        """
        self.data_df = data_df
        self.data_df['日期'] = pd.to_datetime(self.data_df['日期'])
        
    def calculate_pct_change(self, row):
        """计算涨跌幅"""
        # akshare已经提供了涨跌幅列，直接使用
        if '涨跌幅' in row.index and not pd.isna(row['涨跌幅']):
            # akshare返回的涨跌幅是百分比形式，需要转换为小数
            return row['涨跌幅'] / 100
        
        # 如果没有涨跌幅列，尝试手动计算
        if '涨跌额' in row.index and '收盘' in row.index:
            if pd.isna(row['涨跌额']) or pd.isna(row['收盘']):
                return 0
            prev_close = row['收盘'] - row['涨跌额']
            if prev_close == 0:
                return 0
            return row['涨跌额'] / prev_close
        
        return 0
    
    def is_limit_up(self, pct_change, board_type):
        """
        判断是否涨停
        
        Args:
            pct_change: 涨跌幅
            board_type: 板块类型 (main/cyb/kcb)
        """
        if board_type in ['cyb', 'kcb']:
            return pct_change >= CYB_KCYB_LIMIT_UP
        else:
            return pct_change >= LIMIT_UP_THRESHOLD
    
    def is_limit_down(self, pct_change, board_type):
        """
        判断是否跌停
        
        Args:
            pct_change: 涨跌幅
            board_type: 板块类型 (main/cyb/kcb)
        """
        if board_type in ['cyb', 'kcb']:
            return pct_change <= CYB_KCYB_LIMIT_DOWN
        else:
            return pct_change <= LIMIT_DOWN_THRESHOLD
    
    def calculate_consecutive_boards(self):
        """计算每只股票的连板数（完全向量化版本）"""
        print("开始计算连板数（向量化处理）...")
        
        # 确保股票代码列是字符串类型
        self.data_df['股票代码'] = self.data_df['股票代码'].astype(str)
        
        # 确保日期列是datetime类型
        self.data_df['日期'] = pd.to_datetime(self.data_df['日期'])
        
        # 按股票代码和日期排序
        self.data_df = self.data_df.sort_values(['股票代码', '日期']).reset_index(drop=True)
        
        print(f"处理 {len(self.data_df)} 条记录...")
        
        # 向量化计算涨跌幅
        if '涨跌幅' in self.data_df.columns:
            self.data_df['涨跌幅_decimal'] = self.data_df['涨跌幅'] / 100
        else:
            self.data_df['涨跌幅_decimal'] = 0
        
        # 向量化获取板块类型
        print("识别板块类型...")
        self.data_df['板块类型'] = 'main'
        self.data_df.loc[self.data_df['股票代码'].str.startswith('688'), '板块类型'] = 'kcb'
        self.data_df.loc[self.data_df['股票代码'].str.startswith('300'), '板块类型'] = 'cyb'
        
        # 向量化判断涨停
        print("判断涨跌停...")
        self.data_df['是否涨停'] = False
        self.data_df['是否跌停'] = False
        
        # 主板涨跌停
        main_mask = self.data_df['板块类型'] == 'main'
        self.data_df.loc[main_mask & (self.data_df['涨跌幅_decimal'] >= LIMIT_UP_THRESHOLD), '是否涨停'] = True
        self.data_df.loc[main_mask & (self.data_df['涨跌幅_decimal'] <= LIMIT_DOWN_THRESHOLD), '是否跌停'] = True
        
        # 创业板/科创板涨跌停
        cyb_kcb_mask = self.data_df['板块类型'].isin(['cyb', 'kcb'])
        self.data_df.loc[cyb_kcb_mask & (self.data_df['涨跌幅_decimal'] >= CYB_KCYB_LIMIT_UP), '是否涨停'] = True
        self.data_df.loc[cyb_kcb_mask & (self.data_df['涨跌幅_decimal'] <= CYB_KCYB_LIMIT_DOWN), '是否跌停'] = True
        
        # 计算连板数（使用groupby和cumsum）
        print("计算连板数...")
        
        # 创建涨停标记
        self.data_df['涨停标记'] = self.data_df['是否涨停'].astype(int)
        
        # 为每个连续涨停序列创建组ID
        self.data_df['涨停变化'] = self.data_df.groupby('股票代码')['涨停标记'].diff().fillna(0)
        self.data_df['涨停组'] = (self.data_df['涨停变化'] != 0).astype(int)
        self.data_df['涨停组ID'] = self.data_df.groupby('股票代码')['涨停组'].cumsum()
        
        # 计算每组内的累计涨停数
        self.data_df['连板数'] = self.data_df.groupby(['股票代码', '涨停组ID'])['涨停标记'].cumsum()
        
        # 非涨停日连板数为0
        self.data_df.loc[~self.data_df['是否涨停'], '连板数'] = 0
        
        print("连板数计算完成！")
        
        # 选择需要的列
        result_df = self.data_df[[
            '日期', '股票代码', '股票名称', '收盘', '涨跌幅_decimal',
            '连板数', '板块类型', '是否涨停', '是否跌停'
        ]].copy()
        
        # 重命名列
        result_df = result_df.rename(columns={'涨跌幅_decimal': '涨跌幅', '收盘': '收盘价'})
        
        # 清理临时列
        self.data_df.drop(['涨停标记', '涨停变化', '涨停组', '涨停组ID'], axis=1, inplace=True, errors='ignore')
        
        return result_df
    
    def get_board_type(self, stock_code):
        """获取板块类型"""
        # 确保stock_code是字符串
        stock_code_str = str(stock_code)
        
        if stock_code_str.startswith('688'):
            return 'kcb'
        elif stock_code_str.startswith('300'):
            return 'cyb'
        else:
            return 'main'
    
    def filter_multi_board_stocks(self, board_df, min_boards=MIN_BOARD_COUNT):
        """
        筛选出连板数>=min_boards的股票
        
        Args:
            board_df: 连板数据DataFrame
            min_boards: 最小连板数
        """
        return board_df[board_df['连板数'] >= min_boards].copy()
    
    def get_high_board_stocks(self, board_df, high_boards=HIGH_BOARD_COUNT):
        """
        获取高位板个股（4板以上）
        
        Args:
            board_df: 连板数据DataFrame
            high_boards: 高位板标准
        """
        return board_df[board_df['连板数'] >= high_boards].copy()
    
    def create_premium_matrix(self, board_df, concept_dict=None):
        """
        创建溢价矩阵（第一张图的数据结构）
        
        Args:
            board_df: 连板数据DataFrame
            concept_dict: 股票代码到概念的映射字典
        
        返回：按日期为列、股票为行的涨跌幅矩阵
        """
        # 筛选2板以上个股
        multi_board = self.filter_multi_board_stocks(board_df)
        
        if multi_board.empty:
            return pd.DataFrame()
        
        # 添加概念信息到原始数据
        if concept_dict:
            multi_board['概念'] = multi_board['股票代码'].map(concept_dict)
        
        # 为涨停前一日添加概念标注
        multi_board = self._add_pre_limit_concept(multi_board)
        
        # 创建透视表
        pivot_df = multi_board.pivot_table(
            index=['股票代码', '股票名称', '板块类型'],
            columns='日期',
            values='涨跌幅',
            aggfunc='first'
        )
        
        # 重置索引
        pivot_df = pivot_df.reset_index()
        
        return pivot_df
    
    def _add_pre_limit_concept(self, board_df):
        """
        为涨停前一日添加概念标注
        
        Args:
            board_df: 连板数据DataFrame
        """
        # 按股票代码分组
        for stock_code, group in board_df.groupby('股票代码'):
            group = group.sort_values('日期').reset_index(drop=True)
            
            # 找到所有涨停日
            limit_up_indices = group[group['是否涨停'] == True].index
            
            # 为涨停前一日添加概念标注
            for idx in limit_up_indices:
                if idx > 0:  # 确保有前一日
                    prev_idx = idx - 1
                    if '概念' in group.columns:
                        concept = group.loc[idx, '概念']
                        # 在原DataFrame中更新
                        board_df.loc[
                            (board_df['股票代码'] == stock_code) & 
                            (board_df['日期'] == group.loc[prev_idx, '日期']),
                            '涨停前概念'
                        ] = concept
        
        return board_df
    
    def add_concept_info(self, premium_df, concept_dict):
        """
        为溢价矩阵添加概念信息
        
        Args:
            premium_df: 溢价矩阵
            concept_dict: 股票代码到概念的映射字典
        """
        if '概念' not in premium_df.columns:
            premium_df.insert(2, '概念', '')
        
        for idx, row in premium_df.iterrows():
            stock_code = row['股票代码']
            if stock_code in concept_dict:
                premium_df.at[idx, '概念'] = concept_dict[stock_code]
        
        return premium_df
    
    def format_cell_value(self, value, is_limit_up, is_limit_down):
        """
        格式化单元格值
        
        Args:
            value: 涨跌幅值
            is_limit_up: 是否涨停
            is_limit_down: 是否跌停
        """
        if pd.isna(value):
            return ''
        
        pct_str = f"{value*100:.2f}%"
        
        if is_limit_up:
            return f"涨停 {pct_str}"
        elif is_limit_down:
            return f"跌停 {pct_str}"
        else:
            return pct_str


if __name__ == "__main__":
    """独立运行连板分析"""
    import os
    
    print("=" * 60)
    print("连板分析模块")
    print("=" * 60)
    
    # 加载原始数据
    data_file = 'data/raw_stock_data.csv'
    if not os.path.exists(data_file):
        print(f"错误: 找不到数据文件 {data_file}")
        print("请先运行数据更新！")
        exit(1)
    
    print(f"\n加载数据: {data_file}")
    raw_data = pd.read_csv(data_file, encoding='utf-8-sig')
    print(f"数据形状: {raw_data.shape}")
    
    # 连板分析
    print("\n开始分析连板情况...")
    analyzer = BoardAnalyzer(raw_data)
    board_df = analyzer.calculate_consecutive_boards()
    
    # 保存结果
    output_file = 'output/board_analysis.csv'
    os.makedirs('output', exist_ok=True)
    board_df.to_csv(output_file, index=False, encoding='utf-8-sig')
    
    print(f"\n✓ 连板分析完成！")
    print(f"输出文件: {output_file}")
    print(f"数据形状: {board_df.shape}")
    
    # 显示统计信息
    print("\n连板统计:")
    board_stats = board_df[board_df['连板数'] >= 2].groupby('连板数').size()
    for board_num, count in board_stats.items():
        print(f"  {board_num}板: {count}只股票")

