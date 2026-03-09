# -*- coding: utf-8 -*-
"""
开盘啦数据源

封装kaipanla_crawler接口，提供统一的数据获取方法
"""

import sys
import os
import logging
import time
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

# 添加kaipanla_crawler到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../../kaipanla_crawler'))

try:
    from kaipanla_crawler import KaipanlaCrawler
except ImportError:
    raise ImportError("无法导入kaipanla_crawler，请确保kaipanla_crawler目录存在")

from ..models import IntradayData, LimitUpData, TurnoverData


logger = logging.getLogger(__name__)


class KaipanlaDataSource:
    """开盘啦数据源"""
    
    def __init__(self, max_retries: int = 3, retry_delay: float = 1.0):
        """初始化数据源
        
        Args:
            max_retries: 最大重试次数
            retry_delay: 重试延迟（秒）
        """
        self.crawler = KaipanlaCrawler()
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        logger.info("KaipanlaDataSource initialized")
    
    def _retry_request(self, func, *args, **kwargs) -> Any:
        """带重试的请求包装器
        
        Args:
            func: 要执行的函数
            *args: 位置参数
            **kwargs: 关键字参数
            
        Returns:
            函数执行结果
            
        Raises:
            Exception: 重试次数用尽后抛出最后一次异常
        """
        last_exception = None
        
        for attempt in range(self.max_retries):
            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                last_exception = e
                logger.warning(
                    f"请求失败 (尝试 {attempt + 1}/{self.max_retries}): {e}"
                )
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay * (attempt + 1))  # 指数退避
        
        logger.error(f"请求失败，已达最大重试次数: {last_exception}")
        raise last_exception
    
    def get_sector_strength_ndays(
        self,
        end_date: str,
        num_days: int = 7
    ) -> pd.DataFrame:
        """获取N日板块强度数据
        
        Args:
            end_date: 结束日期，格式 'YYYY-MM-DD'
            num_days: 查询天数，默认7天
            
        Returns:
            DataFrame包含：
            - 日期: 交易日期
            - 板块代码: 板块代码
            - 板块名称: 板块名称
            - 涨停数: 该板块涨停股票数量
            - 涨停股票: 涨停股票列表
            
        Raises:
            Exception: API调用失败
        """
        logger.info(f"获取板块强度数据: end_date={end_date}, num_days={num_days}")
        
        try:
            result = self._retry_request(
                self.crawler.get_sector_strength_ndays,
                end_date=end_date,
                num_days=num_days
            )
            
            if result is None or (isinstance(result, pd.DataFrame) and result.empty):
                logger.warning(f"板块强度数据为空: {end_date}")
                return pd.DataFrame()
            
            logger.info(f"成功获取板块强度数据: {len(result)} 条记录")
            return result
            
        except Exception as e:
            logger.error(f"获取板块强度数据失败: {e}")
            raise
    
    def get_sector_kline_ndays(
        self,
        sector_code: str,
        end_date: str,
        num_days: int = 14
    ) -> Dict[str, Any]:
        """获取板块N日K线数据
        
        通过循环调用get_sector_intraday获取每日的开高低收数据，
        并计算真实的涨跌幅（相对于前一天收盘价）
        
        Args:
            sector_code: 板块代码，如 "803023"
            end_date: 结束日期，格式 'YYYY-MM-DD'
            num_days: 查询天数，默认14天
            
        Returns:
            字典包含：
            - sector_code: 板块代码
            - start_date: 开始日期
            - end_date: 结束日期
            - kline_data: K线数据列表，每个元素包含：
                - date: 日期
                - open: 开盘价
                - high: 最高价
                - low: 最低价
                - close: 收盘价
                - change_pct: 涨跌幅（%，相对于前一天收盘价）
                - turnover: 成交额（元）
                
        Raises:
            Exception: API调用失败
        """
        logger.info(f"获取板块K线数据: sector_code={sector_code}, end_date={end_date}, num_days={num_days}")
        
        from datetime import datetime, timedelta
        
        try:
            # 计算开始日期（向前推num_days*2天，考虑周末和节假日）
            end_dt = datetime.strptime(end_date, '%Y-%m-%d')
            start_dt = end_dt - timedelta(days=num_days * 2)
            
            kline_data = []
            current_dt = start_dt
            prev_close = None
            
            # 循环获取每一天的数据，直到end_date
            while current_dt <= end_dt:
                date_str = current_dt.strftime('%Y-%m-%d')
                
                # 跳过周末
                if current_dt.weekday() >= 5:  # 5=周六, 6=周日
                    current_dt += timedelta(days=1)
                    continue
                
                try:
                    # 获取分时数据（包含开高低收）
                    result = self._retry_request(
                        self.crawler.get_sector_intraday,
                        sector_code=sector_code,
                        date=date_str if date_str != end_date else None  # 当日使用实时接口
                    )
                    
                    if result and 'data' in result:
                        data_df = result['data']
                        if not data_df.empty:
                            # 提取K线数据
                            open_price = float(result.get('open', 0))
                            high_price = float(result.get('high', 0))
                            low_price = float(result.get('low', 0))
                            close_price = float(result.get('close', 0))
                            
                            # 计算涨跌幅（相对于前一天收盘价）
                            if prev_close and prev_close > 0:
                                change_pct = (close_price - prev_close) / prev_close * 100
                            else:
                                # 第一天，相对于昨收价
                                preclose = float(result.get('preclose', 0))
                                if preclose > 0:
                                    change_pct = (close_price - preclose) / preclose * 100
                                else:
                                    change_pct = 0.0
                            
                            # 获取成交额（从get_sector_capital_data）
                            try:
                                capital_data = self._retry_request(
                                    self.crawler.get_sector_capital_data,
                                    sector_code=sector_code,
                                    date=date_str if date_str != end_date else None
                                )
                                turnover = float(capital_data.get('turnover', 0)) if capital_data else 0
                            except:
                                turnover = 0
                            
                            kline_data.append({
                                'date': date_str,
                                'open': open_price,
                                'high': high_price,
                                'low': low_price,
                                'close': close_price,
                                'change_pct': change_pct,
                                'turnover': turnover
                            })
                            
                            # 更新前一天收盘价
                            prev_close = close_price
                            
                            logger.debug(f"获取到 {date_str} 数据: 收盘价={close_price:.2f}, 涨跌幅={change_pct:.2f}%")
                        else:
                            logger.debug(f"{date_str} 分时数据为空")
                    else:
                        logger.debug(f"{date_str} 无数据")
                    
                except Exception as e:
                    logger.warning(f"获取 {date_str} 数据失败: {e}")
                
                current_dt += timedelta(days=1)
            
            # 按日期排序
            kline_data.sort(key=lambda x: x['date'])
            
            # 只保留最近num_days天的数据
            kline_data = kline_data[-num_days:]
            
            logger.info(f"成功获取板块K线数据: {len(kline_data)} 天")
            
            return {
                'sector_code': sector_code,
                'start_date': kline_data[0]['date'] if kline_data else '',
                'end_date': kline_data[-1]['date'] if kline_data else '',
                'kline_data': kline_data
            }
            
        except Exception as e:
            logger.error(f"获取板块K线数据失败: {e}")
            return {
                'sector_code': sector_code,
                'start_date': '',
                'end_date': '',
                'kline_data': []
            }
    
    def get_intraday_data(
        self,
        target: str,
        date: str
    ) -> IntradayData:
        """获取大盘或板块的分时数据
        
        Args:
            target: 目标代码（如 'SH000001' 为上证指数，或板块代码）
            date: 日期字符串，格式 'YYYY-MM-DD'
            
        Returns:
            分时数据，包含：
            - timestamps: 时间戳列表（分钟级）
            - prices: 价格列表
            - pct_changes: 涨跌幅列表
            
        Note:
            如果分时数据获取失败，返回空数据而不抛出异常
        """
        logger.info(f"获取分时数据: target={target}, date={date}")
        
        try:
            # 判断是否为当日（实时数据）
            from datetime import datetime
            today = datetime.now().strftime('%Y-%m-%d')
            is_today = (date == today)
            
            # 如果是当日，使用实时接口（不传date参数）
            api_date = None if is_today else date
            
            # 判断是大盘指数还是板块/个股
            if target.startswith('SH') or target.startswith('SZ'):
                # 判断是否为指数（SH000001, SZ399001等）
                is_index = (target.startswith('SH') and '000' in target) or (target.startswith('SZ') and '399' in target)
                
                if is_index:
                    # 大盘指数使用get_index_intraday
                    result = self._retry_request(
                        self.crawler.get_index_intraday,
                        index_code=target,
                        date=api_date
                    )
                else:
                    # 个股使用get_stock_intraday
                    result = self._retry_request(
                        self.crawler.get_stock_intraday,
                        stock_code=target,
                        date=api_date
                    )
            else:
                # 板块
                result = self._retry_request(
                    self.crawler.get_sector_intraday,
                    sector_code=target,
                    date=api_date
                )
            
            # 检查结果
            if not result:
                logger.warning(f"分时数据为空: {target}, {date}")
                return IntradayData(
                    target=target,
                    date=date,
                    timestamps=[],
                    prices=[],
                    pct_changes=[]
                )
            
            # 保存preclose信息（在转换成DataFrame之前）
            preclose = None
            if isinstance(result, dict):
                preclose = result.get('preclose', 0)
            
            # 处理字典格式的结果
            if isinstance(result, dict):
                data_df = result.get('data', pd.DataFrame())
                if data_df.empty:
                    logger.warning(f"分时数据DataFrame为空: {target}, {date}")
                    return IntradayData(
                        target=target,
                        date=date,
                        timestamps=[],
                        prices=[],
                        pct_changes=[]
                    )
                
                # 如果preclose等于开盘价，说明API返回的preclose不准确
                # 尝试使用get_sector_capital_data获取正确的涨跌幅
                if preclose > 0 and not data_df.empty and 'price' in data_df.columns:
                    first_price = float(data_df['price'].iloc[0])
                    
                    # 如果preclose等于开盘价，说明不准确（误差小于0.01）
                    if abs(preclose - first_price) < 0.01:
                        logger.debug(f"检测到preclose({preclose})等于开盘价，尝试获取正确的昨收价")
                        try:
                            # 使用get_sector_capital_data获取涨跌幅
                            capital_data = self._retry_request(
                                self.crawler.get_sector_capital_data,
                                sector_code=target,
                                date=api_date
                            )
                            if capital_data and 'change_pct' in capital_data:
                                change_pct = float(capital_data['change_pct'])
                                if abs(change_pct) > 0.01:  # 涨跌幅不为0
                                    # 根据涨跌幅反推昨收价
                                    last_price = float(data_df['price'].iloc[-1])
                                    preclose = last_price / (1 + change_pct / 100)
                                    logger.info(f"使用涨跌幅{change_pct}%反推昨收价: {preclose:.2f}")
                        except Exception as e:
                            logger.warning(f"获取涨跌幅失败: {e}")
                
                result = data_df
            
            # 处理DataFrame格式的结果
            if hasattr(result, 'empty') and result.empty:
                logger.warning(f"分时数据DataFrame为空: {target}, {date}")
                return IntradayData(
                    target=target,
                    date=date,
                    timestamps=[],
                    prices=[],
                    pct_changes=[]
                )
            
            # 解析数据
            timestamps = []
            prices = []
            pct_changes = []
            
            # 根据返回的DataFrame结构解析
            if hasattr(result, 'columns') and 'time' in result.columns:
                for _, row in result.iterrows():
                    try:
                        # 解析时间
                        time_str = row['time']
                        dt = datetime.strptime(f"{date} {time_str}", "%Y-%m-%d %H:%M")
                        timestamps.append(dt)
                        
                        # 价格
                        price = float(row.get('price', 0))
                        prices.append(price)
                        
                        # 涨跌幅：优先使用API返回的pct_change，否则自己计算
                        if 'pct_change' in row and pd.notna(row['pct_change']):
                            pct_change = float(row['pct_change'])
                        elif preclose and preclose > 0:
                            # 根据价格和昨收价计算涨跌幅
                            pct_change = (price - preclose) / preclose * 100.0
                        else:
                            pct_change = 0.0
                        
                        pct_changes.append(pct_change)
                    except Exception as parse_error:
                        logger.warning(f"解析分时数据行失败: {parse_error}")
                        continue
            
            logger.info(f"成功获取分时数据: {len(timestamps)} 个数据点")
            
            return IntradayData(
                target=target,
                date=date,
                timestamps=timestamps,
                prices=prices,
                pct_changes=pct_changes
            )
            
        except Exception as e:
            logger.warning(f"获取分时数据失败，返回空数据: {e}")
            # 返回空数据而不是抛出异常
            return IntradayData(
                target=target,
                date=date,
                timestamps=[],
                prices=[],
                pct_changes=[]
            )
    
    def get_limit_up_data(self, date: str) -> LimitUpData:
        """获取涨停相关数据
        
        Args:
            date: 日期字符串，格式 'YYYY-MM-DD'
            
        Returns:
            涨停数据，包含：
            - limit_up_count: 全市场涨停家数
            - limit_down_count: 全市场跌停家数
            - blown_limit_up_rate: 全市场炸板率（%）
            - consecutive_boards: 连板数据（按板块分组）
            - yesterday_limit_up_performance: 昨日涨停今日表现（%）
            
        Raises:
            Exception: API调用失败
        """
        logger.info(f"获取涨停数据: date={date}")
        
        try:
            # 使用板块排名API获取详细的涨停数据
            sector_ranking = self._retry_request(
                self.crawler.get_sector_ranking,
                date=date
            )
            
            if not sector_ranking or 'sectors' not in sector_ranking:
                logger.warning(f"获取板块排名数据失败: {date}")
                return self._create_empty_limit_up_data()
            
            sectors = sector_ranking['sectors']
            summary = sector_ranking.get('summary', {})
            
            # 统计涨停数据
            total_limit_up = 0
            consecutive_boards = {}
            all_stocks = []
            
            for sector in sectors:
                stocks = sector.get('stocks', [])
                for stock in stocks:
                    # 清洗连板天数数据
                    raw_consecutive = stock.get('连板天数', '')
                    clean_consecutive_str = self._clean_consecutive_days(raw_consecutive)
                    clean_consecutive_num = self._get_consecutive_board_number(raw_consecutive)
                    
                    if clean_consecutive_num > 0:
                        total_limit_up += 1
                        consecutive_boards[clean_consecutive_num] = consecutive_boards.get(clean_consecutive_num, 0) + 1
                        
                        all_stocks.append({
                            'code': stock.get('股票代码', ''),
                            'name': stock.get('股票名称', ''),
                            'consecutive_days': clean_consecutive_num,
                            'consecutive_desc': clean_consecutive_str,  # 添加完整描述
                            'sector': sector.get('sector_name', ''),
                            'limit_price': stock.get('涨停价', 0)
                        })
            
            # 获取连板梯队数据作为补充
            try:
                consecutive_data = self._retry_request(
                    self.crawler.get_consecutive_limit_up,
                    date=date
                )
                if consecutive_data and 'ladder' in consecutive_data:
                    # 使用连板梯队数据补充统计
                    ladder_boards = {}
                    for board_level, stocks in consecutive_data['ladder'].items():
                        ladder_boards[board_level] = len(stocks)
                    
                    # 如果连板梯队数据更完整，使用它
                    if sum(ladder_boards.values()) > sum(consecutive_boards.values()):
                        consecutive_boards = ladder_boards
            except Exception as e:
                logger.warning(f"获取连板梯队数据失败: {e}")
            
            # 获取炸板率和昨日涨停今日表现
            blown_limit_up_rate = 0.0
            yesterday_performance = 0.0
            
            try:
                # 使用get_limit_up_ladder获取连板梯队数据（包含昨日涨停今表现）
                ladder_df = self._retry_request(
                    self.crawler.get_limit_up_ladder,
                    date=date
                )
                
                if ladder_df is not None and not ladder_df.empty:
                    # 提取昨日涨停今表现
                    yesterday_performance = float(ladder_df['昨日涨停今表现(%)'].iloc[0])
                    
                    # 提取今日涨停破板率作为炸板率
                    blown_limit_up_rate = float(ladder_df['今日涨停破板率(%)'].iloc[0])
                    
                    logger.info(f"获取到炸板率: {blown_limit_up_rate:.2f}%, 昨日涨停今表现: {yesterday_performance:+.2f}%")
                else:
                    logger.warning(f"连板梯队数据为空: {date}")
                    
            except Exception as e:
                logger.warning(f"获取炸板率和昨日涨停今表现失败: {e}")
                blown_limit_up_rate = 0.0
                yesterday_performance = 0.0
            
            logger.info(
                f"成功获取涨停数据: 涨停{total_limit_up}只, "
                f"连板分布{consecutive_boards}"
            )
            
            return LimitUpData(
                limit_up_count=total_limit_up,
                limit_down_count=summary.get('跌停数', 0),
                blown_limit_up_rate=blown_limit_up_rate,
                consecutive_boards=consecutive_boards,
                yesterday_limit_up_performance=yesterday_performance
            )
            
        except Exception as e:
            logger.error(f"获取涨停数据失败: {e}")
            return self._create_empty_limit_up_data()
    
    def _clean_consecutive_days(self, consecutive_str):
        """清洗连板天数数据，返回标准化的字符串描述
        
        Args:
            consecutive_str: 原始连板天数字符串
            
        Returns:
            str: 标准化的连板描述（如"首板"、"2连板"、"8天5板"）
        """
        import re
        
        if not consecutive_str:
            return "未知"
        
        consecutive_str = str(consecutive_str).strip()
        
        # 处理各种格式
        if '首板' in consecutive_str:
            return "首板"
        elif '连板' in consecutive_str:
            # 提取 "X连板" 中的X
            match = re.search(r'(\d+)连板', consecutive_str)
            if match:
                return f"{match.group(1)}连板"
        elif '板' in consecutive_str and '天' in consecutive_str:
            # 处理 "8天5板" 这种格式，完整保留
            match = re.search(r'(\d+)天(\d+)板', consecutive_str)
            if match:
                days = match.group(1)
                boards = match.group(2)
                return f"{days}天{boards}板"
            # 处理 "X天" 格式（可能是X天X板的简写）
            match = re.search(r'(\d+)天', consecutive_str)
            if match:
                return f"{match.group(1)}天"
        
        # 尝试直接提取数字
        match = re.search(r'(\d+)', consecutive_str)
        if match:
            num = int(match.group(1))
            if num == 1:
                return "首板"
            else:
                return f"{num}连板"
        
        return consecutive_str  # 无法识别时返回原始字符串
    
    def _get_consecutive_board_number(self, consecutive_str):
        """从连板描述中提取板数（用于排序和统计）

        Args:
            consecutive_str: 连板描述字符串（如"首板"、"2连板"、"8天5板"）

        Returns:
            int: 板数，反包板返回 -1
        """
        import re

        if not consecutive_str:
            return 0

        consecutive_str = str(consecutive_str)

        # 处理各种格式
        if '首板' in consecutive_str:
            return 1
        elif '连板' in consecutive_str:
            # 提取 "X连板" 中的X
            match = re.search(r'(\d+)连板', consecutive_str)
            if match:
                return int(match.group(1))
        elif '板' in consecutive_str and '天' in consecutive_str:
            # 处理 "8天5板" 这种格式
            match = re.search(r'(\d+)天(\d+)板', consecutive_str)
            if match:
                days = int(match.group(1))
                boards = int(match.group(2))
                # 检查是否为反包板：天数 > 板数（非连续涨停）
                if days > boards:
                    return -1  # 使用-1作为反包板的特殊标记
                return boards
            # 处理 "X天" 格式
            match = re.search(r'(\d+)天', consecutive_str)
            if match:
                return int(match.group(1))

        # 尝试直接提取数字
        match = re.search(r'(\d+)', consecutive_str)
        if match:
            return int(match.group(1))

        return 0

    def _normalize_stock_code(self, stock_code):
        """标准化股票代码为6位字符串（避免前导0丢失）"""
        if stock_code is None:
            return ""
        code = str(stock_code).strip()
        if not code:
            return ""
        if code.isdigit() and len(code) < 6:
            return code.zfill(6)
        return code

    def _to_number(self, value, default: float = 0.0) -> float:
        """将可能带单位的数值转为float。

        支持：
        - 纯数字/int/float
        - 字符串数字（含逗号）
        - 带单位：万、亿
        - 百分号（去掉%）
        """
        if value is None:
            return default
        if isinstance(value, (int, float)):
            return float(value)

        s = str(value).strip()
        if not s:
            return default

        # 常见无效值
        if s in {"-", "--", "None", "null", "NULL"}:
            return default

        multiplier = 1.0
        if s.endswith("%"):
            s = s[:-1]

        # 单位处理
        if s.endswith("亿"):
            multiplier = 100000000.0
            s = s[:-1]
        elif s.endswith("万"):
            multiplier = 10000.0
            s = s[:-1]

        # 去掉千分位
        s = s.replace(",", "")

        try:
            return float(s) * multiplier
        except Exception:
            return default
    
    def _create_empty_limit_up_data(self) -> LimitUpData:
        """创建空的涨停数据"""
        return LimitUpData(
            limit_up_count=0,
            limit_down_count=0,
            blown_limit_up_rate=0.0,
            consecutive_boards={},
            yesterday_limit_up_performance=0.0
        )
    
    def get_sector_turnover_data(
        self,
        sector_code: str,
        date: str
    ) -> TurnoverData:
        """获取板块成交额和个股数据
        
        Args:
            sector_code: 板块代码（如"803023"）
            date: 日期字符串，格式 'YYYY-MM-DD'
            
        Returns:
            成交额数据，包含：
            - sector_turnover: 板块总成交额（亿元）
            - top5_stocks: Top5个股及其成交额（该接口不返回个股数据）
            - stock_market_caps: 个股流通市值（该接口不返回个股数据）
            
        Raises:
            Exception: API调用失败
        """
        logger.info(f"获取板块成交额数据: sector_code={sector_code}, date={date}")
        
        try:
            # 判断是否为当日
            from datetime import datetime
            today = datetime.now().strftime('%Y-%m-%d')
            is_today = (date == today)
            api_date = None if is_today else date
            
            # 使用get_sector_capital_data接口获取板块总成交额
            result = self._retry_request(
                self.crawler.get_sector_capital_data,
                sector_code=sector_code,
                date=api_date
            )
            
            if not result:
                logger.warning(f"板块成交额数据为空: {sector_code}, {date}")
                return TurnoverData(
                    sector_turnover=0.0,
                    top5_stocks=[],
                    stock_market_caps={}
                )
            
            # 解析数据
            sector_turnover = float(result.get('turnover', 0)) / 100000000  # 转换为亿元
            
            logger.info(
                f"成功获取板块成交额数据: 总成交额{sector_turnover:.2f}亿元"
            )
            
            return TurnoverData(
                sector_turnover=sector_turnover,
                top5_stocks=[],  # 该接口不返回个股数据
                stock_market_caps={}  # 该接口不返回个股数据
            )
            
        except Exception as e:
            logger.error(f"获取板块成交额数据失败: {e}")
            raise

    def get_sector_detailed_data(
        self,
        sector_code: str,
        sector_name: str,
        date: str
    ) -> Dict[str, Any]:
        """获取板块的详细数据（涨停数、连板梯队、资金流入等）
        
        Args:
            sector_code: 板块代码（如"803023"）
            sector_name: 板块名称（如"AI应用"）
            date: 日期字符串，格式 'YYYY-MM-DD'
            
        Returns:
            字典包含：
            - limit_up_count: 板块涨停数
            - limit_up_stocks: 涨停股票列表
            - consecutive_boards: 连板梯队分布 {1: 5, 2: 3, 3: 1}
            - capital_inflow: 主力资金净流入（亿元）
            - capital_inflow_rate: 主力资金净流入率（%）
            - turnover: 成交额（亿元）
            - change_pct: 涨跌幅（%）
            - leading_stock: 龙头股信息
            
        Raises:
            Exception: API调用失败
        """
        logger.info(f"获取板块详细数据: sector_code={sector_code}, sector_name={sector_name}, date={date}")
        
        result = {
            'limit_up_count': 0,
            'limit_up_stocks': [],
            'consecutive_boards': {},
            'capital_inflow': 0.0,
            'capital_inflow_rate': 0.0,
            'turnover': 0.0,
            'change_pct': 0.0,
            'leading_stock': None
        }
        
        try:
            # 判断是否为当日
            from datetime import datetime
            today = datetime.now().strftime('%Y-%m-%d')
            is_today = (date == today)
            api_date = None if is_today else date
            
            # 1. 获取板块排名数据（包含涨停股票列表）
            try:
                sector_ranking = self._retry_request(
                    self.crawler.get_sector_ranking,
                    date=api_date
                )
                
                if sector_ranking and 'sectors' in sector_ranking:
                    # 查找目标板块
                    for sector in sector_ranking['sectors']:
                        if sector.get('sector_code') == sector_code or sector.get('sector_name') == sector_name:
                            stocks = sector.get('stocks', [])
                            result['limit_up_count'] = len(stocks)
                            
                            # 为每只股票添加标准化的连板描述
                            for stock in stocks:
                                raw_consecutive = stock.get('连板天数', '')
                                stock['连板天数_标准'] = self._clean_consecutive_days(raw_consecutive)
                            
                            result['limit_up_stocks'] = stocks
                            
                            # 统计连板梯队（按板数统计，同时记录完整描述）
                            consecutive_boards = {}
                            consecutive_boards_desc = {}  # 新增：保存完整描述
                            for stock in stocks:
                                consecutive_str = stock.get('连板天数', '')
                                consecutive_num = self._get_consecutive_board_number(consecutive_str)
                                consecutive_desc = self._clean_consecutive_days(consecutive_str)
                                
                                if consecutive_num > 0:
                                    consecutive_boards[consecutive_num] = consecutive_boards.get(consecutive_num, 0) + 1
                                    # 记录该板数对应的完整描述（可能有多种，如"2连板"和"8天2板"）
                                    if consecutive_num not in consecutive_boards_desc:
                                        consecutive_boards_desc[consecutive_num] = set()
                                    consecutive_boards_desc[consecutive_num].add(consecutive_desc)
                            
                            result['consecutive_boards'] = consecutive_boards
                            result['consecutive_boards_desc'] = consecutive_boards_desc  # 新增：保存描述映射
                            
                            # 找出核心中军（综合考虑连板高度、市值、成交量）
                            if stocks:
                                # 标准化字段（避免字符串排序/前导0丢失）
                                for stock in stocks:
                                    stock["股票代码"] = self._normalize_stock_code(stock.get("股票代码"))
                                    stock["封单额_数值"] = self._to_number(stock.get("封单额", 0))
                                    # 优先使用总市值；没有则退化到流通市值
                                    market_cap_raw = stock.get("总市值", None)
                                    if market_cap_raw is None or str(market_cap_raw).strip() == "":
                                        market_cap_raw = stock.get("流通市值", 0)
                                    stock["市值_数值"] = self._to_number(market_cap_raw)

                                # 1. 按连板天数和封单额排序，找出连板龙头（空间龙）
                                # 空间龙定义：至少2板以上的个股，最多取4个
                                sorted_by_board = sorted(
                                    stocks,
                                    key=lambda s: (
                                        self._get_consecutive_board_number(s.get('连板天数', '')),
                                        s.get('封单额_数值', 0)
                                    ),
                                    reverse=True
                                )
                                # 过滤出至少2板的个股作为空间龙候选
                                space_dragon_candidates = [
                                    s for s in sorted_by_board
                                    if self._get_consecutive_board_number(s.get('连板天数', '')) >= 2
                                ]
                                # 最多4个空间龙
                                space_dragons = space_dragon_candidates[:4] if space_dragon_candidates else []
                                # 主连板龙头（最高板）
                                board_leader = space_dragon_candidates[0] if space_dragon_candidates else None
                                
                                # 2. 按总市值排序，找出市值龙头
                                sorted_by_market_cap = sorted(
                                    stocks,
                                    key=lambda s: s.get('市值_数值', 0),
                                    reverse=True
                                )
                                market_cap_leader = sorted_by_market_cap[0] if sorted_by_market_cap else None
                                
                                # 3. 需要获取成交额来找成交量龙头，先收集所有股票代码
                                stocks_with_turnover = []
                                for stock in stocks[:10]:  # 只检查前10只，避免API调用过多
                                    stock_code = stock.get('股票代码', '')
                                    if stock_code:
                                        try:
                                            stock_data = self._retry_request(
                                                self.crawler.get_stock_intraday,
                                                stock_code=stock_code,
                                                date=api_date
                                            )
                                            if stock_data and 'total_turnover' in stock_data:
                                                stock['_turnover'] = float(stock_data['total_turnover'])
                                                stocks_with_turnover.append(stock)
                                        except Exception as e:
                                            logger.debug(f"获取{stock.get('股票名称', '')}成交额失败: {e}")
                                
                                # 按成交额排序，找出成交量龙头
                                turnover_leader = None
                                if stocks_with_turnover:
                                    sorted_by_turnover = sorted(
                                        stocks_with_turnover,
                                        key=lambda s: s.get('_turnover', 0),
                                        reverse=True
                                    )
                                    turnover_leader = sorted_by_turnover[0]
                                
                                # 4. 确定主龙头（优先连板龙头）
                                leading = board_leader or market_cap_leader or turnover_leader

                                # 5. 重新设计龙头股分类：空间龙、中军、先锋龙
                                core_leaders = []

                                # 5.1 空间龙：至少2板，最多4个，按连板数降序
                                if space_dragons:
                                    for i, dragon in enumerate(space_dragons, 1):
                                        core_leaders.append({
                                            'type': '空间龙',
                                            'type_detail': f'空间龙#{i}',
                                            'stock': dragon
                                        })

                                # 5.2 中军：市值最大的涨停股，最多2个（排除已是空间龙的）
                                space_dragon_codes = {d.get('股票代码') for d in space_dragons}
                                market_cap_candidates = [
                                    s for s in sorted_by_market_cap
                                    if s.get('股票代码') not in space_dragon_codes
                                ]
                                zhongjun_list = market_cap_candidates[:2]  # 最多2个中军
                                for i, zj in enumerate(zhongjun_list, 1):
                                    core_leaders.append({
                                        'type': '中军',
                                        'type_detail': f'中军#{i}',
                                        'stock': zj
                                    })

                                # 5.3 先锋龙：按首次封板时间排序，最早封板的为先锋，最多2个
                                # 解析首次封板时间
                                def parse_first_seal_time(stock):
                                    time_str = stock.get('首次封板时间', '')
                                    if not time_str or time_str == '-':
                                        return '99:99'  # 没有时间则排最后
                                    return time_str

                                # 排除已是空间龙和中军的股票
                                zhongjun_codes = {z.get('股票代码') for z in zhongjun_list}
                                excluded_codes = space_dragon_codes | zhongjun_codes

                                pioneer_candidates = [
                                    s for s in sorted(stocks, key=parse_first_seal_time)
                                    if s.get('股票代码') not in excluded_codes
                                ]
                                pioneer_list = pioneer_candidates[:2]  # 最多2个先锋
                                for i, p in enumerate(pioneer_list, 1):
                                    core_leaders.append({
                                        'type': '先锋龙',
                                        'type_detail': f'先锋龙#{i}',
                                        'stock': p
                                    })
                                
                                # 6. 获取主龙头的详细数据（使用收盘封单，不是大单净额）
                                leading_turnover = 0.0
                                big_order_net = 0.0
                                big_order_buy = 0.0
                                big_order_sell = 0.0
                                actual_turnover_rate = 0.0  # 实际换手率
                                circulation_market_cap = 0.0  # 流通市值（亿元）

                                try:
                                    if not leading:
                                        raise ValueError("no_leading_stock")

                                    stock_code = leading.get('股票代码', '')
                                    if stock_code:
                                        # 获取成交额和换手率
                                        if '_turnover' in leading:
                                            leading_turnover = leading['_turnover'] / 100000000
                                        else:
                                            stock_data = self._retry_request(
                                                self.crawler.get_stock_intraday,
                                                stock_code=stock_code,
                                                date=api_date
                                            )
                                            if stock_data and 'total_turnover' in stock_data:
                                                leading_turnover = float(stock_data['total_turnover']) / 100000000
                                                # 获取换手率
                                                if 'turnover_rate' in stock_data:
                                                    actual_turnover_rate = float(stock_data['turnover_rate'])

                                        logger.debug(f"龙头股{leading.get('股票名称', '')}成交额: {leading_turnover:.2f}亿元")

                                        # 获取大单流入数据
                                        try:
                                            big_order_data = self._retry_request(
                                                self.crawler.get_stock_big_order_intraday,
                                                stock_code=stock_code,
                                                date=api_date
                                            )
                                            if big_order_data:
                                                big_order_buy = float(big_order_data.get('big_order_buy_total', 0)) / 100000000
                                                big_order_sell = float(big_order_data.get('big_order_sell_total', 0)) / 100000000
                                                big_order_net = float(big_order_data.get('big_order_net_total', 0)) / 100000000
                                                logger.debug(f"龙头股{leading.get('股票名称', '')}大单净额: {big_order_net:.2f}亿元")
                                        except Exception as e:
                                            logger.warning(f"获取大单数据失败: {e}")

                                        # 获取流通市值（用于计算换手率和显示）
                                        try:
                                            # 使用akshare获取详细股票数据
                                            import akshare as ak
                                            stock_info = ak.stock_individual_info_em(symbol=stock_code)
                                            if not stock_info.empty:
                                                circulation_market_cap = float(stock_info[stock_info['item'] == '总市值'].iloc[0]['value']) / 100000000
                                                if circulation_market_cap == 0:
                                                    circulation_market_cap = leading.get('市值_数值', 0) / 100000000
                                            else:
                                                circulation_market_cap = leading.get('市值_数值', 0) / 100000000
                                        except Exception as e:
                                            logger.warning(f"获取流通市值失败: {e}")
                                            circulation_market_cap = leading.get('市值_数值', 0) / 100000000

                                except Exception as e:
                                    logger.warning(f"获取龙头股数据失败: {e}")
                                    # 降级方案
                                    leading_turnover = 0.0
                                    circulation_market_cap = leading.get('市值_数值', 0) / 100000000 if leading else 0

                                # 7. 构建龙头股数据结构（使用收盘封单，不是大单净额）
                                # 获取收盘封单额（从原始数据中获取）
                                seal_amount = leading.get('封单额_数值', 0) / 100000000 if leading else 0

                                result['leading_stock'] = {
                                    'code': leading.get('股票代码', '') if leading else '',
                                    'name': leading.get('股票名称', '') if leading else '',
                                    'consecutive_days': self._clean_consecutive_days(leading.get('连板天数', '')) if leading else '',
                                    'limit_up_price': leading.get('涨停价', 0) if leading else 0,
                                    'turnover': leading_turnover,
                                    'seal_amount': seal_amount,  # 收盘封单额（亿元）
                                    'big_order_net': big_order_net,  # 大单净流入（亿元）
                                    'big_order_buy': big_order_buy,
                                    'big_order_sell': big_order_sell,
                                    'market_cap': circulation_market_cap,  # 流通市值（亿元）
                                    'actual_turnover_rate': actual_turnover_rate,  # 实际换手率(%)
                                    'first_seal_time': leading.get('首次封板时间', '') if leading else '',  # 首次涨停时间
                                    'last_seal_time': leading.get('最终封板时间', '') if leading else '',  # 最终涨停时间
                                    'open_count': leading.get('开板次数', 0) if leading else 0,  # 开板次数
                                }
                                
                                # 8. 添加核心中军列表（空间龙、中军、先锋龙）
                                result['core_leaders'] = []
                                result['space_dragons'] = []  # 空间龙列表（最多4个）
                                result['zhongjun_list'] = []  # 中军列表（最多2个）
                                result['pioneer_list'] = []   # 先锋龙列表（最多2个）

                                for leader_info in core_leaders:
                                    stock = leader_info['stock']
                                    stock_code = stock.get('股票代码', '')

                                    # 获取个股详细数据
                                    stock_turnover = 0.0
                                    actual_turnover_rate = 0.0
                                    big_order_net = 0.0
                                    circulation_market_cap = 0.0

                                    try:
                                        # 获取成交额和换手率
                                        stock_data = self._retry_request(
                                            self.crawler.get_stock_intraday,
                                            stock_code=stock_code,
                                            date=api_date
                                        )
                                        if stock_data:
                                            if 'total_turnover' in stock_data:
                                                stock_turnover = float(stock_data['total_turnover']) / 100000000
                                            if 'turnover_rate' in stock_data:
                                                actual_turnover_rate = float(stock_data['turnover_rate'])

                                        # 获取大单净流入
                                        try:
                                            big_order_data = self._retry_request(
                                                self.crawler.get_stock_big_order_intraday,
                                                stock_code=stock_code,
                                                date=api_date
                                            )
                                            if big_order_data:
                                                big_order_net = float(big_order_data.get('big_order_net_total', 0)) / 100000000
                                        except:
                                            pass

                                        # 获取流通市值
                                        try:
                                            import akshare as ak
                                            stock_info = ak.stock_individual_info_em(symbol=stock_code)
                                            if not stock_info.empty:
                                                circulation_market_cap = float(stock_info[stock_info['item'] == '总市值'].iloc[0]['value']) / 100000000
                                                if circulation_market_cap == 0:
                                                    circulation_market_cap = stock.get('市值_数值', 0) / 100000000
                                            else:
                                                circulation_market_cap = stock.get('市值_数值', 0) / 100000000
                                        except:
                                            circulation_market_cap = stock.get('市值_数值', 0) / 100000000

                                    except Exception as e:
                                        logger.debug(f"获取{stock.get('股票名称', '')}详细数据失败: {e}")
                                        stock_turnover = stock.get('_turnover', 0) / 100000000 if '_turnover' in stock else 0
                                        circulation_market_cap = stock.get('市值_数值', 0) / 100000000

                                    leader_data = {
                                        'type': leader_info['type'],
                                        'type_detail': leader_info.get('type_detail', ''),
                                        'code': stock_code,
                                        'name': stock.get('股票名称', ''),
                                        'consecutive_days': self._clean_consecutive_days(stock.get('连板天数', '')),
                                        'turnover': stock_turnover,
                                        'market_cap': circulation_market_cap,
                                        'actual_turnover_rate': actual_turnover_rate,
                                        'big_order_net': big_order_net,
                                        'seal_amount': stock.get('封单额_数值', 0) / 100000000,
                                        'first_seal_time': stock.get('首次封板时间', ''),
                                        'last_seal_time': stock.get('最终封板时间', ''),
                                        'open_count': stock.get('开板次数', 0),
                                    }

                                    result['core_leaders'].append(leader_data)

                                    # 分类存储
                                    if leader_info['type'] == '空间龙':
                                        result['space_dragons'].append(leader_data)
                                    elif leader_info['type'] == '中军':
                                        result['zhongjun_list'].append(leader_data)
                                    elif leader_info['type'] == '先锋龙':
                                        result['pioneer_list'].append(leader_data)
                                
                                logger.info(f"板块 {sector_name} 核心中军: {len(core_leaders)}只")
                                for leader_info in result['core_leaders']:
                                    logger.info(f"  - {leader_info['type']}: {leader_info['name']}（{leader_info['code']}）")
                            
                            break
            except Exception as e:
                logger.warning(f"获取板块排名数据失败: {e}")
            
            # 2. 获取板块资金数据
            try:
                capital_data = self._retry_request(
                    self.crawler.get_sector_capital_data,
                    sector_code=sector_code,
                    date=api_date
                )
                
                if capital_data:
                    result['capital_inflow'] = float(capital_data.get('main_net_inflow', 0)) / 100000000  # 转换为亿元
                    result['capital_inflow_rate'] = float(capital_data.get('main_net_inflow_rate', 0))
                    result['turnover'] = float(capital_data.get('turnover', 0)) / 100000000  # 转换为亿元
                    result['change_pct'] = float(capital_data.get('change_pct', 0))
            except Exception as e:
                logger.warning(f"获取板块资金数据失败: {e}")
            
            # 格式化连板梯队描述用于日志
            ladder_desc_parts = []
            for board_num in sorted(result['consecutive_boards'].keys(), reverse=True):
                count = result['consecutive_boards'][board_num]
                # 获取该板数的所有描述
                descs = result.get('consecutive_boards_desc', {}).get(board_num, set())
                if descs:
                    # 如果有多种描述，显示所有
                    desc_str = '/'.join(sorted(descs))
                    ladder_desc_parts.append(f"{desc_str}×{count}")
                else:
                    # 降级方案：只显示板数
                    ladder_desc_parts.append(f"{board_num}板×{count}")
            
            ladder_desc = ', '.join(ladder_desc_parts) if ladder_desc_parts else '无'
            
            logger.info(
                f"成功获取板块详细数据: 涨停{result['limit_up_count']}只, "
                f"连板梯队[{ladder_desc}], "
                f"资金流入{result['capital_inflow']:.2f}亿元"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"获取板块详细数据失败: {e}")
            return result
