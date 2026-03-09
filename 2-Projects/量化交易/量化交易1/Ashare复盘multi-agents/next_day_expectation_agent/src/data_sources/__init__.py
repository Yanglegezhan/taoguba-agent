"""
数据源集成层

提供统一的数据源接口，支持多数据源降级和代理配置。
"""

from .kaipanla_client import KaipanlaClient
from .akshare_client import AKShareClient
from .eastmoney_client import EastmoneyClient
from .data_source_manager import DataSourceManager

__all__ = [
    'KaipanlaClient',
    'AKShareClient',
    'EastmoneyClient',
    'DataSourceManager',
]
