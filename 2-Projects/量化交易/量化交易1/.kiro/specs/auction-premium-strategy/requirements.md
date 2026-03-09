# 需求文档

## 简介

本项目旨在评估和验证一个基于A股竞价阶段数据的次日溢价策略。核心假设是：竞价阶段表现出强资金承接特征的个股，在次日开盘时更可能获得正溢价。

## 术语表

- **Auction_System**: 竞价策略评估系统
- **Auction_Spread**: 竞价价差，定义为 (开盘涨幅 - 竞价最低涨幅)
- **Auction_Amount**: 竞价成交金额（单位：万元）
- **Auction_Turnover**: 竞价换手率（竞价成交量/流通股本）
- **Next_Day_Premium**: 次日溢价，定义为 (次日开盘价 - 当日收盘价) / 当日收盘价
- **Sector_Heat**: 板块热度，基于板块内涨停家数和涨幅排名
- **Pressure_Zone**: 套牢压力区，基于历史成交密集区和前高位置
- **Board_Height**: 连板高度，个股当前连续涨停天数
- **Market_Emotion**: 市场情绪指标，基于全市场涨跌停家数比

## 需求

### 需求 1：竞价数据采集

**用户故事：** 作为策略研究者，我希望采集每日竞价阶段的关键数据，以便分析竞价特征与次日溢价的关系。

#### 验收标准

1. WHEN 交易日竞价结束后，THE Auction_System SHALL 采集所有非ST、非新股的个股竞价数据
2. THE Auction_System SHALL 记录每只个股的竞价最低价、竞价最高价、开盘价、竞价成交量、竞价成交额
3. THE Auction_System SHALL 计算 Auction_Spread 为 (开盘涨幅 - 竞价最低涨幅)
4. THE Auction_System SHALL 计算 Auction_Turnover 为 (竞价成交量 / 流通股本 × 100%)
5. WHEN 个股为涨停开盘时，THE Auction_System SHALL 标记该个股为涨停竞价股

### 需求 2：多维度筛选条件

**用户故事：** 作为策略研究者，我希望基于多个维度筛选候选标的，以便提高策略的胜率和盈亏比。

#### 验收标准

1. THE Auction_System SHALL 筛选 Auction_Spread 排名前N的个股（N可配置，默认20）
2. THE Auction_System SHALL 筛选 Auction_Amount 大于阈值的个股（阈值可配置，默认500万）
3. THE Auction_System SHALL 筛选 Auction_Turnover 大于阈值的个股（阈值可配置，默认0.5%）
4. THE Auction_System SHALL 排除流通市值小于5亿或大于500亿的个股
5. THE Auction_System SHALL 排除上市不足60个交易日的次新股
6. THE Auction_System SHALL 排除ST和*ST标记的个股

### 需求 3：题材热度评估

**用户故事：** 作为策略研究者，我希望评估个股所属题材的热度状态，以便判断题材是否处于主升期。

#### 验收标准

1. THE Auction_System SHALL 获取每只候选个股的所属概念板块
2. THE Auction_System SHALL 计算每个板块当日的涨停家数
3. THE Auction_System SHALL 计算每个板块近5日的涨停家数趋势（上升/平稳/下降）
4. WHEN 板块当日涨停家数>=3且近5日趋势为上升时，THE Auction_System SHALL 标记该板块为"主升期"
5. WHEN 板块当日涨停家数>=2且近5日趋势为平稳时，THE Auction_System SHALL 标记该板块为"活跃期"
6. THE Auction_System SHALL 优先选择处于"主升期"或"活跃期"板块的个股

### 需求 4：技术压力评估

**用户故事：** 作为策略研究者，我希望评估个股左侧的套牢压力，以便避免选择压力较大的标的。

#### 验收标准

1. THE Auction_System SHALL 计算个股当前价格距离60日内最高价的距离百分比
2. THE Auction_System SHALL 识别个股近60日内的成交密集区（成交量加权平均价格区间）
3. WHEN 当前价格处于成交密集区下方10%以内时，THE Auction_System SHALL 标记为"压力较大"
4. WHEN 当前价格已突破成交密集区时，THE Auction_System SHALL 标记为"压力较小"
5. THE Auction_System SHALL 优先选择"压力较小"的个股
6. THE Auction_System SHALL 计算个股距离前高的空间百分比作为参考指标

### 需求 5：连板高度与市场情绪

**用户故事：** 作为策略研究者，我希望结合连板高度和市场情绪来调整策略参数，以便适应不同市场环境。

#### 验收标准

