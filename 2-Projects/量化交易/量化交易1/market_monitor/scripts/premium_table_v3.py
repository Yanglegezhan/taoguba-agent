# -*- coding: utf-8 -*-
"""
连板溢价表V3 - 最终版本
前7行显示当日4板以上，不显示股票名称列
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os


class PremiumTableV3:
    """连板溢价表生成器V3"""
    
    def __init__(self, board_df, concept_dict=None, use_correlation=True):
        """
        初始化
        
        Args:
            board_df: 连板分析数据
            concept_dict: 股票代码到概念的映射字典（原始概念）
            use_correlation: 是否使用关联度计算（基于2板当天概念板块涨幅）
        """
        self.board_df = board_df.copy()
        self.concept_dict = concept_dict or {}
        self.use_correlation = use_correlation
        
        # 确保日期是datetime类型
        self.board_df['日期'] = pd.to_datetime(self.board_df['日期'])
        
        # 构建所有股票的概念列表字典（用于关联度计算）
        self.all_stock_concepts = {}
        for stock_code, concepts_str in self.concept_dict.items():
            if concepts_str:
                concepts = [c.strip() for c in concepts_str.split('+') if c.strip()]
                self.all_stock_concepts[stock_code] = concepts
    
    def get_concept_stocks(self, concept_name):
        """获取某个概念下的所有股票代码"""
        stocks = []
        for stock_code, concepts in self.all_stock_concepts.items():
            if concept_name in concepts:
                stocks.append(int(stock_code))  # 转换为int以匹配board_df
        return stocks
    
    def calculate_concept_performance(self, concept_name, date):
        """计算某个概念在指定日期的平均涨幅"""
        concept_stocks = self.get_concept_stocks(concept_name)
        if not concept_stocks:
            return 0.0
        
        # 获取当天这些股票的涨跌幅
        date_data = self.board_df[
            (self.board_df['日期'] == date) & 
            (self.board_df['股票代码'].isin(concept_stocks))
        ]
        
        if date_data.empty:
            return 0.0
        
        # 计算平均涨幅
        avg_pct = date_data['涨跌幅'].mean()
        return avg_pct * 100  # 转换为百分比
    
    def get_best_concepts(self, stock_code, date):
        """
        获取股票在指定日期最相关的概念（基于当天概念板块涨幅）
        
        Args:
            stock_code: 股票代码（字符串）
            date: 日期
        
        Returns:
            str: 最相关的概念（格式：概念1+概念2）
        """
        if not self.use_correlation:
            # 不使用关联度，直接返回原始概念
            return self.concept_dict.get(stock_code, '')
        
        # 获取该股票的所有概念
        stock_concepts = self.all_stock_concepts.get(stock_code, [])
        
        if not stock_concepts:
            return ''
        
        # 如果只有1-2个概念，直接返回
        if len(stock_concepts) <= 2:
            return '+'.join(stock_concepts)
        
        # 计算每个概念在当天的表现
        concept_performance = []
        for concept in stock_concepts:
            avg_pct = self.calculate_concept_performance(concept, date)
            concept_performance.append({
                'concept': concept,
                'avg_pct': avg_pct
            })
        
        # 按平均涨幅排序，取前2个
        concept_performance.sort(key=lambda x: x['avg_pct'], reverse=True)
        best_concepts = [item['concept'] for item in concept_performance[:2]]
        
        return '+'.join(best_concepts)
        
    def generate_table(self, end_date=None, days=20):
        """
        生成连板溢价表
        
        Args:
            end_date: 结束日期（默认为最新日期，格式：'2025-12-26'）
            days: 显示的交易日天数（默认20天）
        
        Returns:
            DataFrame: 连板溢价表
        """
        print(f"生成最近{days}个交易日的连板溢价表...")
        
        # 获取交易日列表
        if end_date is None:
            end_date = self.board_df['日期'].max()
        else:
            end_date = pd.to_datetime(end_date)
        
        print(f"结束日期: {end_date.date()}")
        
        # 获取最近N个交易日
        all_dates = sorted(self.board_df['日期'].unique())
        all_dates = [d for d in all_dates if d <= end_date]
        
        if len(all_dates) < days:
            print(f"警告：只有{len(all_dates)}个交易日，少于请求的{days}天")
            trading_dates = all_dates
        else:
            trading_dates = all_dates[-days:]
        
        print(f"日期范围: {trading_dates[0].date()} 至 {trading_dates[-1].date()}")
        
        # 获取窗口开始日期之前的日期（用于判断是否在窗口内首次2板）
        window_start_date = trading_dates[0]
        dates_before_window = [d for d in all_dates if d < window_start_date]
        prev_window_date = dates_before_window[-1] if dates_before_window else None
        
        print(f"窗口开始前一日: {prev_window_date.date() if prev_window_date else '无'}")
        
        # 获取窗口开始前一日所有2板及以上的股票（这些股票不应该被追踪）
        stocks_before_window = set()
        if prev_window_date:
            prev_data = self.board_df[
                (self.board_df['日期'] == prev_window_date) & 
                (self.board_df['连板数'] >= 2)
            ]
            stocks_before_window = set(prev_data['股票代码'].unique())
            print(f"窗口开始前已有{len(stocks_before_window)}只股票在连板中（将被排除）")
        
        # 构建表格数据
        table_data = {date: [] for date in trading_dates}
        concept_col = []  # 第2列：概念
        stock_names_col = []  # 第3列：股票名称（仅第一个交易日的股票）
        stock_tracking = {}  # {stock_code: {'row': row_idx, 'last_board': board_count, 'had_zero': False}}
        next_row = 7  # 从第8行开始（索引7），前7行是当日4板以上
        first_date = trading_dates[0]  # 第一个交易日
        
        # 初始化前7行的概念列和股票名称列
        for i in range(7):
            concept_col.append('')
            stock_names_col.append('')
        
        for i, date in enumerate(trading_dates):
            print(f"处理 {date.date()} ({i+1}/{len(trading_dates)})...")
            
            # 前一日
            prev_date = trading_dates[i-1] if i > 0 else None
            
            # 1. 前7行：显示当日4板以上的个股
            high_boards = []
            today_high = self.board_df[
                (self.board_df['日期'] == date) & 
                (self.board_df['连板数'] >= 4)
            ].sort_values('连板数', ascending=False)
            
            for idx, row in today_high.head(7).iterrows():
                stock_name = row['股票名称']
                board_count = int(row['连板数'])
                stock_code = row['股票代码']
                
                # 确保股票代码是字符串并补齐到6位
                stock_code_str = str(stock_code).zfill(6)
                concept = self.concept_dict.get(stock_code_str, '')
                
                # 格式：股票名字 连板高度 题材
                cell_value = f"{stock_name} {board_count}板"
                if concept:
                    cell_value += f" {concept}"
                
                high_boards.append(cell_value)
            
            # 补齐到7行
            while len(high_boards) < 7:
                high_boards.append('')
            
            table_data[date] = high_boards.copy()
            
            # 2. 获取当日所有股票数据
            today_data = self.board_df[self.board_df['日期'] == date]
            
            # 3. 处理已追踪的股票（即使断板也继续追踪，包括重新连板）
            stocks_to_add_new_row = []  # 记录需要在新行添加的股票（断板后重新2板的）
            
            for tracking_key, info in list(stock_tracking.items()):
                row_idx = info['row']
                last_board = info['last_board']
                had_zero = info.get('had_zero', False)  # 是否曾经连板数为0
                
                # 获取实际的股票代码（可能是原始代码或带后缀的）
                stock_code = info.get('original_code', tracking_key)
                
                # 确保当前列有足够的行
                while len(table_data[date]) <= row_idx:
                    table_data[date].append('')
                
                # 查找该股票今天的数据
                stock_today = today_data[today_data['股票代码'] == stock_code]
                
                if not stock_today.empty:
                    row_data = stock_today.iloc[0]
                    board_count = int(row_data['连板数'])
                    pct_change = row_data['涨跌幅']
                    is_limit_up = row_data['是否涨停']
                    
                    # 检查是否断板后重新2板（仅对原始追踪记录检查，不对rebound记录检查）
                    is_rebound_key = isinstance(tracking_key, str) and '_rebound_' in tracking_key
                    # 如果当前是2板以上，且之前曾经低于2板（had_zero=True），则认为是重新连板
                    if board_count >= 2 and had_zero and not is_rebound_key:
                        # 断板后重新2板，需要在新行添加，但原行继续显示
                        stocks_to_add_new_row.append({
                            'stock_code': stock_code,
                            'stock_name': row_data['股票名称'],
                            'board_count': board_count,
                            'date': date
                        })
                        # 重置had_zero标记，避免重复添加
                        stock_tracking[tracking_key]['had_zero'] = False
                    
                    # 原行继续显示数据（不管是否重新连板）
                    if board_count >= 2:
                        # 显示连板数
                        # 检查是否炸板（涨停但连板数没增加）
                        if is_limit_up and board_count == last_board:
                            table_data[date][row_idx] = f"{board_count}板(炸)"
                        else:
                            table_data[date][row_idx] = f"{board_count}板"
                        
                        # 更新最后连板数
                        stock_tracking[tracking_key]['last_board'] = board_count
                    elif board_count == 1:
                        # 1板（可能是炸板后的）
                        table_data[date][row_idx] = "1板"
                        stock_tracking[tracking_key]['last_board'] = 1
                        # 标记曾经低于2板
                        stock_tracking[tracking_key]['had_zero'] = True
                    else:
                        # 显示涨跌幅（即使断板也继续显示）
                        if pct_change >= 0:
                            table_data[date][row_idx] = f"+{pct_change*100:.2f}%"
                        else:
                            table_data[date][row_idx] = f"{pct_change*100:.2f}%"
                        
                        # 更新连板数为0，并标记曾经为0
                        stock_tracking[tracking_key]['last_board'] = 0
                        stock_tracking[tracking_key]['had_zero'] = True
                else:
                    # 今天没有数据（停牌等）
                    table_data[date][row_idx] = '-'
            
            
            # 4. 添加今日新出现的2板股票（首次出现）
            # 获取所有正在追踪的原始股票代码
            tracked_codes = set()
            for key, info in stock_tracking.items():
                tracked_codes.add(info.get('original_code', key))
            
            today_new_boards = today_data[
                (today_data['连板数'] >= 2) & 
                (~today_data['股票代码'].isin(tracked_codes)) &
                (~today_data['股票代码'].isin(stocks_before_window))  # 排除窗口开始前已在连板的股票
            ].sort_values('连板数', ascending=False)
            
            for idx, row in today_new_boards.iterrows():
                stock_code = row['股票代码']
                stock_name = row['股票名称']
                board_count = int(row['连板数'])
                
                # 确保stock_code是字符串并补齐到6位
                stock_code_str = str(stock_code).zfill(6)
                
                # 获取最相关的概念（基于当天概念板块涨幅）
                concept = self.get_best_concepts(stock_code_str, date)
                
                # 分配新行号
                row_idx = next_row
                next_row += 1
                
                # 添加概念到第2列
                concept_col.append(concept if concept else '')
                
                # 添加股票名称到第3列（仅第一个交易日的股票）
                if date == first_date:
                    stock_names_col.append(stock_name)
                else:
                    stock_names_col.append('')
                
                # 获取前前日（用于显示概念）
                prev_prev_date = None
                if i >= 2:
                    prev_prev_date = trading_dates[i-2]
                
                # 在前前日列显示概念（题材）
                if prev_prev_date:
                    while len(table_data[prev_prev_date]) <= row_idx:
                        table_data[prev_prev_date].append('')
                    
                    # 显示概念
                    table_data[prev_prev_date][row_idx] = concept if concept else ''
                
                # 在前一日列显示股票名
                if prev_date:
                    while len(table_data[prev_date]) <= row_idx:
                        table_data[prev_date].append('')
                    
                    # 显示股票名
                    table_data[prev_date][row_idx] = stock_name
                
                # 在当日列显示连板数
                while len(table_data[date]) <= row_idx:
                    table_data[date].append('')
                
                table_data[date][row_idx] = f"{board_count}板"
                
                # 添加到追踪列表
                stock_tracking[stock_code] = {
                    'row': row_idx,
                    'last_board': board_count,
                    'had_zero': False  # 初始化为False
                }
            
            # 5. 为断板后重新2板的股票添加新行
            for stock_info in stocks_to_add_new_row:
                stock_code = stock_info['stock_code']
                stock_name = stock_info['stock_name']
                board_count = stock_info['board_count']
                
                # 确保stock_code是字符串并补齐到6位
                stock_code_str = str(stock_code).zfill(6)
                
                # 获取最相关的概念（基于当天概念板块涨幅）
                concept = self.get_best_concepts(stock_code_str, date)
                
                # 分配新行号
                row_idx = next_row
                next_row += 1
                
                # 添加概念到第2列
                concept_col.append(concept if concept else '')
                
                # 第3列为空（不是第一个交易日的股票）
                stock_names_col.append('')
                
                # 获取前前日（用于显示概念）
                prev_prev_date = None
                if i >= 2:
                    prev_prev_date = trading_dates[i-2]
                
                # 在前前日列显示概念（题材）
                if prev_prev_date:
                    while len(table_data[prev_prev_date]) <= row_idx:
                        table_data[prev_prev_date].append('')
                    
                    # 显示概念
                    table_data[prev_prev_date][row_idx] = concept if concept else ''
                
                # 在前一日列显示股票名
                if prev_date:
                    while len(table_data[prev_date]) <= row_idx:
                        table_data[prev_date].append('')
                    
                    # 显示股票名
                    table_data[prev_date][row_idx] = stock_name
                
                # 在当日列显示连板数
                while len(table_data[date]) <= row_idx:
                    table_data[date].append('')
                
                table_data[date][row_idx] = f"{board_count}板"
                
                # 添加到追踪列表（作为新的追踪对象）
                # 注意：这里不能用原来的stock_code作为key，因为会覆盖原有的追踪
                # 我们需要为同一股票的不同周期创建不同的追踪记录
                # 使用 stock_code + 日期 作为唯一标识
                tracking_key = f"{stock_code}_rebound_{date.strftime('%Y%m%d')}"
                stock_tracking[tracking_key] = {
                    'row': row_idx,
                    'last_board': board_count,
                    'had_zero': False,
                    'original_code': stock_code  # 保存原始代码用于查询数据
                }
        
        # 转换为DataFrame
        print("构建DataFrame...")
        
        # 找出最大行数
        max_rows = max(len(col) for col in table_data.values())
        
        # 补齐所有列到相同行数
        for date in table_data:
            while len(table_data[date]) < max_rows:
                table_data[date].append('')
        
        # 补齐概念列和股票名称列
        while len(concept_col) < max_rows:
            concept_col.append('')
        while len(stock_names_col) < max_rows:
            stock_names_col.append('')
        
        # 创建DataFrame
        df = pd.DataFrame(table_data)
        
        # 格式化列名（日期）
        df.columns = [d.strftime('%Y-%m-%d') for d in df.columns]
        
        # 添加第一列：序号
        row_numbers = list(range(1, max_rows + 1))
        df.insert(0, '序号', row_numbers)
        
        # 添加第二列：概念
        df.insert(1, '概念', concept_col)
        
        # 添加第三列：股票名称
        df.insert(2, '股票名称', stock_names_col)
        
        print(f"表格生成完成！形状: {df.shape}")
        print(f"第1列：序号")
        print(f"第2列：概念")
        print(f"第3列：股票名称")
        print(f"第4列起：日期数据")
        print(f"前7行：当日4板以上个股")
        print(f"第8行起：2板以上个股追踪")
        
        return df


def main(auto_mode=False):
    """主函数
    
    Args:
        auto_mode: 自动模式，不询问日期，直接使用最新日期
    """
    print("=" * 60)
    print("生成连板溢价表V3")
    print("=" * 60)
    
    # 1. 加载数据
    print("\n1. 加载连板分析数据...")
    board_df = pd.read_csv('output/board_analysis.csv', encoding='utf-8-sig')
    print(f"数据形状: {board_df.shape}")
    
    # 显示数据日期范围
    board_df['日期'] = pd.to_datetime(board_df['日期'])
    latest_date = board_df['日期'].max()
    earliest_date = board_df['日期'].min()
    print(f"数据日期范围: {earliest_date.date()} 至 {latest_date.date()}")
    
    # 2. 加载或获取概念信息
    print("\n2. 获取概念信息...")
    concept_dict = {}
    
    # 首先加载手动维护的概念
    try:
        from manual_concepts import get_all_concepts
        manual_concepts = get_all_concepts()
        concept_dict.update(manual_concepts)
        print(f"  已加载 {len(manual_concepts)} 只股票的手动概念")
    except:
        print("  未找到手动概念文件")
    
    # 检查是否有缓存的概念数据
    concept_cache_file = 'output/concept_cache.csv'
    if os.path.exists(concept_cache_file):
        print("  从缓存加载概念信息...")
        try:
            # 指定股票代码列为字符串类型
            concept_cache = pd.read_csv(concept_cache_file, encoding='utf-8-sig', dtype={'股票代码': str})
            # 确保股票代码是6位字符串
            concept_cache['股票代码'] = concept_cache['股票代码'].str.zfill(6)
            cached_concepts = dict(zip(concept_cache['股票代码'], concept_cache['概念']))
            # 手动概念优先级更高，不覆盖
            for code, concept in cached_concepts.items():
                if code not in concept_dict:
                    concept_dict[code] = concept
            print(f"  已加载 {len(cached_concepts)} 只股票的缓存概念")
        except Exception as e:
            print(f"  缓存加载失败: {e}")
    
    # 如果概念数量不足，提示用户运行专门的脚本
    stocks_with_boards = board_df[board_df['连板数'] >= 2]['股票代码'].unique()
    stocks_need_concept = [str(code).zfill(6) for code in stocks_with_boards 
                          if str(code).zfill(6) not in concept_dict]
    
    if stocks_need_concept:
        print(f"  还有 {len(stocks_need_concept)} 只股票没有概念信息")
        print("  提示：运行 python fetch_concepts.py 批量获取概念（需要10-20分钟）")
        print("  或者编辑 manual_concepts.py 手动添加重要股票的概念")
    
    print(f"  总计: {len(concept_dict)} 只股票有概念信息")
    
    # 3. 询问用户指定日期（除非是自动模式）
    end_date = None
    if not auto_mode:
        print("\n" + "=" * 60)
        print("请输入结束日期（格式：YYYY-MM-DD）")
        print(f"直接回车使用最新日期: {latest_date.date()}")
        print("=" * 60)
        
        user_input = input("结束日期: ").strip()
        
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
    else:
        print(f"\n自动模式：使用最新日期 {latest_date.date()}")
    
    # 4. 生成表格
    print("\n3. 生成连板溢价表...")
    print("  使用关联度计算: 是（基于2板当天概念板块涨幅）")
    generator = PremiumTableV3(board_df, concept_dict, use_correlation=True)
    
    # 生成表格（使用用户指定的日期或最新日期）
    premium_table = generator.generate_table(end_date=end_date, days=20)
    
    # 4. 保存
    output_file = 'output/连板溢价表_最终版.csv'
    premium_table.to_csv(output_file, index=False, encoding='utf-8-sig')
    print(f"\n已保存到: {output_file}")
    
    # 5. 显示预览
    print("\n表格预览（前10行，前6列）:")
    print(premium_table.iloc[:10, :6])
    
    print("\n" + "=" * 60)
    print("完成！")
    print("=" * 60)
    
    print("\n说明：")
    print("- 第1列：序号")
    print("- 第2列：概念（格式：概念1+概念2）")
    print("- 第3列：股票名称（仅第一个交易日的股票）")
    print("- 前7行：显示当日4板以上的个股")
    print("- 第8行起：按首次出现2板的顺序排列")
    print("- 前一日列显示：概念（题材）")
    print("- 当日列显示：股票名")
    print("- 次日起显示：连板数/涨跌幅（即使断板也继续追踪）")
    print("- 断板后重新2板会在新行显示，原行继续显示完整数据")
    print("\n获取概念信息：")
    print("  方法1：运行 python fetch_concepts.py（需要10-20分钟）")
    print("  方法2：编辑 manual_concepts.py 手动添加")
    print("  详见：如何获取概念.md")
    print("\n指定日期示例：")
    print("  generator.generate_table(end_date='2025-12-20', days=20)")


if __name__ == "__main__":
    main()
