# Requirements Document: A股情绪分析Agent

## Introduction

A股情绪分析Agent是一个基于LLM的智能分析系统，通过计算三条核心情绪指标线（大盘系数、超短情绪、亏钱效应），利用大语言模型识别市场周期节点和分析情绪状态，为短线交易提供决策支持。

系统采用"数据驱动+LLM智能分析"的混合架构，分析最近15个交易日的数据，对最后一日进行深度分析，生成包含图表和分析的Markdown/PDF报告。

## Glossary

- **System**: A股情绪分析Agent系统
- **Data_Fetcher**: 数据获取模块，负责从API获取市场原始数据
- **Sentiment_Calculator**: 情绪指标计算模块，负责计算三条情绪指标线
- **LLM_Analyzer**: LLM分析模块，负责周期节点识别和情绪分析
- **Chart_Generator**: 图表生成模块，负责绘制三线趋势图
- **Report_Exporter**: 报告导出模块，负责生成Markdown/PDF报告
- **Trading_Day**: 交易日，指股票市场开市的日期（非自然日）
- **Market_Coefficient**: 大盘系数，计算公式为上涨家数除以20
- **Ultra_Short_Sentiment**: 超短情绪，计算公式为涨停数加上新增百日新高除以2再加上昨日涨停表现乘以10
- **Loss_Effect**: 亏钱效应，计算公式为炸板率乘以100加上跌停数与大幅回撤家数之和乘以2
- **Cycle_Node**: 周期节点，包括冰冰点、修复、分歧、共振、退潮、背离、三线耦合等
- **MarketDayData**: 单日市场数据对象，包含所有必需的市场指标字段
- **SentimentIndicators**: 情绪指标数据对象，包含15个交易日的三条指标线数据

## Requirements

### Requirement 1: 情绪指标计算

**User Story:** 作为系统，我需要根据市场原始数据计算三条情绪指标线，以便为LLM分析提供量化数据基础。

#### Acceptance Criteria

1. WHEN 提供有效的上涨家数，THE Sentiment_Calculator SHALL 计算大盘系数等于上涨家数除以20
2. WHEN 提供有效的涨停数、新增百日新高家数、昨日涨停表现，THE Sentiment_Calculator SHALL 计算超短情绪等于涨停数加上新增百日新高除以2再加上昨日涨停表现乘以10
3. WHEN 提供有效的炸板率、跌停数、大幅回撤家数，THE Sentiment_Calculator SHALL 计算亏钱效应等于炸板率乘以100加上跌停数与大幅回撤家数之和乘以2
4. WHEN 市场数据缺失必需字段，THE Sentiment_Calculator SHALL 返回错误信息并明确标识缺失的字段名称
5. WHEN 计算情绪指标，THE Sentiment_Calculator SHALL 返回包含三条指标线完整数据的SentimentIndicators对象

### Requirement 2: 数据获取与验证

**User Story:** 作为系统，我需要从API获取市场原始数据并验证完整性，以确保后续计算的准确性。

#### Acceptance Criteria

1. WHEN 指定截止交易日和天数，THE Data_Fetcher SHALL 获取指定交易日前N个交易日的市场数据（非自然日）
2. WHEN 导入CSV格式的市场数据，THE Data_Fetcher SHALL 解析并返回包含所有必需字段的MarketDayData列表
3. WHEN 获取市场数据，THE Data_Fetcher SHALL 自动识别交易日并排除非交易日
4. WHEN 数据缺少必需字段，THE Data_Fetcher SHALL 验证失败并返回包含所有缺失字段名称的错误信息
5. WHEN 成功导入数据，THE Data_Fetcher SHALL 返回包含所有必需字段且类型正确的MarketDayData对象

### Requirement 3: 周期节点识别

**User Story:** 作为交易者，我需要系统识别市场周期节点，以便把握买卖时机。

#### Acceptance Criteria

1. WHEN 提供15个交易日的情绪指标数据，THE LLM_Analyzer SHALL 识别所有周期节点并标注日期和节点类型
2. WHEN 识别周期节点，THE LLM_Analyzer SHALL 判断节点类型包括冰冰点、修复、分歧、共振、退潮、背离、三线耦合
3. WHEN 识别周期节点，THE LLM_Analyzer SHALL 为每个节点提供描述、关键指标数值和置信度
4. WHEN 分析当前阶段，THE LLM_Analyzer SHALL 判断最后一日所处的周期阶段和在演绎顺序中的位置

