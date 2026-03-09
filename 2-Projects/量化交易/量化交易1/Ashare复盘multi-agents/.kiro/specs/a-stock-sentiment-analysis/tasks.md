# Implementation Plan: A股情绪分析Agent

## Overview

本实现计划将A股情绪分析Agent系统分解为可执行的开发任务。系统采用Python实现，复用现有大盘分析Agent的基础设施（LLM客户端、配置模块），并集成开盘啦数据源。

实现策略：
1. 优先实现核心功能（数据获取、指标计算、LLM分析）
2. 使用开盘啦数据源获取高质量市场数据
3. 采用属性测试验证计算逻辑的正确性
4. 渐进式开发，每个阶段都有可运行的功能

## Tasks

- [x] 1. 设置项目结构和核心数据模型
  - 创建`src/sentiment/`目录结构
  - 定义核心数据模型（MarketDayData, DailySentiment, SentimentIndicators）
  - 定义周期节点和分析结果模型（CycleNode, SentimentAnalysisResult）
  - 定义配置模型（DataSourceConfig, AgentConfig）
  - _Requirements: 1.5, 2.5_

- [x] 1.1 为数据模型编写属性测试

  - **Property 8: 标准化数据结构**
  - **Validates: Requirements 2.5**

- [-] 2. 实现情绪指标计算模块
  - [x] 2.1 实现SentimentCalculator类
    - 实现calculate_market_coefficient方法（上涨家数 / 20）
    - 实现calculate_ultra_short_sentiment方法（涨停数 + 新增百日新高/2 + 昨日涨停表现*10）
    - 实现calculate_loss_effect方法（炸板率*100 + (跌停数+大幅回撤家数)*2）
    - 实现calculate_all_indicators方法计算15日完整数据
    - 实现calculate_change_pct方法计算环比变化
    - _Requirements: 1.1, 1.2, 1.3, 1.5_

- [x] 2.2 为大盘系数计算编写属性测试

  - **Property 1: 大盘系数计算正确性**
  - **Validates: Requirements 1.1**

- [x] 2.3 为超短情绪计算编写属性测试

  - **Property 2: 超短情绪计算正确性**
  - **Validates: Requirements 1.2**

- [x] 2.4 为亏钱效应计算编写属性测试

  - **Property 3: 亏钱效应计算正确性**
  - **Validates: Requirements 1.3**

- [ ]* 2.5 为指标计算完整性编写属性测试
  - **Property 5: 指标计算完整性**
  - **Validates: Requirements 1.5**

- [ ]* 2.6 编写单元测试验证边界情况
  - 测试零值输入
  - 测试负值处理
  - 测试极大值处理
  - _Requirements: 1.1, 1.2, 1.3_

- [x] 3. 实现开盘啦数据源集成
  - [x] 3.1 实现KaipanlaSentimentSource类
    - 初始化kaipanla_crawler实例
    - 实现fetch_day_data方法获取单日数据
    - 实现_get_trading_days方法识别交易日
    - 实现_parse_consecutive_limit_up方法解析连板梯队
    - 实现_get_max_consecutive_info方法获取最高板个股信息
    - _Requirements: 2.1, 2.3, 10.1, 10.2, 10.3, 10.4_

  - [x] 3.2 实现fetch_sentiment_market_data方法
    - 获取指定交易日前N个交易日的数据
    - 组装MarketDayData对象
    - 按日期升序排列
    - _Requirements: 2.1, 2.2_

  - [x] 3.3 实现数据验证功能
    - 实现validate_data方法检查必需字段
    - 检查数值范围合理性
    - 返回ValidationResult对象
    - _Requirements: 2.4, 8.2_

- [ ]* 3.4 为数据验证编写属性测试
  - **Property 4: 缺失字段错误处理**
  - **Validates: Requirements 1.4**
  - **Property 7: 数据验证错误信息**
  - **Validates: Requirements 2.4**

- [ ]* 3.5 为CSV解析编写属性测试
  - **Property 6: CSV解析健壮性**
  - **Validates: Requirements 2.2**

- [ ]* 3.6 编写单元测试验证数据获取
  - 测试成功获取15个交易日数据
  - 测试交易日识别功能
  - 测试连板梯队解析
  - 测试最高板个股信息提取
  - _Requirements: 2.1, 2.3, 10.1, 10.3, 10.4_

- [ ] 4. Checkpoint - 确保数据获取和计算模块测试通过
  - 确保所有测试通过，如有问题请询问用户

- [ ] 5. 实现LLM提示词构建
  - [x] 5.1 创建提示词模板文件
    - 创建`prompts/sentiment/system.txt`系统提示词
    - 创建`prompts/sentiment/analysis.txt`分析提示词模板
    - 创建`prompts/sentiment/examples/`目录存放Few-shot示例
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.7_

  - [x] 5.2 实现PromptEngine类
    - 实现load_template方法加载提示词模板
    - 实现render_template方法渲染模板变量
    - 实现format_sentiment_data方法格式化15日数据表格
    - 实现format_latest_comparison方法格式化最新日与昨日环比
    - 实现format_market_details方法格式化市场细节数据
    - _Requirements: 6.6, 6.8_

