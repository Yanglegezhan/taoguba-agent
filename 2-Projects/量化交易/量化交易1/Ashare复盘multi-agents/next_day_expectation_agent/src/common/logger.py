"""
日志系统配置模块

提供统一的日志配置和管理功能，支持控制台和文件输出。
"""

import sys
from pathlib import Path
from typing import Optional
from loguru import logger


class LoggerManager:
    """日志管理器"""
    
    _initialized = False
    
    @classmethod
    def setup_logger(
        cls,
        log_path: Optional[str] = None,
        level: str = "INFO",
        format_string: Optional[str] = None,
        rotation: str = "100 MB",
        retention: str = "30 days",
        console_output: bool = True,
        file_output: bool = True
    ) -> None:
        """
        配置日志系统
        
        Args:
            log_path: 日志文件路径
            level: 日志级别 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            format_string: 日志格式字符串
            rotation: 日志轮转大小
            retention: 日志保留时间
            console_output: 是否输出到控制台
            file_output: 是否输出到文件
        """
        if cls._initialized:
            return
        
        # 移除默认的handler
        logger.remove()
        
        # 默认格式
        if format_string is None:
            format_string = (
                "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
                "<level>{level: <8}</level> | "
                "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
                "<level>{message}</level>"
            )
        
        # 添加控制台输出
        if console_output:
            logger.add(
                sys.stderr,
                format=format_string,
                level=level,
                colorize=True
            )
        
        # 添加文件输出
        if file_output and log_path:
            log_file = Path(log_path)
            log_file.parent.mkdir(parents=True, exist_ok=True)
            
            logger.add(
                log_file,
                format=format_string,
                level=level,
                rotation=rotation,
                retention=retention,
                encoding="utf-8"
            )
        
        cls._initialized = True
        logger.info(f"Logger initialized with level: {level}")
    
    @classmethod
    def get_logger(cls, name: str = None):
        """
        获取logger实例
        
        Args:
            name: logger名称
            
        Returns:
            logger实例
        """
        if not cls._initialized:
            cls.setup_logger()
        
        if name:
            return logger.bind(name=name)
        return logger


def get_logger(name: str = None):
    """
    获取logger实例的便捷函数
    
    Args:
        name: logger名称
        
    Returns:
        logger实例
    """
    return LoggerManager.get_logger(name)
