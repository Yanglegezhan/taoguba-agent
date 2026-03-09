# 需求文档

## 简介

本系统是一个A股次日核心个股超预期分析的智能体系统，通过三个阶段的智能体协作，实现从数据沉淀、策略校准到竞价监测的全流程自动化分析，最终输出明确的买卖建议。系统整合了大盘分析、情绪分析、题材分析、技术分析、外部变量对冲和实时竞价监测等多个维度。

### 技术架构约束

- **智能体架构**：三个Agent（Stage1、Stage2、Stage3）均可独立运作，互不依赖
- **基础模型**：所有Agent使用Gemini-2.0-Flash作为基础LLM
- **主要数据源**：kaipanla_crawler.py提供的接口
- **补充数据源**：AKShare（需禁用代理）、东方财富爬虫接口
- **数据流向**：Stage1输出 → Stage2输入 → Stage3输入（通过文件或数据库传递）

## 术语表

- **System**: 次日核心个股超预期分析系统
- **Stage1_Agent**: 第一阶段数据沉淀与复盘智能体（独立运作）
- **Stage2_Agent**: 第二阶段早盘策略校准智能体（独立运作）
- **Stage3_Agent**: 第三阶段竞价轨迹监测智能体（独立运作）
- **Base_LLM**: 基础大语言模型，使用Gemini-2.0-Flash
- **Kaipanla_API**: 开盘啦爬虫接口，主要数据源
- **AKShare_API**: AKShare数据接口，补充数据源（需配置代理）
- **Eastmoney_API**: 东方财富爬虫接口，补充数据源
- **Gene_Pool**: 基因库，记录核心个股的历史特征和技术位
- **Additional_Pool**: 竞价附加票池，捕捉9:25后不在预设名单内但表现异常的个股
- **Recognition_Stock**: 辨识度个股，来自同花顺热门股排行榜前40名，具有市场关注度高的特征
- **Baseline_Expectation**: 基准预期，个股开盘的及格线
- **Auction_Trajectory**: 竞价轨迹，9:15-9:25的价格和订单变化
- **Expectation_Score**: 超预期分值，综合量能、价格、独立性的评分
- **L2_Data**: Level-2行情数据，包含买卖五档和封单余量
- **Market_Report**: 大盘分析报告
- **Emotion_Report**: 情绪分析报告
- **Theme_Report**: 题材分析报告
- **Overnight_Variables**: 隔夜外部变量，包括美股、期货、政策新闻等
- **Positioning_Signal**: 卡位信号，板块内个股的相对强弱变化
- **Seal_Ratio**: 封单比，封单金额/流通市值
- **Rush_Coefficient**: 抢筹价差系数，(开盘价 - 竞价最低价) / 昨收价
- **Volume_Ratio**: 量比，竞价成交量/昨日分钟均量
- **Reverse_Nuclear**: 极端反核，昨日大跌今日反转的个股
- **Formation_Strength**: 板块阵型强度，板块内强势个股的数量和质量
- **Status_Score**: 地位分值，附加池个股的综合评分
- **Theme_Recognition**: 题材辨识度，个股的新面孔属性和身位优势
- **Price_Volume_Urgency**: 量价急迫性，资金抢筹的力度和速度
- **Emotion_Hedge**: 情绪对冲力，个股相对龙头的卡位能力
- **New_Face**: 新面孔，昨日报告中未出现或今早突发利好的题材
- **Position_Advantage**: 身位优势，在同题材中的排名领先地位
- **Lone_Hero**: 孤胆英雄，龙头弱势时逆势走强的个股
- **Decision_Navigation**: 决策导航推演，9:25后的操作指南
- **Baseline_Table**: 及格线表，核心股的预期底线
- **Signal_Playbook**: 信号触发剧本，附加池的操作模板
- **Decision_Tree**: 多维分支决策树，不同场景的应对策略
- **Scenario_Exceed**: 整体超预期场景，核心大哥全封一字
- **Scenario_Divergence**: 分歧兑现场景，核心大哥低开或炸板
- **Scenario_Switch**: 高低切场景，资金切换到新题材
- **Rush_Positioning**: 暴力抢筹卡位流，9:20后疯狂扫货
- **Weak_Reverse**: 极弱转强反核流，昨日跌停今日反转

## 需求

### 需求 0：数据源配置与管理

**用户故事：** 作为系统管理员，我希望系统能正确配置和管理多个数据源，以便稳定获取市场数据。

#### 验收标准

1. THE System SHALL 使用 Kaipanla_API 作为主要数据源
2. THE System SHALL 支持通过配置文件设置 AKShare_API 的代理参数
3. WHEN AKShare_API 调用前，THE System SHALL 自动配置代理设置
4. THE System SHALL 支持配置 Eastmoney_API 的访问参数
5. WHEN 主要数据源失败时，THE System SHALL 自动切换到补充数据源
6. THE System SHALL 记录每次数据获取的来源和状态
7. THE System SHALL 在配置文件中支持设置数据源优先级
8. WHEN 代理配置错误时，THE System SHALL 输出明确的错误提示

### 需求 1：生成静态复盘报告

**用户故事：** 作为交易者，我希望系统每日自动生成大盘、情绪和题材的复盘报告，以便了解当日市场整体状况。

