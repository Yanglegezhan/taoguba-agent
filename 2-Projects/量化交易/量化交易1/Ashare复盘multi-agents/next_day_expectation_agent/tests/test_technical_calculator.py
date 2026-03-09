"""
测试技术指标计算器

测试TechnicalCalculator类的所有方法：
- calculate_moving_averages: 计算移动平均线
- identify_previous_highs: 识别前期高点
- calculate_chip_concentration: 计算筹码密集区
- calculate_distance_percentages: 计算距离百分比
- calculate_technical_levels: 计算完整技术位
"""

import pytest
from src.stage1.technical_calculator import TechnicalCalculator
from src.common.models import Stock, TechnicalLevels


@pytest.fixture
def calculator():
    """创建技术指标计算器实例"""
    return TechnicalCalculator()


@pytest.fixture
def sample_stock():
    """创建示例个股"""
    return Stock(
        code="000001",
        name="平安银行",
        market_cap=100.0,
        price=15.0,
        change_pct=5.0,
        volume=1000000,
        amount=15000,
        turnover_rate=2.5,
        board_height=0,
        themes=["银行"]
    )


class TestCalculateMovingAverages:
    """测试移动平均线计算"""
    
    def test_calculate_ma_with_sufficient_data(self, calculator, sample_stock):
        """测试有足够数据时的均线计算"""
        # 准备30天的价格数据
        price_history = [10.0 + i * 0.2 for i in range(30)]
        
        result = calculator.calculate_moving_averages(sample_stock, price_history)
        
        # 验证返回的键
        assert "ma5" in result
        assert "ma10" in result
        assert "ma20" in result
        
        # 验证MA5计算正确（最后5天的平均）
        expected_ma5 = sum(price_history[-5:]) / 5
        assert abs(result["ma5"] - expected_ma5) < 0.01
        
        # 验证MA10计算正确
        expected_ma10 = sum(price_history[-10:]) / 10
        assert abs(result["ma10"] - expected_ma10) < 0.01
        
        # 验证MA20计算正确
        expected_ma20 = sum(price_history[-20:]) / 20
        assert abs(result["ma20"] - expected_ma20) < 0.01
    
    def test_calculate_ma_with_insufficient_data(self, calculator, sample_stock):
        """测试数据不足时的均线计算"""
        # 只有3天的数据
        price_history = [10.0, 11.0, 12.0]
        
        result = calculator.calculate_moving_averages(sample_stock, price_history)
        
        # 所有均线应该使用可用数据的平均值
        expected_avg = sum(price_history) / len(price_history)
        assert abs(result["ma5"] - expected_avg) < 0.01
        assert abs(result["ma10"] - expected_avg) < 0.01
        assert abs(result["ma20"] - expected_avg) < 0.01
    
    def test_calculate_ma_with_empty_data(self, calculator, sample_stock):
        """测试空数据时的均线计算"""
        price_history = []
        
        result = calculator.calculate_moving_averages(sample_stock, price_history)
        
        # 应该返回0值
        assert result["ma5"] == 0.0
        assert result["ma10"] == 0.0
        assert result["ma20"] == 0.0


class TestIdentifyPreviousHighs:
    """测试前期高点识别"""
    
    def test_identify_highs_with_clear_peaks(self, calculator, sample_stock):
        """测试有明显高点的情况"""
        # 创建有明显高点的价格序列
        price_history = [
            10.0, 11.0, 12.0, 13.0, 14.0,  # 上涨
            15.0, 16.0, 17.0, 16.0, 15.0,  # 高点17.0
            14.0, 13.0, 12.0, 13.0, 14.0,  # 下跌后反弹
            15.0, 16.0, 15.0, 14.0, 13.0   # 小高点16.0
        ]
        
        result = calculator.identify_previous_highs(sample_stock, price_history)
        
        # 应该识别到高点
        assert len(result) > 0
        # 最高点应该是17.0
        assert result[0] == 17.0
    
    def test_identify_highs_with_monotonic_increase(self, calculator, sample_stock):
        """测试单调上涨的情况"""
        # 单调上涨的价格序列
        price_history = [10.0 + i * 0.5 for i in range(20)]
        
        result = calculator.identify_previous_highs(sample_stock, price_history)
        
        # 应该返回最高价
        assert len(result) > 0
        assert result[0] == max(price_history)
    
    def test_identify_highs_with_insufficient_data(self, calculator, sample_stock):
        """测试数据不足的情况"""
        price_history = [10.0, 11.0, 12.0]
        
        result = calculator.identify_previous_highs(sample_stock, price_history)
        
        # 数据不足时应该返回空列表
        assert len(result) == 0


