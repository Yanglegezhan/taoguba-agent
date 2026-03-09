# Requirements Document

## Introduction

大盘分析Agent是一个智能分析系统，通过多时间周期的上证指数数据（日线、15分钟线、5分钟线、1分钟线）结合均线数据，由LLM自动识别支撑压力位，并对大盘未来走势进行预期分析。该系统旨在为投资者提供技术面分析参考。

## Glossary

- **Market_Analysis_Agent**: 大盘分析智能体，负责接收市场数据并输出分析结果
- **Support_Level**: 支撑位，价格下跌时可能遇到买盘支撑，从而止跌回稳的价位，前期的显著高点和显著低点，尤其是被多次测试但未被成功突破或跌破的位置，容易形成压力或支撑；过去成交量持续较大的交易区域，表明该价位市场参与度高；若价格在其上方，该区成支撑；对于一些主要指数或高价股，像1000点、100元这类整数位，由于心理预期作用，也会形成支撑或压力；支撑压力位也可以是k线穿越最多的一条水平线
- **Resistance_Level**: 压力位，价格上涨时可能遇到卖盘压制，从而回落或停滞的价位区，前期的显著高点和显著低点，尤其是被多次测试但未被成功突破或跌破的位置，容易形成压力或支撑；过去成交量持续较大的交易区域，表明该价位市场参与度高；若价格在其下方，该区成压力；对于一些主要指数或高价股，像1000点、100元这类整数位，由于心理预期作用，也会形成支撑或压力；支撑压力位也可以是k线穿越最多的一条水平线
- **Moving_Average**: 均线，一定周期内收盘价的平均值
- **Daily_Data**: 日线数据，一年内的上证指数日K线数据
- **M15_Data**: 15分钟线数据，一个月内的15分钟K线数据
- **M5_Data**: 5分钟线数据，包括一周内的5分钟K线数据
- **M1_Data**: 一分钟线数据，包括当日的1分钟K线数据
- **Price_Position**: 价格位置，当前价格相对于支撑压力位的位置关系
- **Trend_Expectation**: 走势预期，基于技术分析对未来价格走势的判断
- **Chart_Renderer**: 图表渲染器，负责在K线图上绘制支撑压力位
- **LLM_Provider**: 大语言模型提供商，用于生成分析文本，默认为智谱GLM-4

## Requirements

按执行顺序排列：**基础设施层 → 数据层 → 分析层（LLM核心） → 输出层**

---

### Requirement 1: LLM模型配置（基础设施层）

**User Story:** As a 开发者, I want to 灵活选择LLM模型, so that 我能根据需求和成本选择合适的模型。

#### Acceptance Criteria

1. THE Market_Analysis_Agent SHALL 默认使用智谱GLM-4作为分析模型
2. THE Market_Analysis_Agent SHALL 支持配置其他LLM提供商（OpenAI、Claude、通义千问等）
3. WHEN 用户指定LLM模型 THEN THE Market_Analysis_Agent SHALL 使用指定的模型进行分析
4. THE Market_Analysis_Agent SHALL 提供统一的LLM接口抽象层
5. IF LLM调用失败 THEN THE Market_Analysis_Agent SHALL 返回错误信息并支持重试机制
6. THE Market_Analysis_Agent SHALL 支持配置API密钥和模型参数（temperature、max_tokens等）

---

### Requirement 2: 多周期数据输入（数据层）

**User Story:** As a 投资者, I want to 输入多个时间周期的上证指数数据, so that 系统能够进行多维度的技术分析。

#### Acceptance Criteria

1. WHEN 用户提供一年内的日线数据 THEN THE Market_Analysis_Agent SHALL 解析并存储日线OHLCV数据（开盘价、最高价、最低价、收盘价、成交量）
2. WHEN 用户提供一个月的15分钟线数据 THEN THE Market_Analysis_Agent SHALL 解析并存储15分钟OHLCV数据
3. WHEN 用户提供一周的5分钟线数据 THEN THE Market_Analysis_Agent SHALL 解析并存储历史5分钟OHLCV数据
4. WHEN 用户提供当日的1分钟线数据 THEN THE Market_Analysis_Agent SHALL 解析并存储当日1分钟OHLCV数据
5. WHEN 用户提供均线数据 THEN THE Market_Analysis_Agent SHALL 解析并存储各周期均线数值（MA5、MA10、MA20、MA60、MA120）
6. IF 输入数据格式不正确 THEN THE Market_Analysis_Agent SHALL 返回明确的错误提示信息

