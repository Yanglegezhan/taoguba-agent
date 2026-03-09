"""
AKShare API客户端

提供AKShare数据接口的封装，支持代理配置自动应用。
"""

import os
from typing import Optional, Dict, Any
import pandas as pd
from datetime import datetime
import akshare as ak

from ..common.logger import get_logger

logger = get_logger(__name__)


class AKShareClient:
    """
    AKShare API客户端
    
    封装AKShare接口，提供统一的数据获取方法，支持代理配置。
    """
    
    def __init__(self, proxy_config: Optional[Dict[str, str]] = None):
        """
        初始化AKShare客户端
        
        Args:
            proxy_config: 代理配置字典，格式：
                {
                    'http': 'http://proxy_host:port',
                    'https': 'https://proxy_host:port'
                }
        """
        self.proxy_config = proxy_config
        self._apply_proxy_config()
        logger.info("AKShareClient initialized")
    
    def _apply_proxy_config(self) -> None:
        """
        应用代理配置到环境变量
        
        AKShare使用requests库，会自动读取环境变量中的代理设置。
        """
        if self.proxy_config:
            if 'http' in self.proxy_config:
                os.environ['HTTP_PROXY'] = self.proxy_config['http']
                logger.info(f"Set HTTP_PROXY: {self.proxy_config['http']}")
            
            if 'https' in self.proxy_config:
                os.environ['HTTPS_PROXY'] = self.proxy_config['https']
                logger.info(f"Set HTTPS_PROXY: {self.proxy_config['https']}")
            
            logger.info("Proxy configuration applied")
        else:
            # 清除代理设置
            if 'HTTP_PROXY' in os.environ:
                del os.environ['HTTP_PROXY']
            if 'HTTPS_PROXY' in os.environ:
                del os.environ['HTTPS_PROXY']
            logger.info("No proxy configuration, cleared proxy environment variables")
    
    def get_market_data(
        self,
        date: str,
        market: str = "A"
    ) -> pd.DataFrame:
        """
        获取市场行情数据
        
        Args:
            date: 日期，格式YYYY-MM-DD或YYYYMMDD
            market: 市场类型，默认"A"（A股）
            
        Returns:
            DataFrame: 市场行情数据
            
        Raises:
            Exception: 数据获取失败时抛出异常
        """
        try:
            logger.info(f"Fetching market data from AKShare for date: {date}")
            
            # 转换日期格式
            date_str = date.replace("-", "")
            
            # 获取A股实时行情数据
            data = ak.stock_zh_a_spot_em()
            
            if data is None or data.empty:
                raise Exception(f"No market data returned from AKShare for date: {date}")
            
            logger.info(f"Successfully fetched market data from AKShare, records: {len(data)}")
            return data
            
        except Exception as e:
            logger.error(f"Failed to fetch market data from AKShare: {e}")
            raise
    
    def get_stock_hist(
        self,
        stock_code: str,
        start_date: str,
        end_date: str,
        period: str = "daily",
        adjust: str = "qfq"
    ) -> pd.DataFrame:
        """
        获取个股历史行情数据
        
        Args:
            stock_code: 股票代码
            start_date: 开始日期，格式YYYYMMDD
            end_date: 结束日期，格式YYYYMMDD
            period: 周期，默认"daily"（日线）
            adjust: 复权类型，默认"qfq"（前复权）
            
        Returns:
            DataFrame: 历史行情数据
            
        Raises:
            Exception: 数据获取失败时抛出异常
        """
        try:
            logger.info(f"Fetching stock history from AKShare for {stock_code}, {start_date} to {end_date}")
            
            data = ak.stock_zh_a_hist(
                symbol=stock_code,
                period=period,
                start_date=start_date,
                end_date=end_date,
                adjust=adjust
            )
            
            if data is None or data.empty:
                raise Exception(f"No stock history data returned from AKShare for {stock_code}")
            
            logger.info(f"Successfully fetched stock history from AKShare, records: {len(data)}")
            return data
            
        except Exception as e:
            logger.error(f"Failed to fetch stock history from AKShare: {e}")
            raise
    
    def get_stock_intraday(
        self,
        stock_code: str,
        date: Optional[str] = None
    ) -> pd.DataFrame:
        """
        获取个股分时数据
        
        Args:
            stock_code: 股票代码
            date: 日期，格式YYYY-MM-DD（可选，默认当日）
            
        Returns:
            DataFrame: 分时数据
            
        Raises:
            Exception: 数据获取失败时抛出异常
        """
        try:
            logger.info(f"Fetching stock intraday data from AKShare for {stock_code}")
            
            # AKShare的分时数据接口
            data = ak.stock_intraday_em(symbol=stock_code)
            
            if data is None or data.empty:
                raise Exception(f"No intraday data returned from AKShare for {stock_code}")
            
            logger.info(f"Successfully fetched intraday data from AKShare, records: {len(data)}")
            return data
            
        except Exception as e:
            logger.error(f"Failed to fetch intraday data from AKShare: {e}")
            raise
    
    def get_us_stock_data(
        self,
        symbol: str = "NVDA"
    ) -> Dict[str, Any]:
        """
        获取美股数据
        
        Args:
            symbol: 美股代码，默认"NVDA"
            
        Returns:
            Dict: 美股数据
            
        Raises:
            Exception: 数据获取失败时抛出异常
        """
        try:
            logger.info(f"Fetching US stock data from AKShare for {symbol}")
            
            # 获取美股实时行情
            data = ak.stock_us_spot_em()
            
            if data is None or data.empty:
                raise Exception(f"No US stock data returned from AKShare")
            
            # 筛选指定股票
            stock_data = data[data['代码'] == symbol]
            
            if stock_data.empty:
                raise Exception(f"No data found for US stock: {symbol}")
            
            result = stock_data.iloc[0].to_dict()
            logger.info(f"Successfully fetched US stock data from AKShare for {symbol}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to fetch US stock data from AKShare: {e}")
            raise
    
    def get_index_data(
        self,
        index_code: str = "000001"
    ) -> pd.DataFrame:
        """
        获取指数数据
        
        Args:
            index_code: 指数代码，默认"000001"（上证指数）
            
        Returns:
            DataFrame: 指数数据
            
        Raises:
            Exception: 数据获取失败时抛出异常
        """
        try:
            logger.info(f"Fetching index data from AKShare for {index_code}")
            
            # 获取指数实时行情
            data = ak.stock_zh_index_spot_em()
            
            if data is None or data.empty:
                raise Exception(f"No index data returned from AKShare")
            
            # 筛选指定指数
            index_data = data[data['代码'] == index_code]
            
            if index_data.empty:
                raise Exception(f"No data found for index: {index_code}")
            
            logger.info(f"Successfully fetched index data from AKShare for {index_code}")
            return index_data
            
        except Exception as e:
            logger.error(f"Failed to fetch index data from AKShare: {e}")
            raise
    
    def get_futures_data(
        self,
        symbol: str = "A50"
    ) -> pd.DataFrame:
        """
        获取期货数据
        
        Args:
            symbol: 期货代码，默认"A50"
            
        Returns:
            DataFrame: 期货数据
            
        Raises:
            Exception: 数据获取失败时抛出异常
        """
        try:
            logger.info(f"Fetching futures data from AKShare for {symbol}")
            
            # 获取期货实时行情
            data = ak.futures_foreign_hist(symbol=symbol)
            
            if data is None or data.empty:
                raise Exception(f"No futures data returned from AKShare for {symbol}")
            
            logger.info(f"Successfully fetched futures data from AKShare, records: {len(data)}")
            return data
            
        except Exception as e:
            logger.error(f"Failed to fetch futures data from AKShare: {e}")
            raise
    
    def get_news_headlines(
        self,
        source: str = "sina"
    ) -> pd.DataFrame:
        """
        获取新闻头条
        
        Args:
            source: 新闻源，默认"sina"
            
        Returns:
            DataFrame: 新闻数据
            
        Raises:
            Exception: 数据获取失败时抛出异常
        """
        try:
            logger.info(f"Fetching news headlines from AKShare, source: {source}")
            
            # 获取新浪财经新闻
            data = ak.stock_news_em()
            
            if data is None or data.empty:
                raise Exception(f"No news data returned from AKShare")
            
            logger.info(f"Successfully fetched news headlines from AKShare, records: {len(data)}")
            return data
            
        except Exception as e:
            logger.error(f"Failed to fetch news headlines from AKShare: {e}")
            raise
    
    def get_limit_up_stocks(
        self,
        date: Optional[str] = None
    ) -> pd.DataFrame:
        """
        获取涨停股数据
        
        Args:
            date: 日期，格式YYYY-MM-DD（可选，默认当日）
            
        Returns:
            DataFrame: 涨停股数据
            
        Raises:
            Exception: 数据获取失败时抛出异常
        """
        try:
            logger.info(f"Fetching limit up stocks from AKShare for date: {date}")
            
            # 获取涨停股池
            data = ak.stock_zt_pool_em(date=date.replace("-", "") if date else None)
            
            if data is None or data.empty:
                logger.warning(f"No limit up stocks data returned from AKShare")
                return pd.DataFrame()
            
            logger.info(f"Successfully fetched limit up stocks from AKShare, records: {len(data)}")
            return data
            
        except Exception as e:
            logger.error(f"Failed to fetch limit up stocks from AKShare: {e}")
            raise
    
    def health_check(self) -> bool:
        """
        健康检查
        
        Returns:
            bool: True表示服务正常，False表示服务异常
        """
        try:
            # 尝试获取上证指数数据
            self.get_index_data(index_code="000001")
            logger.info("AKShare health check passed")
            return True
        except Exception as e:
            logger.error(f"AKShare health check failed: {e}")
            return False
