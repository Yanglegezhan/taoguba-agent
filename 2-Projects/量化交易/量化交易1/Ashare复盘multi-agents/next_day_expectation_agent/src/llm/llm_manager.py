"""
LLM管理器模块

提供统一的LLM调用接口，包含重试、错误处理和降级逻辑。
"""

import time
from typing import Any, Dict, Optional, List
from enum import Enum
from ..common.logger import get_logger
from .gemini_client import GeminiClient
from .rule_based_engine import RuleBasedEngine

logger = get_logger(__name__)


class LLMStatus(Enum):
    """LLM状态枚举"""
    AVAILABLE = "available"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"


class LLMManager:
    """
    LLM管理器
    
    提供统一的LLM调用接口，自动处理重试、超时和降级。
    """
    
    def __init__(
        self,
        gemini_client: GeminiClient,
        rule_based_engine: RuleBasedEngine,
        max_retries: int = 3,
        timeout: int = 30,
        enable_fallback: bool = True
    ):
        """
        初始化LLM管理器
        
        Args:
            gemini_client: Gemini客户端实例
            rule_based_engine: 规则引擎实例
            max_retries: 最大重试次数
            timeout: 超时时间（秒）
            enable_fallback: 是否启用降级方案
        """
        self.gemini_client = gemini_client
        self.rule_based_engine = rule_based_engine
        self.max_retries = max_retries
        self.timeout = timeout
        self.enable_fallback = enable_fallback
        self.status = LLMStatus.AVAILABLE
        
        # 统计信息
        self.stats = {
            "total_calls": 0,
            "successful_calls": 0,
            "failed_calls": 0,
            "fallback_calls": 0,
            "total_retries": 0,
            "total_time": 0.0
        }
        
        logger.info(
            f"Initialized LLMManager with max_retries={max_retries}, "
            f"timeout={timeout}, enable_fallback={enable_fallback}"
        )
    
    def call(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        timeout: Optional[int] = None,
        task_type: str = "general"
    ) -> Dict[str, Any]:
        """
        调用LLM生成响应
        
        Args:
            prompt: 输入提示词
            system_instruction: 系统指令（可选）
            temperature: 温度参数（可选）
            max_tokens: 最大token数（可选）
            timeout: 超时时间（可选）
            task_type: 任务类型，用于降级时的规则选择
            
        Returns:
            包含响应和元数据的字典:
            {
                "response": str,  # 生成的响应
                "status": str,    # 状态: "success", "fallback", "error"
                "source": str,    # 来源: "gemini", "rule_based"
                "retries": int,   # 重试次数
                "elapsed": float  # 耗时（秒）
            }
        """
        self.stats["total_calls"] += 1
        start_time = time.time()
        
        timeout_val = timeout if timeout is not None else self.timeout
        retries = 0
        last_exception = None
        
        # 尝试使用Gemini
        for attempt in range(self.max_retries):
            try:
                logger.debug(f"Calling Gemini (attempt {attempt + 1}/{self.max_retries})")
                
                response = self.gemini_client.generate(
                    prompt=prompt,
                    system_instruction=system_instruction,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    timeout=timeout_val
                )
                
                elapsed = time.time() - start_time
                self.stats["successful_calls"] += 1
                self.stats["total_retries"] += retries
                self.stats["total_time"] += elapsed
                self.status = LLMStatus.AVAILABLE
                
                logger.info(
                    f"LLM call succeeded on attempt {attempt + 1} "
                    f"in {elapsed:.2f}s"
                )
                
                return {
                    "response": response,
                    "status": "success",
                    "source": "gemini",
                    "retries": retries,
                    "elapsed": elapsed
                }
                
            except TimeoutError as e:
                retries += 1
                last_exception = e
                logger.warning(
                    f"LLM call timeout on attempt {attempt + 1}: {e}"
                )
                
                # 如果不是最后一次尝试，等待后重试
                if attempt < self.max_retries - 1:
                    wait_time = 2 ** attempt  # 指数退避
                    logger.info(f"Waiting {wait_time}s before retry...")
                    time.sleep(wait_time)
                    
            except Exception as e:
                retries += 1
                last_exception = e
                logger.error(
                    f"LLM call error on attempt {attempt + 1}: {e}"
                )
                
                # 如果不是最后一次尝试，等待后重试
                if attempt < self.max_retries - 1:
                    wait_time = 2 ** attempt
                    logger.info(f"Waiting {wait_time}s before retry...")
                    time.sleep(wait_time)
        
        # 所有重试都失败，尝试降级
        elapsed = time.time() - start_time
        self.stats["failed_calls"] += 1
        self.stats["total_retries"] += retries
        self.stats["total_time"] += elapsed
        
        if self.enable_fallback:
            logger.warning(
                f"All {self.max_retries} attempts failed, "
                f"falling back to rule-based engine"
            )
            self.status = LLMStatus.DEGRADED
            
            try:
                fallback_response = self.rule_based_engine.analyze(
                    prompt=prompt,
                    task_type=task_type
                )
                
                self.stats["fallback_calls"] += 1
                
                return {
                    "response": fallback_response,
                    "status": "fallback",
                    "source": "rule_based",
                    "retries": retries,
                    "elapsed": elapsed,
                    "error": str(last_exception)
                }
                
            except Exception as fallback_error:
                logger.error(f"Fallback also failed: {fallback_error}")
                self.status = LLMStatus.UNAVAILABLE
                
                return {
                    "response": "",
                    "status": "error",
                    "source": "none",
                    "retries": retries,
                    "elapsed": elapsed,
                    "error": f"LLM: {last_exception}, Fallback: {fallback_error}"
                }
        else:
            logger.error("Fallback disabled, returning error")
            self.status = LLMStatus.UNAVAILABLE
            
            return {
                "response": "",
                "status": "error",
                "source": "none",
                "retries": retries,
                "elapsed": elapsed,
                "error": str(last_exception)
            }
    
    def call_batch(
        self,
        prompts: List[str],
        system_instruction: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        task_type: str = "general"
    ) -> List[Dict[str, Any]]:
        """
        批量调用LLM
        
        Args:
            prompts: 提示词列表
            system_instruction: 系统指令（可选）
            temperature: 温度参数（可选）
            max_tokens: 最大token数（可选）
            task_type: 任务类型
            
        Returns:
            响应列表
        """
        results = []
        
        for i, prompt in enumerate(prompts):
            logger.info(f"Processing batch item {i + 1}/{len(prompts)}")
            
            result = self.call(
                prompt=prompt,
                system_instruction=system_instruction,
                temperature=temperature,
                max_tokens=max_tokens,
                task_type=task_type
            )
            
            results.append(result)
        
        return results
    
    def get_status(self) -> Dict[str, Any]:
        """
        获取LLM管理器状态
        
        Returns:
            状态字典
        """
        avg_time = (
            self.stats["total_time"] / self.stats["total_calls"]
            if self.stats["total_calls"] > 0
            else 0.0
        )
        
        success_rate = (
            self.stats["successful_calls"] / self.stats["total_calls"] * 100
            if self.stats["total_calls"] > 0
            else 0.0
        )
        
        return {
            "status": self.status.value,
            "stats": {
                **self.stats,
                "avg_time": avg_time,
                "success_rate": success_rate
            },
            "config": {
                "max_retries": self.max_retries,
                "timeout": self.timeout,
                "enable_fallback": self.enable_fallback
            }
        }
    
    def reset_stats(self) -> None:
        """重置统计信息"""
        self.stats = {
            "total_calls": 0,
            "successful_calls": 0,
            "failed_calls": 0,
            "fallback_calls": 0,
            "total_retries": 0,
            "total_time": 0.0
        }
        logger.info("Reset LLM statistics")
    
    def update_config(
        self,
        max_retries: Optional[int] = None,
        timeout: Optional[int] = None,
        enable_fallback: Optional[bool] = None
    ) -> None:
        """
        更新配置
        
        Args:
            max_retries: 新的最大重试次数
            timeout: 新的超时时间
            enable_fallback: 是否启用降级
        """
        if max_retries is not None:
            self.max_retries = max_retries
        if timeout is not None:
            self.timeout = timeout
        if enable_fallback is not None:
            self.enable_fallback = enable_fallback
        
        logger.info(
            f"Updated LLMManager config: max_retries={self.max_retries}, "
            f"timeout={self.timeout}, enable_fallback={self.enable_fallback}"
        )