class TestCalculateChipConcentration:
    """测试筹码密集区计算"""
    
    def test_calculate_chip_zone_normal(self, calculator, sample_stock):
        """测试正常情况下的筹码密集区计算"""
        # 准备价格和成交量数据
        price_history = [10.0, 10.5, 11.0, 10.8, 11.2, 11.5, 11.3, 11.0, 11.4, 11.6]
        volume_history = [100, 120, 150, 130, 140, 160, 150, 140, 145, 155]
        
        chip_zone_low, chip_zone_high = calculator.calculate_chip_concentration(
            sample_stock, price_history, volume_history
        )
        
        # 验证返回值
        assert chip_zone_low > 0
        assert chip_zone_high > 0
        assert chip_zone_high > chip_zone_low
        
        # 筹码密集区应该在价格范围内
        assert chip_zone_low >= min(price_history) * 0.9
        assert chip_zone_high <= max(price_history) * 1.1
    
    def test_calculate_chip_zone_with_zero_volume(self, calculator, sample_stock):
        """测试成交量为0的情况"""
        price_history = [10.0, 11.0, 12.0]
        volume_history = [0, 0, 0]
        
        chip_zone_low, chip_zone_high = calculator.calculate_chip_concentration(
            sample_stock, price_history, volume_history
        )
        
        # 应该返回基于平均价格的区间
        avg_price = sum(price_history) / len(price_history)
        assert chip_zone_low == pytest.approx(avg_price * 0.95, rel=0.01)
        assert chip_zone_high == pytest.approx(avg_price * 1.05, rel=0.01)
    
    def test_calculate_chip_zone_with_empty_data(self, calculator, sample_stock):
        """测试空数据的情况"""
        price_history = []
        volume_history = []
        
        chip_zone_low, chip_zone_high = calculator.calculate_chip_concentration(
            sample_stock, price_history, volume_history
        )
        
        # 应该返回0值
        assert chip_zone_low == 0.0
        assert chip_zone_high == 0.0
    
    def test_calculate_chip_zone_with_mismatched_length(self, calculator, sample_stock):
        """测试价格和成交量长度不匹配的情况"""
        price_history = [10.0, 11.0, 12.0]
        volume_history = [100, 120]  # 长度不匹配
        
        chip_zone_low, chip_zone_high = calculator.calculate_chip_concentration(
            sample_stock, price_history, volume_history
        )
        
        # 应该返回0值
        assert chip_zone_low == 0.0
        assert chip_zone_high == 0.0


class TestCalculateDistancePercentages:
    """测试距离百分比计算"""
    
    def test_calculate_distance_above_ma(self, calculator):
        """测试价格在均线上方的情况"""
        current_price = 15.0
        ma5 = 14.0
        ma10 = 13.5
        ma20 = 13.0
        previous_high = 16.0
        
        result = calculator.calculate_distance_percentages(
            current_price, ma5, ma10, ma20, previous_high
        )
        
        # 验证返回的键
        assert "distance_to_ma5_pct" in result
        assert "distance_to_ma10_pct" in result
        assert "distance_to_ma20_pct" in result
        assert "distance_to_high_pct" in result
        
        # 验证计算正确性（价格在均线上方，应该是正值）
        assert result["distance_to_ma5_pct"] > 0
        assert result["distance_to_ma10_pct"] > 0
        assert result["distance_to_ma20_pct"] > 0
        
        # 验证距离前高是负值（价格低于前高）
        assert result["distance_to_high_pct"] < 0
        
        # 验证具体数值
        expected_ma5_pct = (15.0 - 14.0) / 14.0 * 100
        assert abs(result["distance_to_ma5_pct"] - expected_ma5_pct) < 0.01
    
    def test_calculate_distance_below_ma(self, calculator):
        """测试价格在均线下方的情况"""
        current_price = 12.0
        ma5 = 13.0
        ma10 = 13.5
        ma20 = 14.0
        previous_high = 16.0
        
        result = calculator.calculate_distance_percentages(
            current_price, ma5, ma10, ma20, previous_high
        )
        
        # 价格在均线下方，应该是负值
        assert result["distance_to_ma5_pct"] < 0
        assert result["distance_to_ma10_pct"] < 0
        assert result["distance_to_ma20_pct"] < 0
    
    def test_calculate_distance_with_zero_ma(self, calculator):
        """测试均线为0的情况"""
        current_price = 15.0
        ma5 = 0.0
        ma10 = 0.0
        ma20 = 0.0
        previous_high = 0.0
        
        result = calculator.calculate_distance_percentages(
            current_price, ma5, ma10, ma20, previous_high
        )
        
        # 均线为0时应该返回0
        assert result["distance_to_ma5_pct"] == 0.0
        assert result["distance_to_ma10_pct"] == 0.0
        assert result["distance_to_ma20_pct"] == 0.0
        assert result["distance_to_high_pct"] == 0.0


