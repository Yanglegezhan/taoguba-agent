"""
东方财富API客户端

提供东方财富数据接口的封装。
"""

import requests
from typing import Optional, Dict, Any, List
import pandas as pd
from datetime import datetime
import json

from ..common.logger import get_logger

logger = get_logger(__name__)


class EastmoneyClient:
    """
    东方财富API客户端
    
    封装东方财富数据接口，提供统一的数据获取方法。
    """
    
    def __init__(self, timeout: int = 30):
        """
        初始化东方财富客户端
        
        Args:
            timeout: 请求超时时间（秒）
        """
        self.timeout = timeout
        self.base_url = "http://push2.eastmoney.com/api/qt"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "http://quote.eastmoney.com/"
        }
        logger.info("EastmoneyClient initialized")
    
    def _request(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        发送HTTP请求
        
        Args:
            url: 请求URL
            params: 请求参数
            
        Returns:
            Dict: 响应数据
            
        Raises:
            Exception: 请求失败时抛出异常
        """
        try:
            response = requests.get(
                url,
                params=params,
                headers=self.headers,
                timeout=self.timeout
            )
            response.raise_for_status()
            
            data = response.json()
            return data
            
        except requests.exceptions.Timeout:
            logger.error(f"Request timeout: {url}")
            raise Exception(f"Request timeout: {url}")
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {e}")
            raise Exception(f"Request failed: {e}")
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            raise Exception(f"Failed to parse JSON response: {e}")
    
    def get_market_data(
        self,
        market: str = "A"
    ) -> pd.DataFrame:
        """
        获取市场行情数据
        
        Args:
            market: 市场类型，默认"A"（A股）
            
        Returns:
            DataFrame: 市场行情数据
            
        Raises:
            Exception: 数据获取失败时抛出异常
        """
        try:
            logger.info(f"Fetching market data from Eastmoney")
            
            url = f"{self.base_url}/clist/get"
            params = {
                "pn": "1",
                "pz": "5000",
                "po": "1",
                "np": "1",
                "fltt": "2",
                "invt": "2",
                "fid": "f3",
                "fs": "m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23",
                "fields": "f1,f2,f3,f4,f5,f6,f7,f8,f9,f10,f12,f13,f14,f15,f16,f17,f18,f20,f21,f23,f24,f25,f22,f11,f62,f128,f136,f115,f152"
            }
            
            data = self._request(url, params)
            
            if not data or 'data' not in data or not data['data']['diff']:
                raise Exception("No market data returned from Eastmoney")
            
            # 转换为DataFrame
            df = pd.DataFrame(data['data']['diff'])
            
            logger.info(f"Successfully fetched market data from Eastmoney, records: {len(df)}")
            return df
            
        except Exception as e:
            logger.error(f"Failed to fetch market data from Eastmoney: {e}")
            raise
    
    def get_stock_info(
        self,
        stock_code: str
    ) -> Dict[str, Any]:
        """
        获取个股信息
        
        Args:
            stock_code: 股票代码
            
        Returns:
            Dict: 个股信息
            
        Raises:
            Exception: 数据获取失败时抛出异常
        """
        try:
            logger.info(f"Fetching stock info from Eastmoney for {stock_code}")
            
            # 判断市场代码
            market_code = "1" if stock_code.startswith("6") else "0"
            secid = f"{market_code}.{stock_code}"
            
            url = f"{self.base_url}/stock/get"
            params = {
                "secid": secid,
                "fields": "f57,f58,f162,f163,f164,f165,f166,f167,f168,f169,f170,f171,f172,f173,f174,f175,f176,f177,f178,f179,f180,f181,f182,f183,f184,f185,f186,f187,f188,f189,f190"
            }
            
            data = self._request(url, params)
            
            if not data or 'data' not in data:
                raise Exception(f"No stock info returned from Eastmoney for {stock_code}")
            
            logger.info(f"Successfully fetched stock info from Eastmoney for {stock_code}")
            return data['data']
            
        except Exception as e:
            logger.error(f"Failed to fetch stock info from Eastmoney: {e}")
            raise
    
    def get_stock_intraday(
        self,
        stock_code: str
    ) -> pd.DataFrame:
        """
        获取个股分时数据
        
        Args:
            stock_code: 股票代码
            
        Returns:
            DataFrame: 分时数据
            
        Raises:
            Exception: 数据获取失败时抛出异常
        """
        try:
            logger.info(f"Fetching stock intraday data from Eastmoney for {stock_code}")
            
            # 判断市场代码
            market_code = "1" if stock_code.startswith("6") else "0"
            secid = f"{market_code}.{stock_code}"
            
            url = f"{self.base_url}/stock/trends2/get"
            params = {
                "secid": secid,
                "fields1": "f1,f2,f3,f4,f5,f6,f7,f8,f9,f10,f11,f12,f13",
                "fields2": "f51,f52,f53,f54,f55,f56,f57,f58",
                "iscr": "0"
            }
            
            data = self._request(url, params)
            
            if not data or 'data' not in data or not data['data']['trends']:
                raise Exception(f"No intraday data returned from Eastmoney for {stock_code}")
            
            # 解析分时数据
            trends = data['data']['trends']
            df = pd.DataFrame([t.split(',') for t in trends])
            
            logger.info(f"Successfully fetched intraday data from Eastmoney, records: {len(df)}")
            return df
            
        except Exception as e:
            logger.error(f"Failed to fetch intraday data from Eastmoney: {e}")
            raise
    
    def get_limit_up_stocks(self) -> pd.DataFrame:
        """
        获取涨停股数据
        
        Returns:
            DataFrame: 涨停股数据
            
        Raises:
            Exception: 数据获取失败时抛出异常
        """
        try:
            logger.info("Fetching limit up stocks from Eastmoney")
            
            url = f"{self.base_url}/clist/get"
            params = {
                "pn": "1",
                "pz": "1000",
                "po": "1",
                "np": "1",
                "fltt": "2",
                "invt": "2",
                "fid": "f3",
                "fs": "m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23",
                "fields": "f1,f2,f3,f4,f5,f6,f7,f8,f9,f10,f12,f13,f14,f15,f16,f17,f18,f20,f21,f23,f24,f25,f22,f11,f62,f128,f136,f115,f152",
                "ut": "fa5fd1943c7b386f172d6893dbfba10b"
            }
            
            data = self._request(url, params)
            
            if not data or 'data' not in data or not data['data']['diff']:
                logger.warning("No limit up stocks data returned from Eastmoney")
                return pd.DataFrame()
            
            # 转换为DataFrame并筛选涨停股
            df = pd.DataFrame(data['data']['diff'])
            
            # f3是涨跌幅字段，筛选涨幅>=9.9%的股票
            if 'f3' in df.columns:
                df['f3'] = pd.to_numeric(df['f3'], errors='coerce')
                limit_up_df = df[df['f3'] >= 9.9]
            else:
                limit_up_df = df
            
            logger.info(f"Successfully fetched limit up stocks from Eastmoney, records: {len(limit_up_df)}")
            return limit_up_df
            
        except Exception as e:
            logger.error(f"Failed to fetch limit up stocks from Eastmoney: {e}")
            raise
    
    def get_sector_data(self) -> pd.DataFrame:
        """
        获取板块数据
        
        Returns:
            DataFrame: 板块数据
            
        Raises:
            Exception: 数据获取失败时抛出异常
        """
        try:
            logger.info("Fetching sector data from Eastmoney")
            
            url = f"{self.base_url}/clist/get"
            params = {
                "pn": "1",
                "pz": "1000",
                "po": "1",
                "np": "1",
                "fltt": "2",
                "invt": "2",
                "fid": "f3",
                "fs": "m:90+t:2",
                "fields": "f1,f2,f3,f4,f5,f6,f7,f8,f9,f10,f12,f13,f14,f15,f16,f17,f18,f20,f21,f23,f24,f25,f22,f11,f62,f128,f136,f115,f152"
            }
            
            data = self._request(url, params)
            
            if not data or 'data' not in data or not data['data']['diff']:
                raise Exception("No sector data returned from Eastmoney")
            
            df = pd.DataFrame(data['data']['diff'])
            
            logger.info(f"Successfully fetched sector data from Eastmoney, records: {len(df)}")
            return df
            
        except Exception as e:
            logger.error(f"Failed to fetch sector data from Eastmoney: {e}")
            raise
    
    def get_news(
        self,
        page: int = 1,
        page_size: int = 20
    ) -> List[Dict[str, Any]]:
        """
        获取新闻数据
        
        Args:
            page: 页码
            page_size: 每页数量
            
        Returns:
            List: 新闻列表
            
        Raises:
            Exception: 数据获取失败时抛出异常
        """
        try:
            logger.info(f"Fetching news from Eastmoney, page: {page}")
            
            url = "https://np-anotice-stock.eastmoney.com/api/security/ann"
            params = {
                "page_size": page_size,
                "page_index": page,
                "ann_type": "A",
                "client_source": "web"
            }
            
            data = self._request(url, params)
            
            if not data or 'data' not in data or not data['data']['list']:
                logger.warning("No news data returned from Eastmoney")
                return []
            
            news_list = data['data']['list']
            logger.info(f"Successfully fetched news from Eastmoney, records: {len(news_list)}")
            return news_list
            
        except Exception as e:
            logger.error(f"Failed to fetch news from Eastmoney: {e}")
            raise
    
    def health_check(self) -> bool:
        """
        健康检查
        
        Returns:
            bool: True表示服务正常，False表示服务异常
        """
        try:
            # 尝试获取市场数据
            self.get_market_data()
            logger.info("Eastmoney health check passed")
            return True
        except Exception as e:
            logger.error(f"Eastmoney health check failed: {e}")
            return False
