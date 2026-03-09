# 需求文档

## 简介

本项目旨在构建一个基于市场情绪的A股隔夜溢价策略系统。核心假设是：在特定市场情绪环境下，具备某些技术特征的个股在次日开盘时更可能获得正溢价。本策略不依赖L2数据，仅使用日线级别数据和市场情绪指标。

## 术语表

- **Overnight_System**: 隔夜溢价策略系统
- **Overnight_Premium**: 隔夜溢价率，定义为 (次日开盘价 - 当日收盘价) / 当日收盘价
- **Market_Emotion_Index**: 市场情绪指数，基于涨跌停比、涨跌家数比、连板高度等综合计算
- **Sector_Momentum**: 板块动量，基于板块涨幅排名和资金流向
- **Individual_Strength**: 个股强度，基于涨幅、换手率、量比等指标
- **Limit_Up_Count**: 涨停家数
- **Limit_Down_Count**: 跌停家数
- **Board_Height**: 市场最高连板高度
- **Emotion_Cycle**: 情绪周期，分为启动期、发酵期、高潮期、退潮期

## 需求

### 需求 1：日线数据采集

**用户故事：** 作为策略研究者，我希望采集每日收盘后的日线数据，以便分析个股特征与次日溢价的关系。

#### 验收标准

1. WHEN 交易日收盘后，THE Overnight_System SHALL 采集所有A股的日线数据
2. THE Overnight_System SHALL 记录每只个股的开盘价、最高价、最低价、收盘价、成交量、成交额
3. THE Overnight_System SHALL 计算每只个股的涨跌幅、换手率、量比
4. THE Overnight_System SHALL 识别涨停、跌停、炸板个股
5. THE Overnight_System SHALL 排除ST、*ST、新股（上市不足20日）

### 需求 2：市场情绪指数计算

**用户故事：** 作为策略研究者，我希望量化市场整体情绪状态，以便判断当前市场环境是否适合执行策略。

#### 验收标准

1. THE Overnight_System SHALL 计算当日涨停家数和跌停家数
2. THE Overnight_System SHALL 计算涨跌停比 = 涨停家数 / (涨停家数 + 跌停家数)
3. THE Overnight_System SHALL 计算上涨家数和下跌家数
4. THE Overnight_System SHALL 计算涨跌家数比 = 上涨家数 / (上涨家数 + 下跌家数)
5. THE Overnight_System SHALL 统计当日最高连板高度
6. THE Overnight_System SHALL 统计连板股数量（2板及以上）
7. THE Overnight_System SHALL 计算综合情绪指数 = 0.4 × 涨跌停比 + 0.3 × 涨跌家数比 + 0.2 × (连板高度/10) + 0.1 × (连板股数量/50)
8. WHEN 综合情绪指数 > 0.7 时，THE Overnight_System SHALL 标记为"强势市场"
9. WHEN 综合情绪指数在 0.4 到 0.7 之间时，THE Overnight_System SHALL 标记为"中性市场"
10. WHEN 综合情绪指数 < 0.4 时，THE Overnight_System SHALL 标记为"弱势市场"

### 需求 3：情绪周期判断

**用户故事：** 作为策略研究者，我希望识别市场情绪所处的周期阶段，以便调整策略参数。

#### 验收标准

1. THE Overnight_System SHALL 记录近5日的情绪指数序列
2. WHEN 情绪指数连续3日上升且当日 > 0.5 时，THE Overnight_System SHALL 标记为"启动期"
3. WHEN 情绪指数维持在 0.6 以上且波动小于 0.1 时，THE Overnight_System SHALL 标记为"发酵期"
4. WHEN 情绪指数达到近20日最高且 > 0.75 时，THE Overnight_System SHALL 标记为"高潮期"
5. WHEN 情绪指数从高位连续2日下降超过 0.1 时，THE Overnight_System SHALL 标记为"退潮期"
6. THE Overnight_System SHALL 在"启动期"和"发酵期"增加选股数量
7. THE Overnight_System SHALL 在"高潮期"保持谨慎，减少选股数量
8. THE Overnight_System SHALL 在"退潮期"暂停选股或仅选择防守型标的

### 需求 4：板块动量分析

**用户故事：** 作为策略研究者，我希望识别当日强势板块，以便从中筛选候选标的。

#### 验收标准

1. THE Overnight_System SHALL 获取所有概念板块和行业板块的涨跌幅
2. THE Overnight_System SHALL 计算每个板块的涨停家数
3. THE Overnight_System SHALL 计算每个板块近3日的涨幅累计
4. THE Overnight_System SHALL 按涨停家数和涨幅对板块进行排名
5. WHEN 板块当日涨停家数 >= 3 且涨幅排名前10 时，THE Overnight_System SHALL 标记为"主线板块"
6. WHEN 板块当日涨停家数 >= 2 且近3日涨幅 > 5% 时，THE Overnight_System SHALL 标记为"活跃板块"
7. THE Overnight_System SHALL 优先从"主线板块"和"活跃板块"中筛选个股

### 需求 5：个股强度评估

**用户故事：** 作为策略研究者，我希望评估个股的日内强度，以便筛选出强势个股。

#### 验收标准