### Requirement 4: 情绪分析与策略建议

**User Story:** 作为交易者，我需要系统分析市场情绪并提供操作策略建议，以便做出交易决策。

#### Acceptance Criteria

1. WHEN 分析市场情绪，THE LLM_Analyzer SHALL 基于超短情绪线所处历史分位点给出0到100分的赚钱效应评分
2. WHEN 分析背离，THE LLM_Analyzer SHALL 判断是否存在顶背离或底背离并分析大盘与情绪的领先滞后关系
3. WHEN 分析细节，THE LLM_Analyzer SHALL 盘点最高板溢价、断板反馈、涨停数、连板家数、炸板率等指标
4. WHEN 提供策略建议，THE LLM_Analyzer SHALL 根据周期节点给出仓位建议包括轻仓、半仓、重仓或空仓
5. WHEN 提供策略建议，THE LLM_Analyzer SHALL 给出具体的操作策略和风险提示
6. WHEN 预判下一节点，THE LLM_Analyzer SHALL 预测下一个可能出现的周期节点和触发条件

### Requirement 5: 报告生成与导出

**User Story:** 作为交易者，我需要系统生成包含图表和分析的报告，以便查看和分享分析结果。

#### Acceptance Criteria

1. WHEN 生成报告，THE Report_Exporter SHALL 包含核心指标概览章节展示最新值、昨日值和环比变化
2. WHEN 生成报告，THE Report_Exporter SHALL 包含情绪趋势图章节展示三线趋势和周期节点标注
3. WHEN 生成报告，THE Report_Exporter SHALL 包含周期节点识别章节列出所有识别的节点和当前阶段判断
4. WHEN 生成报告，THE Report_Exporter SHALL 包含背离分析章节分析大盘与情绪的关系
5. WHEN 生成报告，THE Report_Exporter SHALL 包含细节盘点章节分析各项市场指标
6. WHEN 生成报告，THE Report_Exporter SHALL 包含操作策略建议章节提供仓位建议和策略
7. WHEN 生成报告，THE Report_Exporter SHALL 包含下一节点预判章节预测下一个周期节点
8. WHEN 导出报告，THE Report_Exporter SHALL 支持Markdown格式导出
9. WHEN 导出报告，THE Report_Exporter SHALL 支持PDF格式导出
10. WHEN 成功导出报告，THE Report_Exporter SHALL 返回有效的报告文件路径且文件实际存在

### Requirement 6: LLM提示词构建

**User Story:** 作为系统，我需要构建高质量的LLM提示词，以确保LLM输出准确和一致的分析结果。

#### Acceptance Criteria

1. WHEN 构建提示词，THE LLM_Analyzer SHALL 包含周期方法论的完整定义和演绎顺序说明
2. WHEN 构建提示词，THE LLM_Analyzer SHALL 包含各类周期节点的识别标准和特征描述
3. WHEN 构建提示词，THE LLM_Analyzer SHALL 包含背离、共振、三线耦合等关键概念的详细解释
4. WHEN 构建提示词，THE LLM_Analyzer SHALL 包含顺序逻辑说明大盘领先情绪的基本规律
5. WHEN 构建提示词，THE LLM_Analyzer SHALL 包含极值定义使用标准差定义极端冰点和极端高潮
6. WHEN 构建提示词，THE LLM_Analyzer SHALL 包含15个交易日的三线数据以结构化格式呈现并包含最新日与昨日的环比数据
7. WHEN 构建提示词，THE LLM_Analyzer SHALL 包含Few-shot示例展示期望的分析深度和格式
8. WHEN 构建提示词，THE LLM_Analyzer SHALL 明确要求JSON格式输出避免额外的解释文本

### Requirement 7: 配置管理

**User Story:** 作为系统管理员，我需要通过配置文件管理系统参数，以便灵活调整系统行为。

#### Acceptance Criteria

1. WHEN 加载配置，THE System SHALL 成功加载LLM配置包括提供商、模型和API密钥
2. WHEN 加载配置，THE System SHALL 成功加载数据源配置包括提供商、超时时间和最大重试次数
3. WHEN 加载配置，THE System SHALL 成功加载输出配置包括输出目录、默认格式和图表格式
4. WHEN 加载配置，THE System SHALL 支持配置分析的交易日数量默认为15
5. WHEN 配置文件缺失或格式错误，THE System SHALL 使用默认配置并记录警告信息

