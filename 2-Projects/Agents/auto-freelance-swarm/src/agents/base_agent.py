"""
智能体基类
定义所有智能体的通用接口和方法
"""

import os
import json
import yaml
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path

# 配置日志
logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """
    智能体基类
    
    提供所有智能体的通用功能:
    - LLM 调用
    - 配置管理
    - 日志记录
    - 工具注册
    """

    def __init__(
        self,
        name: str,
        config: Optional[Dict[str, Any]] = None,
        llm_provider=None,
        tools: Optional[List] = None
    ):
        """
        初始化智能体
        
        Args:
            name: 智能体名称
            config: 智能体配置
            llm_provider: LLM 提供者
            tools: 可用工具列表
        """
        self.name = name
        self.config = config or {}
        self.llm_provider = llm_provider
        self.tools = tools or []
        
        # 创建工具字典，便于快速查找
        self.tool_dict = {tool.name: tool for tool in self.tools}
        
        # 加载系统提示
        self.system_prompt = self._load_system_prompt()
        
        # 对话历史
        self.conversation_history: List[Dict[str, str]] = []
        
        logger.info(f"智能体 {name} 初始化完成")

    def _load_system_prompt(self) -> str:
        """加载系统提示"""
        return self.config.get("system_prompt", "")

    @abstractmethod
    async def execute(self, input_data: Any, context: Optional[Dict] = None) -> Dict[str, Any]:
        """
        执行智能体任务
        
        Args:
            input_data: 输入数据
            context: 上下文信息
            
        Returns:
            执行结果
        """
        pass

    async def call_llm(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> str:
        """
        调用 LLM
        
        Args:
            messages: 消息列表
            temperature: 温度参数
            max_tokens: 最大 token 数
            **kwargs: 其他参数
            
        Returns:
            LLM 响应
        """
        if not self.llm_provider:
            raise ValueError("LLM provider 未设置")
        
        try:
            response = await self.llm_provider.chat.completions.create(
                model=self.config.get("model", "gpt-4o"),
                messages=messages,
                temperature=temperature or self.config.get("temperature", 0.7),
                max_tokens=max_tokens or self.config.get("max_tokens", 2000),
                **kwargs
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"LLM 调用失败: {e}")
            raise

    async def call_llm_with_tools(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        调用 LLM 并使用工具
        
        Args:
            messages: 消息列表
            tools: 工具定义列表
            **kwargs: 其他参数
            
        Returns:
            LLM 响应，包含工具调用信息
        """
        if not self.llm_provider:
            raise ValueError("LLM provider 未设置")
        
        try:
            response = await self.llm_provider.chat.completions.create(
                model=self.config.get("model", "gpt-4o"),
                messages=messages,
                tools=tools or [],
                **kwargs
            )
            
            # 解析响应
            result = {
                "content": response.choices[0].message.content,
                "tool_calls": []
            }
            
            # 检查是否有工具调用
            if response.choices[0].message.tool_calls:
                for tool_call in response.choices[0].message.tool_calls:
                    result["tool_calls"].append({
                        "id": tool_call.id,
                        "name": tool_call.function.name,
                        "arguments": json.loads(tool_call.function.arguments)
                    })
            
            return result
        except Exception as e:
            logger.error(f"LLM 工具调用失败: {e}")
            raise

    async def execute_tool(self, tool_name: str, **kwargs) -> Any:
        """
        执行工具
        
        Args:
            tool_name: 工具名称
            **kwargs: 工具参数
            
        Returns:
            工具执行结果
        """
        if tool_name not in self.tool_dict:
            raise ValueError(f"工具 {tool_name} 不存在")
        
        tool = self.tool_dict[tool_name]
        return await tool.execute(**kwargs)

    def add_message(self, role: str, content: str):
        """添加对话消息"""
        self.conversation_history.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })

    def clear_history(self):
        """清空对话历史"""
        self.conversation_history = []

    def get_messages(self) -> List[Dict[str, str]]:
        """获取对话历史"""
        messages = []
        
        # 添加系统提示
        if self.system_prompt:
            messages.append({
                "role": "system",
                "content": self.system_prompt
            })
        
        # 添加对话历史
        messages.extend(self.conversation_history)
        
        return messages

    def save_conversation(self, filepath: str):
        """保存对话历史"""
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.conversation_history, f, ensure_ascii=False, indent=2)

    def load_conversation(self, filepath: str):
        """加载对话历史"""
        with open(filepath, 'r', encoding='utf-8') as f:
            self.conversation_history = json.load(f)


class AgentTool(ABC):
    """
    智能体工具基类
    """

    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description

    @abstractmethod
    async def execute(self, **kwargs) -> Any:
        """执行工具"""
        pass

    def get_definition(self) -> Dict[str, Any]:
        """获取工具定义 (用于 LLM 函数调用)"""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.get_parameters()
            }
        }

    @abstractmethod
    def get_parameters(self) -> Dict[str, Any]:
        """获取参数定义"""
        pass


def load_config(config_path: str) -> Dict[str, Any]:
    """加载配置文件"""
    path = Path(config_path)
    
    if not path.exists():
        logger.warning(f"配置文件不存在: {config_path}")
        return {}
    
    if path.suffix in ['.yaml', '.yml']:
        with open(path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    elif path.suffix == '.json':
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    else:
        raise ValueError(f"不支持的配置文件格式: {path.suffix}")
