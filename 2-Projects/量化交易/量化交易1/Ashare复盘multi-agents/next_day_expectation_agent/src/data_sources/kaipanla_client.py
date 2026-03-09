"""
Kaipanla API客户端

提供开盘啦数据接口的封装，支持行情数据和竞价数据获取。
"""

import sys
import importlib.util
from pathlib import Path
from typing import Optional, Dict, Any, List
import pandas as pd
from datetime import datetime

# 添加kaipanla_crawler路径 - 从项目根目录查找
current_file = Path(__file__).resolve()
# 从 next_day_expectation_agent/src/data_sources/kaipanla_client.py
# 向上到 next_day_expectation_agent/
project_root = current_file.parent.parent.parent
# 向上到 Ashare复盘multi-agents/
ashare_root = project_root.parent
# 向上到项目根目录
workspace_root = ashare_root.parent
# kaipanla_crawler 在项目根目录下
kaipanla_path = workspace_root / "kaipanla_crawler"

if str(kaipanla_path) not in sys.path:
    sys.path.insert(0, str(kaipanla_path))

try:
    from kaipanla_crawler import KaipanlaCrawler
except ImportError:
    # 如果导入失败，尝试从绝对路径导入
    spec = importlib.util.spec_from_file_location(
        "kaipanla_crawler",
        kaipanla_path / "kaipanla_crawler.py"
    )
    if spec and spec.loader:
        kaipanla_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(kaipanla_module)
        KaipanlaCrawler = kaipanla_module.KaipanlaCrawler
    else:
        raise ImportError("Cannot import KaipanlaCrawler")

from ..common.logger import get_logger

logger = get_logger(__name__)