### Requirement 8: 错误处理与日志

**User Story:** 作为系统管理员，我需要系统提供清晰的错误信息和日志，以便排查问题和监控运行状态。

#### Acceptance Criteria

1. WHEN API调用失败，THE System SHALL 自动重试最多3次并记录错误日志
2. WHEN 数据验证失败，THE System SHALL 立即返回错误信息包含缺失字段列表
3. WHEN 计算过程中出现异常数据，THE System SHALL 标记异常数据并记录警告
4. WHEN LLM调用失败，THE System SHALL 重试最多3次失败后返回错误信息
5. WHEN 文件操作失败，THE System SHALL 返回详细错误信息和建议
6. WHEN 图表生成失败，THE System SHALL 仍然生成文本报告作为降级服务
7. WHEN PDF导出失败，THE System SHALL 降级为Markdown格式导出
8. WHEN 发生任何错误，THE System SHALL 提供清晰的错误信息和可能的解决方案

### Requirement 9: 图表可视化

**User Story:** 作为交易者，我需要系统生成直观的三线趋势图，以便快速理解市场情绪变化。

#### Acceptance Criteria

1. WHEN 生成图表，THE Chart_Generator SHALL 绘制三条主线包括大盘系数、超短情绪和亏钱效应
2. WHEN 绘制主线，THE Chart_Generator SHALL 使用不同颜色和样式区分三条线
3. WHEN 标注周期节点，THE Chart_Generator SHALL 在对应交易日期的下方添加标记和文字
4. WHEN 生成图表，THE Chart_Generator SHALL 包含图例说明三条线的含义和节点类型
5. WHEN 导出图表，THE Chart_Generator SHALL 支持PNG格式输出可嵌入Markdown报告

### Requirement 10: 数据源集成

**User Story:** 作为系统，我需要支持多种数据源，以便灵活选择数据提供商。

#### Acceptance Criteria

1. WHEN 使用开盘啦数据源，THE Data_Fetcher SHALL 通过kaipanla_crawler获取市场数据
2. WHEN 使用开盘啦数据源，THE Data_Fetcher SHALL 提供准确率99%以上的涨停数和炸板率
3. WHEN 使用开盘啦数据源，THE Data_Fetcher SHALL 提供最高板个股名字和概念信息
4. WHEN 使用开盘啦数据源，THE Data_Fetcher SHALL 提供昨日断板今日表现数据
5. WHEN 使用AKShare数据源，THE Data_Fetcher SHALL 通过AKShare API获取市场数据作为备选方案
6. WHEN 配置数据源，THE System SHALL 支持通过配置文件选择数据源提供商

### Requirement 11: 命令行接口

**User Story:** 作为用户，我需要通过命令行运行情绪分析，以便集成到自动化工作流。

#### Acceptance Criteria

1. WHEN 运行CLI，THE System SHALL 接受分析日期参数默认为最新交易日
2. WHEN 运行CLI，THE System SHALL 接受输出格式参数支持md、pdf或all
3. WHEN 运行CLI，THE System SHALL 接受输出路径参数可选
4. WHEN 运行CLI，THE System SHALL 显示执行进度包括数据获取、指标计算、LLM分析、报告生成
5. WHEN 分析完成，THE System SHALL 输出报告文件路径和图表文件路径
6. WHEN 分析失败，THE System SHALL 输出清晰的错误信息和退出码

### Requirement 12: 性能与可扩展性

**User Story:** 作为系统架构师，我需要系统具有良好的性能和可扩展性，以支持未来功能扩展。

#### Acceptance Criteria

1. WHEN 获取相同日期的数据，THE System SHALL 使用缓存避免重复API调用
2. WHEN 获取多个交易日的数据，THE System SHALL 支持并行处理提高效率
3. WHEN 添加新的数据源，THE System SHALL 通过插件化架构支持注册新数据源
4. WHEN 添加新的报告格式，THE System SHALL 通过扩展接口支持注册新格式化器
5. WHEN 系统负载增加，THE System SHALL 保持响应时间在可接受范围内
