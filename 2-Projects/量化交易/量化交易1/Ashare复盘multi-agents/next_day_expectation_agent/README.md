# 次日核心个股超预期分析系统

## 概述

本系统是一个A股次日核心个股超预期分析的智能体系统，通过三个阶段的智能体协作，实现从数据沉淀、策略校准到竞价监测的全流程自动化分析。

## 系统架构

- **Stage1 Agent**: 数据沉淀与复盘（收盘后运行）
- **Stage2 Agent**: 早盘策略校准（7:00-9:00运行）
- **Stage3 Agent**: 竞价轨迹监测（9:15-9:25运行）

## 技术栈

- Python 3.9+
- Gemini-2.0-Flash (LLM)
- Kaipanla API (主数据源)
- AKShare (补充数据源)
- SQLite (历史数据存储)

## 快速开始

### 安装依赖

```bash
pip install -r requirements.txt
```

### 配置

复制配置模板并填写必要信息：

```bash
cp config/system_config.yaml.template config/system_config.yaml
cp config/agent_config.yaml.template config/agent_config.yaml
cp config/data_source_config.yaml.template config/data_source_config.yaml
```

### 运行

```bash
# Stage1: 数据复盘（收盘后）
python -m src.stage1.agent --date 2025-02-12

# Stage2: 策略校准（早盘前）
python -m src.stage2.agent --date 2025-02-13

# Stage3: 竞价监测（竞价期间）
python -m src.stage3.agent --date 2025-02-13
```

## 目录结构

```
next_day_expectation_agent/
├── config/                 # 配置文件
├── data/                   # 数据存储
│   ├── stage1_output/     # Stage1输出
│   ├── stage2_output/     # Stage2输出
│   ├── stage3_output/     # Stage3输出
│   ├── historical/        # 历史数据库
│   └── logs/              # 日志文件
├── src/                    # 源代码
│   ├── common/            # 公共模块
│   ├── stage1/            # Stage1 Agent
│   ├── stage2/            # Stage2 Agent
│   └── stage3/            # Stage3 Agent
├── tests/                  # 测试代码
└── docs/                   # 文档
```

## 文档

详细文档请参考：
- [需求文档](../../.kiro/specs/next-day-core-stock-expectation-analysis/requirements.md)
- [设计文档](../../.kiro/specs/next-day-core-stock-expectation-analysis/design.md)
- [任务列表](../../.kiro/specs/next-day-core-stock-expectation-analysis/tasks.md)
