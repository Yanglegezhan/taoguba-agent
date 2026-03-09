# 系统架构文档

## 概述

本系统采用三阶段流水线架构，每个Agent独立运作，通过文件系统传递数据。

## 架构图

```
数据源层 → 数据采集 → 数据存储 → Agent流水线 → 决策导航 → 报告推送
```

## Agent架构

每个Agent包含以下核心组件：
1. Configuration Manager - 配置管理
2. Data Input Handler - 数据输入处理
3. LLM Integration Layer - LLM集成
4. Business Logic Processor - 业务逻辑处理
5. Data Output Handler - 数据输出处理
6. Error Handler & Logger - 错误处理和日志

## 数据流

### Stage1 → Stage2
- 输入：当日行情数据
- 输出：gene_pool_{date}.json, market_report_{date}.json, emotion_report_{date}.json, theme_report_{date}.json

### Stage2 → Stage3
- 输入：Stage1输出 + 隔夜外部数据
- 输出：baseline_expectation_{date}.json, new_themes_{date}.json

### Stage3 输出
- 输入：Stage2输出 + 竞价实时数据
- 输出：decision_navigation_{date}.json, daily_report_{date}.html

## 技术栈

- Python 3.9+
- Gemini-2.0-Flash (LLM)
- SQLite (历史数据)
- YAML (配置管理)
- Loguru (日志系统)

## 扩展性

系统设计支持：
- 新增数据源
- 自定义Agent
- 扩展决策规则
- 集成其他LLM模型