---

### Requirement 3: 数据时间隔离（数据层 - 防止未来视角）

**User Story:** As a 投资者, I want to 确保分析只使用指定日期之前的数据, so that 分析结果不会受到未来数据的污染，保证回测和实盘分析的一致性。

#### Acceptance Criteria

1. WHEN 用户指定分析日期 THEN THE Market_Analysis_Agent SHALL 严格过滤数据，只使用该日期及之前的数据
2. THE Market_Analysis_Agent SHALL 在数据加载时验证数据时间戳，拒绝加载超出指定日期的数据
3. THE Market_Analysis_Agent SHALL 在分析报告中明确标注数据截止时间
4. IF 输入数据包含指定日期之后的数据 THEN THE Market_Analysis_Agent SHALL 自动过滤掉未来数据并给出警告
5. THE Market_Analysis_Agent SHALL 支持"当日盘中"模式，只使用当日指定时间点之前的分钟线数据
6. THE Market_Analysis_Agent SHALL 在计算均线时严格使用截止时间之前的数据

---

### Requirement 4: 提示词工程与上下文设计（分析层 - LLM核心）

**User Story:** As a 开发者, I want to 设计高质量的提示词和上下文结构, so that LLM能够准确理解市场数据并给出专业的技术分析。

#### Acceptance Criteria

1. THE Market_Analysis_Agent SHALL 设计系统提示词（System Prompt），定义Agent的角色为专业技术分析师
2. THE Market_Analysis_Agent SHALL 将市场数据结构化为LLM易于理解的格式（关键点位摘要而非原始数据）
3. THE Market_Analysis_Agent SHALL 在上下文中包含多周期K线数据、均线位置等预处理信息
4. THE Market_Analysis_Agent SHALL 设计分析任务提示词模板，引导LLM按照固定结构输出分析结论
5. THE Market_Analysis_Agent SHALL 使用Few-shot示例引导LLM输出格式和分析风格
6. THE Market_Analysis_Agent SHALL 将复杂分析任务拆分为多个子任务（支撑压力识别、短期预期、中长期预期）
7. THE Market_Analysis_Agent SHALL 设计上下文压缩策略，在token限制内传递最关键的市场信息
8. THE Market_Analysis_Agent SHALL 支持提示词模板的版本管理和A/B测试

---

### Requirement 5: 支撑压力位识别（分析层 - LLM分析）

**User Story:** As a 投资者, I want to LLM自动识别支撑压力位, so that 我能了解大盘当前所处的关键价位区域。

#### Acceptance Criteria

1. WHEN 日线数据被提供给LLM THEN THE Market_Analysis_Agent SHALL 由LLM识别日线级别的支撑压力位（基于前期高低点、成交密集区）
2. WHEN 15分钟线数据被提供给LLM THEN THE Market_Analysis_Agent SHALL 由LLM识别15分钟级别的支撑压力位
3. WHEN 5分钟线数据被提供给LLM THEN THE Market_Analysis_Agent SHALL 由LLM识别5分钟级别的支撑压力位
4. WHEN 1分钟线数据被提供给LLM THEN THE Market_Analysis_Agent SHALL 由LLM识别1分钟级别的支撑压力位
5. WHEN 均线数据被提供给LLM THEN THE Market_Analysis_Agent SHALL 由LLM将均线位置作为动态支撑压力位纳入分析
6. THE Market_Analysis_Agent SHALL 由LLM按照重要性对支撑压力位进行排序（日线级别 > 15分钟级别 > 5分钟级别 > 1分钟级别；近期的支撑压力位 > 远期的支撑压力位）
7. THE Market_Analysis_Agent SHALL 由LLM标注当日最关键的支撑位和压力位

---

### Requirement 6: 当前价格位置分析（分析层 - LLM分析）

**User Story:** As a 投资者, I want to 了解当前价格相对于支撑压力位的位置, so that 我能判断当前市场所处的技术位置。

#### Acceptance Criteria