class TestCalculateTechnicalLevels:
    """测试完整技术位计算"""
    
    def test_calculate_technical_levels_complete(self, calculator, sample_stock):
        """测试完整的技术位计算"""
        # 准备充足的历史数据
        price_history = [10.0 + i * 0.2 for i in range(30)]
        volume_history = [100 + i * 5 for i in range(30)]
        
        result = calculator.calculate_technical_levels(
            sample_stock, price_history, volume_history
        )
        
        # 验证返回类型
        assert isinstance(result, TechnicalLevels)
        
        # 验证所有字段都有值
        assert result.ma5 > 0
        assert result.ma10 > 0
        assert result.ma20 > 0
        assert result.previous_high > 0
        assert result.chip_zone_low > 0
        assert result.chip_zone_high > 0
        
        # 验证逻辑关系
        assert result.chip_zone_high > result.chip_zone_low
        assert result.ma5 > 0  # 均线应该是正值
    
    def test_calculate_technical_levels_with_minimal_data(self, calculator, sample_stock):
        """测试最少数据的技术位计算"""
        price_history = [10.0, 11.0, 12.0]
        volume_history = [100, 110, 120]
        
        result = calculator.calculate_technical_levels(
            sample_stock, price_history, volume_history
        )
        
        # 应该能够返回结果，即使数据不足
        assert isinstance(result, TechnicalLevels)
        # 均线应该使用可用数据计算
        assert result.ma5 > 0
    
    def test_calculate_technical_levels_error_handling(self, calculator, sample_stock):
        """测试错误处理"""
        # 传入空数据
        price_history = []
        volume_history = []
        
        result = calculator.calculate_technical_levels(
            sample_stock, price_history, volume_history
        )
        
        # 应该返回默认值而不是抛出异常
        assert isinstance(result, TechnicalLevels)
        assert result.ma5 == 0.0
        assert result.ma10 == 0.0
        assert result.ma20 == 0.0


class TestIntegration:
    """集成测试"""
    
    def test_realistic_stock_scenario(self, calculator):
        """测试真实股票场景"""
        # 创建一个真实的股票对象
        stock = Stock(
            code="002810",
            name="韩建河山",
            market_cap=45.2,
            price=15.68,
            change_pct=10.0,
            volume=1250000,
            amount=19600,
            turnover_rate=4.2,
            board_height=5,
            themes=["AI", "数字经济"]
        )
        
        # 模拟60天的价格数据（上涨趋势）
        price_history = []
        for i in range(60):
            base_price = 10.0
            trend = i * 0.1  # 上涨趋势
            noise = (i % 5 - 2) * 0.05  # 小幅波动
            price_history.append(base_price + trend + noise)
        
        # 模拟成交量数据
        volume_history = [100000 + i * 1000 for i in range(60)]
        
        # 计算技术位
        result = calculator.calculate_technical_levels(stock, price_history, volume_history)
        
        # 验证结果的合理性
        assert result.ma5 > 0
        assert result.ma10 > 0
        assert result.ma20 > 0
        assert result.ma5 > result.ma10  # 上涨趋势中，短期均线应该在长期均线上方
        assert result.ma10 > result.ma20
        
        # 验证前期高点
        assert result.previous_high >= max(price_history[-60:])
        
        # 验证筹码密集区
        assert result.chip_zone_high > result.chip_zone_low
        
        # 验证距离百分比
        # 在上涨趋势中，当前价格应该在均线上方
        assert result.distance_to_ma5_pct != 0.0  # 应该有距离


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