class KaipanlaClient:
    """
    Kaipanla API客户端
    
    封装开盘啦爬虫接口，提供统一的数据获取方法。
    """
    
    def __init__(self):
        """初始化Kaipanla客户端"""
        self.crawler = KaipanlaCrawler()
        logger.info("KaipanlaClient initialized")
    
    def get_market_data(
        self,
        date: str,
        start_date: Optional[str] = None
    ) -> pd.DataFrame:
        """
        获取市场行情数据
        
        Args:
            date: 结束日期，格式YYYY-MM-DD
            start_date: 开始日期，格式YYYY-MM-DD（可选）
            
        Returns:
            DataFrame: 市场行情数据
            
        Raises:
            Exception: 数据获取失败时抛出异常
        """
        try:
            logger.info(f"Fetching market data for date: {date}, start_date: {start_date}")
            
            if start_date:
                data = self.crawler.get_daily_data(end_date=date, start_date=start_date)
            else:
                data = self.crawler.get_daily_data(end_date=date)
            
            if data is None or (isinstance(data, pd.DataFrame) and data.empty):
                raise Exception(f"No market data returned for date: {date}")
            
            logger.info(f"Successfully fetched market data, records: {len(data) if isinstance(data, pd.DataFrame) else 1}")
            return data
            
        except Exception as e:
            logger.error(f"Failed to fetch market data: {e}")
            raise
    
    def get_auction_data(
        self,
        stock_code: str,
        date: Optional[str] = None
    ) -> pd.DataFrame:
        """
        获取个股竞价数据（分时数据）
        
        Args:
            stock_code: 股票代码
            date: 日期，格式YYYY-MM-DD（可选，默认当日）
            
        Returns:
            DataFrame: 竞价分时数据
            
        Raises:
            Exception: 数据获取失败时抛出异常
        """
        try:
            logger.info(f"Fetching auction data for stock: {stock_code}, date: {date}")
            
            data = self.crawler.get_stock_intraday(stock_code=stock_code, date=date)
            
            if data is None or data.empty:
                raise Exception(f"No auction data returned for stock: {stock_code}")
            
            logger.info(f"Successfully fetched auction data, records: {len(data)}")
            return data
            
        except Exception as e:
            logger.error(f"Failed to fetch auction data: {e}")
            raise
    
    def get_sector_intraday(
        self,
        sector_code: str,
        date: Optional[str] = None
    ) -> pd.DataFrame:
        """
        获取板块分时数据
        
        Args:
            sector_code: 板块代码
            date: 日期，格式YYYY-MM-DD（可选，默认当日）
            
        Returns:
            DataFrame: 板块分时数据
            
        Raises:
            Exception: 数据获取失败时抛出异常
        """
        try:
            logger.info(f"Fetching sector intraday data for sector: {sector_code}, date: {date}")
            
            data = self.crawler.get_sector_intraday(sector_code=sector_code, date=date)
            
            if data is None or data.empty:
                raise Exception(f"No sector intraday data returned for sector: {sector_code}")
            
            logger.info(f"Successfully fetched sector intraday data, records: {len(data)}")
            return data
            
        except Exception as e:
            logger.error(f"Failed to fetch sector intraday data: {e}")
            raise
    
    def get_abnormal_stocks(self) -> pd.DataFrame:
        """
        获取异动个股数据（实时）
        
        Returns:
            DataFrame: 异动个股数据
            
        Raises:
            Exception: 数据获取失败时抛出异常
        """
        try:
            logger.info("Fetching abnormal stocks data")
            
            data = self.crawler.get_abnormal_stocks()
            
            if data is None or data.empty:
                logger.warning("No abnormal stocks data returned")
                return pd.DataFrame()
            
            logger.info(f"Successfully fetched abnormal stocks data, records: {len(data)}")
            return data
            
        except Exception as e:
            logger.error(f"Failed to fetch abnormal stocks data: {e}")
            raise
    
    def get_limit_up_stocks(
        self,
        date: str
    ) -> pd.DataFrame:
        """
        获取涨停个股数据
        
        Args:
            date: 日期，格式YYYY-MM-DD
            
        Returns:
            DataFrame: 涨停个股数据
            
        Raises:
            Exception: 数据获取失败时抛出异常
        """
        try:
            logger.info(f"Fetching limit up stocks for date: {date}")
            
            # 使用get_market_limit_up_ladder获取历史连板梯队数据
            ladder_data = self.crawler.get_market_limit_up_ladder(date=date)
            
            if not ladder_data or not ladder_data.get('ladder'):
                logger.warning(f"No limit up stocks data returned for date: {date}")
                return pd.DataFrame()
            
            # 合并所有连板数据
            all_stocks = []
            ladder = ladder_data.get('ladder', {})
            
            for consecutive_days, stocks in ladder.items():
                for stock in stocks:
                    # 添加连板天数字段
                    stock['连板天数'] = int(consecutive_days)
                    all_stocks.append(stock)
            
            if not all_stocks:
                logger.warning(f"No stocks found in ladder data")
                return pd.DataFrame()
            
            # 转换为DataFrame
            df = pd.DataFrame(all_stocks)
            
            logger.info(f"Found {len(df)} limit up stocks")
            return df
            
        except Exception as e:
            logger.error(f"Failed to fetch limit up stocks: {e}")
            raise
    
    def get_continuous_limit_up_stocks(
        self,
        date: str
    ) -> pd.DataFrame:
        """
        获取连板个股数据
        
        Args:
            date: 日期，格式YYYY-MM-DD
            
        Returns:
            DataFrame: 连板个股数据（包含连板高度）
            
        Raises:
            Exception: 数据获取失败时抛出异常
        """
        try:
            logger.info(f"Fetching continuous limit up stocks for date: {date}")
            
            # 获取涨停股数据
            limit_up_data = self.get_limit_up_stocks(date=date)
            
            # 筛选连板股（连板天数>1）
            if '连板天数' in limit_up_data.columns:
                continuous_data = limit_up_data[limit_up_data['连板天数'] > 1]
            else:
                # 如果没有连板天数字段，返回所有涨停股
                logger.warning("No '连板天数' column found, returning all limit up stocks")
                continuous_data = limit_up_data
            
            logger.info(f"Found {len(continuous_data)} continuous limit up stocks")
            return continuous_data
            
        except Exception as e:
            logger.error(f"Failed to fetch continuous limit up stocks: {e}")
            raise
    
    def get_sector_ranking(
        self,
        date: str,
        index: int = 693
    ) -> pd.DataFrame:
        """
        获取板块排名数据
        
        Args:
            date: 日期，格式YYYY-MM-DD
            index: 指数代码，默认693（涨停原因）
            
        Returns:
            DataFrame: 板块排名数据
            
        Raises:
            Exception: 数据获取失败时抛出异常
        """
        try:
            logger.info(f"Fetching sector ranking for date: {date}, index: {index}")
            
            data = self.crawler.get_sector_ranking(date=date, index=index)
            
            if data is None or data.empty:
                raise Exception(f"No sector ranking data returned for date: {date}")
            
            logger.info(f"Successfully fetched sector ranking data, records: {len(data)}")
            return data
            
        except Exception as e:
            logger.error(f"Failed to fetch sector ranking: {e}")
            raise
    
    def get_new_high_stocks(
        self,
        date: str,
        start_date: Optional[str] = None
    ) -> pd.DataFrame:
        """
        获取百日新高个股数据
        
        Args:
            date: 结束日期，格式YYYY-MM-DD
            start_date: 开始日期，格式YYYY-MM-DD（可选）
            
        Returns:
            DataFrame: 百日新高个股数据
            
        Raises:
            Exception: 数据获取失败时抛出异常
        """
        try:
            logger.info(f"Fetching new high stocks for date: {date}, start_date: {start_date}")
            
            if start_date:
                data = self.crawler.get_new_high_data(end_date=date, start_date=start_date)
            else:
                data = self.crawler.get_new_high_data(end_date=date)
            
            if data is None or (isinstance(data, pd.DataFrame) and data.empty):
                logger.warning(f"No new high stocks data returned for date: {date}")
                return pd.DataFrame()
            
            logger.info(f"Successfully fetched new high stocks data")
            return data
            
        except Exception as e:
            logger.error(f"Failed to fetch new high stocks: {e}")
            raise
    
    def health_check(self) -> bool:
        """
        健康检查
        
        Returns:
            bool: True表示服务正常，False表示服务异常
        """
        try:
            # 尝试获取最近一个交易日的数据
            today = datetime.now().strftime("%Y-%m-%d")
            self.get_market_data(date=today)
            logger.info("Kaipanla health check passed")
            return True
        except Exception as e:
            logger.error(f"Kaipanla health check failed: {e}")
            return False

    def get_market_limit_up_ladder(
        self,
        date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        获取全市场连板梯队（包含炸板股数据）
        
        Args:
            date: 日期，格式YYYY-MM-DD（可选，默认获取实时数据）
            
        Returns:
            Dict: 连板梯队数据，包含：
                - date: 日期
                - is_realtime: 是否为实时数据
                - ladder: 连板梯队数据（按连板数分组）
                - broken_stocks: 反包板（炸板）股票列表
                - height_marks: 打开高度标注股票列表
                - statistics: 统计信息
            
        Raises:
            Exception: 数据获取失败时抛出异常
        """
        try:
            logger.info(f"Fetching market limit up ladder for date: {date}")
            
            data = self.crawler.get_market_limit_up_ladder(date=date)
            
            if data is None:
                raise Exception(f"No market limit up ladder data returned for date: {date}")
            
            broken_count = len(data.get('broken_stocks', []))
            logger.info(f"Successfully fetched market limit up ladder, broken stocks: {broken_count}")
            return data
            
        except Exception as e:
            logger.error(f"Failed to fetch market limit up ladder: {e}")
            raise
    
    def get_historical_broken_limit_up(
        self,
        date: str
    ) -> List[Dict[str, Any]]:
        """
        获取历史炸板股数据（曾涨停但未封住的个股）
        
        Args:
            date: 日期，格式YYYY-MM-DD
            
        Returns:
            List[Dict]: 炸板股列表，每个元素包含：
                - stock_code: 股票代码
                - stock_name: 股票名称
                - change_pct: 涨幅
                - limit_up_time: 涨停时间（时间戳）
                - open_time: 开板时间（时间戳）
                - yesterday_consecutive: 昨日连板高度
                - yesterday_consecutive_text: 昨日连板高度文字描述
                - sector: 所属板块
                - main_capital_net: 主力净额
                - turnover_amount: 成交额
                - turnover_rate: 换手率
                - actual_circulation: 实际流通
            
        Raises:
            Exception: 数据获取失败时抛出异常
        """
        try:
            logger.info(f"Fetching historical broken limit up stocks for date: {date}")
            
            data = self.crawler.get_historical_broken_limit_up(date=date)
            
            if data is None:
                logger.warning(f"No broken limit up data returned for date: {date}")
                return []
            
            logger.info(f"Successfully fetched {len(data)} broken limit up stocks")
            return data
            
        except Exception as e:
            logger.error(f"Failed to fetch broken limit up stocks: {e}")
            raise
    
    def get_sentiment_indicator(
        self,
        plate_id: str = "801225",
        stocks: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        获取多头空头风向标
        
        Args:
            plate_id: 板块ID，默认"801225"
            stocks: 股票列表（可选）
            
        Returns:
            Dict: 风向标数据，包含：
                - date: 日期
                - plate_id: 板块ID
                - bullish_codes: 多头风向标股票代码列表（前3只）
                - bearish_codes: 空头风向标股票代码列表（后3只）
                - all_stocks: 所有股票代码列表
            
        Raises:
            Exception: 数据获取失败时抛出异常
        """
        try:
            logger.info(f"Fetching sentiment indicator for plate: {plate_id}")
            
            data = self.crawler.get_sentiment_indicator(plate_id=plate_id, stocks=stocks)
            
            if data is None:
                raise Exception(f"No sentiment indicator data returned for plate: {plate_id}")
            
            bullish_count = len(data.get('bullish_codes', []))
            logger.info(f"Successfully fetched sentiment indicator, bullish stocks: {bullish_count}")
            return data
            
        except Exception as e:
            logger.error(f"Failed to fetch sentiment indicator: {e}")
            raise
    
    def get_ths_hot_rank(
        self,
        headless: bool = True,
        wait_time: int = 5,
        timeout: int = 300,
        max_rank: int = 50
    ) -> pd.Series:
        """
        获取同花顺热榜个股数据
        
        Args:
            headless: 是否使用无头模式（不显示浏览器窗口）
            wait_time: 页面加载后等待时间（秒）
            timeout: 操作超时时间（秒）
            max_rank: 最大获取排名数，默认50
            
        Returns:
            pd.Series: index为排名，values为个股名字
            
        Raises:
            Exception: 数据获取失败时抛出异常
        """
        try:
            logger.info(f"Fetching THS hot rank stocks (max_rank={max_rank})")
            
            data = self.crawler.get_ths_hot_rank(
                headless=headless,
                wait_time=wait_time,
                timeout=timeout,
                max_rank=max_rank
            )
            
            if data is None or data.empty:
                logger.warning("No THS hot rank data returned")
                return pd.Series()
            
            logger.info(f"Successfully fetched THS hot rank, stocks: {len(data)}")
            return data
            
        except Exception as e:
            logger.error(f"Failed to fetch THS hot rank: {e}")
            raise
    
    def get_stock_name(
        self,
        stock_code: str
    ) -> str:
        """
        获取股票名称
        
        Args:
            stock_code: 股票代码
            
        Returns:
            str: 股票名称，如果获取失败返回空字符串
        """
        try:
            # 尝试从当日市场数据中获取
            today = datetime.now().strftime("%Y-%m-%d")
            market_data = self.get_market_data(date=today)
            
            if isinstance(market_data, pd.Series):
                market_data = market_data.to_frame().T
            
            if not market_data.empty:
                # 查找匹配的股票代码
                code_col = '代码' if '代码' in market_data.columns else '股票代码'
                name_col = '名称' if '名称' in market_data.columns else '股票名称'
                
                if code_col in market_data.columns and name_col in market_data.columns:
                    matched = market_data[market_data[code_col].astype(str) == stock_code]
                    if not matched.empty:
                        return str(matched.iloc[0][name_col])
            
            logger.warning(f"Stock name not found for code: {stock_code}")
            return ""
            
        except Exception as e:
            logger.error(f"Failed to get stock name for {stock_code}: {e}")
            return ""
    
    def get_stock_names_batch(
        self,
        stock_codes: List[str]
    ) -> Dict[str, str]:
        """
        批量获取股票名称
        
        Args:
            stock_codes: 股票代码列表
            
        Returns:
            Dict[str, str]: 股票代码到名称的映射字典
        """
        try:
            logger.info(f"Fetching stock names for {len(stock_codes)} stocks")
            
            # 获取当日市场数据
            today = datetime.now().strftime("%Y-%m-%d")
            market_data = self.get_market_data(date=today)
            
            if isinstance(market_data, pd.Series):
                market_data = market_data.to_frame().T
            
            result = {}
            
            if not market_data.empty:
                code_col = '代码' if '代码' in market_data.columns else '股票代码'
                name_col = '名称' if '名称' in market_data.columns else '股票名称'
                
                if code_col in market_data.columns and name_col in market_data.columns:
                    for code in stock_codes:
                        matched = market_data[market_data[code_col].astype(str) == code]
                        if not matched.empty:
                            result[code] = str(matched.iloc[0][name_col])
                        else:
                            result[code] = ""
            
            logger.info(f"Successfully fetched {len(result)} stock names")
            return result
            
        except Exception as e:
            logger.error(f"Failed to get stock names batch: {e}")
            return {code: "" for code in stock_codes}
    
    def get_stock_intraday(
        self,
        stock_code: str,
        date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        获取个股分时数据（完整数据，包含价格、涨跌幅等）
        
        Args:
            stock_code: 股票代码
            date: 日期，格式YYYY-MM-DD（可选，默认当日）
            
        Returns:
            Dict: 个股分时数据，包含：
                - stock_code: 股票代码
                - date: 日期
                - preclose_px: 昨收价
                - begin_px: 开盘价
                - lprice: 最低价
                - hprice: 最高价
                - px_change_rate: 涨跌幅
                - total_turnover: 总成交额
                - total_main_inflow: 主力净流入总额
                - total_main_outflow: 主力净流出总额
                - data: DataFrame，包含分时数据
            
        Raises:
            Exception: 数据获取失败时抛出异常
        """
        try:
            logger.info(f"Fetching stock intraday data for stock: {stock_code}, date: {date}")
            
            data = self.crawler.get_stock_intraday(stock_code=stock_code, date=date)
            
            if not data:
                raise Exception(f"No stock intraday data returned for stock: {stock_code}")
            
            logger.info(f"Successfully fetched stock intraday data")
            return data
            
        except Exception as e:
            logger.error(f"Failed to fetch stock intraday data: {e}")
            raise
    
    def get_sector_ranking(
        self,
        date: Optional[str] = None,
        index: int = 0
    ) -> Dict[str, Any]:
        """
        获取涨停原因板块数据
        
        Args:
            date: 日期，格式YYYY-MM-DD（可选，默认当日）
            index: 指数代码，默认0（涨停原因）
            
        Returns:
            Dict: 板块排名数据，包含：
                - summary: 市场概况（涨停数、跌停数等）
                - sectors: 板块列表，每个板块包含：
                    - sector_code: 板块代码
                    - sector_name: 板块名称
                    - stocks: 该板块涨停股票列表
                    - stock_count: 涨停股票数量
            
        Raises:
            Exception: 数据获取失败时抛出异常
        """
        try:
            logger.info(f"Fetching sector ranking for date: {date}, index: {index}")
            
            data = self.crawler.get_sector_ranking(date=date, index=index)
            
            if not data:
                raise Exception(f"No sector ranking data returned for date: {date}")
            
            sector_count = len(data.get('sectors', []))
            logger.info(f"Successfully fetched sector ranking, sectors: {sector_count}")
            return data
            
        except Exception as e:
            logger.error(f"Failed to fetch sector ranking: {e}")
            raise
