"""
Coder Agent (Agent 2): 项目执行智能体
负责根据项目规格说明书生成代码或内容
"""

import os
import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path

from .base_agent import BaseAgent

logger = logging.getLogger(__name__)


class CoderAgent(BaseAgent):
    """
    Coder Agent - 项目执行智能体
    
    核心功能:
    - 根据项目规格说明书生成代码
    - 创建项目目录结构
    - 实现核心功能模块
    - 编写测试用例
    - 生成项目文档
    """

    def __init__(self, config: Dict[str, Any], llm_provider=None, workspace_path: str = "./workspace"):
        # 设置系统提示
        system_prompt = """你是 Auto-Freelance Swarm 的 Coder Agent (代码工程师)。

你的主要职责是:
1. 根据项目规格说明书生成高质量代码
2. 创建合理的项目目录结构
3. 实现核心功能模块
4. 编写测试用例确保代码质量
5. 生成必要的项目文档

技术要求:
- 遵循语言最佳实践和编码规范
- 代码要有适当的注释
- 注重代码的可读性和可维护性
- 考虑错误处理和边界情况
- 确保代码的安全性

交付要求:
- 所有代码必须在指定的工作空间目录内生成
- 禁止写入工作空间外的任何文件
- 生成完整的可运行项目
- 包含基本的README文档

安全准则:
- 不得生成任何恶意代码
- 不得尝试访问受限资源
- 不得生成包含敏感信息的代码
- 所有文件操作限制在工作目录内
"""
        
        config["system_prompt"] = system_prompt
        super().__init__("CoderAgent", config, llm_provider)
        
        self.workspace_path = Path(workspace_path)
        self.current_project = None

    async def execute(self, input_data: Any, context: Optional[Dict] = None) -> Dict[str, Any]:
        """
        执行代码生成任务
        
        Args:
            input_data: 项目规格说明书或需求描述
            context: 上下文信息
            
        Returns:
            生成的代码信息
        """
        logger.info("开始执行代码生成任务")
        
        # 解析输入
        if isinstance(input_data, dict):
            specs = input_data.get("specs", "")
            project_name = input_data.get("project_name", f"project_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        else:
            specs = str(input_data)
            project_name = f"project_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # 创建项目目录
        project_path = self.workspace_path / project_name
        project_path.mkdir(parents=True, exist_ok=True)
        
        self.current_project = {
            "name": project_name,
            "path": str(project_path),
            "created_at": datetime.now().isoformat()
        }
        
        # 生成代码
        code_files = await self.generate_code(specs, project_path, context)
        
        # 生成README
        await self.generate_readme(specs, project_path)
        
        logger.info(f"代码生成完成，项目路径: {project_path}")
        
        return {
            "status": "success",
            "project_name": project_name,
            "project_path": str(project_path),
            "files_created": len(code_files),
            "files": code_files,
            "created_at": datetime.now().isoformat()
        }

    async def generate_code(
        self,
        specs: str,
        project_path: Path,
        context: Optional[Dict] = None
    ) -> List[Dict[str, Any]]:
        """
        根据规格说明书生成代码
        
        Args:
            specs: 项目规格说明书
            project_path: 项目路径
            context: 上下文信息
            
        Returns:
            创建的文件列表
        """
        
        # 分析项目类型
        project_type = await self.detect_project_type(specs)
        logger.info(f"检测到项目类型: {project_type}")
        
        files = []
        
        if project_type == "web":
            files = await self.generate_web_project(specs, project_path, context)
        elif project_type == "script":
            files = await self.generate_script_project(specs, project_path, context)
        elif project_type == "api":
            files = await self.generate_api_project(specs, project_path, context)
        elif project_type == "data":
            files = await self.generate_data_project(specs, project_path, context)
        else:
            files = await self.generate_generic_project(specs, project_path, context)
        
        return files

    async def detect_project_type(self, specs: str) -> str:
        """检测项目类型"""
        
        prompt = f"""请从以下项目规格说明书中判断项目类型:

{specs}

只需要返回以下类型之一:
- web: 网站/Web应用
- script: 自动化脚本/工具
- api: API接口服务
- data: 数据处理/分析
- other: 其他

只返回类型名称，不要其他内容。"""
        
        messages = self.get_messages()
        messages.append({
            "role": "user",
            "content": prompt
        })
        
        try:
            response = await self.call_llm(messages, temperature=0.3)
            return response.strip().lower()
        except Exception as e:
            logger.error(f"检测项目类型失败: {e}")
            return "script"

    async def generate_web_project(
        self,
        specs: str,
        project_path: Path,
        context: Optional[Dict] = None
    ) -> List[Dict[str, Any]]:
        """生成Web项目"""
        
        files = []
        
        # 生成主应用文件
        main_file = project_path / "app.py"
        content = await self.generate_web_app_code(specs)
        await self.write_file(str(main_file), content)
        files.append({"name": "app.py", "path": str(main_file), "type": "python"})
        
        # 生成requirements.txt
        req_file = project_path / "requirements.txt"
        await self.write_file(str(req_file), self.get_web_requirements())
        files.append({"name": "requirements.txt", "path": str(req_file), "type": "text"})
        
        # 生成模板目录和文件
        templates_dir = project_path / "templates"
        templates_dir.mkdir(exist_ok=True)
        
        template_file = templates_dir / "index.html"
        await self.write_file(str(template_file), self.get_basic_template())
        files.append({"name": "index.html", "path": str(template_file), "type": "html"})
        
        return files

    async def generate_script_project(
        self,
        specs: str,
        project_path: Path,
        context: Optional[Dict] = None
    ) -> List[Dict[str, Any]]:
        """生成脚本项目"""
        
        files = []
        
        # 主脚本文件
        main_script = project_path / "main.py"
        content = await self.generate_script_code(specs)
        await self.write_file(str(main_script), content)
        files.append({"name": "main.py", "path": str(main_script), "type": "python"})
        
        # 配置文件
        config_file = project_path / "config.yaml"
        await self.write_file(str(config_file), self.get_default_config())
        files.append({"name": "config.yaml", "path": str(config_file), "type": "yaml"})
        
        # requirements.txt
        req_file = project_path / "requirements.txt"
        await self.write_file(str(req_file), "requests>=2.28.0\npyyaml>=6.0\n")
        files.append({"name": "requirements.txt", "path": str(req_file), "type": "text"})
        
        return files

    async def generate_api_project(
        self,
        specs: str,
        project_path: Path,
        context: Optional[Dict] = None
    ) -> List[Dict[str, Any]]:
        """生成API项目"""
        
        files = []
        
        # 主应用
        main_file = project_path / "main.py"
        content = await self.generate_api_code(specs)
        await self.write_file(str(main_file), content)
        files.append({"name": "main.py", "path": str(main_file), "type": "python"})
        
        # models.py
        models_file = project_path / "models.py"
        await self.write_file(str(models_file), self.get_default_models())
        files.append({"name": "models.py", "path": str(models_file), "type": "python"})
        
        # requirements.txt
        req_file = project_path / "requirements.txt"
        await self.write_file(str(req_file), self.get_api_requirements())
        files.append({"name": "requirements.txt", "path": str(req_file), "type": "text"})
        
        return files

    async def generate_data_project(
        self,
        specs: str,
        project_path: Path,
        context: Optional[Dict] = None
    ) -> List[Dict[str, Any]]:
        """生成数据处理项目"""
        
        files = []
        
        # 数据处理脚本
        process_file = project_path / "process.py"
        content = await self.generate_data_processing_code(specs)
        await self.write_file(str(process_file), content)
        files.append({"name": "process.py", "path": str(process_file), "type": "python"})
        
        # requirements.txt
        req_file = project_path / "requirements.txt"
        await self.write_file(str(req_file), "pandas>=1.5.0\nnumpy>=1.23.0\nopenpyxl>=3.0.0\n")
        files.append({"name": "requirements.txt", "path": str(req_file), "type": "text"})
        
        return files

    async def generate_generic_project(
        self,
        specs: str,
        project_path: Path,
        context: Optional[Dict] = None
    ) -> List[Dict[str, Any]]:
        """生成通用项目"""
        
        files = []
        
        # 主文件
        main_file = project_path / "main.py"
        content = await self.generate_generic_code(specs)
        await self.write_file(str(main_file), content)
        files.append({"name": "main.py", "path": str(main_file), "type": "python"})
        
        return files

    async def generate_web_app_code(self, specs: str) -> str:
        """生成Web应用代码"""
        
        prompt = f"""请根据以下项目规格说明书生成Flask Web应用代码:

{specs}

要求:
1. 使用Flask框架
2. 包含基本的路由和视图函数
3. 适当的错误处理
4. 代码规范，有注释

只需要生成app.py的内容。"""
        
        messages = self.get_messages()
        messages.append({
            "role": "user",
            "content": prompt
        })
        
        try:
            return await self.call_llm(messages, max_tokens=3000)
        except Exception as e:
            logger.error(f"生成Web应用代码失败: {e}")
            return self.get_flask_template()

    async def generate_script_code(self, specs: str) -> str:
        """生成脚本代码"""
        
        prompt = f"""请根据以下项目需求生成Python脚本代码:

{specs}

要求:
1. 完整的可运行脚本
2. 包含命令行参数解析 (argparse)
3. 适当的日志记录
4. 错误处理
5. 良好的代码结构

只需要生成main.py的内容。"""
        
        messages = self.get_messages()
        messages.append({
            "role": "user",
            "content": prompt
        })
        
        try:
            return await self.call_llm(messages, max_tokens=3000)
        except Exception as e:
            logger.error(f"生成脚本代码失败: {e}")
            return self.get_script_template()

    async def generate_api_code(self, specs: str) -> str:
        """生成API代码"""
        
        prompt = f"""请根据以下项目规格说明书生成FastAPI应用代码:

{specs}

要求:
1. 使用FastAPI框架
2. 包含基本的CRUD路由
3. 使用Pydantic进行数据验证
4. 适当的错误处理
5. 包含OpenAPI文档注释

只需要生成main.py的内容。"""
        
        messages = self.get_messages()
        messages.append({
            "role": "user",
            "content": prompt
        })
        
        try:
            return await self.call_llm(messages, max_tokens=3000)
        except Exception as e:
            logger.error(f"生成API代码失败: {e}")
            return self.get_fastapi_template()

    async def generate_data_processing_code(self, specs: str) -> str:
        """生成数据处理代码"""
        
        prompt = f"""请根据以下项目需求生成数据处理Python脚本:

{specs}

要求:
1. 使用pandas进行数据处理
2. 包含数据读取、处理、保存的完整流程
3. 适当的日志记录
4. 错误处理

只需要生成process.py的内容。"""
        
        messages = self.get_messages()
        messages.append({
            "role": "user",
            "content": prompt
        })
        
        try:
            return await self.call_llm(messages, max_tokens=3000)
        except Exception as e:
            logger.error(f"生成数据处理代码失败: {e}")
            return self.get_data_template()

    async def generate_generic_code(self, specs: str) -> str:
        """生成通用代码"""
        
        prompt = f"""请根据以下项目需求生成Python代码:

{specs}

请生成完整、可运行的Python代码，包含适当的注释和错误处理。"""
        
        messages = self.get_messages()
        messages.append({
            "role": "user",
            "content": prompt
        })
        
        try:
            return await self.call_llm(messages, max_tokens=3000)
        except Exception as e:
            logger.error(f"生成代码失败: {e}")
            return "# 项目代码\n\nprint('Hello, World!')\n"

    async def write_file(self, filepath: str, content: str):
        """安全地写入文件"""
        
        # 安全检查：确保文件在工作空间内
        file_path = Path(filepath).resolve()
        workspace = self.workspace_path.resolve()
        
        if not str(file_path).startswith(str(workspace)):
            raise ValueError(f"不允许写入工作空间外的文件: {filepath}")
        
        # 写入文件
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        logger.info(f"文件已创建: {filepath}")

    async def generate_readme(self, specs: str, project_path: Path):
        """生成README文档"""
        
        prompt = f"""请根据以下项目规格说明书生成README文档:

{specs}

请生成标准的README.md，包含:
1. 项目简介
2. 功能特性
3. 技术栈
4. 安装说明
5. 使用方法
6. 目录结构

只需要生成README.md的内容。"""
        
        messages = self.get_messages()
        messages.append({
            "role": "user",
            "content": prompt
        })
        
        try:
            readme_content = await self.call_llm(messages, max_tokens=2000)
        except Exception as e:
            logger.error(f"生成README失败: {e}")
            readme_content = f"""# {self.current_project['name']}

## 项目简介

## 安装

```bash
pip install -r requirements.txt
```

## 运行

```bash
python main.py
```
"""
        
        readme_path = project_path / "README.md"
        await self.write_file(str(readme_path), readme_content)

    # 模板代码
    def get_flask_template(self) -> str:
        return '''"""Flask Web应用"""
from flask import Flask, render_template, request, jsonify
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

@app.route('/')
def index():
    """首页"""
    return render_template('index.html')

@app.route('/api/hello')
def hello():
    """示例API"""
    return jsonify({'message': 'Hello, World!'})

@app.errorhandler(404)
def not_found(error):
    """404错误处理"""
    return jsonify({'error': 'Not Found'}), 404

@app.errorhandler(500)
def internal_error(error):
    """500错误处理"""
    return jsonify({'error': 'Internal Server Error'}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
'''

    def get_script_template(self) -> str:
        return '''"""自动化脚本"""
import argparse
import logging
import sys

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='自动化脚本')
    parser.add_argument('--input', '-i', help='输入文件路径')
    parser.add_argument('--output', '-o', help='输出文件路径')
    parser.add_argument('--verbose', '-v', action='store_true', help='详细输出')
    
    args = parser.parse_args()
    
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    
    logger.info("脚本开始执行")
    
    try:
        # 在这里添加您的业务逻辑
        logger.info("执行完成")
    except Exception as e:
        logger.error(f"执行失败: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
'''

    def get_fastapi_template(self) -> str:
        return '''"""FastAPI应用"""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="API服务", version="1.0.0")

class Item(BaseModel):
    """数据模型"""
    name: str
    description: Optional[str] = None
    price: float

@app.get("/")
def read_root():
    """根路由"""
    return {"message": "API服务正常运行"}

@app.get("/items/{item_id}")
def read_item(item_id: int):
    """获取单个项目"""
    return {"item_id": item_id, "name": "示例项目"}

@app.post("/items/")
def create_item(item: Item):
    """创建项目"""
    logger.info(f"创建项目: {item.name}")
    return {"item": item.dict()}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
'''

    def get_data_template(self) -> str:
        return '''"""数据处理脚本"""
import pandas as pd
import numpy as np
import logging
import sys

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def process_data(input_file: str, output_file: str):
    """处理数据
    
    Args:
        input_file: 输入文件路径
        output_file: 输出文件路径
    """
    logger.info(f"读取数据: {input_file}")
    
    try:
        # 读取数据
        df = pd.read_csv(input_file)
        logger.info(f"读取到 {len(df)} 条记录")
        
        # 数据处理
        # TODO: 添加您的数据处理逻辑
        
        # 保存结果
        df.to_csv(output_file, index=False)
        logger.info(f"处理完成，结果已保存: {output_file}")
        
    except Exception as e:
        logger.error(f"处理失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='数据处理脚本')
    parser.add_argument('--input', '-i', required=True, help='输入文件')
    parser.add_argument('--output', '-o', required=True, help='输出文件')
    
    args = parser.parse_args()
    
    process_data(args.input, args.output)
'''

    def get_web_requirements(self) -> str:
        return '''flask>=2.3.0
gunicorn>=21.0.0
'''

    def get_api_requirements(self) -> str:
        return '''fastapi>=0.100.0
uvicorn>=0.23.0
pydantic>=2.0.0
'''

    def get_default_config(self) -> str:
        return '''# 配置文件

# 日志配置
log_level: INFO

# 输入输出
input_file: input.csv
output_file: output.csv

# 其他配置
'''

    def get_default_models(self) -> str:
        return '''"""数据模型"""
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class Item(BaseModel):
    """项目模型"""
    id: Optional[int] = None
    name: str
    description: Optional[str] = None
    created_at: Optional[datetime] = None
'''

    def get_basic_template(self) -> str:
        return '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>项目首页</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; }
        h1 { color: #333; }
    </style>
</head>
<body>
    <h1>欢迎使用</h1>
    <p>项目正在运行中...</p>
</body>
</html>
'''
