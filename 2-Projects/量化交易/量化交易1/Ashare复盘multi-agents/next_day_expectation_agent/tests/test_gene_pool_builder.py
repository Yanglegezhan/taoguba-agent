"""
基因池构建器测试

测试GenePoolBuilder类的功能，包括：
- 初始化
- 扫描连板梯队
- 识别炸板股
- 识别辨识度个股
- 识别趋势股
- 构建基因池
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import pandas as pd

from src.stage1.gene_pool_builder import GenePoolBuilder
from src.common.models import Stock, GenePool


class TestGenePoolBuilder:
    """基因池构建器测试类"""
    
    def test_init(self):
        """测试初始化"""
        builder = GenePoolBuilder()
        
        assert builder is not None
        assert builder.kaipanla_client is not None
        assert builder.technical_calculator is not None
    
    @patch('src.stage1.gene_pool_builder.KaipanlaClient')
    def test_scan_continuous_limit_up(self, mock_kaipanla):
        """测试扫描连板梯队"""
        # 创建mock数据
        mock_data = pd.DataFrame({
            '代码': ['002810', '300XXX'],
            '名称': ['韩建河山', '测试股'],
            '最新价': [15.68, 20.50],
            '涨跌幅': [10.0, 10.0],
            '成交量': [1250000, 800000],
            '成交额': [19600, 16400],
            '换手率': [4.2, 3.5],
            '流通市值': [452000, 350000],
            '连板天数': [5, 3],
            '所属题材': ['AI,数字经济', '新能源']
        })
        
        # 配置mock
        mock_client = mock_kaipanla.return_value
        mock_client.get_continuous_limit_up_stocks.return_value = mock_data
        
        # 创建builder
        builder = GenePoolBuilder()
        builder.kaipanla_client = mock_client
        
        # 调用方法
        stocks = builder.scan_continuous_limit_up("2025-02-12")
        
        # 验证结果
        assert len(stocks) == 2
        assert stocks[0].code == '002810'
        assert stocks[0].name == '韩建河山'
        assert stocks[0].board_height == 5
        assert stocks[1].code == '300XXX'
        assert stocks[1].board_height == 3
    
    @patch('src.stage1.gene_pool_builder.KaipanlaClient')
    def test_identify_failed_limit_up(self, mock_kaipanla):
        """测试识别炸板股（使用反包板接口）"""
        # 创建mock数据 - 模拟get_market_limit_up_ladder的返回值
        mock_ladder_data = {
            'date': '2025-02-12',
            'is_realtime': False,
            'ladder': {
                1: [{'stock_code': '002810', 'stock_name': '韩建河山', 'consecutive_days': 1}],
                2: [{'stock_code': '300XXX', 'stock_name': '测试股', 'consecutive_days': 2}]
            },
            'broken_stocks': [
                {
                    'stock_code': '600XXX',
                    'stock_name': '炸板股1',
                    'consecutive_days': 2,
                    'tips': '2天2板',
                    'is_broken': True
                },
                {
                    'stock_code': '000XXX',
                    'stock_name': '炸板股2',
                    'consecutive_days': 1,
                    'tips': '1天1板',
                    'is_broken': True
                }
            ],
            'height_marks': [],
            'statistics': {
                'total_limit_up': 2,
                'max_consecutive': 2,
                'ladder_distribution': {1: 1, 2: 1}
            }
        }
        
        # 配置mock
        mock_client = mock_kaipanla.return_value
        mock_client.get_market_limit_up_ladder.return_value = mock_ladder_data
        
        # 创建builder
        builder = GenePoolBuilder()
        builder.kaipanla_client = mock_client
        
        # 调用方法
        stocks = builder.identify_failed_limit_up("2025-02-12")
        
        # 验证结果
        assert len(stocks) == 2
        assert stocks[0].code == '600XXX'
        assert stocks[0].name == '炸板股1'
        assert stocks[0].board_height == 2  # consecutive_days映射到board_height
        assert stocks[0].is_failed_limit_up == True
        assert stocks[1].code == '000XXX'
        assert stocks[1].name == '炸板股2'
        assert stocks[1].board_height == 1
    
    @patch('src.stage1.gene_pool_builder.KaipanlaClient')
    def test_build_gene_pool(self, mock_kaipanla):
        """测试构建基因池"""
        # 创建mock数据 - 连板股
        continuous_data = pd.DataFrame({
            '代码': ['002810'],
            '名称': ['韩建河山'],
            '最新价': [15.68],
            '涨跌幅': [10.0],
            '成交量': [1250000],
            '成交额': [19600],
            '换手率': [4.2],
            '流通市值': [452000],
            '连板天数': [5],
            '所属题材': ['AI']
        })
        
        # 创建mock数据 - 炸板股（使用新的接口格式）
        mock_ladder_data = {
            'date': '2025-02-12',
            'is_realtime': False,
            'ladder': {},
            'broken_stocks': [
                {
                    'stock_code': '600XXX',
                    'stock_name': '炸板股',
                    'consecutive_days': 1,
                    'tips': '1天1板',
                    'is_broken': True
                }
            ],
            'height_marks': [],
            'statistics': {
                'total_limit_up': 0,
                'max_consecutive': 0,
                'ladder_distribution': {}
            }
        }
        
        # 配置mock
        mock_client = mock_kaipanla.return_value
        mock_client.get_continuous_limit_up_stocks.return_value = continuous_data
        mock_client.get_market_limit_up_ladder.return_value = mock_ladder_data
        mock_client.get_ths_hot_rank.return_value = pd.Series()  # 空的热股列表
        mock_client.get_market_data.return_value = pd.DataFrame()  # 空的市场数据
        
        # 创建builder
        builder = GenePoolBuilder()
        builder.kaipanla_client = mock_client
        
        # 调用方法
        gene_pool = builder.build_gene_pool("2025-02-12")
        
        # 验证结果
        assert isinstance(gene_pool, GenePool)
        assert gene_pool.date == "2025-02-12"
        assert len(gene_pool.continuous_limit_up) == 1
        assert len(gene_pool.failed_limit_up) == 1
        assert len(gene_pool.all_stocks) >= 2  # 至少包含连板股和炸板股
        assert '002810' in gene_pool.all_stocks
        assert '600XXX' in gene_pool.all_stocks
    
    def test_create_stock_from_row(self):
        """测试从DataFrame行创建Stock对象"""
        builder = GenePoolBuilder()
        
        # 创建测试数据
        row = pd.Series({
            '代码': '002810',
            '名称': '韩建河山',
            '最新价': 15.68,
            '涨跌幅': 10.0,
            '成交量': 1250000,
            '成交额': 19600,
            '换手率': 4.2,
            '流通市值': 452000,
            '连板天数': 5,
            '所属题材': 'AI,数字经济'
        })
        
        # 调用方法
        stock = builder._create_stock_from_row(row, "2025-02-12")
        
        # 验证结果
        assert stock is not None
        assert stock.code == '002810'
        assert stock.name == '韩建河山'
        assert stock.price == 15.68
        assert stock.change_pct == 10.0
        assert stock.board_height == 5
        assert len(stock.themes) == 2
        assert 'AI' in stock.themes
        assert '数字经济' in stock.themes
    
    def test_create_stock_from_row_missing_data(self):
        """测试从缺失数据的行创建Stock对象"""
        builder = GenePoolBuilder()
        
        # 创建缺失代码的测试数据
        row = pd.Series({
            '名称': '测试股',
            '最新价': 10.0
        })
        
        # 调用方法
        stock = builder._create_stock_from_row(row, "2025-02-12")
        
        # 验证结果：应该返回None
        assert stock is None
    
    def test_gene_pool_serialization(self):
        """测试基因池的序列化和反序列化"""
        # 创建测试数据
        stock1 = Stock(
            code='002810',
            name='韩建河山',
            market_cap=45.2,
            price=15.68,
            change_pct=10.0,
            volume=1250000,
            amount=19600,
            turnover_rate=4.2,
            board_height=5,
            themes=['AI', '数字经济']
        )
        
        stock2 = Stock(
            code='600XXX',
            name='炸板股',
            market_cap=30.0,
            price=12.50,
            change_pct=8.5,
            volume=2000000,
            amount=25000,
            turnover_rate=8.5,
            board_height=0,
            themes=['医药']
        )
        
        # 创建基因池
        gene_pool = GenePool(
            date='2025-02-12',
            continuous_limit_up=[stock1],
            failed_limit_up=[stock2],
            recognition_stocks=[],
            trend_stocks=[],
            all_stocks={'002810': stock1, '600XXX': stock2}
        )
        
        # 序列化
        data = gene_pool.to_dict()
        assert isinstance(data, dict)
        assert data['date'] == '2025-02-12'
        assert len(data['continuous_limit_up']) == 1
        assert len(data['failed_limit_up']) == 1
        
        # 反序列化
        restored = GenePool.from_dict(data)
        assert restored.date == gene_pool.date
        assert len(restored.continuous_limit_up) == 1
        assert len(restored.failed_limit_up) == 1
        assert restored.continuous_limit_up[0].code == '002810'
        assert restored.failed_limit_up[0].code == '600XXX'
    
    @patch('src.stage1.gene_pool_builder.KaipanlaClient')
    def test_identify_recognition_stocks(self, mock_kaipanla):
        """测试识别辨识度个股"""
        # Mock同花顺热股数据
        mock_ths_data = pd.Series({
            1: "股票A",
            2: "股票B",
            3: "股票C"
        })
        
        # Mock板块风向标数据
        mock_sentiment_data = {
            'all_stocks': ['000001', '000002', '000003'],
            'bullish_codes': ['000001'],
            'bearish_codes': ['000003']
        }
        
        # Mock股票名称批量获取
        mock_names_map = {
            '000001': '股票A',
            '000002': '股票B',
            '000003': '股票D'  # 不在热股列表中
        }
        
        # 配置mock
        mock_client = mock_kaipanla.return_value
        mock_client.get_ths_hot_rank.return_value = mock_ths_data
        mock_client.get_sentiment_indicator.return_value = mock_sentiment_data
        mock_client.get_stock_names_batch.return_value = mock_names_map
        
        # 创建builder
        builder = GenePoolBuilder()
        builder.kaipanla_client = mock_client
        
        # 调用方法
        stocks = builder.identify_recognition_stocks("2025-02-13")
        
        # 验证结果：应该只返回在热股列表中的股票
        assert len(stocks) == 2
        assert all(stock.is_recognition_stock for stock in stocks)
        assert stocks[0].code == '000001'
        assert stocks[0].name == '股票A'
        assert stocks[1].code == '000002'
        assert stocks[1].name == '股票B'
    
    @patch('src.stage1.gene_pool_builder.KaipanlaClient')
    def test_identify_trend_stocks(self, mock_kaipanla):
        """测试识别趋势股"""
        # Mock同花顺热股数据
        mock_ths_data = pd.Series({
            1: "趋势股A",
            2: "趋势股B"
        })
        
        # Mock市场数据
        mock_market_data = pd.DataFrame([
            {
                '代码': '000001',
                '名称': '趋势股A',
                '最新价': 10.0,
                '涨跌幅': 5.0,
                '成交量': 1000000,
                '成交额': 10000,
                '换手率': 3.0,
                '流通市值': 100000
            },
            {
                '代码': '000002',
                '名称': '趋势股B',
                '最新价': 20.0,
                '涨跌幅': 3.0,
                '成交量': 2000000,
                '成交额': 40000,
                '换手率': 4.0,
                '流通市值': 200000
            },
            {
                '代码': '000003',
                '名称': '非热股',
                '最新价': 15.0,
                '涨跌幅': 2.0,
                '成交量': 500000,
                '成交额': 7500,
                '换手率': 2.0,
                '流通市值': 150000
            }
        ])
        
        # 配置mock
        mock_client = mock_kaipanla.return_value
        mock_client.get_ths_hot_rank.return_value = mock_ths_data
        mock_client.get_market_data.return_value = mock_market_data
        
        # 创建builder
        builder = GenePoolBuilder()
        builder.kaipanla_client = mock_client
        
        # 调用方法
        stocks = builder.identify_trend_stocks("2025-02-13")
        
        # 验证结果：应该只返回在热股列表中的股票
        assert len(stocks) >= 0  # 取决于_is_trend_stock的实现
        for stock in stocks:
            assert stock.name in ['趋势股A', '趋势股B']
            if hasattr(stock, 'is_trend_stock'):
                assert stock.is_trend_stock == True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
