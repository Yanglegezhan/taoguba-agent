"""
数据源管理器

提供统一的数据源管理，支持多数据源降级和数据来源记录。
"""

from typing import Optional, Dict, Any, List, Callable
from enum import Enum
import pandas as pd
from datetime import datetime
from .kaipanla_client import KaipanlaClient
from .akshare_client import AKShareClient
from .eastmoney_client import EastmoneyClient

from ..common.logger import get_logger

logger = get_logger(__name__)


class DataSource(Enum):
    """数据源枚举"""
    KAIPANLA = "kaipanla"
    AKSHARE = "akshare"
    EASTMONEY = "eastmoney"


class DataSourceManager:
    """
    数据源管理器
    
    管理多个数据源，支持优先级配置和自动降级。
    """
    
    def __init__(
        self,
        priority: Optional[List[str]] = None,
        akshare_proxy: Optional[Dict[str, str]] = None,
        eastmoney_timeout: int = 30
    ):
        """
        初始化数据源管理器
        
        Args:
            priority: 数据源优先级列表，默认["kaipanla", "akshare", "eastmoney"]
            akshare_proxy: AKShare代理配置
            eastmoney_timeout: 东方财富超时时间
        """
        # 设置默认优先级
        self.priority = priority or ["kaipanla", "akshare", "eastmoney"]
        
        # 初始化数据源客户端
        self.clients = {
            DataSource.KAIPANLA: KaipanlaClient(),
            DataSource.AKSHARE: AKShareClient(proxy_config=akshare_proxy),
            DataSource.EASTMONEY: EastmoneyClient(timeout=eastmoney_timeout)
        }
        
        # 数据来源记录
        self.data_source_log: List[Dict[str, Any]] = []
        
        logger.info(f"DataSourceManager initialized with priority: {self.priority}")
    
    def _get_source_enum(self, source_name: str) -> DataSource:
        """
        将字符串转换为DataSource枚举
        
        Args:
            source_name: 数据源名称字符串
            
        Returns:
            DataSource: 数据源枚举
        """
        source_map = {
            "kaipanla": DataSource.KAIPANLA,
            "akshare": DataSource.AKSHARE,
            "eastmoney": DataSource.EASTMONEY
        }
        return source_map.get(source_name.lower())
    
    def _log_data_source(
        self,
        data_type: str,
        source: DataSource,
        success: bool,
        error: Optional[str] = None
    ) -> None:
        """
        记录数据来源
        
        Args:
            data_type: 数据类型
            source: 数据源
            success: 是否成功
            error: 错误信息（可选）
        """
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "data_type": data_type,
            "source": source.value,
            "success": success,
            "error": error
        }
        self.data_source_log.append(log_entry)
        
        if success:
            logger.info(f"Data fetched successfully from {source.value} for {data_type}")
        else:
            logger.warning(f"Failed to fetch data from {source.value} for {data_type}: {error}")
    
    def _fetch_with_fallback(
        self,
        data_type: str,
        fetch_func: Callable[[DataSource], Any],
        sources: Optional[List[str]] = None
    ) -> tuple[Any, DataSource]:
        """
        使用降级策略获取数据
        
        Args:
            data_type: 数据类型
            fetch_func: 获取数据的函数，接收DataSource参数
            sources: 数据源列表（可选，默认使用self.priority）
            
        Returns:
            tuple: (数据, 数据源)
            
        Raises:
            Exception: 所有数据源都失败时抛出异常
        """
        sources = sources or self.priority
        last_error = None
        
        for source_name in sources:
            source = self._get_source_enum(source_name)
            if source is None:
                logger.warning(f"Unknown data source: {source_name}, skipping")
                continue
            
            try:
                logger.info(f"Trying to fetch {data_type} from {source.value}")
                data = fetch_func(source)
                self._log_data_source(data_type, source, success=True)
                return data, source
                
            except Exception as e:
                last_error = str(e)
                self._log_data_source(data_type, source, success=False, error=last_error)
                logger.warning(f"Failed to fetch {data_type} from {source.value}: {e}")
                continue
        
        # 所有数据源都失败
        error_msg = f"All data sources failed for {data_type}. Last error: {last_error}"
        logger.error(error_msg)
        raise Exception(error_msg)
    
    def get_market_data(
        self,
        date: str,
        start_date: Optional[str] = None
    ) -> tuple[pd.DataFrame, DataSource]:
        """
        获取市场行情数据（支持降级）
        
        Args:
            date: 结束日期，格式YYYY-MM-DD
            start_date: 开始日期，格式YYYY-MM-DD（可选）
            
        Returns:
            tuple: (DataFrame, 数据源)
            
        Raises:
            Exception: 所有数据源都失败时抛出异常
        """
        def fetch(source: DataSource) -> pd.DataFrame:
            client = self.clients[source]
            if source == DataSource.KAIPANLA:
                return client.get_market_data(date=date, start_date=start_date)
            elif source == DataSource.AKSHARE:
                return client.get_market_data(date=date)
            elif source == DataSource.EASTMONEY:
                return client.get_market_data()
            else:
                raise Exception(f"Unsupported data source: {source}")
        
        return self._fetch_with_fallback("market_data", fetch)
    
    def get_auction_data(
        self,
        stock_code: str,
        date: Optional[str] = None
    ) -> tuple[pd.DataFrame, DataSource]:
        """
        获取个股竞价数据（支持降级）
        
        Args:
            stock_code: 股票代码
            date: 日期，格式YYYY-MM-DD（可选）
            
        Returns:
            tuple: (DataFrame, 数据源)
            
        Raises:
            Exception: 所有数据源都失败时抛出异常
        """
        def fetch(source: DataSource) -> pd.DataFrame:
            client = self.clients[source]
            if source == DataSource.KAIPANLA:
                return client.get_auction_data(stock_code=stock_code, date=date)
            elif source == DataSource.AKSHARE:
                return client.get_stock_intraday(stock_code=stock_code, date=date)
            elif source == DataSource.EASTMONEY:
                return client.get_stock_intraday(stock_code=stock_code)
            else:
                raise Exception(f"Unsupported data source: {source}")
        
        return self._fetch_with_fallback("auction_data", fetch)
    
    def get_limit_up_stocks(
        self,
        date: str
    ) -> tuple[pd.DataFrame, DataSource]:
        """
        获取涨停股数据（支持降级）
        
        Args:
            date: 日期，格式YYYY-MM-DD
            
        Returns:
            tuple: (DataFrame, 数据源)
            
        Raises:
            Exception: 所有数据源都失败时抛出异常
        """
        def fetch(source: DataSource) -> pd.DataFrame:
            client = self.clients[source]
            if source == DataSource.KAIPANLA:
                return client.get_limit_up_stocks(date=date)
            elif source == DataSource.AKSHARE:
                return client.get_limit_up_stocks(date=date)
            elif source == DataSource.EASTMONEY:
                return client.get_limit_up_stocks()
            else:
                raise Exception(f"Unsupported data source: {source}")
        
        return self._fetch_with_fallback("limit_up_stocks", fetch)
    
    def get_us_stock_data(
        self,
        symbol: str = "NVDA"
    ) -> tuple[Dict[str, Any], DataSource]:
        """
        获取美股数据（支持降级）
        
        Args:
            symbol: 美股代码
            
        Returns:
            tuple: (Dict, 数据源)
            
        Raises:
            Exception: 所有数据源都失败时抛出异常
        """
        def fetch(source: DataSource) -> Dict[str, Any]:
            client = self.clients[source]
            if source == DataSource.AKSHARE:
                return client.get_us_stock_data(symbol=symbol)
            else:
                raise Exception(f"US stock data not supported by {source.value}")
        
        # 只有AKShare支持美股数据
        return self._fetch_with_fallback("us_stock_data", fetch, sources=["akshare"])
    
    def get_futures_data(
        self,
        symbol: str = "A50"
    ) -> tuple[pd.DataFrame, DataSource]:
        """
        获取期货数据（支持降级）
        
        Args:
            symbol: 期货代码
            
        Returns:
            tuple: (DataFrame, 数据源)
            
        Raises:
            Exception: 所有数据源都失败时抛出异常
        """
        def fetch(source: DataSource) -> pd.DataFrame:
            client = self.clients[source]
            if source == DataSource.AKSHARE:
                return client.get_futures_data(symbol=symbol)
            else:
                raise Exception(f"Futures data not supported by {source.value}")
        
        # 只有AKShare支持期货数据
        return self._fetch_with_fallback("futures_data", fetch, sources=["akshare"])
    
    def get_news_headlines(self) -> tuple[pd.DataFrame, DataSource]:
        """
        获取新闻头条（支持降级）
        
        Returns:
            tuple: (DataFrame, 数据源)
            
        Raises:
            Exception: 所有数据源都失败时抛出异常
        """
        def fetch(source: DataSource) -> pd.DataFrame:
            client = self.clients[source]
            if source == DataSource.AKSHARE:
                return client.get_news_headlines()
            elif source == DataSource.EASTMONEY:
                news_list = client.get_news()
                return pd.DataFrame(news_list)
            else:
                raise Exception(f"News data not supported by {source.value}")
        
        # AKShare和Eastmoney支持新闻数据
        return self._fetch_with_fallback("news_headlines", fetch, sources=["akshare", "eastmoney"])
    
    def get_sector_data(self) -> tuple[pd.DataFrame, DataSource]:
        """
        获取板块数据（支持降级）
        
        Returns:
            tuple: (DataFrame, 数据源)
            
        Raises:
            Exception: 所有数据源都失败时抛出异常
        """
        def fetch(source: DataSource) -> pd.DataFrame:
            client = self.clients[source]
            if source == DataSource.EASTMONEY:
                return client.get_sector_data()
            else:
                raise Exception(f"Sector data not supported by {source.value}")
        
        # 只有Eastmoney支持板块数据
        return self._fetch_with_fallback("sector_data", fetch, sources=["eastmoney"])
    
    def health_check_all(self) -> Dict[str, bool]:
        """
        检查所有数据源的健康状态
        
        Returns:
            Dict: 数据源健康状态字典
        """
        health_status = {}
        
        for source, client in self.clients.items():
            try:
                status = client.health_check()
                health_status[source.value] = status
            except Exception as e:
                logger.error(f"Health check failed for {source.value}: {e}")
                health_status[source.value] = False
        
        logger.info(f"Health check results: {health_status}")
        return health_status
    
    def get_data_source_log(
        self,
        data_type: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        获取数据来源日志
        
        Args:
            data_type: 数据类型过滤（可选）
            limit: 返回记录数限制
            
        Returns:
            List: 数据来源日志列表
        """
        if data_type:
            filtered_log = [
                entry for entry in self.data_source_log
                if entry['data_type'] == data_type
            ]
        else:
            filtered_log = self.data_source_log
        
        # 返回最近的记录
        return filtered_log[-limit:]
    
    def clear_data_source_log(self) -> None:
        """清空数据来源日志"""
        self.data_source_log.clear()
        logger.info("Data source log cleared")
