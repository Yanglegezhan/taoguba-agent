"""
LLM工厂模块

提供便捷的LLM实例创建功能。
"""

from typing import Optional
from ..common.config import ConfigManager, get_config
from ..common.logger import get_logger
from .gemini_client import GeminiClient
from .rule_based_engine import RuleBasedEngine
from .llm_manager import LLMManager

logger = get_logger(__name__)


def create_gemini_client(
    config_manager: Optional[ConfigManager] = None,
    api_key: Optional[str] = None,
    **kwargs
) -> GeminiClient:
    """
    创建Gemini客户端实例
    
    Args:
        config_manager: 配置管理器（可选）
        api_key: API密钥（可选，如果不提供则从配置读取）
        **kwargs: 其他配置参数
        
    Returns:
        GeminiClient实例
    """
    if config_manager is None:
        config_manager = get_config()
    
    llm_config = config_manager.system_config.llm
    
    # 使用提供的参数或配置中的参数
    client_config = {
        "api_key": api_key or llm_config.api_key,
        "model_name": kwargs.get("model_name", llm_config.model_name),
        "temperature": kwargs.get("temperature", llm_config.temperature),
        "max_tokens": kwargs.get("max_tokens", llm_config.max_tokens),
        "top_p": kwargs.get("top_p", llm_config.top_p),
        "top_k": kwargs.get("top_k", llm_config.top_k),
        "timeout": kwargs.get("timeout", llm_config.timeout),
        "max_retries": kwargs.get("max_retries", llm_config.max_retries)
    }
    
    if not client_config["api_key"]:
        logger.warning("No API key provided, GeminiClient may not work properly")
    
    return GeminiClient(**client_config)


def create_rule_based_engine() -> RuleBasedEngine:
    """
    创建规则引擎实例
    
    Returns:
        RuleBasedEngine实例
    """
    return RuleBasedEngine()


def create_llm_manager(
    config_manager: Optional[ConfigManager] = None,
    api_key: Optional[str] = None,
    **kwargs
) -> LLMManager:
    """
    创建LLM管理器实例
    
    Args:
        config_manager: 配置管理器（可选）
        api_key: API密钥（可选）
        **kwargs: 其他配置参数
        
    Returns:
        LLMManager实例
    """
    if config_manager is None:
        config_manager = get_config()
    
    llm_config = config_manager.system_config.llm
    
    # 创建Gemini客户端
    gemini_client = create_gemini_client(
        config_manager=config_manager,
        api_key=api_key,
        **kwargs
    )
    
    # 创建规则引擎
    rule_based_engine = create_rule_based_engine()
    
    # 创建LLM管理器
    manager_config = {
        "max_retries": kwargs.get("max_retries", llm_config.max_retries),
        "timeout": kwargs.get("timeout", llm_config.timeout),
        "enable_fallback": kwargs.get("enable_fallback", llm_config.enable_fallback)
    }
    
    return LLMManager(
        gemini_client=gemini_client,
        rule_based_engine=rule_based_engine,
        **manager_config
    )


# 全局LLM管理器实例（延迟初始化）
_global_llm_manager: Optional[LLMManager] = None


def get_llm_manager(
    config_manager: Optional[ConfigManager] = None,
    force_recreate: bool = False
) -> LLMManager:
    """
    获取全局LLM管理器实例
    
    Args:
        config_manager: 配置管理器（可选）
        force_recreate: 是否强制重新创建实例
        
    Returns:
        LLMManager实例
    """
    global _global_llm_manager
    
    if _global_llm_manager is None or force_recreate:
        _global_llm_manager = create_llm_manager(config_manager=config_manager)
        logger.info("Created global LLMManager instance")
    
    return _global_llm_manager
