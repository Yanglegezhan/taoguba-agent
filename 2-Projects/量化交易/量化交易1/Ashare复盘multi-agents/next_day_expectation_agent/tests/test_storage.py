"""
存储层测试

测试FileStorageManager和DatabaseManager的基本功能
"""

import pytest
import os
import tempfile
import shutil
from pathlib import Path
from datetime import datetime

from src.storage import FileStorageManager, DatabaseManager
from src.common.models import (
    Stock, TechnicalLevels, GenePool, BaselineExpectation,
    AuctionData, ExpectationScore, StatusScore, AdditionalPool
)


class TestFileStorageManager:
    """测试文件存储管理器"""
    
    @pytest.fixture
    def temp_dir(self):
        """创建临时目录"""
        temp_path = tempfile.mkdtemp()
        yield temp_path
        shutil.rmtree(temp_path)
    
    @pytest.fixture
    def storage_manager(self, temp_dir):
        """创建存储管理器实例"""
        return FileStorageManager(base_dir=temp_dir)
    
    @pytest.fixture
    def sample_stock(self):
        """创建示例股票数据"""
        technical_levels = TechnicalLevels(
            ma5=14.2,
            ma10=13.1,
            ma20=12.5,
            previous_high=16.8,
            chip_zone_low=13.0,
            chip_zone_high=14.5,
            distance_to_ma5_pct=10.4,
            distance_to_high_pct=-6.7
        )
        
        return Stock(
            code='002810',
            name='韩建河山',
            market_cap=45.2,
            price=15.68,
            change_pct=10.0,
            volume=1250000,
            amount=19600,
            turnover_rate=4.2,
            board_height=5,
            themes=['AI', '数字经济'],
            technical_levels=technical_levels
        )
    
    @pytest.fixture
    def sample_gene_pool(self, sample_stock):
        """创建示例基因池"""
        return GenePool(
            date='20250213',
            continuous_limit_up=[sample_stock],
            failed_limit_up=[],
            recognition_stocks=[],
            trend_stocks=[],
            all_stocks={'002810': sample_stock}
        )
    
    def test_directory_structure_creation(self, storage_manager, temp_dir):
        """测试目录结构创建"""
        expected_dirs = [
            'config',
            'stage1_output',
            'stage2_output',
            'stage3_output',
            'historical',
            'logs'
        ]
        
        for dir_name in expected_dirs:
            dir_path = Path(temp_dir) / dir_name
            assert dir_path.exists(), f"Directory {dir_name} should exist"
            assert dir_path.is_dir(), f"{dir_name} should be a directory"
    
    def test_get_file_path(self, storage_manager):
        """测试文件路径获取"""
        # 测试基因池文件路径
        path = storage_manager.get_file_path('gene_pool', '20250213')
        assert 'stage1_output' in str(path)
        assert 'gene_pool_20250213.json' in str(path)
        
        # 测试基准预期文件路径
        path = storage_manager.get_file_path('baseline_expectation', '20250213')
        assert 'stage2_output' in str(path)
        assert 'baseline_expectation_20250213.json' in str(path)
        
        # 测试决策导航文件路径
        path = storage_manager.get_file_path('decision_navigation', '20250213')
        assert 'stage3_output' in str(path)
        assert 'decision_navigation_20250213.json' in str(path)
    
    def test_save_and_load_gene_pool(self, storage_manager, sample_gene_pool):
        """测试基因池保存和加载"""
        # 保存
        filepath = storage_manager.save_gene_pool(sample_gene_pool)
        assert os.path.exists(filepath)
        
        # 加载
        loaded_pool = storage_manager.load_gene_pool('20250213')
        assert loaded_pool.date == sample_gene_pool.date
        assert len(loaded_pool.continuous_limit_up) == 1
        assert loaded_pool.continuous_limit_up[0].code == '002810'
        assert loaded_pool.continuous_limit_up[0].name == '韩建河山'
    
    def test_save_and_load_baseline_expectations(self, storage_manager):
        """测试基准预期保存和加载"""
        expectations = {
            '002810': BaselineExpectation(
                stock_code='002810',
                stock_name='韩建河山',
                expected_open_min=5.0,
                expected_open_max=8.0,
                expected_amount_min=15000,
                logic='5连板+题材主升期',
                confidence=0.85
            )
        }
        
        # 保存
        filepath = storage_manager.save_baseline_expectations(expectations, '20250213')
        assert os.path.exists(filepath)
        
        # 加载
        loaded_expectations = storage_manager.load_baseline_expectations('20250213')
        assert '002810' in loaded_expectations
        assert loaded_expectations['002810'].expected_open_min == 5.0
        assert loaded_expectations['002810'].confidence == 0.85
    
    def test_file_exists(self, storage_manager, sample_gene_pool):
        """测试文件存在性检查"""
        # 文件不存在
        assert not storage_manager.file_exists('gene_pool', '20250213')
        
        # 保存文件
        storage_manager.save_gene_pool(sample_gene_pool)
        
        # 文件存在
        assert storage_manager.file_exists('gene_pool', '20250213')
    
    def test_list_files(self, storage_manager, sample_gene_pool):
        """测试文件列表"""
        # 保存多个文件
        gene_pool1 = sample_gene_pool
        storage_manager.save_gene_pool(gene_pool1)
        
        gene_pool2 = GenePool(
            date='20250214',
            continuous_limit_up=[],
            failed_limit_up=[],
            recognition_stocks=[],
            trend_stocks=[],
            all_stocks={}
        )
        storage_manager.save_gene_pool(gene_pool2)
        
        # 列出文件
        files = storage_manager.list_files('gene_pool')
        assert len(files) == 2
        assert any('20250213' in f for f in files)
        assert any('20250214' in f for f in files)
    
    def test_get_storage_stats(self, storage_manager, sample_gene_pool):
        """测试存储统计"""
        # 保存一些文件
        storage_manager.save_gene_pool(sample_gene_pool)
        
        # 获取统计
        stats = storage_manager.get_storage_stats()
        assert 'base_dir' in stats
        assert 'total_size_mb' in stats
        assert 'stages' in stats
        assert 'stage1_output' in stats['stages']