#### 验收标准

1. WHEN 交易日收盘后，THE Stage1_Agent SHALL 读取当日完整行情数据
2. THE Stage1_Agent SHALL 调用现有的大盘分析Agent生成 Market_Report
3. THE Stage1_Agent SHALL 调用现有的情绪分析Agent生成 Emotion_Report
4. THE Stage1_Agent SHALL 调用现有的题材分析Agent生成 Theme_Report
5. THE Stage1_Agent SHALL 将三份报告存储到指定目录并标注日期
6. THE Stage1_Agent SHALL 在报告中标注关键指标（涨停家数、跌停家数、主力资金流向、热门题材等）

### 需求 2：构建个股基因库

**用户故事：** 作为交易者，我希望系统自动识别和记录核心个股的特征，以便建立个股画像和跟踪池。

#### 验收标准

1. THE Stage1_Agent SHALL 扫描当日连板梯队中的所有个股
2. THE Stage1_Agent SHALL 识别当日炸板股（曾涨停但未封住的个股）
3. THE Stage1_Agent SHALL 获取同花顺热门股排行榜前40名作为 Recognition_Stock 基础池
4. THE Stage1_Agent SHALL 从同花顺热门股前40名中筛选符合趋势特征的个股作为趋势核心股（近期沿均线上涨的个股）
5. THE Stage1_Agent SHALL 将技术支撑位作为补充筛选条件，优先选择处于技术支撑位的个股
6. THE Stage1_Agent SHALL 记录每只个股的连板高度、板块归属、市值、换手率等基础信息
7. THE Stage1_Agent SHALL 将识别的个股添加到 Gene_Pool 并更新其历史记录
8. THE Stage1_Agent SHALL 为每只个股生成唯一标识符用于跨日追踪
9. THE Stage1_Agent SHALL 支持通过配置文件设置热门股数量（默认40，最大40）

### 需求 3：计算个股技术位

**用户故事：** 作为交易者，我希望系统自动计算个股的关键技术位，以便判断支撑和压力。

#### 验收标准

1. THE Stage1_Agent SHALL 计算 Gene_Pool 内每只个股的5日、10日、20日均线
2. THE Stage1_Agent SHALL 识别每只个股近60日内的前期高点
3. THE Stage1_Agent SHALL 计算每只个股近10日的筹码密集区（成交量加权价格区间）
4. THE Stage1_Agent SHALL 计算当前价格距离各均线的距离百分比
5. THE Stage1_Agent SHALL 计算当前价格距离前期高点的距离百分比
6. THE Stage1_Agent SHALL 标注个股是否处于筹码密集区内、上方或下方
7. THE Stage1_Agent SHALL 将技术位数据存储到 Gene_Pool 中对应个股记录

### 需求 4：接入隔夜外部变量

**用户故事：** 作为交易者，我希望系统在早盘前自动获取隔夜外部市场信息，以便评估对A股的影响。

#### 验收标准

1. WHEN 交易日早盘前（7:00-9:00），THE Stage2_Agent SHALL 获取隔夜美股主要指数收盘数据
2. THE Stage2_Agent SHALL 获取NVDA等科技龙头股的涨跌幅
3. THE Stage2_Agent SHALL 获取中概股指数的涨跌幅
4. THE Stage2_Agent SHALL 获取A50期货的最新价格和涨跌幅
5. THE Stage2_Agent SHALL 获取富时中国A50指数期货数据
6. THE Stage2_Agent SHALL 抓取四大证券报（证券时报、上海证券报、中国证券报、证券日报）的头条新闻
7. THE Stage2_Agent SHALL 抓取工信部、发改委等部门的最新政策公告
8. THE Stage2_Agent SHALL 将所有 Overnight_Variables 整合为结构化数据

### 需求 5：生成个股基准预期

**用户故事：** 作为交易者，我希望系统根据昨日表现和外部变量，为每只核心个股设定开盘及格线，以便判断是否超预期。

#### 验收标准

1. THE Stage2_Agent SHALL 读取 Gene_Pool 中所有个股的昨日表现
2. THE Stage2_Agent SHALL 结合 Market_Report、Emotion_Report 和 Theme_Report 评估市场环境
3. THE Stage2_Agent SHALL 结合 Overnight_Variables 评估外部影响
4. THE Stage2_Agent SHALL 为每只个股计算 Baseline_Expectation（预期开盘涨幅区间）
5. WHEN 个股昨日涨停且题材处于主升期时，THE Stage2_Agent SHALL 设定较高的 Baseline_Expectation（如+5%~+8%）
6. WHEN 个股昨日炸板或题材退潮时，THE Stage2_Agent SHALL 设定较低的 Baseline_Expectation（如-2%~+2%）
7. THE Stage2_Agent SHALL 输出每只个股的 Baseline_Expectation 及其计算逻辑说明

### 需求 6：捕捉突发新题材

**用户故事：** 作为交易者，我希望系统能实时捕捉早间突发的新题材，以便快速发现潜在机会。

#### 验收标准

