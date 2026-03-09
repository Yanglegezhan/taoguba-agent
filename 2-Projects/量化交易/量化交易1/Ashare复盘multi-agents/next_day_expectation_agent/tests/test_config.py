"""
配置管理模块测试
"""

import pytest
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from common.config import ConfigManager, SystemConfig, DataConfig


class TestConfigManager:
    """配置管理器测试"""
    
    def test_default_system_config(self):
        """测试默认系统配置"""
        config = SystemConfig()
        
        assert config.data.base_path == "./data"
        assert config.logging.level == "INFO"
        assert config.performance.max_workers == 4
        assert config.performance.timeout == 30
    
    def test_config_manager_singleton(self):
        """测试配置管理器单例模式"""
        manager1 = ConfigManager()
        manager2 = ConfigManager()
        
        assert manager1 is manager2
    
    def test_data_config_validation(self):
        """测试数据配置验证"""
        data_config = DataConfig(
            base_path="./test_data",
            stage1_output="./test_data/stage1"
        )
        
        assert data_config.base_path == "./test_data"
        assert data_config.stage1_output == "./test_data/stage1"
