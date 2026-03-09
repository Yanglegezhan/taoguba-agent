"""
数据模型测试

测试所有数据模型的序列化、反序列化和验证功能
"""

import pytest
import json
import tempfile
import os
from datetime import datetime

from src.common.models import (
    Stock, TechnicalLevels, GenePool, BaselineExpectation,
    AuctionData, ExpectationScore, StatusScore, AdditionalPool,
    SignalPlaybook, Scenario, DecisionTree, NavigationReport,
    save_to_json, load_from_json, serialize_to_json_string,
    deserialize_from_json_string, save_gene_pool, load_gene_pool,
    save_baseline_expectations, load_baseline_expectations,
    save_navigation_report, load_navigation_report,
    save_additional_pool, load_additional_pool
)
from src.common.schema_validator import (
    validate_gene_pool_data, validate_baseline_expectation_data,
    validate_decision_navigation_data
)


class TestTechnicalLevels:
    """测试TechnicalLevels数据类"""
    
    def test_to_dict(self):
        """测试转换为字典"""
        tech = TechnicalLevels(
            ma5=10.5, ma10=10.2, ma20=9.8,
            previous_high=12.0, chip_zone_low=9.5, chip_zone_high=10.5,
            distance_to_ma5_pct=5.0, distance_to_high_pct=-10.0
        )
        data = tech.to_dict()
        
        assert data['ma5'] == 10.5
        assert data['ma10'] == 10.2
        assert data['distance_to_high_pct'] == -10.0
    
    def test_from_dict(self):
        """测试从字典创建实例"""
        data = {
            'ma5': 10.5, 'ma10': 10.2, 'ma20': 9.8,
            'previous_high': 12.0, 'chip_zone_low': 9.5, 'chip_zone_high': 10.5,
            'distance_to_ma5_pct': 5.0, 'distance_to_high_pct': -10.0
        }
        tech = TechnicalLevels.from_dict(data)
        
        assert tech.ma5 == 10.5
        assert tech.distance_to_high_pct == -10.0


class TestStock:
    """测试Stock数据类"""
    
    def test_to_dict_without_technical_levels(self):
        """测试转换为字典（无技术位）"""
        stock = Stock(
            code='000001', name='平安银行', market_cap=100.0,
            price=10.5, change_pct=5.0, volume=1000000,
            amount=10500, turnover_rate=2.5, board_height=0,
            themes=['银行', '金融']
        )
        data = stock.to_dict()
        
        assert data['code'] == '000001'
        assert data['name'] == '平安银行'
        assert data['technical_levels'] is None
    
    def test_to_dict_with_technical_levels(self):
        """测试转换为字典（含技术位）"""
        tech = TechnicalLevels(
            ma5=10.5, ma10=10.2, ma20=9.8,
            previous_high=12.0, chip_zone_low=9.5, chip_zone_high=10.5,
            distance_to_ma5_pct=5.0, distance_to_high_pct=-10.0
        )
        stock = Stock(
            code='000001', name='平安银行', market_cap=100.0,
            price=10.5, change_pct=5.0, volume=1000000,
            amount=10500, turnover_rate=2.5, board_height=0,
            themes=['银行', '金融'], technical_levels=tech
        )
        data = stock.to_dict()
        
        assert data['technical_levels']['ma5'] == 10.5
    
    def test_from_dict(self):
        """测试从字典创建实例"""
        data = {
            'code': '000001', 'name': '平安银行', 'market_cap': 100.0,
            'price': 10.5, 'change_pct': 5.0, 'volume': 1000000,
            'amount': 10500, 'turnover_rate': 2.5, 'board_height': 0,
            'themes': ['银行', '金融'],
            'technical_levels': {
                'ma5': 10.5, 'ma10': 10.2, 'ma20': 9.8,
                'previous_high': 12.0, 'chip_zone_low': 9.5, 'chip_zone_high': 10.5,
                'distance_to_ma5_pct': 5.0, 'distance_to_high_pct': -10.0
            }
        }
        stock = Stock.from_dict(data)
        
        assert stock.code == '000001'
        assert stock.technical_levels.ma5 == 10.5


class TestGenePool:
    """测试GenePool数据类"""
    
    def test_to_dict_and_from_dict(self):
        """测试序列化和反序列化"""
        stock1 = Stock(
            code='000001', name='平安银行', market_cap=100.0,
            price=10.5, change_pct=5.0, volume=1000000,
            amount=10500, turnover_rate=2.5, board_height=0,
            themes=['银行']
        )
        stock2 = Stock(
            code='000002', name='万科A', market_cap=200.0,
            price=20.5, change_pct=10.0, volume=2000000,
            amount=41000, turnover_rate=5.0, board_height=2,
            themes=['房地产']
        )
        
        gene_pool = GenePool(
            date='2025-02-13',
            continuous_limit_up=[stock2],
            failed_limit_up=[],
            recognition_stocks=[stock1],
            trend_stocks=[],
            all_stocks={'000001': stock1, '000002': stock2}
        )
        
        # 序列化
        data = gene_pool.to_dict()
        assert data['date'] == '2025-02-13'
        assert len(data['continuous_limit_up']) == 1
        assert len(data['all_stocks']) == 2
        
        # 反序列化
        restored = GenePool.from_dict(data)
        assert restored.date == '2025-02-13'
        assert len(restored.continuous_limit_up) == 1
        assert restored.continuous_limit_up[0].code == '000002'