1. THE Stage2_Agent SHALL 监控早间7:00-9:15的新闻流
2. WHEN 检测到重大政策利好或行业事件时，THE Stage2_Agent SHALL 立即标记为"突发题材"
3. THE Stage2_Agent SHALL 搜索与突发题材相关的A股个股
4. THE Stage2_Agent SHALL 将相关个股添加到当日临时监控池
5. THE Stage2_Agent SHALL 为新题材个股设定初步的 Baseline_Expectation
6. THE Stage2_Agent SHALL 在输出中标注"新题材"标签和相关新闻链接

### 需求 7：监测竞价撤单行为

**用户故事：** 作为交易者，我希望系统监测9:15-9:20的撤单行为，以便识别诱多嫌疑。

#### 验收标准

1. WHEN 竞价时间到达9:20时，THE Stage3_Agent SHALL 获取所有监控个股的9:15-9:20竞价分时数据
2. THE Stage3_Agent SHALL 计算每只个股在9:15和9:19的价格差异
3. WHEN 个股9:15涨停但9:19价格下跌超过3%时，THE Stage3_Agent SHALL 标记为"诱多嫌疑"
4. THE Stage3_Agent SHALL 计算9:15-9:20期间的撤单量（买盘减少量）
5. WHEN 撤单量超过初始挂单量的50%时，THE Stage3_Agent SHALL 标记为"大规模撤单"
6. THE Stage3_Agent SHALL 在输出中标注撤单行为的严重程度（轻度/中度/重度）

### 需求 8：监测真实博弈期价格轨迹

**用户故事：** 作为交易者，我希望系统监测9:20-9:25的真实博弈期，以便判断资金的真实意图。

#### 验收标准

1. THE Stage3_Agent SHALL 获取所有监控个股的9:20-9:25竞价分时数据（每分钟或更高频）
2. THE Stage3_Agent SHALL 计算价格重心的移动方向（向上/向下/震荡）
3. WHEN 价格稳步向上且买盘持续增加时，THE Stage3_Agent SHALL 标记为"强势"
4. WHEN 价格逐级下杀时，THE Stage3_Agent SHALL 标记为"弱势"
5. THE Stage3_Agent SHALL 计算9:20-9:25期间的买盘增量和卖盘增量
6. THE Stage3_Agent SHALL 识别价格轨迹的关键转折点（如突然拉升或跳水）
7. THE Stage3_Agent SHALL 输出每只个股的竞价轨迹评级（强/中/弱）

### 需求 9：监测板块联动与卡位信号

**用户故事：** 作为交易者，我希望系统监测板块内个股的竞价联动，以便识别卡位机会。

#### 验收标准

1. THE Stage3_Agent SHALL 识别每只监控个股所属的主要题材板块
2. THE Stage3_Agent SHALL 获取同板块内其他核心个股的竞价表现
3. THE Stage3_Agent SHALL 计算板块内个股的竞价涨幅排名
4. WHEN 板块龙头竞价下杀但其他个股逆势走强时，THE Stage3_Agent SHALL 标记为 Positioning_Signal
5. THE Stage3_Agent SHALL 计算个股相对板块的超额涨幅
6. THE Stage3_Agent SHALL 在输出中标注板块联动情况和卡位信号强度

### 需求 10：获取竞价最终快照

**用户故事：** 作为交易者，我希望系统在9:25:00准确获取竞价最终数据，以便进行精确计算。

#### 验收标准

1. WHEN 时间到达9:25:00时，THE Stage3_Agent SHALL 获取所有监控个股的最终竞价数据
2. THE Stage3_Agent SHALL 记录每只个股的开盘价、竞价成交金额、竞价成交量
3. THE Stage3_Agent SHALL 获取 L2_Data 中的买卖五档数据
4. WHEN 个股为涨停开盘时，THE Stage3_Agent SHALL 获取封单余量
5. THE Stage3_Agent SHALL 计算开盘涨幅相对昨日收盘价的百分比
6. THE Stage3_Agent SHALL 验证数据完整性，若缺失则标记为"数据异常"

### 需求 11：计算超预期分值（量能维度）

**用户故事：** 作为交易者，我希望系统评估竞价量能是否达标，以便判断资金承接力度。

#### 验收标准

1. THE Stage3_Agent SHALL 计算竞价成交金额与昨日全天成交金额的比值（Auction_Amount / Yesterday_Amount）
2. THE Stage3_Agent SHALL 结合个股市值计算竞价换手率
3. WHEN 竞价成交金额占比超过5%且换手率超过1%时，THE Stage3_Agent SHALL 标记量能为"充足"
4. WHEN 竞价成交金额占比低于2%或换手率低于0.3%时，THE Stage3_Agent SHALL 标记量能为"不足"
5. THE Stage3_Agent SHALL 根据量能充足程度计算量能分值（0-100分）
6. THE Stage3_Agent SHALL 在输出中标注量能评级和具体数值

### 需求 12：计算超预期分值（价格维度）

**用户故事：** 作为交易者，我希望系统评估开盘价是否超过基准预期，以便判断市场认可度。

#### 验收标准

1. THE Stage3_Agent SHALL 获取个股的 Baseline_Expectation（预期开盘涨幅区间）
2. THE Stage3_Agent SHALL 计算实际开盘涨幅
3. WHEN 实际开盘涨幅超过 Baseline_Expectation 上限时，THE Stage3_Agent SHALL 标记为"超预期"
4. WHEN 实际开盘涨幅低于 Baseline_Expectation 下限时，THE Stage3_Agent SHALL 标记为"不及预期"
5. THE Stage3_Agent SHALL 计算价格超预期幅度（实际涨幅 - 预期上限）
6. THE Stage3_Agent SHALL 根据超预期幅度计算价格分值（0-100分）

