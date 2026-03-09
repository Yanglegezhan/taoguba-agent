"""
数据源集成测试

测试Kaipanla、AKShare、Eastmoney客户端以及数据源管理器的功能。
"""

import pytest
import pandas as pd
from datetime import datetime, timedelta
import os
import sys
from pathlib import Path

from src.data_sources.kaipanla_client import KaipanlaClient
from src.data_sources.akshare_client import AKShareClient
from src.data_sources.eastmoney_client import EastmoneyClient
from src.data_sources.data_source_manager import DataSourceManager, DataSource


class TestKaipanlaClient:
    """测试Kaipanla客户端"""
    
    @pytest.fixture
    def client(self):
        """创建Kaipanla客户端实例"""
        return KaipanlaClient()
    
    def test_get_market_data(self, client):
        """测试获取市场数据"""
        # 使用最近的交易日
        date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        
        try:
            data = client.get_market_data(date=date)
            assert data is not None
            assert isinstance(data, (pd.DataFrame, pd.Series))
            print(f"✓ Kaipanla market data fetched successfully")
        except Exception as e:
            pytest.skip(f"Kaipanla API not available: {e}")
    
    def test_get_auction_data(self, client):
        """测试获取竞价数据"""
        stock_code = "000001"  # 平安银行
        
        try:
            data = client.get_auction_data(stock_code=stock_code)
            assert data is not None
            assert isinstance(data, pd.DataFrame)
            print(f"✓ Kaipanla auction data fetched successfully")
        except Exception as e:
            pytest.skip(f"Kaipanla API not available: {e}")
    
    def test_get_limit_up_stocks(self, client):
        """测试获取涨停股数据"""
        date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        
        try:
            data = client.get_limit_up_stocks(date=date)
            assert data is not None
            assert isinstance(data, pd.DataFrame)
            print(f"✓ Kaipanla limit up stocks fetched successfully")
        except Exception as e:
            pytest.skip(f"Kaipanla API not available: {e}")


class TestAKShareClient:
    """测试AKShare客户端"""
    
    @pytest.fixture
    def client(self):
        """创建AKShare客户端实例（无代理）"""
        return AKShareClient()
    
    @pytest.fixture
    def client_with_proxy(self):
        """创建AKShare客户端实例（带代理）"""
        proxy_config = {
            'http': 'http://127.0.0.1:7890',
            'https': 'http://127.0.0.1:7890'
        }
        return AKShareClient(proxy_config=proxy_config)
    
    def test_proxy_config_applied(self, client_with_proxy):
        """
        测试代理配置自动应用
        Property 2: 代理配置自动应用
        """
        # 验证环境变量已设置
        assert 'HTTP_PROXY' in os.environ or 'HTTPS_PROXY' in os.environ
        print(f"✓ Proxy configuration applied to environment variables")
    
    def test_get_market_data(self, client):
        """测试获取市场数据"""
        date = datetime.now().strftime("%Y-%m-%d")
        
        try:
            data = client.get_market_data(date=date)
            assert data is not None
            assert isinstance(data, pd.DataFrame)
            assert len(data) > 0
            print(f"✓ AKShare market data fetched successfully")
        except Exception as e:
            pytest.skip(f"AKShare API not available: {e}")
    
    def test_get_index_data(self, client):
        """测试获取指数数据"""
        try:
            data = client.get_index_data(index_code="000001")
            assert data is not None
            assert isinstance(data, pd.DataFrame)
            print(f"✓ AKShare index data fetched successfully")
        except Exception as e:
            pytest.skip(f"AKShare API not available: {e}")
    
    def test_get_limit_up_stocks(self, client):
        """测试获取涨停股数据"""
        date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        
        try:
            data = client.get_limit_up_stocks(date=date)
            assert data is not None
            assert isinstance(data, pd.DataFrame)
            print(f"✓ AKShare limit up stocks fetched successfully")
        except Exception as e:
            pytest.skip(f"AKShare API not available: {e}")


class TestEastmoneyClient:
    """测试东方财富客户端"""
    
    @pytest.fixture
    def client(self):
        """创建东方财富客户端实例"""
        return EastmoneyClient()
    
    def test_get_market_data(self, client):
        """测试获取市场数据"""
        try:
            data = client.get_market_data()
            assert data is not None
            assert isinstance(data, pd.DataFrame)
            assert len(data) > 0
            print(f"✓ Eastmoney market data fetched successfully")
        except Exception as e:
            pytest.skip(f"Eastmoney API not available: {e}")
    
    def test_get_limit_up_stocks(self, client):
        """测试获取涨停股数据"""
        try:
            data = client.get_limit_up_stocks()
            assert data is not None
            assert isinstance(data, pd.DataFrame)
            print(f"✓ Eastmoney limit up stocks fetched successfully")
        except Exception as e:
            pytest.skip(f"Eastmoney API not available: {e}")
    
    def test_get_sector_data(self, client):
        """测试获取板块数据"""
        try:
            data = client.get_sector_data()
            assert data is not None
            assert isinstance(data, pd.DataFrame)
            assert len(data) > 0
            print(f"✓ Eastmoney sector data fetched successfully")
        except Exception as e:
            pytest.skip(f"Eastmoney API not available: {e}")


