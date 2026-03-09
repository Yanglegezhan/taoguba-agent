"""
配置管理模块

提供统一的配置加载和验证功能。
"""

from pathlib import Path
from typing import Any, Dict, Optional
import yaml
from pydantic import BaseModel, Field, validator
from .logger import get_logger

logger = get_logger(__name__)


class DataConfig(BaseModel):
    """数据存储配置"""
    base_path: str = "./data"
    stage1_output: str = "./data/stage1_output"
    stage2_output: str = "./data/stage2_output"
    stage3_output: str = "./data/stage3_output"
    historical_db: str = "./data/historical/gene_pool_history.db"
    logs_path: str = "./data/logs"


class LoggingConfig(BaseModel):
    """日志配置"""
    level: str = "INFO"
    format: str = "{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} - {message}"
    rotation: str = "100 MB"
    retention: str = "30 days"
    console_output: bool = True
    file_output: bool = True


class TimingConfig(BaseModel):
    """时间配置"""
    stage1_run_time: str = "15:30"
    stage2_run_time: str = "07:00"
    stage3_start_time: str = "09:15"
    stage3_end_time: str = "09:25"


class NotificationConfig(BaseModel):
    """推送配置"""
    enabled: bool = True
    wechat: Dict[str, Any] = Field(default_factory=dict)
    email: Dict[str, Any] = Field(default_factory=dict)


class PerformanceConfig(BaseModel):
    """性能配置"""
    max_workers: int = 4
    timeout: int = 30
    retry_times: int = 3


class LLMConfig(BaseModel):
    """LLM配置"""
    api_key: str = ""
    model_name: str = "gemini-2.0-flash-exp"
    temperature: float = 0.7
    max_tokens: int = 2048
    top_p: float = 0.95
    top_k: int = 40
    timeout: int = 30
    max_retries: int = 3
    enable_fallback: bool = True


class SystemConfig(BaseModel):
    """系统配置"""
    data: DataConfig = Field(default_factory=DataConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    timing: TimingConfig = Field(default_factory=TimingConfig)
    notification: NotificationConfig = Field(default_factory=NotificationConfig)
    performance: PerformanceConfig = Field(default_factory=PerformanceConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)


class ConfigManager:
    """配置管理器"""
    
    _instance = None
    _system_config: Optional[SystemConfig] = None
    _agent_config: Optional[Dict[str, Any]] = None
    _data_source_config: Optional[Dict[str, Any]] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def load_config(
        self,
        system_config_path: str = "config/system_config.yaml",
        agent_config_path: str = "config/agent_config.yaml",
        data_source_config_path: str = "config/data_source_config.yaml"
    ) -> None:
        """
        加载所有配置文件
        
        Args:
            system_config_path: 系统配置文件路径
            agent_config_path: Agent配置文件路径
            data_source_config_path: 数据源配置文件路径
        """
        # 加载系统配置
        self._system_config = self._load_system_config(system_config_path)
        logger.info(f"Loaded system config from {system_config_path}")
        
        # 加载Agent配置
        self._agent_config = self._load_yaml(agent_config_path)
        logger.info(f"Loaded agent config from {agent_config_path}")
        
        # 加载数据源配置
        self._data_source_config = self._load_yaml(data_source_config_path)
        logger.info(f"Loaded data source config from {data_source_config_path}")
        
        # 创建必要的目录
        self._create_directories()
    
    def _load_system_config(self, config_path: str) -> SystemConfig:
        """加载并验证系统配置"""
        config_file = Path(config_path)
        
        if not config_file.exists():
            logger.warning(f"System config file not found: {config_path}, using defaults")
            return SystemConfig()
        
        with open(config_file, 'r', encoding='utf-8') as f:
            config_data = yaml.safe_load(f)
        
        return SystemConfig(**config_data)
    
    def _load_yaml(self, config_path: str) -> Dict[str, Any]:
        """加载YAML配置文件"""
        config_file = Path(config_path)
        
        if not config_file.exists():
            logger.warning(f"Config file not found: {config_path}, using empty config")
            return {}
        
        with open(config_file, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or {}
    
    def _create_directories(self) -> None:
        """创建必要的目录"""
        if self._system_config:
            dirs = [
                self._system_config.data.base_path,
                self._system_config.data.stage1_output,
                self._system_config.data.stage2_output,
                self._system_config.data.stage3_output,
                self._system_config.data.logs_path,
            ]
            
            # 创建历史数据库目录
            db_path = Path(self._system_config.data.historical_db)
            dirs.append(str(db_path.parent))
            
            for dir_path in dirs:
                Path(dir_path).mkdir(parents=True, exist_ok=True)
            
            logger.info("Created necessary directories")
    
    @property
    def system_config(self) -> SystemConfig:
        """获取系统配置"""
        if self._system_config is None:
            self.load_config()
        return self._system_config
    
    @property
    def agent_config(self) -> Dict[str, Any]:
        """获取Agent配置"""
        if self._agent_config is None:
            self.load_config()
        return self._agent_config
    
    @property
    def data_source_config(self) -> Dict[str, Any]:
        """获取数据源配置"""
        if self._data_source_config is None:
            self.load_config()
        return self._data_source_config
    
    def get_stage_config(self, stage: str) -> Dict[str, Any]:
        """
        获取指定Stage的配置
        
        Args:
            stage: Stage名称 (stage1, stage2, stage3)
            
        Returns:
            Stage配置字典
        """
        return self.agent_config.get(stage, {})
    
    def save_config(
        self,
        config_type: str,
        config_data: Dict[str, Any],
        config_path: str
    ) -> None:
        """
        保存配置到文件
        
        Args:
            config_type: 配置类型 (system, agent, data_source)
            config_data: 配置数据
            config_path: 配置文件路径
        """
        config_file = Path(config_path)
        config_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(config_file, 'w', encoding='utf-8') as f:
            yaml.dump(config_data, f, allow_unicode=True, default_flow_style=False)
        
        logger.info(f"Saved {config_type} config to {config_path}")


# 全局配置管理器实例
config_manager = ConfigManager()


def get_config() -> ConfigManager:
    """获取配置管理器实例"""
    return config_manager