### 需求 13：计算超预期分值（独立性维度）

**用户故事：** 作为交易者，我希望系统评估个股涨幅的独立性，以便排除指数贡献的影响。

#### 验收标准

1. THE Stage3_Agent SHALL 获取大盘指数（上证指数、创业板指）的竞价涨幅
2. THE Stage3_Agent SHALL 计算个股相对大盘的超额涨幅
3. WHEN 个股涨幅显著高于大盘涨幅时，THE Stage3_Agent SHALL 标记为"独立性强"
4. WHEN 个股涨幅与大盘涨幅接近时，THE Stage3_Agent SHALL 标记为"跟随指数"
5. THE Stage3_Agent SHALL 根据超额涨幅计算独立性分值（0-100分）
6. THE Stage3_Agent SHALL 在输出中标注个股是否受指数影响

### 需求 14：综合计算超预期分值

**用户故事：** 作为交易者，我希望系统综合量能、价格、独立性三个维度，计算最终的超预期分值。

#### 验收标准

1. THE Stage3_Agent SHALL 获取量能分值、价格分值、独立性分值
2. THE Stage3_Agent SHALL 根据可配置的权重计算综合 Expectation_Score
3. THE Stage3_Agent SHALL 支持自定义三个维度的权重（默认：量能40%、价格40%、独立性20%）
4. THE Stage3_Agent SHALL 将 Expectation_Score 标准化到0-100分区间
5. THE Stage3_Agent SHALL 根据分值划分等级（优秀>=80、良好60-80、一般40-60、较差<40）
6. THE Stage3_Agent SHALL 在输出中展示分值计算的详细过程

### 需求 15：输出买卖建议

**用户故事：** 作为交易者，我希望系统根据超预期分值和其他因素，给出明确的操作建议和置信度。

#### 验收标准

1. THE Stage3_Agent SHALL 根据 Expectation_Score 生成操作建议（打板/低吸/观望/撤退）
2. WHEN Expectation_Score >= 80 且无诱多嫌疑时，THE Stage3_Agent SHALL 建议"打板"
3. WHEN Expectation_Score 在60-80之间且技术位支撑良好时，THE Stage3_Agent SHALL 建议"低吸"
4. WHEN Expectation_Score < 60 或存在诱多嫌疑时，THE Stage3_Agent SHALL 建议"观望"或"撤退"
5. THE Stage3_Agent SHALL 计算建议的置信度（0-100%）
6. THE Stage3_Agent SHALL 在建议中标注关键风险点（如压力位、题材退潮、大规模撤单等）
7. THE Stage3_Agent SHALL 输出建议的理由和支持证据

### 需求 15A：竞价附加票池 - 顶级封单监控

**用户故事：** 作为交易者，我希望系统捕捉竞价结束后全市场封单最强的个股，以便发现突发机会。

#### 验收标准

1. THE Stage3_Agent SHALL 在9:25后扫描全市场涨停个股
2. THE Stage3_Agent SHALL 筛选不在 Gene_Pool 内的涨停个股
3. THE Stage3_Agent SHALL 获取每只涨停个股的封单金额和流通市值
4. THE Stage3_Agent SHALL 计算封单比（封单金额/流通市值）
5. WHEN 封单金额排名全市场Top 10 且封单比>5% 或封单金额>5亿时，THE Stage3_Agent SHALL 将该股加入"顶级封单池"
6. THE Stage3_Agent SHALL 识别该股是否有突发题材或重大公告
7. THE Stage3_Agent SHALL 扫描该股所属板块的其他个股联动情况
8. THE Stage3_Agent SHALL 标注该股的题材属性和联动强度

### 需求 15B：竞价附加票池 - 急迫抢筹监控

**用户故事：** 作为交易者，我希望系统捕捉竞价阶段暴力拉升的个股，以便识别资金急于进场的信号。

#### 验收标准

1. THE Stage3_Agent SHALL 计算每只个股的抢筹价差系数：(开盘价 - 竞价最低价) / 昨收价
2. THE Stage3_Agent SHALL 筛选抢筹价差系数 > 3% 的个股
3. THE Stage3_Agent SHALL 验证该股竞价成交金额是否放量（相比昨日全天成交额）
4. WHEN 抢筹价差系数 > 3% 且竞价金额放量时，THE Stage3_Agent SHALL 将该股加入"急迫抢筹池"
5. THE Stage3_Agent SHALL 分析该股在9:20-9:25期间的拉升轨迹
6. THE Stage3_Agent SHALL 标注该股的拉升速度和资金强度
7. THE Stage3_Agent SHALL 评估该股是否为资金不可撤单期的疯狂扫货行为

### 需求 15C：竞价附加票池 - 能量爆发监控

**用户故事：** 作为交易者，我希望系统捕捉竞价金额和量比双高的个股，以便识别主线机会。

#### 验收标准

