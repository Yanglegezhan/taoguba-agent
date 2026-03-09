"""
通用工具函数模块
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Optional


def get_trading_date(date: Optional[str] = None, offset: int = 0) -> str:
    """
    获取交易日期
    
    Args:
        date: 日期字符串 (YYYY-MM-DD)，None表示今天
        offset: 日期偏移量（天数）
        
    Returns:
        日期字符串 (YYYY-MM-DD)
    """
    if date:
        base_date = datetime.strptime(date, "%Y-%m-%d")
    else:
        base_date = datetime.now()
    
    target_date = base_date + timedelta(days=offset)
    return target_date.strftime("%Y-%m-%d")


def load_json(file_path: str) -> Dict[str, Any]:
    """
    加载JSON文件
    
    Args:
        file_path: 文件路径
        
    Returns:
        JSON数据字典
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_json(data: Dict[str, Any], file_path: str, indent: int = 2) -> None:
    """
    保存JSON文件
    
    Args:
        data: 要保存的数据
        file_path: 文件路径
        indent: 缩进空格数
    """
    file = Path(file_path)
    file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=indent)


def format_number(value: float, decimals: int = 2) -> str:
    """
    格式化数字
    
    Args:
        value: 数值
        decimals: 小数位数
        
    Returns:
        格式化后的字符串
    """
    return f"{value:.{decimals}f}"


def format_percentage(value: float, decimals: int = 2) -> str:
    """
    格式化百分比
    
    Args:
        value: 数值（如0.05表示5%）
        decimals: 小数位数
        
    Returns:
        格式化后的百分比字符串
    """
    return f"{value * 100:.{decimals}f}%"


def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    """
    安全除法，避免除零错误
    
    Args:
        numerator: 分子
        denominator: 分母
        default: 除零时的默认值
        
    Returns:
        除法结果
    """
    if denominator == 0:
        return default
    return numerator / denominator


def clamp(value: float, min_value: float, max_value: float) -> float:
    """
    将值限制在指定范围内
    
    Args:
        value: 输入值
        min_value: 最小值
        max_value: 最大值
        
    Returns:
        限制后的值
    """
    return max(min_value, min(value, max_value))


def is_trading_day(date: str) -> bool:
    """
    判断是否为交易日（简化版，实际应查询交易日历）
    
    Args:
        date: 日期字符串 (YYYY-MM-DD)
        
    Returns:
        是否为交易日
    """
    dt = datetime.strptime(date, "%Y-%m-%d")
    # 简化判断：周一到周五为交易日
    # 实际应用中应查询完整的交易日历
    return dt.weekday() < 5


def get_next_trading_day(date: str) -> str:
    """
    获取下一个交易日（简化版）
    
    Args:
        date: 日期字符串 (YYYY-MM-DD)
        
    Returns:
        下一个交易日字符串
    """
    current = datetime.strptime(date, "%Y-%m-%d")
    next_day = current + timedelta(days=1)
    
    # 跳过周末
    while next_day.weekday() >= 5:
        next_day += timedelta(days=1)
    
    return next_day.strftime("%Y-%m-%d")


def get_previous_trading_day(date: str) -> str:
    """
    获取上一个交易日（简化版）
    
    Args:
        date: 日期字符串 (YYYY-MM-DD)
        
    Returns:
        上一个交易日字符串
    """
    current = datetime.strptime(date, "%Y-%m-%d")
    prev_day = current - timedelta(days=1)
    
    # 跳过周末
    while prev_day.weekday() >= 5:
        prev_day -= timedelta(days=1)
    
    return prev_day.strftime("%Y-%m-%d")