class TestDatabaseManager:
    """测试数据库管理器"""
    
    @pytest.fixture
    def temp_db(self):
        """创建临时数据库"""
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        temp_file.close()
        yield temp_file.name
        if os.path.exists(temp_file.name):
            os.unlink(temp_file.name)
    
    @pytest.fixture
    def db_manager(self, temp_db):
        """创建数据库管理器实例"""
        manager = DatabaseManager(db_path=temp_db)
        yield manager
        manager.close()
    
    @pytest.fixture
    def sample_stock(self):
        """创建示例股票数据"""
        technical_levels = TechnicalLevels(
            ma5=14.2,
            ma10=13.1,
            ma20=12.5,
            previous_high=16.8,
            chip_zone_low=13.0,
            chip_zone_high=14.5,
            distance_to_ma5_pct=10.4,
            distance_to_high_pct=-6.7
        )
        
        return Stock(
            code='002810',
            name='韩建河山',
            market_cap=45.2,
            price=15.68,
            change_pct=10.0,
            volume=1250000,
            amount=19600,
            turnover_rate=4.2,
            board_height=5,
            themes=['AI', '数字经济'],
            technical_levels=technical_levels
        )
    
    @pytest.fixture
    def sample_gene_pool(self, sample_stock):
        """创建示例基因池"""
        return GenePool(
            date='20250213',
            continuous_limit_up=[sample_stock],
            failed_limit_up=[],
            recognition_stocks=[],
            trend_stocks=[],
            all_stocks={'002810': sample_stock}
        )
    
    def test_database_initialization(self, db_manager, temp_db):
        """测试数据库初始化"""
        assert os.path.exists(temp_db)
        
        # 检查表是否创建
        conn = db_manager._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        expected_tables = [
            'gene_pool_history',
            'baseline_expectation_history',
            'auction_monitoring_history',
            'additional_pool_history'
        ]
        
        for table in expected_tables:
            assert table in tables, f"Table {table} should exist"
    
    def test_insert_and_query_gene_pool(self, db_manager, sample_gene_pool):
        """测试基因池插入和查询"""
        # 插入
        count = db_manager.insert_gene_pool(sample_gene_pool)
        assert count == 1
        
        # 查询
        results = db_manager.query_gene_pool(date='20250213')
        assert len(results) == 1
        assert results[0]['stock_code'] == '002810'
        assert results[0]['stock_name'] == '韩建河山'
        assert results[0]['category'] == 'continuous_limit_up'
    
    def test_insert_and_query_baseline_expectations(self, db_manager):
        """测试基准预期插入和查询"""
        expectations = {
            '002810': BaselineExpectation(
                stock_code='002810',
                stock_name='韩建河山',
                expected_open_min=5.0,
                expected_open_max=8.0,
                expected_amount_min=15000,
                logic='5连板+题材主升期',
                confidence=0.85
            )
        }
        
        # 插入
        count = db_manager.insert_baseline_expectations(expectations, '20250213')
        assert count == 1
        
        # 查询
        results = db_manager.query_baseline_expectations(date='20250213')
        assert len(results) == 1
        assert results[0]['stock_code'] == '002810'
        assert results[0]['expected_open_min'] == 5.0
    
    def test_insert_and_query_auction_monitoring(self, db_manager):
        """测试竞价监测插入和查询"""
        auction_data = AuctionData(
            stock_code='002810',
            auction_low_price=15.0,
            auction_high_price=17.0,
            open_price=16.5,
            auction_volume=1000000,
            auction_amount=16500,
            seal_amount=5000,
            withdrawal_detected=False,
            trajectory_rating='强'
        )
        
        expectation_score = ExpectationScore(
            stock_code='002810',
            volume_score=85.0,
            price_score=90.0,
            independence_score=75.0,
            total_score=85.0,
            rating='优秀',
            recommendation='打板',
            confidence=0.9
        )
        
        # 插入
        count = db_manager.insert_auction_monitoring(
            '20250213', '002810', '韩建河山',
            auction_data, expectation_score
        )
        assert count == 1
        
        # 查询
        results = db_manager.query_auction_monitoring(date='20250213')
        assert len(results) == 1
        assert results[0]['stock_code'] == '002810'
        assert results[0]['expectation_score'] == 85.0
        assert results[0]['recommendation'] == '打板'
    
    def test_get_database_stats(self, db_manager, sample_gene_pool):
        """测试数据库统计"""
        # 插入一些数据
        db_manager.insert_gene_pool(sample_gene_pool)
        
        # 获取统计
        stats = db_manager.get_database_stats()
        assert 'db_path' in stats
        assert 'db_size_mb' in stats
        assert 'tables' in stats
        assert 'gene_pool_history' in stats['tables']
        assert stats['tables']['gene_pool_history']['record_count'] == 1


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