1. THE Stage3_Agent SHALL 计算全市场所有个股的竞价成交金额排名
2. THE Stage3_Agent SHALL 计算全市场所有个股的竞价量比（竞价成交量/昨日分钟均量）
3. THE Stage3_Agent SHALL 筛选竞价金额排名前30的个股
4. THE Stage3_Agent SHALL 筛选竞价量比排名前50的个股
5. WHEN 个股同时满足竞价金额前30且量比前50时，THE Stage3_Agent SHALL 将该股加入"能量爆发池"
6. THE Stage3_Agent SHALL 区分大容量票（金额>2亿）和小票（量比>100倍）
7. THE Stage3_Agent SHALL 标注该股是"中军表态"、"机构入场"、"散户合力"还是"游资点火"
8. THE Stage3_Agent SHALL 评估金额与量比的共振强度

### 需求 15D：竞价附加票池 - 极端反核监控

**用户故事：** 作为交易者，我希望系统捕捉昨日大跌但今日反转的个股，以便识别情绪逆转信号。

#### 验收标准

1. THE Stage3_Agent SHALL 筛选昨日跌幅 > -7% 或昨日跌停的个股
2. THE Stage3_Agent SHALL 计算这些个股今日竞价的开盘涨幅
3. WHEN 昨日大跌个股今日竞价开盘涨幅 > -2% 或红开时，THE Stage3_Agent SHALL 标记为"反核候选"
4. THE Stage3_Agent SHALL 计算竞价成交额占昨日全天成交额的比例
5. WHEN 竞价成交额占比在5%-10%之间时，THE Stage3_Agent SHALL 将该股加入"极端反核池"
6. THE Stage3_Agent SHALL 评估该股是否为全场情绪的"救火队长"
7. THE Stage3_Agent SHALL 分析反核成功对 Gene_Pool 内高位股的影响
8. THE Stage3_Agent SHALL 标注反核的置信度和风险等级

### 需求 15E：竞价附加票池 - 板块阵型监控

**用户故事：** 作为交易者，我希望系统评估板块的整体强度，以便判断龙头是否有群众基础。

#### 验收标准

1. THE Stage3_Agent SHALL 识别所有板块及其成分股
2. THE Stage3_Agent SHALL 计算每个板块内高开>3%且量比超常的个股数量
3. WHEN 板块内有3只以上个股同时满足"高开>3%"且"量比超常"时，THE Stage3_Agent SHALL 标记该板块为"强势阵型"
4. THE Stage3_Agent SHALL 识别板块内的非龙头助攻股
5. THE Stage3_Agent SHALL 评估板块阵型的完整度（独狼/领袖）
6. THE Stage3_Agent SHALL 分析板块阵型对 Gene_Pool 内龙头股的支撑作用
7. THE Stage3_Agent SHALL 输出板块强度排名和关键助攻股列表

### 需求 15F：附加池过滤与地位判定引擎

**用户故事：** 作为交易者，我希望系统从附加票池中筛选出最核心的个股，以便聚焦最有价值的机会。

#### 验收标准

1. THE Stage3_Agent SHALL 对所有附加票池候选个股进行综合评分
2. THE Stage3_Agent SHALL 计算每只候选个股的题材辨识度分值（0-100分）
3. THE Stage3_Agent SHALL 计算每只候选个股的量价急迫性分值（0-100分）
4. THE Stage3_Agent SHALL 计算每只候选个股的情绪对冲力分值（0-100分）
5. THE Stage3_Agent SHALL 根据三个维度的加权平均计算最终地位分值
6. THE Stage3_Agent SHALL 筛选地位分值排名前5的个股作为最终附加池
7. THE Stage3_Agent SHALL 输出每只最终附加池个股的地位判定理由

### 需求 15F1：题材辨识度评分

**用户故事：** 作为交易者，我希望系统评估附加池个股的题材辨识度，以便识别新面孔和身位优势。

#### 验收标准

1. THE Stage3_Agent SHALL 判断个股是否属于昨日报告中的"新面孔"或今早突发利好题材
2. WHEN 个股属于新面孔或突发利好题材时，THE Stage3_Agent SHALL 给予题材辨识度加分（+30分）
3. THE Stage3_Agent SHALL 识别个股所属题材的所有异动股
4. THE Stage3_Agent SHALL 计算个股在同题材异动股中的涨幅排名、量比排名、金额排名
5. WHEN 个股在同题材中涨幅第一时，THE Stage3_Agent SHALL 给予身位优势加分（+25分）
6. WHEN 个股在同题材中量比第一时，THE Stage3_Agent SHALL 给予身位优势加分（+25分）
7. WHEN 个股在同题材中金额第一时，THE Stage3_Agent SHALL 给予身位优势加分（+20分）
8. THE Stage3_Agent SHALL 输出题材辨识度总分（0-100分）

### 需求 15F2：量价急迫性评分

**用户故事：** 作为交易者，我希望系统评估附加池个股的量价急迫性，以便识别资金疯狂抢筹的信号。

#### 验收标准