1. THE Overnight_System SHALL 计算个股当日涨幅排名（在所属板块内）
2. THE Overnight_System SHALL 计算个股换手率（相对于近20日平均）
3. THE Overnight_System SHALL 计算个股量比
4. THE Overnight_System SHALL 计算个股振幅
5. THE Overnight_System SHALL 计算收盘价相对于日内高点的位置 = (收盘价 - 最低价) / (最高价 - 最低价)
6. WHEN 收盘价位置 > 0.8 且涨幅 > 5% 时，THE Overnight_System SHALL 标记为"强势收盘"
7. WHEN 个股为涨停且未开板 时，THE Overnight_System SHALL 标记为"一字涨停"或"T字涨停"
8. WHEN 个股涨停后开板又封回 时，THE Overnight_System SHALL 标记为"炸板回封"

### 需求 6：候选股筛选条件

**用户故事：** 作为策略研究者，我希望基于多维度条件筛选候选标的，以便提高策略胜率。

#### 验收标准

1. THE Overnight_System SHALL 筛选涨幅在 3% 到 9.9% 之间的个股（非涨停但强势）
2. THE Overnight_System SHALL 筛选换手率在 3% 到 20% 之间的个股
3. THE Overnight_System SHALL 筛选量比 > 1.5 的个股
4. THE Overnight_System SHALL 筛选流通市值在 20亿 到 200亿 之间的个股
5. THE Overnight_System SHALL 筛选收盘价位置 > 0.7 的个股
6. THE Overnight_System SHALL 筛选所属板块为"主线板块"或"活跃板块"的个股
7. THE Overnight_System SHALL 排除近5日内有涨停的个股（避免高位接力）
8. THE Overnight_System SHALL 排除近20日跌幅超过 20% 的个股（避免下跌趋势）

### 需求 7：综合评分与排序

**用户故事：** 作为策略研究者，我希望对候选股进行综合评分，以便选出最优标的。

#### 验收标准

1. THE Overnight_System SHALL 计算板块强度得分（主线板块 30分，活跃板块 20分，其他 10分）
2. THE Overnight_System SHALL 计算涨幅得分（涨幅越高得分越高，满分 25分）
3. THE Overnight_System SHALL 计算换手率得分（适中换手率得分最高，满分 20分）
4. THE Overnight_System SHALL 计算收盘位置得分（位置越高得分越高，满分 15分）
5. THE Overnight_System SHALL 计算量比得分（量比适中得分最高，满分 10分）
6. THE Overnight_System SHALL 计算综合得分 = 板块得分 + 涨幅得分 + 换手得分 + 位置得分 + 量比得分
7. THE Overnight_System SHALL 按综合得分降序排列候选股
8. THE Overnight_System SHALL 输出得分最高的前N只个股（N根据市场情绪调整）

### 需求 8：策略回测与评估

**用户故事：** 作为策略研究者，我希望对策略进行历史回测，以便评估策略有效性。

#### 验收标准

1. THE Overnight_System SHALL 支持指定日期范围的历史回测
2. THE Overnight_System SHALL 计算每日筛选结果的次日溢价率
3. THE Overnight_System SHALL 统计策略胜率（次日溢价为正的比例）
4. THE Overnight_System SHALL 统计平均溢价率和中位数溢价率
5. THE Overnight_System SHALL 统计不同市场情绪下的胜率差异
6. THE Overnight_System SHALL 统计不同情绪周期下的表现差异
7. THE Overnight_System SHALL 输出每日筛选明细和次日表现记录

### 需求 9：风险控制

**用户故事：** 作为策略研究者，我希望系统具备风控机制，以便控制风险敞口。

#### 验收标准

1. THE Overnight_System SHALL 设置单日最大选股数量（强势市场 5只，中性市场 3只，弱势市场 1只）
2. THE Overnight_System SHALL 设置单只个股最大仓位比例（默认 20%）
3. WHEN 市场情绪为"弱势市场"时，THE Overnight_System SHALL 暂停选股或仅选择1只
4. WHEN 情绪周期为"退潮期"时，THE Overnight_System SHALL 暂停选股
5. WHEN 连续3日策略亏损时，THE Overnight_System SHALL 发出风险预警
6. THE Overnight_System SHALL 记录每笔交易的盈亏情况

### 需求 10：结果输出

**用户故事：** 作为策略研究者，我希望以清晰格式查看策略结果。

#### 验收标准

1. THE Overnight_System SHALL 输出每日候选股票列表，包含所有评分维度
2. THE Overnight_System SHALL 输出当日市场情绪状态和情绪周期
3. THE Overnight_System SHALL 输出主线板块和活跃板块列表
4. THE Overnight_System SHALL 生成回测结果统计报表
5. THE Overnight_System SHALL 支持导出Excel格式数据
6. THE Overnight_System SHALL 在输出中标注风险提示

### 需求 11：参数配置

**用户故事：** 作为策略研究者，我希望能够灵活配置策略参数。

#### 验收标准

1. THE Overnight_System SHALL 支持通过配置文件设置所有筛选阈值
2. THE Overnight_System SHALL 支持配置情绪指数的权重参数
3. THE Overnight_System SHALL 支持配置评分系统的权重参数
4. THE Overnight_System SHALL 支持保存和加载配置
5. THE Overnight_System SHALL 记录每次回测使用的参数配置

