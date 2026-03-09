"""
工具函数模块测试
"""

import pytest
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from common.utils import (
    get_trading_date,
    format_number,
    format_percentage,
    safe_divide,
    clamp,
    get_next_trading_day,
    get_previous_trading_day
)


class TestUtils:
    """工具函数测试"""
    
    def test_format_number(self):
        """测试数字格式化"""
        assert format_number(123.456, 2) == "123.46"
        assert format_number(123.456, 1) == "123.5"
        assert format_number(123, 2) == "123.00"
    
    def test_format_percentage(self):
        """测试百分比格式化"""
        assert format_percentage(0.05, 2) == "5.00%"
        assert format_percentage(0.1234, 2) == "12.34%"
        assert format_percentage(-0.03, 2) == "-3.00%"
    
    def test_safe_divide(self):
        """测试安全除法"""
        assert safe_divide(10, 2) == 5.0
        assert safe_divide(10, 0) == 0.0
        assert safe_divide(10, 0, default=1.0) == 1.0
    
    def test_clamp(self):
        """测试值限制"""
        assert clamp(5, 0, 10) == 5
        assert clamp(-5, 0, 10) == 0
        assert clamp(15, 0, 10) == 10
    
    def test_get_next_trading_day(self):
        """测试获取下一个交易日"""
        # 周五 -> 周一
        next_day = get_next_trading_day("2025-02-07")  # Friday
        assert next_day == "2025-02-10"  # Monday
        
        # 周四 -> 周五
        next_day = get_next_trading_day("2025-02-06")  # Thursday
        assert next_day == "2025-02-07"  # Friday
    
    def test_get_previous_trading_day(self):
        """测试获取上一个交易日"""
        # 周一 -> 周五
        prev_day = get_previous_trading_day("2025-02-10")  # Monday
        assert prev_day == "2025-02-07"  # Friday
        
        # 周二 -> 周一
        prev_day = get_previous_trading_day("2025-02-11")  # Tuesday
        assert prev_day == "2025-02-10"  # Monday
