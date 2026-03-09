# -*- coding: utf-8 -*-
"""
市场整体分析模块 - 生成市场整体情况表（第二张图）
"""

import pandas as pd
import numpy as np
from datetime import datetime
import akshare as ak
from config import *


class MarketAnalyzer:
    """市场整体分析类"""
    
    def __init__(self, board_df):
        """
        初始化
        
        Args:
            board_df: 连板分析结果DataFrame
        """
        self.board_df = board_df
    
    def calculate_market_metrics(self):
        """
        计算市场整体指标
        
        返回按日期汇总的市场指标
        """
        # 按日期分组统计
        daily_stats = []
        
        for date, group in self.board_df.groupby('日期'):
            # 基础统计
            total_stocks = len(group)
            up_stocks = len(group[group['涨跌幅'] > 0])
            down_stocks = len(group[group['涨跌幅'] < 0])
            flat_stocks = len(group[group['涨跌幅'] == 0])
            
            # 涨跌停统计
            limit_up_stocks = len(group[group['是否涨停'] == True])
            limit_down_stocks = len(group[group['是否跌停'] == True])
            
            # 连板统计
            board_2 = len(group[group['连板数'] == 2])
            board_3 = len(group[group['连板数'] == 3])
            board_4 = len(group[group['连板数'] == 4])
            board_5_plus = len(group[group['连板数'] >= 5])
            
            # 首板统计（连板数为1）
            first_board = len(group[group['连板数'] == 1])
            
            # 20cm首板（创业板和科创板的首板）
            first_board_20cm = len(group[
                (group['连板数'] == 1) & 
                (group['板块类型'].isin(['cyb', 'kcb']))
            ])
            
            # 涨幅统计
            avg_pct_change = group['涨跌幅'].mean()
            median_pct_change = group['涨跌幅'].median()
            
            # 涨停率
            limit_up_rate = limit_up_stocks / total_stocks if total_stocks > 0 else 0
            
            # 上涨家数占比
            up_rate = up_stocks / total_stocks if total_stocks > 0 else 0
            
            daily_stats.append({
                '日期': date,
                '总家数': total_stocks,
                '上涨家数': up_stocks,
                '下跌家数': down_stocks,
                '平盘家数': flat_stocks,
                '涨停数': limit_up_stocks,
                '跌停数': limit_down_stocks,
                '首板数': first_board,
                '20cm首板数': first_board_20cm,
                '2板数': board_2,
                '3板数': board_3,
                '4板数': board_4,
                '5板+数': board_5_plus,
                '平均涨跌幅': avg_pct_change,
                '中位数涨跌幅': median_pct_change,
                '涨停率': limit_up_rate,
                '上涨率': up_rate
            })
        
        return pd.DataFrame(daily_stats)
    
    def get_index_data(self, start_date, end_date):
        """
        获取大盘指数数据
        
        Args:
            start_date: 开始日期 YYYYMMDD 字符串
            end_date: 结束日期 YYYYMMDD 字符串
        """
        try:
            # 获取上证指数
            sh_index = ak.stock_zh_index_daily(symbol="sh000001")
            
            # 确保date列是datetime类型
            if 'date' in sh_index.columns:
                sh_index['date'] = pd.to_datetime(sh_index['date'])
            
            # 转换start_date和end_date为datetime
            start_dt = pd.to_datetime(start_date)
            end_dt = pd.to_datetime(end_date)
            
            # 筛选日期范围
            sh_index = sh_index[(sh_index['date'] >= start_dt) & (sh_index['date'] <= end_dt)]
            
            # 重命名列
            sh_index = sh_index.rename(columns={'close': '上证指数', 'date': '日期'})
            
            # 计算涨跌幅
            sh_index['上证涨跌幅'] = sh_index['上证指数'].pct_change()
            
            return sh_index[['日期', '上证指数', '上证涨跌幅']]
        except Exception as e:
            print(f"获取指数数据失败: {e}")
            return pd.DataFrame()
    
    def calculate_momentum_indicators(self, market_df):
        """
        计算动能指标
        
        Args:
            market_df: 市场统计数据
        """
        # 连板高度（最高连板数）
        market_df['连板高度'] = market_df.apply(
            lambda row: self._get_max_board_count(row['日期']), axis=1
        )
        
        # 炸板率（假设有炸板数据）
        # 这里简化处理，实际需要更复杂的逻辑
        market_df['炸板率'] = 0.0
        
        return market_df
    
    def _get_max_board_count(self, date):
        """获取指定日期的最高连板数"""
        date_data = self.board_df[self.board_df['日期'] == date]
        if not date_data.empty:
            return date_data['连板数'].max()
        return 0
    
    def create_market_overview(self, start_date, end_date):
        """
        创建市场整体情况表（第二张图）
        
        Args:
            start_date: 开始日期
            end_date: 结束日期
        """
        # 计算市场指标
        market_metrics = self.calculate_market_metrics()
        
        # 获取指数数据
        index_data = self.get_index_data(start_date, end_date)
        
        # 合并数据
        if not index_data.empty:
            market_metrics['日期'] = pd.to_datetime(market_metrics['日期'])
            index_data['日期'] = pd.to_datetime(index_data['日期'])
            market_overview = pd.merge(
                market_metrics, 
                index_data, 
                on='日期', 
                how='left'
            )
        else:
            market_overview = market_metrics
        
        # 计算动能指标
        market_overview = self.calculate_momentum_indicators(market_overview)
        
        # 排序
        market_overview = market_overview.sort_values('日期')
        
        return market_overview
    
    def add_extreme_value_markers(self, df, columns, percentile=10):
        """
        为极值数据添加标记（用于后续着色）
        
        Args:
            df: 数据DataFrame
            columns: 需要标记的列
            percentile: 极值百分位（默认10%）
        """
        for col in columns:
            if col in df.columns:
                # 计算上下极值
                upper_threshold = df[col].quantile(1 - percentile/100)
                lower_threshold = df[col].quantile(percentile/100)
                
                # 添加标记列
                df[f'{col}_极值标记'] = df[col].apply(
                    lambda x: 'high' if x >= upper_threshold else ('low' if x <= lower_threshold else 'normal')
                )
        
        return df


if __name__ == "__main__":
    # 测试代码
    print("市场分析模块")