1. THE Stage3_Agent SHALL 计算个股的抢筹价差：(开盘价 - 竞价最低价) / 昨收价
2. WHEN 抢筹价差 > 5% 时，THE Stage3_Agent SHALL 给予满分（50分）
3. WHEN 抢筹价差在3%-5%之间时，THE Stage3_Agent SHALL 给予30分
4. WHEN 抢筹价差在1%-3%之间时，THE Stage3_Agent SHALL 给予10分
5. THE Stage3_Agent SHALL 计算竞价成交额占昨日全天成交额的比例
6. WHEN 竞价成交额占比 >= 10% 时，THE Stage3_Agent SHALL 给予满分（50分）
7. WHEN 竞价成交额占比在5%-10%之间时，THE Stage3_Agent SHALL 给予30分
8. WHEN 竞价成交额占比在3%-5%之间时，THE Stage3_Agent SHALL 给予10分
9. THE Stage3_Agent SHALL 输出量价急迫性总分（0-100分）

### 需求 15F3：情绪对冲力评分

**用户故事：** 作为交易者，我希望系统评估附加池个股的情绪对冲力，以便识别卡位机会。

#### 验收标准

1. THE Stage3_Agent SHALL 识别 Gene_Pool 中的核心龙头股（如韩建河山等）
2. THE Stage3_Agent SHALL 计算核心龙头股的竞价表现是否不及预期
3. WHEN 核心龙头竞价不及预期时，THE Stage3_Agent SHALL 标记为"龙头弱势"状态
4. THE Stage3_Agent SHALL 计算附加池个股相对龙头的超额涨幅
5. WHEN 处于"龙头弱势"状态且附加池个股逆势抢筹爆量时，THE Stage3_Agent SHALL 给予高分（80-100分）
6. WHEN 附加池个股与龙头同步走强时，THE Stage3_Agent SHALL 给予中等分（40-60分）
7. WHEN 附加池个股表现弱于龙头时，THE Stage3_Agent SHALL 给予低分（0-30分）
8. THE Stage3_Agent SHALL 标注个股是否具有"孤胆英雄"或"卡位"特征
9. THE Stage3_Agent SHALL 输出情绪对冲力总分（0-100分）

### 需求 15G：9:25决策导航推演引擎

**用户故事：** 作为交易者，我希望系统在9:25后生成可执行的操作指南，以便快速决策和行动。

#### 验收标准

1. THE Stage3_Agent SHALL 在9:25后立即生成《9:25决策导航推演报告》
2. THE Stage3_Agent SHALL 在报告中包含三个核心部分：核心基因池对标预期、附加池X信号触发、多维分支决策树
3. THE Stage3_Agent SHALL 为每个部分生成明确的操作指南
4. THE Stage3_Agent SHALL 输出报告的格式为结构化文本或HTML
5. THE Stage3_Agent SHALL 在报告中标注关键决策点和风险提示
6. THE Stage3_Agent SHALL 支持自定义报告模板和格式

### 需求 15G1：核心基因池对标预期

**用户故事：** 作为交易者，我希望系统为每只核心股设定及格线，以便判断是否符合预期。

#### 验收标准

1. THE Stage3_Agent SHALL 为 Gene_Pool 中每只核心股生成"及格线表"
2. THE Stage3_Agent SHALL 设定每只核心股的竞价金额底线
3. THE Stage3_Agent SHALL 设定每只核心股的开盘涨幅底线
4. THE Stage3_Agent SHALL 标注每只核心股的"及格"和"不及预期"判定标准
5. WHEN 核心股不及预期时，THE Stage3_Agent SHALL 输出"全场防守，不看新仓"的操作建议
6. WHEN 核心股超预期时，THE Stage3_Agent SHALL 输出"可追高或持有"的操作建议
7. THE Stage3_Agent SHALL 在及格线表中标注每只核心股的连板高度、昨日表现等关键信息

### 需求 15G2：附加池X信号触发剧本

**用户故事：** 作为交易者，我希望系统为附加池个股设定触发剧本，以便快速识别操作机会。

#### 验收标准

1. THE Stage3_Agent SHALL 定义多个通用信号剧本（暴力抢筹卡位流、极弱转强反核流等）
2. THE Stage3_Agent SHALL 为每个剧本设定明确的触发信号条件
3. THE Stage3_Agent SHALL 为每个剧本设定地位判定规则
4. THE Stage3_Agent SHALL 为每个剧本设定应对策略（轻仓跟随/重仓首选/观望等）
5. WHEN 附加池个股触发某个剧本时，THE Stage3_Agent SHALL 输出该剧本的完整操作指南
6. THE Stage3_Agent SHALL 在剧本中标注核心大哥的状态对应对策略的影响
7. THE Stage3_Agent SHALL 支持自定义剧本和触发条件

### 需求 15G2A：暴力抢筹卡位流剧本

**用户故事：** 作为交易者，我希望系统识别暴力抢筹的个股，以便判断是助攻还是卡位。

#### 验收标准

1. THE Stage3_Agent SHALL 定义暴力抢筹信号：(开盘价 - 竞价最低价) > 3% 且竞价量比 > 50
2. WHEN 个股触发暴力抢筹信号时，THE Stage3_Agent SHALL 标记为"暴力抢筹卡位流"
3. THE Stage3_Agent SHALL 判断核心大哥（如名雕股份）的竞价表现
4. WHEN 核心大哥正常时，THE Stage3_Agent SHALL 输出"它是助攻，可轻仓跟随"
5. WHEN 核心大哥大幅低开时，THE Stage3_Agent SHALL 判断板块内是否有2只以上同类抢筹股
6. WHEN 板块内有2只以上同类抢筹股时，THE Stage3_Agent SHALL 输出"它是分离卡位，重仓首选"
7. THE Stage3_Agent SHALL 在剧本中标注买入时机和止损位

