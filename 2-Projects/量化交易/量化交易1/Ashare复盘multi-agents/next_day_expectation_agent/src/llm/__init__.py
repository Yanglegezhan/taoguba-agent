"""
LLM集成层

提供与大语言模型的集成功能，包括Gemini客户端和规则引擎降级方案。
"""

from .gemini_client import GeminiClient
from .rule_based_engine import RuleBasedEngine
from .llm_manager import LLMManager, LLMStatus
from .llm_factory import (
    create_gemini_client,
    create_rule_based_engine,
    create_llm_manager,
    get_llm_manager
)

__all__ = [
    'GeminiClient',
    'RuleBasedEngine',
    'LLMManager',
    'LLMStatus',
    'create_gemini_client',
    'create_rule_based_engine',
    'create_llm_manager',
    'get_llm_manager'
]
