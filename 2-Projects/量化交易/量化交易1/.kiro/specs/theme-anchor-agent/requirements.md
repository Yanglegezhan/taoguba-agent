# Requirements Document

## Introduction

A股超短线题材锚定Agent是一个智能市场分析系统，模拟十年经验游资操盘手的思维模式，通过多维度数据解构识别当日热点题材，还原市场资金真实意图。系统基于"龙头战法"与"情绪周期论"，对板块强度、盘面联动、情绪周期和题材结构进行系统化分析。

## Glossary

- **Theme_Anchor_Agent**: 题材锚定智能分析系统
- **Sector**: 板块（行业或概念板块）
- **Strength_Score**: 板块强度分数
- **Target_Sector_Set**: 目标板块集合（筛选后的核心板块）
- **Intraday_Data**: 分时图数据（分钟级价格数据）
- **Limit_Up**: 涨停
- **Consecutive_Board**: 连板（连续涨停天数）
- **Blown_Board**: 炸板（涨停后打开）
- **Leading_Stock**: 龙头股
- **Emotion_Cycle**: 情绪周期
- **Market_Index**: 大盘指数
- **Turnover**: 成交额
- **Market_Cap**: 流通市值
- **Resonance_Point**: 共振点（大盘关键变盘节点）
- **Time_Lag**: 时差（板块与大盘起涨时间差）
- **Pyramid_Structure**: 金字塔结构（板块内连板梯队）

## Requirements

### Requirement 1: 题材筛选与强度初筛

**User Story:** 作为市场分析师，我希望系统能够自动筛选出当日最强势的核心板块，以便聚焦分析重点题材。

#### Acceptance Criteria

1. WHEN 系统接收到N日板块强度数据 THEN THE Theme_Anchor_Agent SHALL 识别所有强度分数（N日累计涨停数）大于8000的板块并将其加入Target_Sector_Set
2. WHEN Target_Sector_Set中的板块数量少于7个 THEN THE Theme_Anchor_Agent SHALL 从强度分数2000到8000范围内按分数降序补齐至7个板块
5. WHEN 生成Target_Sector_Set后 THEN THE Theme_Anchor_Agent SHALL 标记每个板块是"新面孔"还是"老面孔"
6. WHEN 判定板块新旧时 THEN THE Theme_Anchor_Agent SHALL 将首次进入前7的板块标记为"新面孔"，连续多日在前7的板块标记为"老面孔"

### Requirement 2: 盘面联动与主动性分析

**User Story:** 作为操盘手，我希望系统能够分析板块与大盘的联动关系，识别具有主动性的领涨板块，以便判断资金流向和市场情绪引领者。

#### Acceptance Criteria

1. WHEN 系统接收到Market_Index的Intraday_Data和目标板块的Intraday_Data THEN THE Theme_Anchor_Agent SHALL 识别大盘分时图的关键Resonance_Point（急跌低点、V型反转点、突破点）
2. WHEN 识别到Resonance_Point后 THEN THE Theme_Anchor_Agent SHALL 计算每个目标板块与大盘的Time_Lag
3. WHEN 板块起涨时间早于大盘5到10分钟 THEN THE Theme_Anchor_Agent SHALL 将该板块标记为"先锋"（Leading）
4. WHEN 大盘上涨1%时某板块上涨超过3% THEN THE Theme_Anchor_Agent SHALL 将该板块标记为"强度共振"（Resonance）
5. WHEN 大盘跳水时某板块保持平稳或逆势上涨 THEN THE Theme_Anchor_Agent SHALL 将该板块标记为"分离"（Divergence）
6. WHEN 某板块拉升时其他板块同步跳水 THEN THE Theme_Anchor_Agent SHALL 识别并记录"跷跷板效应"（Seesaw）及资金来源板块

### Requirement 3: 情绪周期定性

**User Story:** 作为交易员，我希望系统能够判定当前题材所处的情绪周期阶段，以便评估风险和机会。

#### Acceptance Criteria

1. WHEN 系统接收到涨停家数、连板高度、全市场炸板率、昨日涨停今日表现和板块分时数据 THEN THE Theme_Anchor_Agent SHALL 调用LLM分析并判定每个目标板块的Emotion_Cycle阶段
2. WHEN LLM分析板块情绪周期时 THEN THE Theme_Anchor_Agent SHALL 提供结构化的市场数据（涨停数、连板梯队、炸板率、分时走势等）作为上下文
3. WHEN LLM返回情绪周期判定结果时 THEN THE Theme_Anchor_Agent SHALL 解析并验证结果包含阶段标签（启动期/高潮期/分化期/修复期/退潮期）、置信度和判定理由
4. WHEN LLM判定失败或返回无效结果时 THEN THE Theme_Anchor_Agent SHALL 记录错误并返回默认的"未知"阶段标记
5. WHEN 生成情绪周期分析提示词时 THEN THE Theme_Anchor_Agent SHALL 包含情绪周期理论的关键特征描述（启动期、高潮期、分化期、修复期、退潮期的典型特征）
6. WHEN 板块历史数据可用时 THEN THE Theme_Anchor_Agent SHALL 将历史情绪周期信息提供给LLM作为参考

