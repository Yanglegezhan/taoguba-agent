"""统一LLM客户端 - 基于OpenAI兼容接口"""
import time
import requests
from typing import List, Optional

from openai import OpenAI

from .base import LLMConfig, LLMMessage, LLMResponse, LLMError


class LLMClient:
    """统一LLM客户端，支持所有OpenAI兼容的API"""

    def __init__(self, config: LLMConfig):
        self.config = config
        self._client: Optional[OpenAI] = None
        self._is_gemini = config.provider == "gemini"

    def _get_client(self) -> OpenAI:
        """获取OpenAI客户端"""
        if self._client is None and not self._is_gemini:
            # 创建自定义的 httpx 客户端，禁用 SSL 验证（用于解决证书问题）
            import httpx
            http_client = httpx.Client(
                verify=False,  # 禁用 SSL 验证
                timeout=httpx.Timeout(None if self.config.timeout is None else self.config.timeout, connect=10.0)
            )

            self._client = OpenAI(
                api_key=self.config.api_key,
                base_url=self.config.base_url,
                timeout=None if self.config.timeout is None else self.config.timeout,
                http_client=http_client,
                max_retries=0  # 禁用重试
            )
        return self._client

    def _call_gemini(self, messages: List[LLMMessage]) -> LLMResponse:
        """调用Gemini API"""
        # 转换消息格式
        contents = []
        system_instruction = None

        for msg in messages:
            if msg.role == "system":
                system_instruction = msg.content
            else:
                contents.append({
                    "role": "user" if msg.role == "user" else "model",
                    "parts": [{"text": msg.content}]
                })

        # 构建请求
        url = f"{self.config.base_url}/models/{self.config.model}:generateContent?key={self.config.api_key}"

        payload = {
            "contents": contents,
            "generationConfig": {
                "temperature": self.config.temperature,
            }
        }

        # 只有在明确设置了max_tokens时才添加限制
        if self.config.max_tokens and self.config.max_tokens > 0:
            payload["generationConfig"]["maxOutputTokens"] = self.config.max_tokens

        if system_instruction:
            payload["systemInstruction"] = {
                "parts": [{"text": system_instruction}]
            }

        # 发送请求（禁用代理）
        response = requests.post(
            url,
            json=payload,
            timeout=self.config.timeout,
            verify=False,
            proxies={'http': None, 'https': None}  # 禁用代理
        )

        if response.status_code != 200:
            raise Exception(f"Gemini API错误: {response.status_code} - {response.text}")

        result = response.json()

        # 解析响应
        if "candidates" not in result or len(result["candidates"]) == 0:
            raise Exception(f"Gemini返回空响应: {result}")

        content = result["candidates"][0]["content"]["parts"][0]["text"]

        # 获取token使用情况
        usage_metadata = result.get("usageMetadata", {})

        return LLMResponse(
            content=content,
            usage={
                "prompt_tokens": usage_metadata.get("promptTokenCount", 0),
                "completion_tokens": usage_metadata.get("candidatesTokenCount", 0),
                "total_tokens": usage_metadata.get("totalTokenCount", 0),
            },
            model=self.config.model,
            raw_response=result
        )

    def chat(self, messages: List[LLMMessage]) -> LLMResponse:
        """发送消息并获取响应，不重试"""
        if self._is_gemini:
            return self._call_gemini(messages)

        client = self._get_client()
        formatted_messages = [msg.to_dict() for msg in messages]

        try:
            # 构建请求参数
            request_params = {
                "model": self.config.model,
                "messages": formatted_messages,
                "temperature": self.config.temperature,
                **self.config.extra_params
            }

            # 只有当 max_tokens 不为 None 时才添加该参数
            if self.config.max_tokens is not None:
                request_params["max_tokens"] = self.config.max_tokens

            response = client.chat.completions.create(**request_params)

            # 检查响应内容
            content = response.choices[0].message.content or ""

            # 记录响应信息
            import logging
            logger = logging.getLogger(__name__)
            logger.debug(f"LLM API响应: model={response.model}, "
                       f"finish_reason={response.choices[0].finish_reason}, "
                       f"content_length={len(content)}")

            # 如果内容为空，记录详细信息并抛出错误
            if not content or content.strip() == "":
                logger.warning(f"LLM返回空内容, finish_reason={response.choices[0].finish_reason}")
                logger.warning(f"完整响应: {response}")
                # 抛出错误，不再重试
                raise ValueError("LLM返回了空响应")

            return LLMResponse(
                content=content,
                usage={
                    "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                    "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                    "total_tokens": response.usage.total_tokens if response.usage else 0,
                },
                model=response.model,
                raw_response=response
            )
        except Exception as e:
            raise LLMError(
                error_code="LLM_API_ERROR",
                error_message=str(e),
                retryable=False,  # 不再标记为可重试
                raw_error=e
            )

    def validate_config(self) -> tuple[bool, Optional[str]]:
        """验证配置"""
        return self.config.validate()

    def _is_retryable(self, error: Exception) -> bool:
        """判断是否可重试"""
        error_str = str(error).lower()
        retryable_keywords = ["timeout", "rate limit", "429", "500", "502", "503", "504"]
        return any(kw in error_str for kw in retryable_keywords)


def create_client(
    api_key: str,
    model: str = "glm-4",
    provider: str = "zhipu",
    base_url: Optional[str] = None,
    **kwargs
) -> LLMClient:
    """快速创建LLM客户端

    Args:
        api_key: API密钥
        model: 模型名称
        provider: 提供商（zhipu/openai/deepseek/qwen）
        base_url: 自定义API地址（可选）
        **kwargs: 其他配置参数

    Examples:
        # 智谱GLM-4（默认）
        client = create_client("your-api-key")

        # OpenAI GPT-4
        client = create_client("your-api-key", model="gpt-4", provider="openai")

        # DeepSeek
        client = create_client("your-api-key", model="deepseek-chat", provider="deepseek")

        # 自定义API地址
        client = create_client("your-api-key", model="xxx", base_url="https://your-api.com/v1")
    """
    config = LLMConfig(
        api_key=api_key,
        model=model,
        provider=provider,
        base_url=base_url,
        **kwargs
    )
    return LLMClient(config)
