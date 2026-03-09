# -*- coding: utf-8 -*-
"""
配置管理器

加载和管理暗线分析Agent的配置
"""

import os
import logging
import yaml
from pathlib import Path
from typing import Any, Dict, Optional
from dotenv import load_dotenv

# 修复导入路径
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.models.data_models import (
    AgentConfig,
    DataSourceConfig,
    AnalysisConfig,
    LLMConfig,
    OutputConfig,
    LoggingConfig
)


class ConfigManager:
    """配置管理器 - 支持YAML文件和环境变量覆盖"""

    def __init__(self, config_path: Optional[str] = None):
        """
        初始化配置管理器

        Args:
            config_path: 配置文件路径，如果为None则使用默认路径
        """
        # 确定配置文件路径
        if config_path is None:
            project_root = Path(__file__).parent.parent
            config_path = project_root / "config" / "config.yaml"

        self.config_path = Path(config_path)

        # 加载 .env 文件
        env_path = self.config_path.parent.parent / ".env"
        if env_path.exists():
            load_dotenv(env_path)

        # 加载配置
        self._config: Dict[str, Any] = {}
        self._load_config()

        self.logger = logging.getLogger(__name__)

    def _load_config(self):
        """加载YAML配置文件"""
        if not self.config_path.exists():
            # 尝试加载示例配置
            example_path = self.config_path.parent / "config.example.yaml"
            if example_path.exists():
                self.config_path = example_path

        with open(self.config_path, 'r', encoding='utf-8') as f:
            self._config = yaml.safe_load(f) or {}

    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置值（支持点表示法）

        Args:
            key: 配置键，如 'llm.api_key'
            default: 默认值

        Returns:
            配置值
        """
        keys = key.split('.')
        value = self._config

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        return value

    def get_llm_config(self) -> LLMConfig:
        """获取LLM配置"""
        llm_config = self.get('llm', {})

        return LLMConfig(
            provider=llm_config.get('provider', 'zhipu'),
            api_key=self._get_env_or_config('LLM_API_KEY', llm_config.get('api_key', '')),
            model_name=llm_config.get('model_name', 'glm-4.7-flash'),
            temperature=llm_config.get('temperature', 0.7),
            max_tokens=llm_config.get('max_tokens'),
            timeout=llm_config.get('timeout')
        )

    def get_data_source_config(self) -> DataSourceConfig:
        """获取数据源配置"""
        ds_config = self.get('data_source', {})
        kaipanla_config = ds_config.get('kaipanla', {})
        tushare_config = ds_config.get('tushare', {})
        akshare_config = ds_config.get('akshare', {})

        return DataSourceConfig(
            kaipanla_timeout=kaipanla_config.get('timeout', 60),
            kaipanla_max_retries=kaipanla_config.get('max_retries', 3),
            tushare_token=self._get_env_or_config('TUSHARE_TOKEN', tushare_config.get('api_token', '')),
            tushare_timeout=tushare_config.get('timeout', 30),
            akshare_timeout=akshare_config.get('timeout', 30)
        )

    def get_analysis_config(self) -> AnalysisConfig:
        """获取分析配置"""
        analysis_config = self.get('analysis', {})

        return AnalysisConfig(
            lift_ratio_threshold=analysis_config.get('lift_ratio_threshold', 2.0),
            min_sample_size=analysis_config.get('min_sample_size', 3),
            naming_similarity_threshold=analysis_config.get('naming_similarity_threshold', 0.7),
            ma_periods=analysis_config.get('ma_periods', [5, 10, 20, 60]),
            lookback_days=analysis_config.get('lookback_days', 250),
            recent_limit_up_window=analysis_config.get('recent_limit_up_window', 20),
            pb_break_threshold=analysis_config.get('pb_break_threshold', 1.0),
            price_ranges=analysis_config.get('price_ranges', [10, 30]),
            market_cap_ranges=analysis_config.get('market_cap_ranges', [50, 100, 1000])
        )

    def get_output_config(self) -> OutputConfig:
        """获取输出配置"""
        output_config = self.get('output', {})

        return OutputConfig(
            report_dir=output_config.get('report_dir', 'output/reports'),
            format=output_config.get('format', ['markdown', 'json']),
            include_stock_details=output_config.get('include_stock_details', True)
        )

    def get_logging_config(self) -> LoggingConfig:
        """获取日志配置"""
        logging_config = self.get('logging', {})

        return LoggingConfig(
            level=logging_config.get('level', 'INFO'),
            file=logging_config.get('file', 'logs/dark_line_agent.log'),
            max_bytes=logging_config.get('max_bytes', 10485760),
            backup_count=logging_config.get('backup_count', 5),
            console_output=logging_config.get('console_output', True)
        )

    def get_agent_config(self) -> AgentConfig:
        """获取完整Agent配置"""
        return AgentConfig(
            data_source=self.get_data_source_config(),
            analysis=self.get_analysis_config(),
            llm=self.get_llm_config(),
            output=self.get_output_config(),
            logging=self.get_logging_config()
        )

    def _get_env_or_config(self, env_key: str, config_value: Any) -> Any:
        """
        优先从环境变量获取，否则使用配置值

        Args:
            env_key: 环境变量键
            config_value: 配置值

        Returns:
            优先使用的值
        """
        env_value = os.getenv(env_key)
        if env_value:
            return env_value
        return config_value

    def reload(self):
        """重新加载配置文件"""
        self._load_config()
