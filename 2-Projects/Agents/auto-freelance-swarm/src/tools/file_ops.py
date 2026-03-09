"""
文件操作工具
"""

import os
import asyncio
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path

from ..agents.base_agent import AgentTool

logger = logging.getLogger(__name__)


class FileReadTool(AgentTool):
    """文件读取工具"""
    
    def __init__(self, allowed_paths: List[str] = None):
        description = "读取文件内容。输入文件路径，返回文件内容。"
        super().__init__("read_file", description)
        self.allowed_paths = allowed_paths or ["./workspace"]
    
    async def execute(self, filepath: str, **kwargs) -> str:
        """读取文件"""
        # 安全检查
        if not self._is_allowed(filepath):
            return f"错误: 无权访问文件 {filepath}"
        
        try:
            path = Path(filepath)
            if not path.exists():
                return f"错误: 文件不存在 {filepath}"
            
            content = path.read_text(encoding='utf-8')
            return content
        except Exception as e:
            logger.error(f"读取文件失败: {e}")
            return f"错误: 读取文件失败 - {str(e)}"
    
    def _is_allowed(self, filepath: str) -> bool:
        """检查是否允许访问"""
        filepath = str(Path(filepath).resolve())
        
        for allowed in self.allowed_paths:
            allowed = str(Path(allowed).resolve())
            if filepath.startswith(allowed):
                return True
        
        return False
    
    def get_parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "filepath": {
                    "type": "string",
                    "description": "要读取的文件路径"
                }
            },
            "required": ["filepath"]
        }


class FileWriteTool(AgentTool):
    """文件写入工具"""
    
    def __init__(self, allowed_paths: List[str] = None):
        description = "写入内容到文件。如果文件不存在则创建，存在则覆盖。"
        super().__init__("write_file", description)
        self.allowed_paths = allowed_paths or ["./workspace"]
    
    async def execute(self, filepath: str, content: str, **kwargs) -> str:
        """写入文件"""
        # 安全检查
        if not self._is_allowed(filepath):
            return f"错误: 无权写入文件 {filepath}"
        
        # 禁止写入敏感文件
        forbidden = [".env", ".git", ".ssh", "config.yaml", "settings.yaml"]
        for f in forbidden:
            if f in filepath:
                return f"错误: 禁止写入敏感文件 {filepath}"
        
        try:
            path = Path(filepath)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding='utf-8')
            logger.info(f"文件已写入: {filepath}")
            return f"成功: 文件已写入 {filepath}"
        except Exception as e:
            logger.error(f"写入文件失败: {e}")
            return f"错误: 写入文件失败 - {str(e)}"
    
    def _is_allowed(self, filepath: str) -> bool:
        """检查是否允许写入"""
        filepath = str(Path(filepath).resolve())
        
        for allowed in self.allowed_paths:
            allowed = str(Path(allowed).resolve())
            if filepath.startswith(allowed):
                return True
        
        return False
    
    def get_parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "filepath": {
                    "type": "string",
                    "description": "要写入的文件路径"
                },
                "content": {
                    "type": "string",
                    "description": "要写入的内容"
                }
            },
            "required": ["filepath", "content"]
        }


class FileListTool(AgentTool):
    """文件列表工具"""
    
    def __init__(self, allowed_paths: List[str] = None):
        description = "列出目录下的文件。输入目录路径，返回文件列表。"
        super().__init__("list_files", description)
        self.allowed_paths = allowed_paths or ["./workspace"]
    
    async def execute(self, directory: str = ".", pattern: str = "*", **kwargs) -> str:
        """列出文件"""
        # 安全检查
        if not self._is_allowed(directory):
            return f"错误: 无权访问目录 {directory}"
        
        try:
            path = Path(directory)
            if not path.exists():
                return f"错误: 目录不存在 {directory}"
            
            if not path.is_dir():
                return f"错误: {directory} 不是目录"
            
            # 列出文件
            files = []
            for f in path.glob(pattern):
                if f.is_file():
                    rel_path = f.relative_to(path)
                    files.append(str(rel_path))
            
            if not files:
                return f"目录 {directory} 中没有匹配的文件"
            
            return "\n".join(files)
        except Exception as e:
            logger.error(f"列出文件失败: {e}")
            return f"错误: 列出文件失败 - {str(e)}"
    
    def _is_allowed(self, directory: str) -> bool:
        """检查是否允许访问"""
        directory = str(Path(directory).resolve())
        
        for allowed in self.allowed_paths:
            allowed = str(Path(allowed).resolve())
            if directory.startswith(allowed):
                return True
        
        return False
    
    def get_parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "directory": {
                    "type": "string",
                    "description": "要列出的目录路径"
                },
                "pattern": {
                    "type": "string",
                    "description": "文件匹配模式，如 *.py",
                    "default": "*"
                }
            },
            "required": ["directory"]
        }


class RunCommandTool(AgentTool):
    """运行命令工具"""
    
    def __init__(self, allowed_commands: List[str] = None):
        description = "在终端运行命令。用于执行Python脚本、安装依赖等。"
        super().__init__("run_command", description)
        self.allowed_commands = allowed_commands or ["python", "pip", "git", "npm", "node"]
        self.forbidden_patterns = ["rm -rf", "del /f", "format", "mkfs", "> /dev"]
    
    async def execute(self, command: str, cwd: str = None, **kwargs) -> str:
        """运行命令"""
        # 安全检查
        if not self._is_allowed(command):
            return f"错误: 命令不允许执行"
        
        try:
            import subprocess
            
            result = subprocess.run(
                command,
                shell=True,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=300  # 5分钟超时
            )
            
            output = result.stdout
            if result.stderr:
                output += f"\nstderr: {result.stderr}"
            
            if result.returncode != 0:
               n命令返回非零退出码: output += f"\ {result.returncode}"
            
            return output
        except subprocess.TimeoutExpired:
            return "错误: 命令执行超时"
        except Exception as e:
            logger.error(f"运行命令失败: {e}")
            return f"错误: 运行命令失败 - {str(e)}"
    
    def _is_allowed(self, command: str) -> bool:
        """检查命令是否允许"""
        # 检查禁止的模式
        for pattern in self.forbidden_patterns:
            if pattern in command:
                return False
        
        # 检查是否在允许列表中
        command_name = command.split()[0] if command.split() else ""
        return command_name in self.allowed_commands
    
    def get_parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "要执行的命令"
                },
                "cwd": {
                    "type": "string",
                    "description": "命令执行的工作目录"
                }
            },
            "required": ["command"]
        }
