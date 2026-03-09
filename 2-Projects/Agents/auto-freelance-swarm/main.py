"""
Auto-Freelance Swarm 主入口
多智能体副业协作系统
"""

import os
import sys
import asyncio
import logging
import argparse
from pathlib import Path
from datetime import datetime

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_config():
    """加载配置文件"""
    import yaml
    
    config_path = project_root / "config" / "settings.yaml"
    
    if not config_path.exists():
        logger.warning(f"配置文件不存在: {config_path}")
        return {}
    
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def init_llm_provider(config: dict):
    """初始化LLM提供者"""
    from openai import AsyncOpenAI
    
    # 从环境变量获取API Key
    api_key = os.environ.get("OPENAI_API_KEY", "")
    
    if not api_key:
        logger.warning("未设置OPENAI_API_KEY环境变量")
        return None
    
    base_url = config.get("llm", {}).get("default_provider", "openai")
    
    if base_url == "openai":
        base_url = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
    elif base_url == "anthropic":
        base_url = "https://api.anthropic.com"
    elif base_url == "silicon":
        base_url = os.environ.get("SILICON_BASE_URL", "https://api.siliconflow.cn/v1")
    
    return AsyncOpenAI(api_key=api_key, base_url=base_url)


async def run_demo(llm_provider, config: dict):
    """运行演示模式"""
    logger.info("启动演示模式...")
    
    from src.core.workflow import run_workflow_demo
    
    await run_workflow_demo(llm_provider, config)


async def run_api_server(config: dict):
    """运行API服务器"""
    logger.info("启动API服务器...")
    
    import uvicorn
    from src.api.main import app
    
    host = config.get("api", {}).get("host", "0.0.0.0")
    port = config.get("api", {}).get("port", 8000)
    
    uvicorn.run(app, host=host, port=port)


async def run_streamlit_ui(config: dict):
    """运行Streamlit界面"""
    logger.info("启动Streamlit界面...")
    
    import subprocess
    
    ui_path = project_root / "ui" / "dashboard.py"
    
    subprocess.run([
        sys.executable, "-m", "streamlit", "run",
        str(ui_path),
        "--server.port", "8501",
        "--server.address", "0.0.0.0"
    ])


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="Auto-Freelance Swarm")
    parser.add_argument(
        "mode",
        choices=["demo", "api", "ui", "all"],
        default="demo",
        help="运行模式: demo=演示模式, api=API服务器, ui=Web界面, all=全部启动"
    )
    parser.add_argument(
        "--config",
        default="config/settings.yaml",
        help="配置文件路径"
    )
    parser.add_argument(
        "--workspace",
        default="./workspace",
        help="工作空间目录"
    )
    
    args = parser.parse_args()
    
    # 加载配置
    config = load_config()
    
    # 检查API Key
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        logger.error("请设置OPENAI_API_KEY环境变量")
        print("\n请先设置OPENAI_API_KEY环境变量:")
        print("  Windows: set OPENAI_API_KEY=your-api-key")
        print("  Linux/Mac: export OPENAI_API_KEY=your-api-key")
        print("\n或者复制config/.env.example为.env并填入配置")
        sys.exit(1)
    
    # 初始化LLM
    llm_provider = init_llm_provider(config)
    
    if args.mode == "demo":
        asyncio.run(run_demo(llm_provider, config))
    elif args.mode == "api":
        asyncio.run(run_api_server(config))
    elif args.mode == "ui":
        asyncio.run(run_streamlit_ui(config))
    elif args.mode == "all":
        logger.info("启动全部服务...")
        
        # 启动API和UI
        import threading
        
        # API服务器线程
        api_thread = threading.Thread(
            target=lambda: asyncio.run(run_api_server(config)),
            daemon=True
        )
        api_thread.start()
        
        # 等待API服务器启动
        import time
        time.sleep(2)
        
        # Streamlit UI
        asyncio.run(run_streamlit_ui(config))


if __name__ == "__main__":
    main()
