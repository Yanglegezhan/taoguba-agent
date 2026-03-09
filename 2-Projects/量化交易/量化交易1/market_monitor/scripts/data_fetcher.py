# -*- coding: utf-8 -*-
"""
数据获取模块 - 使用akshare获取A股数据
"""

import akshare as ak
import pandas as pd
from datetime import datetime, timedelta
import os
from config import *


class DataFetcher:
    """数据获取类"""
    
    def __init__(self):
        self.data_dir = DATA_DIR
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)
    
    def get_stock_list(self):
        """获取A股股票列表"""
        try:
            # 获取A股实时行情数据
            stock_zh_a_spot_df = ak.stock_zh_a_spot_em()
            return stock_zh_a_spot_df[['代码', '名称']]
        except Exception as e:
            print(f"获取股票列表失败: {e}")
            return pd.DataFrame()
    
    def get_stock_daily_data(self, stock_code, start_date, end_date):
        """
        获取个股日线数据
        
        Args:
            stock_code: 股票代码
            start_date: 开始日期 YYYYMMDD
            end_date: 结束日期 YYYYMMDD
        """
        try:
            # 确保stock_code是字符串
            stock_code_str = str(stock_code)
            
            # 使用akshare获取个股日线数据
            df = ak.stock_zh_a_hist(
                symbol=stock_code_str,
                period="daily",
                start_date=start_date,
                end_date=end_date,
                adjust="qfq"  # 前复权
            )
            return df
        except Exception as e:
            print(f"获取{stock_code}数据失败: {e}")
            return pd.DataFrame()
    
    def get_limit_up_stocks(self, date_str):
        """
        获取指定日期的涨停股票列表
        
        Args:
            date_str: 日期字符串 YYYYMMDD 或 YYYY-MM-DD
        
        Returns:
            list: 涨停股票代码列表
        """
        try:
            # 转换日期格式
            if '-' in date_str:
                date_str = date_str.replace('-', '')
            
            # 使用akshare获取涨停股票
            limit_up_df = ak.stock_zt_pool_em(date=date_str)
            
            if not limit_up_df.empty and '代码' in limit_up_df.columns:
                return limit_up_df['代码'].astype(str).tolist()
            return []
        except Exception as e:
            print(f"获取{date_str}涨停股票失败: {e}")
            return []
    
    def get_recent_limit_up_stocks(self, days=20):
        """
        获取最近N天的涨停股票列表（去重）
        
        Args:
            days: 天数
        
        Returns:
            list: 股票代码列表
        """
        print(f"正在获取最近{days}天的涨停股票列表...")
        
        end_date = datetime.now()
        all_limit_up_stocks = set()
        
        # 向前推N天（考虑到周末和节假日，实际查询天数要多一些）
        for i in range(days * 2):  # 查询2倍天数以确保覆盖足够的交易日
            check_date = end_date - timedelta(days=i)
            date_str = check_date.strftime('%Y%m%d')
            
            stocks = self.get_limit_up_stocks(date_str)
            if stocks:
                all_limit_up_stocks.update(stocks)
                print(f"  {check_date.date()}: {len(stocks)}只涨停股票")
        
        result = list(all_limit_up_stocks)
        print(f"总计: {len(result)}只股票在最近{days}天有涨停记录")
        return result
    
    def get_selected_stocks_data(self, stock_codes, start_date, end_date):
        """
        获取指定股票列表的日线数据
        
        Args:
            stock_codes: 股票代码列表
            start_date: 开始日期 YYYYMMDD
            end_date: 结束日期 YYYYMMDD
        
        Returns:
            DataFrame: 股票数据
        """
        all_data = []
        total = len(stock_codes)
        
        print(f"开始获取{total}只股票的数据...")
        
        for idx, code in enumerate(stock_codes):
            if (idx + 1) % 50 == 0:
                print(f"进度: {idx + 1}/{total}")
            
            df = self.get_stock_daily_data(code, start_date, end_date)
            if not df.empty:
                df['股票代码'] = str(code)
                # 尝试获取股票名称
                try:
                    stock_info = ak.stock_individual_info_em(symbol=str(code))
                    if not stock_info.empty:
                        name_row = stock_info[stock_info['item'] == '股票简称']
                        if not name_row.empty:
                            df['股票名称'] = name_row['value'].values[0]
                        else:
                            df['股票名称'] = code
                    else:
                        df['股票名称'] = code
                except:
                    df['股票名称'] = code
                
                all_data.append(df)
        
        if all_data:
            result = pd.concat(all_data, ignore_index=True)
            result['股票代码'] = result['股票代码'].astype(str)
            print(f"成功获取{len(result)}条数据记录")
            return result
        
        print("未获取到任何数据")
        return pd.DataFrame()
    
    def get_all_stocks_data(self, start_date, end_date):
        """
        获取所有股票的日线数据
        
        Args:
            start_date: 开始日期 YYYYMMDD
            end_date: 结束日期 YYYYMMDD
        """
        stock_list = self.get_stock_list()
        
        # 确保代码列是字符串类型
        stock_list['代码'] = stock_list['代码'].astype(str)
        
        all_data = []
        
        total = len(stock_list)
        for idx, row in stock_list.iterrows():
            code = row['代码']
            name = row['名称']
            
            if (idx + 1) % 100 == 0:
                print(f"进度: {idx + 1}/{total}")
            
            df = self.get_stock_daily_data(code, start_date, end_date)
            if not df.empty:
                df['股票代码'] = code
                df['股票名称'] = name
                all_data.append(df)
        
        if all_data:
            result = pd.concat(all_data, ignore_index=True)
            # 确保股票代码列是字符串类型
            result['股票代码'] = result['股票代码'].astype(str)
            return result
        return pd.DataFrame()
    
    def get_stock_board_info(self, stock_code):
        """
        判断股票所属板块（主板/创业板/科创板）
        
        Args:
            stock_code: 股票代码
        """
        # 确保stock_code是字符串
        stock_code_str = str(stock_code)
        
        if stock_code_str.startswith('688'):
            return 'kcb'  # 科创板
        elif stock_code_str.startswith('300'):
            return 'cyb'  # 创业板
        else:
            return 'main'  # 主板
    
    def get_stock_concept(self, stock_code):
        """
        获取股票所属概念板块（返回前两个最相关的概念）
        
        Args:
            stock_code: 股票代码
        
        Returns:
            str: 概念字符串，格式如 "航天+商业航天"
        """
        try:
            # 确保stock_code是字符串
            stock_code_str = str(stock_code)
            
            # 获取个股所属概念
            concept_df = ak.stock_individual_info_em(symbol=stock_code_str)
            if not concept_df.empty:
                # 提取概念信息
                concepts = concept_df[concept_df['item'] == '所属概念']['value'].values
                if len(concepts) > 0:
                    # 概念通常是用逗号或分号分隔的字符串
                    concept_str = concepts[0]
                    # 分割概念
                    concept_list = [c.strip() for c in concept_str.replace('；', ',').split(',') if c.strip()]
                    # 返回前两个概念
                    if len(concept_list) >= 2:
                        return f"{concept_list[0]}+{concept_list[1]}"
                    elif len(concept_list) == 1:
                        return concept_list[0]
            return ""
        except Exception as e:
            return ""
    
    def get_stock_concept_full(self, stock_code):
        """
        获取股票所属概念板块（完整版本）
        
        Args:
            stock_code: 股票代码
        
        Returns:
            str: 完整概念字符串
        """
        try:
            # 确保stock_code是字符串
            stock_code_str = str(stock_code)
            
            # 获取个股所属概念
            concept_df = ak.stock_individual_info_em(symbol=stock_code_str)
            if not concept_df.empty:
                # 提取概念信息
                concepts = concept_df[concept_df['item'] == '所属概念']['value'].values
                if len(concepts) > 0:
                    return concepts[0]
            return ""
        except Exception as e:
            return ""
    
    def save_data(self, df, filename):
        """保存数据到CSV"""
        filepath = os.path.join(self.data_dir, filename)
        df.to_csv(filepath, index=False, encoding='utf-8-sig')
        print(f"数据已保存到: {filepath}")
    
    def load_data(self, filename):
        """从CSV加载数据"""
        filepath = os.path.join(self.data_dir, filename)
        if os.path.exists(filepath):
            return pd.read_csv(filepath, encoding='utf-8-sig')
        return pd.DataFrame()


if __name__ == "__main__":
    # 测试代码
    fetcher = DataFetcher()
    
    # 测试获取股票列表
    stock_list = fetcher.get_stock_list()
    print(f"获取到{len(stock_list)}只股票")
    print(stock_list.head())
