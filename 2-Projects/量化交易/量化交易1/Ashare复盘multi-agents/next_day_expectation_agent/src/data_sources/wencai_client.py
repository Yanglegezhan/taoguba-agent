"""
问财（同花顺）数据客户端

使用 pywencai 包获取同花顺数据，包括热门股排行等。
"""

import pandas as pd
from typing import Optional, List, Dict, Any
from datetime import datetime

try:
    import pywencai
except ImportError:
    pywencai = None

from ..common.logger import get_logger

logger = get_logger(__name__)


class WencaiClient:
    """
    问财数据客户端
    
    使用 pywencai 包获取同花顺数据。
    """
    
    def __init__(self):
        """初始化问财客户端"""
        if pywencai is None:
            logger.warning("pywencai 未安装，请运行: pip install pywencai")
            raise ImportError("pywencai package is not installed")
        
        logger.info("WencaiClient initialized")
    
    def get_hot_stocks(
        self,
        max_rank: int = 50,
        date: Optional[str] = None
    ) -> pd.DataFrame:
        """
        获取同花顺热门股排行
        
        使用问财查询获取热门股数据。查询语句：
        - "热门股票前N" - 获取当前热门股
        - "今日热门股票" - 获取今日热门股（默认前50）
        
        Args:
            max_rank: 最大获取排名数，默认50
            date: 日期（可选），格式YYYY-MM-DD，暂不支持历史日期查询
            
        Returns:
            pd.DataFrame: 热门股数据，包含股票代码、名称、排名等信息
            
        Raises:
            Exception: 数据获取失败时抛出异常
        """
        try:
            logger.info(f"Fetching hot stocks from Wencai (max_rank={max_rank}, date={date})")
            
            # 构建查询语句 - 使用"热门股票前N"可以直接返回DataFrame
            if max_rank <= 50:
                query = f"热门股票前{max_rank}"
            else:
                # 如果需要超过50只，先获取50只再扩展
                query = "今日热门股票"
            
            logger.debug(f"Wencai query: {query}")
            
            # 调用 pywencai 查询
            df = pywencai.get(query=query, loop=True)
            
            # 检查返回类型
            if isinstance(df, dict):
                logger.warning(f"Wencai returned dict instead of DataFrame, keys: {list(df.keys())}")
                return pd.DataFrame()
            
            if df is None or df.empty:
                logger.warning(f"No data returned from Wencai for query: {query}")
                return pd.DataFrame()
            
            # 限制返回数量
            if len(df) > max_rank:
                df = df.head(max_rank)
            
            logger.info(f"Successfully fetched {len(df)} hot stocks from Wencai")
            logger.debug(f"Columns: {df.columns.tolist()}")
            
            return df
            
        except Exception as e:
            logger.error(f"Failed to fetch hot stocks from Wencai: {e}")
            raise
    
    def get_hot_stocks_simple(
        self,
        max_rank: int = 50,
        date: Optional[str] = None
    ) -> pd.Series:
        """
        获取同花顺热门股排行（简化版）
        
        返回格式与 kaipanla_client.get_ths_hot_rank 一致，
        便于替换使用。
        
        Args:
            max_rank: 最大获取排名数，默认50
            date: 日期（可选），格式YYYY-MM-DD
            
        Returns:
            pd.Series: index为排名，values为个股名称
            
        Raises:
            Exception: 数据获取失败时抛出异常
        """
        try:
            # 获取完整数据
            df = self.get_hot_stocks(max_rank=max_rank, date=date)
            
            if df.empty:
                return pd.Series()
            
            # 提取股票名称列
            # 可能的列名：'股票名称', '股票简称', '名称', 'name', '证券简称'
            name_column = None
            for col in ['股票简称', '股票名称', '名称', 'name', '证券简称']:
                if col in df.columns:
                    name_column = col
                    break
            
            if name_column is None:
                logger.error(f"Cannot find stock name column in DataFrame. Columns: {df.columns.tolist()}")
                return pd.Series()
            
            # 提取排名列（如果有）
            rank_column = None
            for col in ['个股热度排名', '排名', '热度排名', '同花顺热度排名', 'rank']:
                if col in df.columns:
                    rank_column = col
                    break
            
            # 构建 Series
            if rank_column:
                # 使用排名作为 index
                result = pd.Series(
                    data=df[name_column].values,
                    index=df[rank_column].values
                )
            else:
                # 使用序号作为 index（从1开始）
                result = pd.Series(
                    data=df[name_column].values,
                    index=range(1, len(df) + 1)
                )
            
            logger.info(f"Converted to simple format: {len(result)} stocks")
            return result
            
        except Exception as e:
            logger.error(f"Failed to get hot stocks in simple format: {e}")
            raise
    
    def get_hot_stocks_with_codes(
        self,
        max_rank: int = 50,
        date: Optional[str] = None
    ) -> pd.DataFrame:
        """
        获取同花顺热门股排行（包含股票代码）
        
        返回包含股票代码和名称的 DataFrame，便于后续处理。
        
        Args:
            max_rank: 最大获取排名数，默认50
            date: 日期（可选），格式YYYY-MM-DD
            
        Returns:
            pd.DataFrame: 包含 'rank', 'code', 'name' 列的数据
            
        Raises:
            Exception: 数据获取失败时抛出异常
        """
        try:
            # 获取完整数据
            df = self.get_hot_stocks(max_rank=max_rank, date=date)
            
            if df.empty:
                return pd.DataFrame(columns=['rank', 'code', 'name'])
            
            # 提取股票代码列
            code_column = None
            for col in ['股票代码', '代码', 'code', 'stock_code', '证券代码']:
                if col in df.columns:
                    code_column = col
                    break
            
            # 提取股票名称列
            name_column = None
            for col in ['股票简称', '股票名称', '名称', 'name', '证券简称']:
                if col in df.columns:
                    name_column = col
                    break
            
            # 提取排名列
            rank_column = None
            for col in ['个股热度排名', '排名', '热度排名', '同花顺热度排名', 'rank']:
                if col in df.columns:
                    rank_column = col
                    break
            
            # 构建结果 DataFrame
            result_data = {}
            
            if rank_column:
                result_data['rank'] = df[rank_column]
            else:
                result_data['rank'] = range(1, len(df) + 1)
            
            if code_column:
                # 清理代码格式（去除.SZ, .SH后缀）
                codes = df[code_column].astype(str)
                codes = codes.str.replace('.SZ', '', regex=False)
                codes = codes.str.replace('.SH', '', regex=False)
                result_data['code'] = codes
            else:
                logger.warning("Cannot find stock code column, using empty strings")
                result_data['code'] = [''] * len(df)
            
            if name_column:
                result_data['name'] = df[name_column]
            else:
                logger.error("Cannot find stock name column")
                return pd.DataFrame(columns=['rank', 'code', 'name'])
            
            result = pd.DataFrame(result_data)
            
            logger.info(f"Converted to DataFrame with codes: {len(result)} stocks")
            return result
            
        except Exception as e:
            logger.error(f"Failed to get hot stocks with codes: {e}")
            raise