1. THE Auction_System SHALL 记录每只候选个股的 Board_Height（连板天数）
2. THE Auction_System SHALL 计算当日全市场涨停家数和跌停家数
3. THE Auction_System SHALL 计算 Market_Emotion 为 (涨停家数 - 跌停家数) / (涨停家数 + 跌停家数)
4. WHEN Market_Emotion > 0.5 时，THE Auction_System SHALL 标记市场情绪为"强势"
5. WHEN Market_Emotion 在 0 到 0.5 之间时，THE Auction_System SHALL 标记市场情绪为"中性"
6. WHEN Market_Emotion < 0 时，THE Auction_System SHALL 标记市场情绪为"弱势"
7. WHEN 市场情绪为"弱势"时，THE Auction_System SHALL 降低筛选数量或提高筛选阈值

### 需求 6：策略回测与评估

**用户故事：** 作为策略研究者，我希望对策略进行历史回测，以便评估策略的有效性和稳定性。

#### 验收标准

1. THE Auction_System SHALL 支持指定日期范围的历史回测
2. THE Auction_System SHALL 计算每日筛选结果的次日溢价率
3. THE Auction_System SHALL 统计策略的胜率（次日溢价为正的比例）
4. THE Auction_System SHALL 统计策略的平均溢价率和中位数溢价率
5. THE Auction_System SHALL 统计策略的最大回撤和盈亏比
6. THE Auction_System SHALL 按不同筛选条件组合输出对比分析报告
7. THE Auction_System SHALL 输出每日筛选明细和次日表现的详细记录

### 需求 7：结果输出与可视化

**用户故事：** 作为策略研究者，我希望以清晰的格式查看策略结果，以便快速做出决策。

#### 验收标准

1. THE Auction_System SHALL 输出每日候选股票列表，包含所有筛选维度的数值
2. THE Auction_System SHALL 按综合评分对候选股票进行排序
3. THE Auction_System SHALL 生成回测结果的统计图表（胜率曲线、收益分布等）
4. THE Auction_System SHALL 支持导出Excel格式的详细数据
5. THE Auction_System SHALL 在输出中标注每只个股的风险提示（如压力位、题材退潮等）

### 需求 8：风险控制与仓位管理

**用户故事：** 作为策略研究者，我希望系统具备完善的风控机制，以便控制单笔和整体风险敞口。

#### 验收标准

1. THE Auction_System SHALL 设置单日最大选股数量上限（可配置，默认3只）
2. THE Auction_System SHALL 设置单只个股最大仓位比例（可配置，默认30%）
3. WHEN 次日开盘价低于买入价一定比例时，THE Auction_System SHALL 触发止损信号（止损比例可配置，默认-3%）
4. WHEN 次日开盘价高于买入价一定比例时，THE Auction_System SHALL 触发止盈信号（止盈比例可配置，默认+5%）
5. WHEN 市场情绪为"弱势"时，THE Auction_System SHALL 自动降低单日选股数量至1只或暂停选股
6. THE Auction_System SHALL 计算并监控策略的最大连续亏损次数
7. WHEN 连续亏损次数达到阈值时，THE Auction_System SHALL 发出风险预警（阈值可配置，默认5次）
8. THE Auction_System SHALL 记录每笔交易的盈亏情况用于风控分析

### 需求 9：异常情况处理

**用户故事：** 作为策略研究者，我希望系统能识别和处理异常情况，以便避免在特殊市场环境下产生错误信号。

#### 验收标准

1. WHEN 个股当日为复牌首日时，THE Auction_System SHALL 排除该个股
2. WHEN 个股当日有重大利好/利空公告时，THE Auction_System SHALL 标记为"事件驱动"并单独分析
3. WHEN 大盘出现极端行情（涨停/跌停家数超过500家）时，THE Auction_System SHALL 标记为"极端市场"
4. WHEN 处于"极端市场"状态时，THE Auction_System SHALL 暂停策略信号输出或调整参数
5. THE Auction_System SHALL 识别并排除因除权除息导致的异常竞价数据
6. WHEN 竞价数据出现明显异常值时，THE Auction_System SHALL 进行数据清洗或标记

### 需求 10：参数配置与优化

**用户故事：** 作为策略研究者，我希望能够灵活配置和优化策略参数，以便找到最优参数组合。

#### 验收标准

1. THE Auction_System SHALL 支持通过配置文件设置所有筛选阈值
2. THE Auction_System SHALL 支持参数网格搜索功能
3. WHEN 执行参数优化时，THE Auction_System SHALL 输出不同参数组合的回测结果对比
4. THE Auction_System SHALL 记录每次回测使用的参数配置
5. THE Auction_System SHALL 支持保存和加载最优参数配置
