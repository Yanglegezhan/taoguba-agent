# Implementation Plan: 大盘分析Agent

## Overview

使用Python实现大盘分析Agent，采用分层架构，核心分析由LLM（默认智谱GLM-4）完成。实现顺序遵循依赖关系：基础设施层 → 数据层 → 分析层 → 输出层。

## Tasks

- [x] 1. 项目初始化和基础设施
  - [x] 1.1 创建项目结构和依赖配置
    - 创建 `pyproject.toml` 或 `requirements.txt`
    - 依赖：zhipuai, openai, pandas, matplotlib, mplfinance, pydantic
    - 创建目录结构：`src/`, `prompts/`, `tests/`
    - _Requirements: 1.1_

  - [x] 1.2 实现LLM接口抽象层
    - 创建 `src/llm/base.py`：LLMConfig, LLMMessage, LLMResponse, LLMProvider抽象类
    - 创建 `src/llm/zhipu.py`：ZhipuProvider实现（默认）
    - 创建 `src/llm/factory.py`：LLMFactory
    - _Requirements: 1.1, 1.2, 1.3, 1.4_

  - [ ]* 1.3 编写LLM配置有效性属性测试
    - **Property 10: LLM配置有效性**
    - **Validates: Requirements 1.1, 1.4**

  - [x] 1.4 实现LLM重试机制和错误处理
    - 实现指数退避重试
    - 统一错误响应格式
    - _Requirements: 1.5, 1.6_

- [x] 2. Checkpoint - 确保LLM基础设施可用
  - 确保所有测试通过，如有问题请询问用户

- [ ] 3. 数据层实现
  - [x] 3.1 实现数据模型
    - 创建 `src/models/market_data.py`：TimeFrame, OHLCV, MovingAverage, MarketData, AnalysisInput
    - 使用Pydantic进行数据验证
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_

  - [ ]* 3.2 编写数据解析正确性属性测试
    - **Property 1: 数据解析正确性（Round-trip）**
    - **Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5**

  - [x] 3.3 实现Tushare数据源
    - 创建 `src/data/tushare_source.py`：TushareConfig, TushareDataSource
    - 实现日线数据获取（三个月）
    - 实现15分钟线数据获取（一周）
    - 实现5分钟线数据获取（当日）
    - 实现均线计算（MA5/10/20/60/120）
    - 从config.yaml加载Tushare API Token
    - 注意：已被AKShare数据源替代
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_

  - [x] 3.4 实现数据解析器
    - 创建 `src/data/parser.py`：支持CSV和JSON格式解析（用于离线数据）
    - 实现格式错误检测和错误信息返回
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6_

  - [ ]* 3.5 编写数据格式错误检测属性测试
    - **Property 2: 数据格式错误检测**
    - **Validates: Requirements 2.6**

  - [x] 3.6 实现时间隔离过滤器
    - 创建 `src/data/time_filter.py`：TimeIsolationFilter
    - 实现日期过滤和盘中时间过滤
    - 实现未来数据警告机制
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6_

  - [ ]* 3.7 编写时间隔离正确性属性测试
    - **Property 3: 时间隔离正确性**
    - **Property 4: 盘中模式时间隔离**
    - **Validates: Requirements 3.1, 3.2, 3.4, 3.5, 3.6**

- [x] 4. Checkpoint - 确保数据层功能完整
  - 确保所有测试通过，如有问题请询问用户

- [x] 5. 分析层实现（核心）
  - [x] 5.1 实现上下文构建器
    - 创建 `src/analysis/context_builder.py`：MarketContext, ContextBuilder
    - 实现数据摘要生成
    - 实现关键点位提取
    - 实现均线位置格式化
    - _Requirements: 4.2, 4.3, 4.7_

  - [x] 5.2 创建提示词模板
    - 创建 `prompts/system.txt`：系统提示词
    - 创建 `prompts/support_resistance.txt`：支撑压力位识别模板
    - 创建 `prompts/short_term.txt`：短期预期模板
    - 创建 `prompts/long_term.txt`：中长期预期模板
    - 创建 `prompts/examples/`：Few-shot示例
    - _Requirements: 4.1, 4.4, 4.5, 4.6_

  - [x] 5.3 实现提示词引擎
    - 创建 `src/analysis/prompt_engine.py`：PromptTemplate, PromptEngine
    - 实现模板加载和变量替换
    - 实现上下文压缩策略
    - _Requirements: 4.4, 4.7, 4.8_

  - [x] 5.4 实现分析结果模型
    - 创建 `src/models/analysis_result.py`：PriceLevel, PositionAnalysis, ShortTermExpectation, LongTermExpectation, AnalysisReport
    - 实现LLM响应解析
    - _Requirements: 5.1-5.7, 6.1-6.4, 7.1-7.5, 8.1-8.5_

  - [x] 5.5 实现价格距离计算
    - 在 `src/analysis/calculator.py` 中实现距离计算和位置判断
    - _Requirements: 6.1, 6.2, 6.3_

  - [x] 5.6 编写价格距离计算属性测试

    - **Property 5: 价格距离计算正确性**
    - **Property 6: 价格位置判断一致性**
    - **Validates: Requirements 5.1, 5.2, 5.3**

  - [x] 5.7 实现核心分析Agent
    - 创建 `src/agent/market_agent.py`：MarketAnalysisAgent
    - 实现完整分析流程：数据加载 → 时间过滤 → 上下文构建 → LLM分析 → 结果解析
    - _Requirements: 5.1-5.7, 6.1-6.4, 7.1-7.5, 8.1-8.5_

  - [x] 5.8 编写支撑压力位数量约束属性测试

    - **Property 7: 支撑压力位数量约束**
    - **Validates: Requirements 5.4**

- [ ] 6. Checkpoint - 确保分析层核心功能可用
  - 确保所有测试通过，如有问题请询问用户

- [x] 7. 输出层实现
  - [x] 7.1 实现报告生成器
    - 创建 `src/output/report_generator.py`：ReportGenerator
    - 实现JSON格式输出
    - 实现文本格式输出
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5_

  - [x] 7.2 编写报告结构完整性属性测试

    - **Property 8: 报告结构完整性**
    - **Property 9: JSON/文本格式输出一致性**
    - **Validates: Requirements 9.1, 9.3, 9.4, 9.5**

  - [x] 7.3 实现图表渲染器
    - 创建 `src/output/chart_renderer.py`：ChartRenderer
    - 使用mplfinance绘制K线图
    - 实现支撑压力位水平线绘制（不同级别不同线型）
    - 实现均线绘制
    - 实现PNG输出
    - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5, 10.6, 10.7_

- [x] 8. Checkpoint - 确保输出层功能完整
  - 确保所有测试通过，如有问题请询问用户

- [ ] 9. 集成和入口
  - [x] 9.1 创建CLI入口
    - 创建 `src/cli.py`：命令行接口
    - 支持指定数据文件、分析日期、LLM配置
    - 支持输出格式选择（JSON/文本/图表/Markdown）
    - _Requirements: 全部_

  - [x] 9.2 创建示例数据和使用文档
    - 创建 `examples/sample_data.json`：示例输入数据
    - 创建 `README.md`：使用说明
    - _Requirements: 全部_

- [x] 10. Final Checkpoint - 确保所有功能集成完成
  - 确保所有测试通过，如有问题请询问用户

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- 核心价值在于提示词设计（Task 5.2），需要根据实际效果迭代优化
- LLM分析结果的质量依赖于提示词和上下文设计
- 图表渲染使用mplfinance库，需要确保数据格式兼容
- 属性测试使用hypothesis库
