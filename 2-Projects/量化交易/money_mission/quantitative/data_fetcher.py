"""
数据获取模块
支持A股、加密货币、外汇数据获取
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AShareDataFetcher:
    """A股数据获取器（使用baostock或tushare）"""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        # 尝试导入相关库
        try:
            import baostock as bs
            bs.login()
            self.bs = bs
            self.use_baostock = True
        except ImportError:
            self.use_baostock = False
            logger.warning("baostock未安装，尝试使用MCP A-share工具")

    def fetch_stock_data(
        self,
        code: str,
        start_date: str,
        end_date: str,
        frequency: str = 'd'
    ) -> pd.DataFrame:
        """
        获取A股历史数据

        Args:
            code: 股票代码，如 'sh.600000', 'sz.000001'
            start_date: 开始日期 'YYYY-MM-DD'
            end_date: 结束日期 'YYYY-MM-DD'
            frequency: 'd'=日线, 'w'=周线, 'm'=月线

        Returns:
            包含OHLCV的DataFrame
        """
        # 尝试使用MCP A-share工具
        try:
            # 这里需要通过MCP工具调用，演示使用方式
            result = self._fetch_with_mcp(code, start_date, end_date, frequency)
            if result is not None and not result.empty:
                return result
        except Exception as e:
            logger.debug(f"MCP获取失败: {e}")

        # 回退到baostock
        if self.use_baostock:
            return self._fetch_with_baostock(code, start_date, end_date, frequency)

        return pd.DataFrame()

    def _fetch_with_baostock(
        self,
        code: str,
        start_date: str,
        end_date: str,
        frequency: str
    ) -> pd.DataFrame:
        """使用baostock获取数据"""
        freq_map = {'d': 'd', 'w': 'w', 'm': 'm'}
        bs_freq = freq_map.get(frequency, 'd')

        rs = self.bs.query_history_k_data_plus(
            code,
            "date,code,open,high,low,close,volume,amount,adjustflag",
            start_date=start_date,
            end_date=end_date,
            frequency=bs_freq,
            adjustflag="2"  # 前复权
        )

        data_list = []
        while (rs.error_code == '0') & rs.next():
            data_list.append(rs.get_row_data())

        if not data_list:
            return pd.DataFrame()

        df = pd.DataFrame(data_list, columns=[
            'date', 'code', 'open', 'high', 'low', 'close', 'volume', 'amount', 'adjustflag'
        ])

        df['date'] = pd.to_datetime(df['date'])
        df.set_index('date', inplace=True)

        # 转换数值类型
        for col in ['open', 'high', 'low', 'close', 'volume', 'amount']:
            df[col] = pd.to_numeric(df[col], errors='coerce')

        df['symbol'] = code
        return df

    def _fetch_with_mcp(
        self,
        code: str,
        start_date: str,
        end_date: str,
        frequency: str
    ) -> pd.DataFrame:
        """使用MCP A-share工具获取数据"""
        # 注意：这里需要在实际运行时通过MCP工具调用
        # 这是演示代码结构
        logger.info(f"使用MCP获取 {code} 数据: {start_date} to {end_date}")
        return pd.DataFrame()


class CryptoDataFetcher:
    """加密货币数据获取器（支持多个交易所）"""

    def __init__(self, exchange: str = 'binance'):
        self.exchange = exchange
        try:
            import ccxt
            self.exchange_class = getattr(ccxt, exchange)
            self.client = self.exchange_class()
            self.use_ccxt = True
        except ImportError:
            self.use_ccxt = False
            logger.warning("ccxt未安装")

    def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str = '1d',
        since: Optional[int] = None,
        limit: int = 500
    ) -> pd.DataFrame:
        """
        获取K线数据

        Args:
            symbol: 交易对，如 'BTC/USDT'
            timeframe: 时间周期 '1m', '5m', '1h', '1d', '1w'
            since: 时间戳（毫秒）
            limit: 获取数量

        Returns:
            OHLCV数据
        """
        if not self.use_ccxt:
            logger.warning("ccxt未安装，无法获取数据")
            return pd.DataFrame()

        try:
            ohlcv = self.client.fetch_ohlcv(symbol, timeframe, since, limit)

            df = pd.DataFrame(ohlcv, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume'
            ])

            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            df['symbol'] = symbol

            return df
        except Exception as e:
            logger.error(f"获取数据失败: {e}")
            return pd.DataFrame()


class ForexDataFetcher:
    """外汇数据获取器"""

    def __init__(self, provider: str = 'yfinance'):
        self.provider = provider
        try:
            import yfinance as yf
            self.yf = yf
            self.use_yfinance = True
        except ImportError:
            self.use_yfinance = False
            logger.warning("yfinance未安装")

    def fetch_forex_data(
        self,
        pair: str,
        start_date: str,
        end_date: str,
        interval: str = '1d'
    ) -> pd.DataFrame:
        """
        获取外汇数据

        Args:
            pair: 货币对，如 'EURUSD=X', 'USDJPY=X'
            start_date: 开始日期
            end_date: 结束日期
            interval: 时间周期

        Returns:
            OHLCV数据
        """
        if not self.use_yfinance:
            return pd.DataFrame()

        try:
            data = self.yf.download(pair, start=start_date, end=end_date, interval=interval)

            # 重命名列
            data.columns = data.columns.str.lower()
            data['symbol'] = pair

            return data
        except Exception as e:
            logger.error(f"获取外汇数据失败: {e}")
            return pd.DataFrame()


# 热门股票列表
HOT_STOCKS = [
    'sh.600519',  # 贵州茅台
    'sh.600036',  # 招商银行
    'sz.000001',  # 平安银行
    'sz.000858',  # 五粮液
    'sh.600276',  # 恒瑞医药
    'sz.300750',  # 宁德时代
    'sh.600009',  # 上海机场
    'sz.000002',  # 万科A
]

# 热门加密货币
HOT_CRYPTOS = [
    'BTC/USDT',
    'ETH/USDT',
    'BNB/USDT',
    'SOL/USDT',
    'DOGE/USDT',
]

# 热门外汇对
HOT_FOREX = [
    'EURUSD=X',
    'GBPUSD=X',
    'USDJPY=X',
    'AUDUSD=X',
]