### 需求 15G2B：极弱转强反核流剧本

**用户故事：** 作为交易者，我希望系统识别极弱转强的个股，以便把握反转机会。

#### 验收标准

1. THE Stage3_Agent SHALL 定义极弱转强信号：昨日跌停 且 今日竞价成交额达昨日全天10% 且 开盘在-2%以上
2. WHEN 个股触发极弱转强信号时，THE Stage3_Agent SHALL 标记为"极弱转强反核流"
3. THE Stage3_Agent SHALL 输出买入点判定规则："开盘1分钟不破开盘价，反手向上点火时跟随"
4. THE Stage3_Agent SHALL 标注该剧本的风险等级为"高风险高收益"
5. THE Stage3_Agent SHALL 在剧本中标注止损位和止盈位
6. THE Stage3_Agent SHALL 评估反核成功对全场情绪的影响

### 需求 15G3：多维分支决策树

**用户故事：** 作为交易者，我希望系统根据不同市场场景生成决策树，以便应对各种情况。

#### 验收标准

1. THE Stage3_Agent SHALL 在9:10生成"今日操作推演图"
2. THE Stage3_Agent SHALL 定义至少3个主要场景：整体超预期、分歧兑现、高低切
3. THE Stage3_Agent SHALL 为每个场景设定触发条件
4. THE Stage3_Agent SHALL 为每个场景设定盘感描述
5. THE Stage3_Agent SHALL 为每个场景设定具体策略
6. THE Stage3_Agent SHALL 支持自定义场景和策略
7. THE Stage3_Agent SHALL 在决策树中标注每个分支的置信度

### 需求 15G3A：场景1 - 整体超预期

**用户故事：** 作为交易者，我希望系统识别整体超预期场景，以便把握强势行情。

#### 验收标准

1. THE Stage3_Agent SHALL 定义整体超预期触发条件：核心大哥全封一字
2. THE Stage3_Agent SHALL 输出盘感描述："资金极度亢奋，顶背离被忽视"
3. THE Stage3_Agent SHALL 输出策略："扫板附加池X中最先涨停的那只（做卡位）；或者低吸基因池中形态最好的回踩"
4. THE Stage3_Agent SHALL 标注该场景的风险："顶背离风险，注意及时止盈"
5. THE Stage3_Agent SHALL 输出具体的操作时机和仓位建议

### 需求 15G3B：场景2 - 分歧兑现

**用户故事：** 作为交易者，我希望系统识别分歧兑现场景，以便及时防守。

#### 验收标准

1. THE Stage3_Agent SHALL 定义分歧兑现触发条件：核心大哥大幅低开或炸板
2. THE Stage3_Agent SHALL 输出盘感描述："情绪退潮，危险信号"
3. THE Stage3_Agent SHALL 输出策略："空仓观望。即便附加池X有个股乱跳，也不要动，大概率是冲高回落诱多"
4. THE Stage3_Agent SHALL 标注该场景的风险等级为"高风险"
5. THE Stage3_Agent SHALL 输出持仓的止损建议

### 需求 15G3C：场景3 - 高低切

**用户故事：** 作为交易者，我希望系统识别高低切场景，以便把握题材切换机会。

#### 验收标准

1. THE Stage3_Agent SHALL 定义高低切触发条件：核心大哥震荡 且 新题材/新面孔X爆量
2. THE Stage3_Agent SHALL 输出盘感描述："资金在尝试切换到燃气轮机或其他新面孔"
3. THE Stage3_Agent SHALL 输出策略："放弃高位连板，手动狙击X中满足'大单点火'的那个标的"
4. THE Stage3_Agent SHALL 识别新题材的可持续性
5. THE Stage3_Agent SHALL 输出新题材的龙头候选和跟随标的
6. THE Stage3_Agent SHALL 标注题材切换的风险和机会

### 需求 16：生成每日监控报告

**用户故事：** 作为交易者，我希望系统生成结构化的每日监控报告，以便快速查看所有监控个股和附加票池的情况。

#### 验收标准

1. THE System SHALL 在9:25后立即生成当日监控报告
2. THE System SHALL 在报告中分别列出基因池个股和附加票池个股
3. THE System SHALL 按 Expectation_Score 降序排列基因池个股
4. THE System SHALL 按维度分类展示附加票池个股（顶级封单/急迫抢筹/能量爆发/极端反核/板块阵型）
5. THE System SHALL 在报告中标注每只个股的操作建议和置信度
6. THE System SHALL 在报告中展示市场整体情况（大盘涨幅、涨停家数等）
7. THE System SHALL 支持导出为Excel、PDF或HTML格式
8. THE System SHALL 在报告中包含时间戳和数据来源说明
9. THE System SHALL 在报告中标注附加票池个股的发现维度和关键指标

### 需求 17：历史数据存储与回溯

**用户故事：** 作为交易者，我希望系统保存历史监控数据，以便回溯分析和策略优化。

#### 验收标准