- [ ]* 5.3 为提示词构建编写属性测试
  - **Property 11: 提示词包含周期方法论**
  - **Validates: Requirements 6.1**
  - **Property 12: 提示词包含节点识别标准**
  - **Validates: Requirements 6.2**
  - **Property 13: 提示词包含关键概念**
  - **Validates: Requirements 6.3**
  - **Property 14: 提示词包含数据表格**
  - **Validates: Requirements 6.6**

- [ ]* 5.4 编写单元测试验证提示词质量
  - 测试提示词包含所有必需元素
  - 测试数据表格格式正确
  - 测试Few-shot示例加载
  - _Requirements: 6.1, 6.2, 6.3, 6.6, 6.7_

- [x] 6. 实现LLM分析模块
  - [x] 6.1 实现SentimentLLMAnalyzer类
    - 初始化LLM客户端和PromptEngine
    - 实现build_prompt方法构建完整提示词
    - 实现analyze_sentiment方法调用LLM
    - 实现parse_response方法解析JSON响应
    - 实现错误处理和重试逻辑（最多3次）
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 6.8, 8.4_

  - [x] 6.2 实现响应解析和验证
    - 解析cycle_nodes列表
    - 解析current_stage和stage_position
    - 解析money_making_score（0-100）
    - 解析各类分析文本
    - 验证响应完整性
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 4.1, 4.2, 4.3, 4.4, 4.5, 4.6_

- [ ]* 6.3 编写单元测试验证LLM分析
  - 测试提示词构建包含所有必需元素
  - 测试成功解析LLM响应
  - 测试响应验证功能
  - 测试错误处理和重试
  - _Requirements: 3.1, 4.1, 6.8, 8.4_

- [ ] 7. Checkpoint - 确保LLM分析模块测试通过
  - 确保所有测试通过，如有问题请询问用户

- [x] 8. 实现图表生成模块
  - [x] 8.1 实现SentimentChartGenerator类
    - 使用matplotlib和seaborn绘制折线图
    - 绘制三条主线（大盘系数、超短情绪、亏钱效应）
    - 使用不同颜色和样式区分（紫色、红色粗虚线、绿色）
    - 在对应交易日期下方标注周期节点
    - 添加图例说明
    - 导出PNG格式
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5_

- [ ]* 8.2 编写单元测试验证图表生成
  - 测试图表文件成功生成
  - 测试图表包含三条主线
  - 测试节点标注位置正确
  - 测试图例完整性
  - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5_

- [x] 9. 实现报告导出模块
  - [x] 9.1 实现SentimentReportExporter类
    - 实现export_report方法
    - 实现_format_markdown方法生成Markdown报告
    - 实现_format_indicators_table方法格式化指标表格
    - 实现_format_cycle_nodes方法格式化周期节点
    - 实现_embed_chart方法嵌入图表
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7, 5.8, 5.10_

  - [x] 9.2 实现PDF导出功能
    - 实现_format_pdf方法生成PDF报告
    - 使用reportlab库
    - 支持中文字体
    - 嵌入图表
    - _Requirements: 5.9_

- [ ]* 9.3 为报告生成编写属性测试
  - **Property 9: 报告章节完整性**
  - **Validates: Requirements 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7**
  - **Property 10: 报告文件路径返回**
  - **Validates: Requirements 5.10**

- [ ]* 9.4 编写单元测试验证报告导出
  - 测试Markdown报告生成
  - 测试PDF报告生成
  - 测试报告包含所有必需章节
  - 测试图表嵌入
  - 测试文件路径返回
  - _Requirements: 5.1, 5.8, 5.9, 5.10_

- [x] 10. 实现主控模块和错误处理
  - [x] 10.1 实现SentimentAnalysisAgent类
    - 初始化所有子模块
    - 实现analyze方法协调整个流程
    - 实现进度显示功能
    - 集成所有模块（数据获取→计算→分析→图表→报告）
    - _Requirements: 11.4_

  - [x] 10.2 实现统一错误处理
    - 实现ErrorHandler类
    - 实现handle_data_fetch_error方法
    - 实现handle_validation_error方法
    - 实现handle_llm_error方法
    - 实现handle_file_error方法
    - 配置日志记录
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.8_

  - [x] 10.3 实现降级策略
    - 图表生成失败时仍生成文本报告
    - PDF导出失败时降级为Markdown
    - LLM分析失败时提供基础指标数据
    - _Requirements: 8.6, 8.7_

- [ ]* 10.4 编写集成测试
  - 测试端到端分析流程
  - 测试错误处理和重试
  - 测试降级策略
  - _Requirements: 8.1, 8.4, 8.6, 8.7_

