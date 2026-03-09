# -*- coding: utf-8 -*-
"""
市场监控系统主程序
"""

import os
import sys
import pandas as pd
from datetime import datetime, timedelta
import argparse

from config import *
from data_fetcher import DataFetcher
from board_analyzer import BoardAnalyzer
from market_analyzer import MarketAnalyzer


class MarketMonitor:
    """市场监控主类"""
    
    def __init__(self):
        self.data_fetcher = DataFetcher()
        self.output_dir = OUTPUT_DIR
        
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
    
    def initialize_data(self):
        """初始化数据 - 获取2年历史数据"""
        print("=" * 50)
        print("开始初始化数据（获取2年历史数据）...")
        print("=" * 50)
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=INITIAL_DAYS)
        
        start_date_str = start_date.strftime('%Y%m%d')
        end_date_str = end_date.strftime('%Y%m%d')
        
        print(f"数据范围: {start_date_str} 至 {end_date_str}")
        
        # 获取所有股票数据
        print("正在获取股票数据...")
        all_data = self.data_fetcher.get_all_stocks_data(start_date_str, end_date_str)
        
        if all_data.empty:
            print("获取数据失败！")
            return False
        
        # 保存原始数据
        self.data_fetcher.save_data(all_data, 'raw_stock_data.csv')
        print(f"成功获取 {len(all_data)} 条数据记录")
        
        return True
    
    def update_data_smart(self):
        """智能增量更新数据 - 只更新最近有涨停的股票"""
        print("=" * 50)
        print("开始智能增量更新数据...")
        print("=" * 50)
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=UPDATE_DAYS)
        
        start_date_str = start_date.strftime('%Y%m%d')
        end_date_str = end_date.strftime('%Y%m%d')
        
        print(f"更新范围: {start_date_str} 至 {end_date_str}")
        
        # 1. 获取最近20天有涨停的股票列表
        limit_up_stocks = self.data_fetcher.get_recent_limit_up_stocks(days=20)
        
        if not limit_up_stocks:
            print("未找到涨停股票，执行全量更新...")
            return self.update_data()
        
        print(f"\n找到{len(limit_up_stocks)}只股票需要更新")
        print("预计时间: 1-3分钟")
        
        # 2. 只获取这些股票的数据
        new_data = self.data_fetcher.get_selected_stocks_data(
            limit_up_stocks, 
            start_date_str, 
            end_date_str
        )
        
        if new_data.empty:
            print("获取增量数据失败！")
            return False
        
        # 3. 加载历史数据
        old_data = self.data_fetcher.load_data('raw_stock_data.csv')
        
        # 确保新数据的股票代码是字符串并补齐6位
        new_data['股票代码'] = new_data['股票代码'].astype(str).str.zfill(6)
        new_data['日期'] = pd.to_datetime(new_data['日期']).dt.strftime('%Y-%m-%d')
        
        if not old_data.empty:
            # 确保旧数据的股票代码也是字符串并补齐6位
            old_data['股票代码'] = old_data['股票代码'].astype(str).str.zfill(6)
            old_data['日期'] = pd.to_datetime(old_data['日期']).dt.strftime('%Y-%m-%d')
            
            # 合并数据并去重
            combined_data = pd.concat([old_data, new_data], ignore_index=True)
            
            print(f"合并前: 旧数据{len(old_data)}条 + 新数据{len(new_data)}条 = {len(combined_data)}条")
            
            combined_data = combined_data.drop_duplicates(
                subset=['股票代码', '日期'], 
                keep='last'
            )
            
            print(f"去重后: {len(combined_data)}条记录")
        else:
            combined_data = new_data
        
        # 4. 保存更新后的数据
        self.data_fetcher.save_data(combined_data, 'raw_stock_data.csv')
        print(f"数据更新完成，共 {len(combined_data)} 条记录")
        
        return True
    
    def update_data(self):
        """增量更新数据"""
        print("=" * 50)
        print("开始增量更新数据...")
        print("=" * 50)
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=UPDATE_DAYS)
        
        start_date_str = start_date.strftime('%Y%m%d')
        end_date_str = end_date.strftime('%Y%m%d')
        
        print(f"更新范围: {start_date_str} 至 {end_date_str}")
        
        # 获取增量数据
        print("正在获取增量数据...")
        new_data = self.data_fetcher.get_all_stocks_data(start_date_str, end_date_str)
        
        if new_data.empty:
            print("获取增量数据失败！")
            return False
        
        # 加载历史数据
        old_data = self.data_fetcher.load_data('raw_stock_data.csv')
        
        # 确保新数据的股票代码是字符串并补齐6位
        new_data['股票代码'] = new_data['股票代码'].astype(str).str.zfill(6)
        new_data['日期'] = pd.to_datetime(new_data['日期']).dt.strftime('%Y-%m-%d')
        
        if not old_data.empty:
            # 确保旧数据的股票代码也是字符串并补齐6位
            old_data['股票代码'] = old_data['股票代码'].astype(str).str.zfill(6)
            old_data['日期'] = pd.to_datetime(old_data['日期']).dt.strftime('%Y-%m-%d')
            
            # 合并数据并去重
            combined_data = pd.concat([old_data, new_data], ignore_index=True)
            
            print(f"合并前: 旧数据{len(old_data)}条 + 新数据{len(new_data)}条 = {len(combined_data)}条")
            
            combined_data = combined_data.drop_duplicates(
                subset=['股票代码', '日期'], 
                keep='last'
            )
            
            print(f"去重后: {len(combined_data)}条记录")
        else:
            combined_data = new_data
        
        # 保存更新后的数据
        self.data_fetcher.save_data(combined_data, 'raw_stock_data.csv')
        print(f"数据更新完成，共 {len(combined_data)} 条记录")
        
        return True
    
    def generate_board_premium_csv_v2(self):
        """生成连板溢价CSV V2（新格式）"""
        print("=" * 50)
        print("生成连板溢价表V2（最近20个交易日）...")
        print("=" * 50)
        
        # 加载连板分析数据
        board_file = os.path.join(self.output_dir, 'board_analysis.csv')
        
        if not os.path.exists(board_file):
            print("请先生成连板分析数据！")
            return
        
        board_df = pd.read_csv(board_file, encoding='utf-8-sig')
        board_df['日期'] = pd.to_datetime(board_df['日期'])
        
        # 获取概念信息
        print("正在获取概念信息...")
        concept_dict = {}
        unique_stocks = board_df['股票代码'].unique()
        
        for idx, stock_code in enumerate(unique_stocks):
            if (idx + 1) % 100 == 0:
                print(f"概念获取进度: {idx + 1}/{len(unique_stocks)}")
            
            concept = self.data_fetcher.get_stock_concept(stock_code)
            if concept:
                concept_dict[stock_code] = concept
        
        print(f"获取到 {len(concept_dict)} 只股票的概念信息")
        
        # 导入V2生成器
        from premium_table_v2 import PremiumTableV2
        
        # 生成表格
        generator = PremiumTableV2(board_df, concept_dict)
        premium_table = generator.generate_table(days=20)
        
        # 保存
        output_file = os.path.join(self.output_dir, '连板溢价表_V2.csv')
        premium_table.to_csv(output_file, index=False, encoding='utf-8-sig')
        print(f"连板溢价表V2已生成: {output_file}")
        
        return premium_table
        """生成连板溢价CSV（第一张图）"""
        print("=" * 50)
        print("生成连板溢价表...")
        print("=" * 50)
        
        # 加载数据
        raw_data = self.data_fetcher.load_data('raw_stock_data.csv')
        
        if raw_data.empty:
            print("没有数据！请先初始化或更新数据。")
            return
        
        # 连板分析
        print("正在分析连板情况...")
        analyzer = BoardAnalyzer(raw_data)
        board_df = analyzer.calculate_consecutive_boards()
        
        # 保存连板分析结果
        board_df.to_csv(
            os.path.join(self.output_dir, 'board_analysis.csv'),
            index=False,
            encoding='utf-8-sig'
        )
        
        # 获取概念信息（在创建矩阵前）
        print("正在获取概念信息...")
        concept_dict = {}
        unique_stocks = board_df['股票代码'].unique()
        
        for idx, stock_code in enumerate(unique_stocks):
            if (idx + 1) % 50 == 0:
                print(f"概念获取进度: {idx + 1}/{len(unique_stocks)}")
            
            concept = self.data_fetcher.get_stock_concept(stock_code)
            concept_dict[stock_code] = concept
        
        # 创建溢价矩阵（传入概念字典）
        print("正在创建溢价矩阵...")
        premium_df = analyzer.create_premium_matrix(board_df, concept_dict)
        
        if premium_df.empty:
            print("没有符合条件的连板股票！")
            return
        
        # 添加概念信息列
        premium_df = analyzer.add_concept_info(premium_df, concept_dict)
        
        # 添加连板数信息
        print("正在添加连板数信息...")
        premium_df = self._add_board_count_info(premium_df, board_df)
        
        # 保存结果
        output_file = os.path.join(self.output_dir, '连板溢价表.csv')
        premium_df.to_csv(output_file, index=False, encoding='utf-8-sig')
        print(f"连板溢价表已生成: {output_file}")
        
        return premium_df
    
    def _add_board_count_info(self, premium_df, board_df):
        """为溢价表添加连板数信息"""
        # 为每个股票添加最高连板数
        max_boards = board_df.groupby('股票代码')['连板数'].max().to_dict()
        premium_df.insert(3, '最高连板数', premium_df['股票代码'].map(max_boards))
        
        return premium_df
    
    def generate_market_overview_csv(self):
        """生成市场整体情况CSV（第二张图）"""
        print("=" * 50)
        print("生成市场整体情况表...")
        print("=" * 50)
        
        # 加载连板分析数据
        board_file = os.path.join(self.output_dir, 'board_analysis.csv')
        
        if not os.path.exists(board_file):
            print("请先生成连板溢价表！")
            return
        
        board_df = pd.read_csv(board_file, encoding='utf-8-sig')
        board_df['日期'] = pd.to_datetime(board_df['日期'])
        
        # 市场分析
        print("正在分析市场整体情况...")
        market_analyzer = MarketAnalyzer(board_df)
        
        # 获取日期范围
        start_date = board_df['日期'].min().strftime('%Y%m%d')
        end_date = board_df['日期'].max().strftime('%Y%m%d')
        
        # 创建市场概览
        market_overview = market_analyzer.create_market_overview(start_date, end_date)
        
        # 添加极值标记
        print("正在标记极值数据...")
        columns_to_mark = ['涨停数', '跌停数', '上涨率', '涨停率', '连板高度']
        market_overview = market_analyzer.add_extreme_value_markers(
            market_overview, 
            columns_to_mark
        )
        
        # 保存结果
        output_file = os.path.join(self.output_dir, '市场整体情况表.csv')
        market_overview.to_csv(output_file, index=False, encoding='utf-8-sig')
        print(f"市场整体情况表已生成: {output_file}")
        
        return market_overview
    
    def run_full_analysis(self):
        """运行完整分析流程"""
        print("\n" + "=" * 50)
        print("市场监控系统 - 完整分析")
        print("=" * 50 + "\n")
        
        # 生成连板溢价表（原版）
        self.generate_board_premium_csv()
        
        # 生成连板溢价表V2（新格式）
        self.generate_board_premium_csv_v2()
        
        # 生成市场整体情况表
        self.generate_market_overview_csv()
        
        print("\n" + "=" * 50)
        print("分析完成！")
        print("=" * 50)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='市场监控系统')
    parser.add_argument(
        '--mode',
        choices=['init', 'update', 'update-smart', 'analyze', 'full'],
        default='full',
        help='运行模式: init=初始化, update=全量更新, update-smart=智能更新, analyze=分析, full=完整流程'
    )
    
    args = parser.parse_args()
    
    monitor = MarketMonitor()
    
    if args.mode == 'init':
        monitor.initialize_data()
    elif args.mode == 'update':
        monitor.update_data()
    elif args.mode == 'update-smart':
        monitor.update_data_smart()
    elif args.mode == 'analyze':
        monitor.run_full_analysis()
    elif args.mode == 'full':
        # 检查是否已有数据
        if not os.path.exists(os.path.join(DATA_DIR, 'raw_stock_data.csv')):
            print("首次运行，开始初始化数据...")
            if monitor.initialize_data():
                monitor.run_full_analysis()
        else:
            print("数据已存在，开始智能更新并分析...")
            if monitor.update_data_smart():
                monitor.run_full_analysis()


if __name__ == "__main__":
    main()