1. THE System SHALL 将每日的 Gene_Pool 快照存储到数据库
2. THE System SHALL 将每日的 Baseline_Expectation 存储到数据库
3. THE System SHALL 将每日的竞价监测结果存储到数据库
4. THE System SHALL 将每日的操作建议和实际表现存储到数据库
5. THE System SHALL 支持按日期、个股代码、题材等维度查询历史数据
6. THE System SHALL 计算历史建议的准确率和盈亏情况
7. THE System SHALL 支持导出历史数据用于外部分析

### 需求 18：异常情况处理

**用户故事：** 作为交易者，我希望系统能识别和处理异常情况，以便避免错误决策。

#### 验收标准

1. WHEN 个股停牌或复牌首日时，THE System SHALL 排除该个股或单独标注
2. WHEN 个股有重大公告（如重组、业绩预告等）时，THE System SHALL 标注为"事件驱动"
3. WHEN 大盘出现极端行情（开盘涨跌超过2%）时，THE System SHALL 调整 Baseline_Expectation
4. WHEN 竞价数据获取失败或异常时，THE System SHALL 标记为"数据异常"并跳过该个股
5. WHEN 外部变量数据获取失败时，THE System SHALL 使用默认值并标注"数据缺失"
6. THE System SHALL 记录所有异常情况到日志文件

### 需求 19：实时推送与提醒

**用户故事：** 作为交易者，我希望系统能实时推送关键信息，以便及时做出反应。

#### 验收标准

1. THE System SHALL 支持通过企业微信、钉钉或邮件推送监控报告
2. WHEN 检测到"打板"建议且置信度>=80%时，THE System SHALL 立即推送提醒
3. WHEN 检测到 Positioning_Signal 时，THE System SHALL 推送卡位机会提醒
4. WHEN 检测到"诱多嫌疑"时，THE System SHALL 推送风险警告
5. THE System SHALL 支持自定义推送规则和阈值
6. THE System SHALL 在推送消息中包含个股代码、建议、置信度和关键指标

### 需求 20：参数配置与优化

**用户故事：** 作为交易者，我希望系统支持灵活的参数配置，以便适应不同市场环境和个人偏好。

#### 验收标准

1. THE System SHALL 支持通过配置文件设置所有阈值和权重
2. THE System SHALL 支持配置监控个股池的筛选条件
3. THE System SHALL 支持配置 Baseline_Expectation 的计算规则
4. THE System SHALL 支持配置超预期分值的权重分配
5. THE System SHALL 支持配置操作建议的触发条件
6. THE System SHALL 提供参数配置的模板和说明文档
7. THE System SHALL 支持保存和加载多套参数配置方案

### 需求 21：Agent独立运作能力

**用户故事：** 作为系统架构师，我希望每个Agent都能独立运作，以便灵活部署和维护。

#### 验收标准

1. THE Stage1_Agent SHALL 能够独立启动和运行，不依赖其他Agent
2. THE Stage2_Agent SHALL 能够独立启动和运行，不依赖其他Agent
3. THE Stage3_Agent SHALL 能够独立启动和运行，不依赖其他Agent
4. THE System SHALL 通过文件系统或数据库实现Agent间的数据传递
5. WHEN 某个Agent失败时，THE System SHALL 不影响其他Agent的运行
6. THE System SHALL 支持单独运行任意一个Agent进行测试或调试
7. THE System SHALL 为每个Agent提供独立的配置文件
8. THE System SHALL 为每个Agent提供独立的日志文件

### 需求 22：LLM集成与调用

**用户故事：** 作为开发者，我希望系统正确集成Gemini-2.0-Flash模型，以便实现智能分析功能。

#### 验收标准

1. THE System SHALL 使用 Gemini-2.0-Flash 作为所有Agent的基础LLM
2. THE System SHALL 支持通过配置文件设置Gemini API密钥
3. THE System SHALL 支持配置LLM调用参数（温度、最大token等）
4. THE System SHALL 实现LLM调用的错误处理和重试机制
5. WHEN LLM调用失败时，THE System SHALL 记录错误并尝试重试（最多3次）
6. THE System SHALL 记录每次LLM调用的输入、输出和耗时
7. THE System SHALL 支持配置LLM调用的超时时间
8. THE System SHALL 在LLM不可用时提供降级方案（使用规则引擎）

### 需求 23：数据接口与格式规范

**用户故事：** 作为开发者，我希望系统定义清晰的数据接口和格式规范，以便Agent之间能够正确传递数据。

#### 验收标准

1. THE System SHALL 定义 Gene_Pool 的标准数据结构（JSON格式）
2. THE System SHALL 定义 Additional_Pool 的标准数据结构（JSON格式）
3. THE System SHALL 定义 Stage1_Agent 输出的报告格式（包含Market_Report、Emotion_Report、Theme_Report）
4. THE System SHALL 定义 Stage2_Agent 输出的 Baseline_Expectation 数据格式
5. THE System SHALL 定义 Stage3_Agent 输出的决策导航报告格式
6. THE System SHALL 定义 Agent 间数据传递的文件命名规范（包含日期和Agent标识）
7. THE System SHALL 定义数据存储的目录结构规范
8. THE System SHALL 提供数据格式的JSON Schema定义文件
9. THE System SHALL 实现数据格式的验证功能
10. WHEN 数据格式不符合规范时，THE System SHALL 输出明确的错误提示