- [ ] 11. Checkpoint - 确保主控模块和错误处理测试通过
  - 确保所有测试通过，如有问题请询问用户

- [x] 12. 实现配置管理
  - [x] 12.1 扩展config.yaml配置文件
    - 添加sentiment配置节
    - 配置数据源（provider, timeout, max_retries）
    - 配置分析参数（num_trading_days）
    - 配置输出（dir, default_format, chart_format）
    - 配置提示词（template_dir, temperature, max_tokens）
    - _Requirements: 7.1, 7.2, 7.3, 7.4_

  - [x] 12.2 实现配置加载和验证
    - 复用现有的load_config函数
    - 实现配置验证逻辑
    - 实现默认配置降级
    - _Requirements: 7.5_

- [ ]* 12.3 为配置管理编写属性测试
  - **Property 15: 配置加载健壮性**
  - **Validates: Requirements 7.1, 7.2, 7.3**
  - **Property 16: 配置缺失降级**
  - **Validates: Requirements 7.5**

- [ ]* 12.4 编写单元测试验证配置管理
  - 测试成功加载完整配置
  - 测试配置缺失时使用默认值
  - 测试配置验证功能
  - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5_

- [x] 13. 实现命令行接口
  - [x] 13.1 创建sentiment_cli.py
    - 使用argparse解析命令行参数
    - 支持--date参数指定分析日期
    - 支持--format参数指定输出格式（md/pdf/all）
    - 支持--output参数指定输出路径
    - 支持--config参数指定配置文件
    - 显示执行进度
    - 输出报告和图表路径
    - _Requirements: 11.1, 11.2, 11.3, 11.4, 11.5_

  - [x] 13.2 实现错误处理和退出码
    - 成功时返回0
    - 失败时返回非零退出码
    - 输出清晰的错误信息
    - _Requirements: 11.6_

- [ ]* 13.3 编写单元测试验证CLI
  - 测试参数解析
  - 测试进度显示
  - 测试输出路径返回
  - 测试错误处理和退出码
  - _Requirements: 11.1, 11.2, 11.3, 11.4, 11.5, 11.6_

- [ ] 14. 实现性能优化和缓存
  - [ ] 14.1 实现数据缓存
    - 使用functools.lru_cache缓存API调用结果
    - 实现CacheManager类管理缓存
    - 支持缓存过期时间配置
    - _Requirements: 12.1_

  - [ ] 14.2 实现并行数据获取
    - 使用ThreadPoolExecutor并行获取多日数据
    - 配置最大并发数
    - _Requirements: 12.2_

- [ ]* 14.3 编写性能测试
  - 测试缓存命中率
  - 测试并行获取性能提升
  - 测试响应时间
  - _Requirements: 12.1, 12.2, 12.5_

- [ ] 15. 创建使用示例和文档
  - [ ] 15.1 创建example_kaipanla_source.py示例
    - 示例1：基本使用
    - 示例2：获取多日数据
    - 示例3：数据验证
    - 示例4：连板梯队分析
    - 示例5：完整分析流程

  - [ ] 15.2 创建文档
    - 创建KAIPANLA_INTEGRATION.md集成说明
    - 创建QUICKSTART_KAIPANLA.md快速开始指南
    - 创建网络超时说明.md故障排查文档
    - 更新README.md添加情绪分析功能说明

  - [ ] 15.3 创建数据导出工具
    - 创建export_data_to_csv.py导出工具
    - 支持导出原始市场数据
    - 支持导出计算的情绪指标
    - 支持导出合并数据

- [ ] 16. 最终集成测试和验证
  - [ ] 16.1 运行完整的端到端测试
    - 测试从数据获取到报告生成的完整流程
    - 测试使用真实API数据
    - 验证报告质量和准确性

  - [ ] 16.2 运行所有属性测试
    - 确保所有属性测试通过（每个至少100次迭代）
    - 验证计算逻辑的正确性

  - [ ] 16.3 运行所有单元测试
    - 确保代码覆盖率 >= 80%
    - 验证边界情况和错误处理

- [ ] 17. Final Checkpoint - 确保所有测试通过
  - 确保所有测试通过，如有问题请询问用户

## Notes

- 任务标记`*`的为可选任务，可以跳过以加快MVP开发
- 每个任务都引用了具体的需求编号，确保可追溯性
- Checkpoint任务确保增量验证，及时发现问题
- 属性测试验证通用正确性属性，单元测试验证具体示例和边界情况
- 优先使用开盘啦数据源，提供更准确的市场数据
- 复用现有大盘分析Agent的LLM客户端和配置模块
- 所有属性测试必须运行至少100次迭代
- 每个正确性属性必须由单个属性测试实现
- 测试标签格式：**Feature: a-stock-sentiment-analysis, Property {number}: {property_text}**
