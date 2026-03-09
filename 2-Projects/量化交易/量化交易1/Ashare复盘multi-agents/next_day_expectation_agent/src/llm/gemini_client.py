"""
Gemini客户端模块

提供与Google Gemini-2.0-Flash模型的集成功能。
"""

import time
from typing import Any, Dict, Optional, List
import google.generativeai as genai
from ..common.logger import get_logger

logger = get_logger(__name__)


class GeminiClient:
    """
    Gemini LLM客户端
    
    提供与Gemini-2.0-Flash模型的交互接口，支持参数配置和错误处理。
    """
    
    def __init__(
        self,
        api_key: str,
        model_name: str = "gemini-2.0-flash-exp",
        temperature: float = 0.7,
        max_tokens: int = 2048,
        top_p: float = 0.95,
        top_k: int = 40,
        timeout: int = 30,
        max_retries: int = 3
    ):
        """
        初始化Gemini客户端
        
        Args:
            api_key: Gemini API密钥
            model_name: 模型名称，默认为gemini-2.0-flash-exp
            temperature: 温度参数，控制输出随机性 (0.0-1.0)
            max_tokens: 最大生成token数
            top_p: nucleus sampling参数
            top_k: top-k sampling参数
            timeout: 请求超时时间（秒）
            max_retries: 最大重试次数
        """
        self.api_key = api_key
        self.model_name = model_name
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.top_p = top_p
        self.top_k = top_k
        self.timeout = timeout
        self.max_retries = max_retries
        
        # 配置API密钥
        genai.configure(api_key=api_key)
        
        # 初始化模型
        self.generation_config = genai.GenerationConfig(
            temperature=temperature,
            max_output_tokens=max_tokens,
            top_p=top_p,
            top_k=top_k
        )
        
        self.model = genai.GenerativeModel(
            model_name=model_name,
            generation_config=self.generation_config
        )
        
        logger.info(
            f"Initialized GeminiClient with model={model_name}, "
            f"temperature={temperature}, max_tokens={max_tokens}"
        )
    
    def generate(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        timeout: Optional[int] = None
    ) -> str:
        """
        生成文本响应
        
        Args:
            prompt: 输入提示词
            system_instruction: 系统指令（可选）
            temperature: 临时覆盖温度参数（可选）
            max_tokens: 临时覆盖最大token数（可选）
            timeout: 临时覆盖超时时间（可选）
            
        Returns:
            生成的文本响应
            
        Raises:
            TimeoutError: 请求超时
            Exception: 其他错误
        """
        # 使用临时参数或默认参数
        temp = temperature if temperature is not None else self.temperature
        max_tok = max_tokens if max_tokens is not None else self.max_tokens
        timeout_val = timeout if timeout is not None else self.timeout
        
        # 如果提供了临时参数，创建临时配置
        if temperature is not None or max_tokens is not None:
            temp_config = genai.GenerationConfig(
                temperature=temp,
                max_output_tokens=max_tok,
                top_p=self.top_p,
                top_k=self.top_k
            )
            model = genai.GenerativeModel(
                model_name=self.model_name,
                generation_config=temp_config
            )
        else:
            model = self.model
        
        # 构建完整提示
        full_prompt = prompt
        if system_instruction:
            full_prompt = f"{system_instruction}\n\n{prompt}"
        
        logger.debug(f"Generating response for prompt (length={len(full_prompt)})")
        
        start_time = time.time()
        
        try:
            # 生成响应
            response = model.generate_content(
                full_prompt,
                request_options={'timeout': timeout_val}
            )
            
            elapsed = time.time() - start_time
            
            # 提取文本
            if response.text:
                result = response.text
                logger.info(
                    f"Generated response successfully in {elapsed:.2f}s "
                    f"(length={len(result)})"
                )
                return result
            else:
                logger.warning("Empty response from Gemini")
                return ""
                
        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f"Error generating response after {elapsed:.2f}s: {e}")
            raise
    
    def generate_with_retry(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        timeout: Optional[int] = None,
        max_retries: Optional[int] = None
    ) -> str:
        """
        带重试机制的生成方法
        
        Args:
            prompt: 输入提示词
            system_instruction: 系统指令（可选）
            temperature: 临时覆盖温度参数（可选）
            max_tokens: 临时覆盖最大token数（可选）
            timeout: 临时覆盖超时时间（可选）
            max_retries: 临时覆盖最大重试次数（可选）
            
        Returns:
            生成的文本响应
            
        Raises:
            Exception: 所有重试失败后抛出最后一次的异常
        """
        retries = max_retries if max_retries is not None else self.max_retries
        last_exception = None
        
        for attempt in range(retries):
            try:
                result = self.generate(
                    prompt=prompt,
                    system_instruction=system_instruction,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    timeout=timeout
                )
                return result
                
            except Exception as e:
                last_exception = e
                logger.warning(
                    f"Attempt {attempt + 1}/{retries} failed: {e}"
                )
                
                # 如果不是最后一次尝试，等待后重试
                if attempt < retries - 1:
                    wait_time = 2 ** attempt  # 指数退避
                    logger.info(f"Waiting {wait_time}s before retry...")
                    time.sleep(wait_time)
        
        # 所有重试都失败
        logger.error(f"All {retries} attempts failed")
        raise last_exception
    
    def generate_structured(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        expected_format: str = "json",
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> str:
        """
        生成结构化响应
        
        Args:
            prompt: 输入提示词
            system_instruction: 系统指令（可选）
            expected_format: 期望的输出格式（json, markdown等）
            temperature: 临时覆盖温度参数（可选）
            max_tokens: 临时覆盖最大token数（可选）
            
        Returns:
            生成的结构化文本响应
        """
        # 添加格式指令
        format_instruction = f"\n\nPlease provide the response in {expected_format} format."
        enhanced_prompt = prompt + format_instruction
        
        return self.generate_with_retry(
            prompt=enhanced_prompt,
            system_instruction=system_instruction,
            temperature=temperature,
            max_tokens=max_tokens
        )
    
    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> str:
        """
        多轮对话
        
        Args:
            messages: 消息列表，每个消息包含role和content
                     例如: [{"role": "user", "content": "Hello"}]
            temperature: 临时覆盖温度参数（可选）
            max_tokens: 临时覆盖最大token数（可选）
            
        Returns:
            生成的响应
        """
        # 使用临时参数或默认参数
        temp = temperature if temperature is not None else self.temperature
        max_tok = max_tokens if max_tokens is not None else self.max_tokens
        
        # 创建配置
        temp_config = genai.GenerationConfig(
            temperature=temp,
            max_output_tokens=max_tok,
            top_p=self.top_p,
            top_k=self.top_k
        )
        
        model = genai.GenerativeModel(
            model_name=self.model_name,
            generation_config=temp_config
        )
        
        # 启动聊天会话
        chat = model.start_chat(history=[])
        
        # 发送消息
        for msg in messages[:-1]:  # 除了最后一条
            if msg["role"] == "user":
                chat.send_message(msg["content"])
        
        # 发送最后一条消息并获取响应
        last_message = messages[-1]["content"]
        response = chat.send_message(last_message)
        
        return response.text if response.text else ""
    
    def update_config(
        self,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        top_p: Optional[float] = None,
        top_k: Optional[int] = None,
        timeout: Optional[int] = None,
        max_retries: Optional[int] = None
    ) -> None:
        """
        更新客户端配置
        
        Args:
            temperature: 新的温度参数
            max_tokens: 新的最大token数
            top_p: 新的top_p参数
            top_k: 新的top_k参数
            timeout: 新的超时时间
            max_retries: 新的最大重试次数
        """
        if temperature is not None:
            self.temperature = temperature
        if max_tokens is not None:
            self.max_tokens = max_tokens
        if top_p is not None:
            self.top_p = top_p
        if top_k is not None:
            self.top_k = top_k
        if timeout is not None:
            self.timeout = timeout
        if max_retries is not None:
            self.max_retries = max_retries
        
        # 重新创建生成配置
        self.generation_config = genai.GenerationConfig(
            temperature=self.temperature,
            max_output_tokens=self.max_tokens,
            top_p=self.top_p,
            top_k=self.top_k
        )
        
        # 重新创建模型
        self.model = genai.GenerativeModel(
            model_name=self.model_name,
            generation_config=self.generation_config
        )
        
        logger.info("Updated GeminiClient configuration")
    
    def get_config(self) -> Dict[str, Any]:
        """
        获取当前配置
        
        Returns:
            配置字典
        """
        return {
            "model_name": self.model_name,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "top_p": self.top_p,
            "top_k": self.top_k,
            "timeout": self.timeout,
            "max_retries": self.max_retries
        }