### Requirement 4: 题材容量与结构画像

**User Story:** 作为投资决策者，我希望系统能够分析题材的资金容量和内部结构健康度，以便判断题材的持续性和适配资金规模。

#### Acceptance Criteria

1. WHEN 系统接收到板块成交额、板块内个股流通市值和Top5成交额个股的成交额数据 THEN THE Theme_Anchor_Agent SHALL 计算并分类板块容量
2. WHEN 核心中军成交额大于30亿每日且板块总成交额巨大 THEN THE Theme_Anchor_Agent SHALL 将该板块标记为"大容量主线"
3. WHEN 板块内无大市值股票且全靠小盘连板股 THEN THE Theme_Anchor_Agent SHALL 将该板块标记为"小众投机题材"
4. WHEN 分析板块结构时 THEN THE Theme_Anchor_Agent SHALL 构建Pyramid_Structure展示连板梯队分布
5. WHEN 构建Pyramid_Structure时 THEN THE Theme_Anchor_Agent SHALL 统计5板、3板、1板个股数量并评估梯队完整性
6. WHEN Pyramid_Structure断层较少时 THEN THE Theme_Anchor_Agent SHALL 将该板块结构标记为"健康"

### Requirement 5: 数据输入与集成

**User Story:** 作为系统用户，我希望系统能够从开盘啦API获取所需的市场数据，以便进行自动化分析。

#### Acceptance Criteria

1. WHEN 系统启动分析流程时 THEN THE Theme_Anchor_Agent SHALL 从开盘啦API获取板块强度分数列表
2. WHEN 系统需要盘面联动分析时 THEN THE Theme_Anchor_Agent SHALL 从开盘啦API获取大盘和板块的Intraday_Data
3. WHEN 系统需要情绪周期分析时 THEN THE Theme_Anchor_Agent SHALL 从开盘啦API获取涨停数据、连板数据和全市场炸板率数据
4. WHEN 系统需要容量分析时 THEN THE Theme_Anchor_Agent SHALL 从开盘啦API获取板块成交额和个股市值数据
5. WHEN API调用失败时 THEN THE Theme_Anchor_Agent SHALL 记录错误并返回明确的错误信息
6. WHEN 数据缺失或异常时 THEN THE Theme_Anchor_Agent SHALL 标记数据质量问题并继续处理可用数据

### Requirement 6: 分析报告生成

**User Story:** 作为决策者，我希望系统能够生成结构化的分析报告，清晰呈现所有分析结果和关键发现。

#### Acceptance Criteria

1. WHEN 所有分析步骤完成后 THEN THE Theme_Anchor_Agent SHALL 生成包含所有目标板块的综合分析报告
2. WHEN 生成报告时 THEN THE Theme_Anchor_Agent SHALL 包含板块筛选结果、新旧标记和强度分数
3. WHEN 生成报告时 THEN THE Theme_Anchor_Agent SHALL 包含盘面联动分析结果（先锋、共振、分离、跷跷板效应）
4. WHEN 生成报告时 THEN THE Theme_Anchor_Agent SHALL 包含情绪周期判定结果和风险提示
5. WHEN 生成报告时 THEN THE Theme_Anchor_Agent SHALL 包含容量分类和结构健康度评估
6. WHEN 生成报告时 THEN THE Theme_Anchor_Agent SHALL 按板块强度或综合评分排序展示结果

### Requirement 7: 历史数据追踪

**User Story:** 作为分析师，我希望系统能够追踪板块的历史表现，以便判断板块是新面孔还是老面孔，以及识别情绪周期的演变。

#### Acceptance Criteria

1. WHEN 系统运行时 THEN THE Theme_Anchor_Agent SHALL 维护板块历史强度排名数据
2. WHEN 判定板块新旧时 THEN THE Theme_Anchor_Agent SHALL 查询该板块在过去7日内是否进入过前7强
3. WHEN 板块在过去7日内未进入过前7强 THEN THE Theme_Anchor_Agent SHALL 将其标记为"新面孔"
4. WHEN 板块在过去7日内连续进入前7强 THEN THE Theme_Anchor_Agent SHALL 将其标记为"老面孔"并记录持续天数
5. WHEN 存储历史数据时 THEN THE Theme_Anchor_Agent SHALL 使用本地文件或数据库持久化存储
6. WHEN 历史数据不存在时 THEN THE Theme_Anchor_Agent SHALL 初始化历史记录并将所有板块标记为"新面孔"