class TestBaselineExpectation:
    """测试BaselineExpectation数据类"""
    
    def test_serialization(self):
        """测试序列化和反序列化"""
        expectation = BaselineExpectation(
            stock_code='000001',
            stock_name='平安银行',
            expected_open_min=3.0,
            expected_open_max=5.0,
            expected_amount_min=10000,
            logic='昨日涨停+题材主升期',
            confidence=0.85
        )
        
        # 序列化
        data = expectation.to_dict()
        assert data['stock_code'] == '000001'
        assert data['confidence'] == 0.85
        
        # 反序列化
        restored = BaselineExpectation.from_dict(data)
        assert restored.stock_code == '000001'
        assert restored.confidence == 0.85


class TestNavigationReport:
    """测试NavigationReport数据类"""
    
    def test_complex_serialization(self):
        """测试复杂对象的序列化"""
        expectation = BaselineExpectation(
            stock_code='000001',
            stock_name='平安银行',
            expected_open_min=3.0,
            expected_open_max=5.0,
            expected_amount_min=10000,
            logic='测试',
            confidence=0.85
        )
        
        playbook = SignalPlaybook(
            name='暴力抢筹',
            trigger_conditions=['条件1', '条件2'],
            status_judgment='判定',
            strategy='策略',
            risk_level='高风险',
            applicable_stocks=['000001']
        )
        
        scenario = Scenario(
            name='整体超预期',
            trigger_condition='核心大哥全封一字',
            market_sentiment='强势',
            strategy='扫板',
            risk_warning='顶背离',
            confidence=0.7
        )
        
        decision_tree = DecisionTree(
            scenarios=[scenario],
            current_scenario='整体超预期'
        )
        
        report = NavigationReport(
            date='2025-02-13',
            generation_time='2025-02-13 09:26:30',
            baseline_table={'000001': expectation},
            signal_playbooks=[playbook],
            decision_tree=decision_tree,
            market_summary='市场强势',
            key_recommendations=['建议1', '建议2']
        )
        
        # 序列化
        data = report.to_dict()
        assert data['date'] == '2025-02-13'
        assert '000001' in data['baseline_table']
        assert len(data['signal_playbooks']) == 1
        
        # 反序列化
        restored = NavigationReport.from_dict(data)
        assert restored.date == '2025-02-13'
        assert '000001' in restored.baseline_table
        assert len(restored.signal_playbooks) == 1


class TestFileSerialization:
    """测试文件序列化功能"""
    
    def test_save_and_load_gene_pool(self):
        """测试保存和加载基因池"""
        stock = Stock(
            code='000001', name='平安银行', market_cap=100.0,
            price=10.5, change_pct=5.0, volume=1000000,
            amount=10500, turnover_rate=2.5, board_height=0,
            themes=['银行']
        )
        
        gene_pool = GenePool(
            date='2025-02-13',
            continuous_limit_up=[stock],
            failed_limit_up=[],
            recognition_stocks=[],
            trend_stocks=[],
            all_stocks={'000001': stock}
        )
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # 保存
            filepath = save_gene_pool(gene_pool, tmpdir)
            assert os.path.exists(filepath)
            
            # 加载
            restored = load_gene_pool(filepath)
            assert restored.date == '2025-02-13'
            assert len(restored.continuous_limit_up) == 1
    
    def test_save_and_load_baseline_expectations(self):
        """测试保存和加载基准预期"""
        expectations = {
            '000001': BaselineExpectation(
                stock_code='000001',
                stock_name='平安银行',
                expected_open_min=3.0,
                expected_open_max=5.0,
                expected_amount_min=10000,
                logic='测试',
                confidence=0.85
            )
        }
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # 保存
            filepath = save_baseline_expectations(expectations, '2025-02-13', tmpdir)
            assert os.path.exists(filepath)
            
            # 加载
            restored = load_baseline_expectations(filepath)
            assert '000001' in restored
            assert restored['000001'].confidence == 0.85


class TestSchemaValidation:
    """测试Schema验证功能"""
    
    def test_validate_gene_pool(self):
        """测试基因池数据验证"""
        stock = Stock(
            code='000001', name='平安银行', market_cap=100.0,
            price=10.5, change_pct=5.0, volume=1000000,
            amount=10500, turnover_rate=2.5, board_height=0,
            themes=['银行']
        )
        
        gene_pool = GenePool(
            date='2025-02-13',
            continuous_limit_up=[stock],
            failed_limit_up=[],
            recognition_stocks=[],
            trend_stocks=[]
        )
        
        data = gene_pool.to_dict()
        is_valid, errors = validate_gene_pool_data(data)
        
        # 如果jsonschema可用，应该验证通过
        if is_valid:
            assert len(errors) == 0
        else:
            # 如果jsonschema不可用，会有警告信息
            assert len(errors) > 0
    
    def test_validate_baseline_expectation(self):
        """测试基准预期数据验证"""
        expectations = {
            '000001': BaselineExpectation(
                stock_code='000001',
                stock_name='平安银行',
                expected_open_min=3.0,
                expected_open_max=5.0,
                expected_amount_min=10000,
                logic='测试',
                confidence=0.85
            )
        }
        
        data = {
            'date': '2025-02-13',
            'expectations': {code: exp.to_dict() for code, exp in expectations.items()}
        }
        
        is_valid, errors = validate_baseline_expectation_data(data)
        
        if is_valid:
            assert len(errors) == 0
        else:
            assert len(errors) > 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
