"""
网络搜索工具
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional

from ..agents.base_agent import AgentTool

logger = logging.getLogger(__name__)


class WebSearchTool(AgentTool):
    """网络搜索工具"""
    
    def __init__(self):
        description = "搜索网络信息。用于查找项目需求、技术文档等。"
        super().__init__("web_search", description)
    
    async def execute(self, query: str, num_results: int = 5, **kwargs) -> str:
        """执行搜索"""
        try:
            # 使用批量搜索
            from mcp__matrix__batch_web_search import mcp__matrix__batch_web_search
            
            result = await mcp__matrix__batch_web_search(
                queries=[{
                    "query": query,
                    "num_results": num_results
                }],
                display_text=f"搜索: {query}"
            )
            
            if result and len(result) > 0:
                return str(result[0])
            else:
                return "未找到相关结果"
        except Exception as e:
            logger.error(f"搜索失败: {e}")
            return f"搜索失败: {str(e)}"
    
    def get_parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "搜索关键词"
                },
                "num_results": {
                    "type": "integer",
                    "description": "返回结果数量",
                    "default": 5
                }
            },
            "required": ["query"]
        }


class WebExtractTool(AgentTool):
    """网页内容提取工具"""
    
    def __init__(self):
        description = "提取网页内容。输入URL，返回页面文本内容。"
        super().__init__("web_extract", description)
    
    async def execute(self, url: str, prompt: str = None, **kwargs) -> str:
        """提取网页内容"""
        try:
            from mcp__matrix__extract_content_from_websites import mcp__matrix__extract_content_from_websites
            
            task_prompt = prompt or "提取页面主要内容"
            
            result = await mcp__matrix__extract_content_from_websites(
                tasks=[{
                    "url": url,
                    "prompt": task_prompt
                }],
                display_text=f"提取: {url}"
            )
            
            if result and len(result) > 0:
                return str(result[0])
            else:
                return "无法提取页面内容"
        except Exception as e:
            logger.error(f"提取失败: {e}")
            return f"提取失败: {str(e)}"
    
    def get_parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "要提取的网页URL"
                },
                "prompt": {
                    "type": "string",
                    "description": "提取提示",
                    "default": "提取页面主要内容"
                }
            },
            "required": ["url"]
        }
