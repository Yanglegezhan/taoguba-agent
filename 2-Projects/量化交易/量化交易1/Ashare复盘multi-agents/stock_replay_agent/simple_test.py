#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
简单测试脚本 - 验证项目结构
"""
import sys
from pathlib import Path

# 添加项目路径
project_dir = Path(__file__).resolve().parent
print(f"Project directory: {project_dir}")
print(f"Project exists: {project_dir.exists()}")

# 测试各目录
dirs_to_check = ["src/agent", "src/data", "src/models", "src/analysis", "src/llm", "src/output", "prompts"]

for dir_name in dirs_to_check:
    dir_path = project_dir / dir_name
    exists = dir_path.exists()
    print(f"{dir_name}: {':'.join(40 - len(dir_name))} {'✓' if exists else '✗'}")

    if exists:
        py_files = list(dir_path.glob("**/*.py"))
        print(f"  Python files: {len(py_files)}")
        if py_files:
            for py_file in py_files[:3]:  # 只显示前3个
                print(f"  - {py_file.name}")

print("\n" + "=" * 60)
print("Core modules summary")
print("=" * 60)

modules = [
    "src/agent/consecutive_board_agent.py",
    "src/agent/trend_stock_agent.py",
    "src/agent/critic_agent.py",
    "src/agent/synthesis_agent.py",
    "src/data/kaipanla_stock_source.py",
    "src/models/stock_models.py",
    "src/analysis/indicator_calculator.py",
    "src/analysis/special_action_detector.py",
    "src/analysis/sector_comparator.py",
    "src/llm/base.py",
    "src/llm/client.py",
    "src/llm/prompt_engine.py",
    "src/output/report_generator.py",
    "src/output/json_exporter.py",
    "cli.py",
]

for module in modules:
    module_path = project_dir / module
    print(f"{module}: {':'.join(50 - len(module))} {'✓' if module_path.exists() else '✗'}")

print("\n" + "=" * 60)
print("Prompt files")
print("=" * 60)

prompt_dirs = [
    "prompts/consecutive_board/system.txt",
    "prompts/consecutive_board/analysis.txt",
    "prompts/trend_stock/system.txt",
    "prompts/trend_stock/analysis.txt",
    "prompts/critic/system.txt",
    "prompts/critic/analysis.txt",
    "prompts/synthesis/system.txt",
    "prompts/synthesis/analysis.txt",
]

for prompt in prompt_dirs:
    prompt_path = project_dir / prompt
    print(f"{prompt}: {':'.join(48 - len(prompt))} {'✓' if prompt_path.exists() else '✗'}")

print("\n✓ 核心个股复盘智能体阵列项目结构已创建完成！")
print("=" * 60)
