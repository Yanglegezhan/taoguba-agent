#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""运行暗线分析"""

import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / 'src'))

from config.config_manager import ConfigManager
from src.agent import DarkLineAgent
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def main():
    """主函数"""
    # 加载配置
    config_path = project_root / 'config' / 'config.yaml'
    config = ConfigManager(config_path)
    
    # 创建Agent
    agent = DarkLineAgent(config)
    
    # 执行分析
    date = '2026-02-05'
    print(f"\n{'='*80}")
    print(f"开始分析 {date} 的涨停暗线")
    print(f"{'='*80}\n")
    
    agent.analyze(date)
    
    print(f"\n{'='*80}")
    print("分析完成！")
    print(f"{'='*80}\n")

if __name__ == '__main__':
    main()