1. WHEN 支撑压力位被LLM识别 THEN THE Market_Analysis_Agent SHALL 由LLM计算当前价格距离上方最近压力位的距离（点数和百分比）
2. WHEN 支撑压力位被LLM识别 THEN THE Market_Analysis_Agent SHALL 由LLM计算当前价格距离下方最近支撑位的距离（点数和百分比）
3. THE Market_Analysis_Agent SHALL 由LLM判断当前价格处于支撑位附近、压力位附近还是中间区域
4. THE Market_Analysis_Agent SHALL 由LLM输出当前价格上下方各3个关键支撑压力位

---

### Requirement 7: 短期走势预期（分析层 - LLM分析 - 次日预期）

**User Story:** As a 投资者, I want to 获得次日大盘走势预期, so that 我能为次日交易做好准备。

#### Acceptance Criteria

1. WHEN 分析完成 THEN THE Market_Analysis_Agent SHALL 由LLM根据当日收盘位置给出次日开盘预期场景
2. WHEN 预期次日在压力位上方开盘 THEN THE Market_Analysis_Agent SHALL 由LLM给出突破预期分析（突破概率、目标位）
3. WHEN 预期次日在支撑位与压力位之间开盘 THEN THE Market_Analysis_Agent SHALL 由LLM给出震荡修复预期分析
4. WHEN 预期次日在支撑位下方开盘 THEN THE Market_Analysis_Agent SHALL 由LLM给出下探预期分析（支撑测试、止跌信号）
5. THE Market_Analysis_Agent SHALL 由LLM给出次日关键观察点位和操作建议

---

### Requirement 8: 中长期走势预期（分析层 - LLM分析）

**User Story:** As a 投资者, I want to 获得中长期大盘走势预期, so that 我能把握大盘整体趋势方向。

#### Acceptance Criteria

1. WHEN 日线数据分析完成 THEN THE Market_Analysis_Agent SHALL 由LLM判断当前大盘处于上升趋势、下降趋势还是震荡趋势
2. WHEN 趋势被判断 THEN THE Market_Analysis_Agent SHALL 由LLM给出周线级别的趋势预期（1-4周）
3. WHEN 趋势被判断 THEN THE Market_Analysis_Agent SHALL 由LLM给出月线级别的趋势预期（1-3个月）
4. THE Market_Analysis_Agent SHALL 由LLM标注中长期关键支撑压力位
5. THE Market_Analysis_Agent SHALL 由LLM给出趋势转折的关键信号和观察点位

---

### Requirement 9: 分析报告输出（输出层）

**User Story:** As a 投资者, I want to 获得结构化的分析报告, so that 我能快速理解分析结论。

#### Acceptance Criteria

1. THE Market_Analysis_Agent SHALL 输出包含以下部分的结构化报告：当前位置分析、支撑压力位列表、短期预期、中长期预期
2. THE Market_Analysis_Agent SHALL 使用清晰的格式展示关键数据（表格形式展示支撑压力位）
3. THE Market_Analysis_Agent SHALL 对预期结论给出置信度评级（高、中、低）
4. WHEN 输出报告 THEN THE Market_Analysis_Agent SHALL 包含分析时间戳和数据截止时间
5. THE Market_Analysis_Agent SHALL 支持JSON格式和文本格式两种输出方式

---

### Requirement 10: 支撑压力位图表可视化（输出层）

**User Story:** As a 投资者, I want to 在K线图上直观看到支撑压力位, so that 我能更直观地理解当前价格与关键位置的关系。

#### Acceptance Criteria

1. THE Chart_Renderer SHALL 在K线图上绘制水平线标注支撑位（绿色）和压力位（红色）
2. THE Chart_Renderer SHALL 区分不同级别的支撑压力位（日线级别用实线、15分钟级别用虚线、5分钟级别用点线）
3. THE Chart_Renderer SHALL 在支撑压力位旁标注价格数值
4. THE Chart_Renderer SHALL 绘制均线并标注均线名称（MA5、MA10、MA20等）
5. THE Chart_Renderer SHALL 高亮显示当日最关键的支撑位和压力位
6. THE Chart_Renderer SHALL 支持输出PNG图片格式
7. WHEN 用户指定时间范围 THEN THE Chart_Renderer SHALL 按指定范围绘制K线图