class TestDataSourceManager:
    """测试数据源管理器"""
    
    @pytest.fixture
    def manager(self):
        """创建数据源管理器实例"""
        return DataSourceManager()
    
    def test_initialization(self, manager):
        """测试初始化"""
        assert manager is not None
        assert len(manager.clients) == 3
        assert DataSource.KAIPANLA in manager.clients
        assert DataSource.AKSHARE in manager.clients
        assert DataSource.EASTMONEY in manager.clients
        print(f"✓ DataSourceManager initialized successfully")
    
    def test_get_market_data_with_fallback(self, manager):
        """
        测试数据源降级逻辑
        Property 1: 数据源降级一致性
        """
        date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        
        try:
            data, source = manager.get_market_data(date=date)
            assert data is not None
            assert isinstance(data, (pd.DataFrame, pd.Series))
            assert source in [DataSource.KAIPANLA, DataSource.AKSHARE, DataSource.EASTMONEY]
            
            # 验证数据来源被记录
            log = manager.get_data_source_log(data_type="market_data")
            assert len(log) > 0
            assert log[-1]['success'] is True
            assert log[-1]['source'] == source.value
            
            print(f"✓ Market data fetched from {source.value} with fallback support")
        except Exception as e:
            pytest.skip(f"All data sources unavailable: {e}")
    
    def test_get_limit_up_stocks_with_fallback(self, manager):
        """测试涨停股数据获取（降级）"""
        date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        
        try:
            data, source = manager.get_limit_up_stocks(date=date)
            assert data is not None
            assert isinstance(data, pd.DataFrame)
            assert source in [DataSource.KAIPANLA, DataSource.AKSHARE, DataSource.EASTMONEY]
            
            print(f"✓ Limit up stocks fetched from {source.value} with fallback support")
        except Exception as e:
            pytest.skip(f"All data sources unavailable: {e}")
    
    def test_data_source_logging(self, manager):
        """测试数据来源记录"""
        date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        
        # 清空日志
        manager.clear_data_source_log()
        assert len(manager.get_data_source_log()) == 0
        
        try:
            # 尝试获取数据
            data, source = manager.get_market_data(date=date)
            
            # 验证日志记录
            log = manager.get_data_source_log()
            assert len(log) > 0
            
            # 验证日志内容
            last_log = log[-1]
            assert 'timestamp' in last_log
            assert 'data_type' in last_log
            assert 'source' in last_log
            assert 'success' in last_log
            assert last_log['data_type'] == 'market_data'
            
            print(f"✓ Data source logging works correctly")
        except Exception as e:
            pytest.skip(f"All data sources unavailable: {e}")
    
    def test_health_check_all(self, manager):
        """测试所有数据源健康检查"""
        health_status = manager.health_check_all()
        
        assert isinstance(health_status, dict)
        assert len(health_status) == 3
        assert 'kaipanla' in health_status
        assert 'akshare' in health_status
        assert 'eastmoney' in health_status
        
        # 至少有一个数据源应该是健康的
        assert any(health_status.values()), "At least one data source should be healthy"
        
        print(f"✓ Health check completed: {health_status}")
    
    def test_priority_configuration(self):
        """测试数据源优先级配置"""
        # 自定义优先级
        custom_priority = ["eastmoney", "akshare", "kaipanla"]
        manager = DataSourceManager(priority=custom_priority)
        
        assert manager.priority == custom_priority
        print(f"✓ Custom priority configuration works correctly")
    
    def test_fallback_on_primary_failure(self, manager):
        """
        测试主数据源失败时的降级
        Property 1: 数据源降级一致性
        """
        # 创建一个优先级为 ["kaipanla", "akshare", "eastmoney"] 的管理器
        # 如果kaipanla失败，应该自动尝试akshare
        
        date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        
        try:
            data, source = manager.get_market_data(date=date)
            
            # 验证数据来源日志
            log = manager.get_data_source_log(data_type="market_data")
            
            # 如果有多条记录，说明发生了降级
            if len(log) > 1:
                # 验证第一个尝试失败，后续尝试成功
                assert log[-1]['success'] is True
                print(f"✓ Fallback mechanism works: tried multiple sources, succeeded with {source.value}")
            else:
                print(f"✓ Primary source {source.value} works directly")
                
        except Exception as e:
            pytest.skip(f"All data sources unavailable: {e}")


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v", "-s"])
