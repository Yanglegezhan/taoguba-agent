# 需求文档 - 开盘啦数据爬虫API

## 简介

本项目旨在构建一个完整的开盘啦APP数据爬虫系统，用于采集A股市场的实时和历史交易数据。系统提供统一的API接口，支持市场情绪分析、连板梯队追踪、板块热度监控等多维度数据获取。

## 术语表

- **KaipanlaCrawler**: 开盘啦数据爬虫主类
- **Limit_Up**: 涨停，股票当日涨幅达到10%（ST股为5%）
- **Consecutive_Limit_Up**: 连板，连续多日涨停
- **Board_Height**: 连板高度，连续涨停的天数
- **Sector_Ladder**: 板块连板梯队，按板块分类的涨停股票分布
- **Market_Sentiment**: 市场情绪，基于涨跌停家数的市场强弱指标
- **Intraday_Data**: 分时数据，盘中每分钟的价格和成交数据
- **Abnormal_Stock**: 异动个股，盘中出现异常波动的股票
- **New_High**: 百日新高，股价创近100个交易日新高

## 需求

### 需求 1：统一交易数据接口

**用户故事：** 作为量化研究者，我希望通过统一接口获取每日完整的交易数据，以便进行市场分析和策略回测。

#### 验收标准

1. THE KaipanlaCrawler SHALL 提供 `get_daily_data(end_date, start_date=None)` 方法
2. WHEN 只传入 end_date 时，THE KaipanlaCrawler SHALL 返回单日数据的 Series 对象
3. WHEN 传入 start_date 和 end_date 时，THE KaipanlaCrawler SHALL 返回日期范围的 DataFrame 对象
4. THE 返回数据 SHALL 包含以下字段：
   - 日期、涨停数、实际涨停、跌停数、实际跌停
   - 上涨家数、下跌家数、平盘家数
   - 上证指数、最新价、涨跌幅、成交额
   - 首板数量、2连板数量、3连板数量、4连板以上数量、连板率
   - 大幅回撤家数
5. THE KaipanlaCrawler SHALL 自动过滤非交易日数据
6. THE KaipanlaCrawler SHALL 支持60秒超时设置以应对网络波动

### 需求 2：百日新高数据追踪

**用户故事：** 作为量化研究者，我希望获取百日新高数据，以便识别市场强势股票和趋势信号。

#### 验收标准

1. THE KaipanlaCrawler SHALL 提供 `get_new_high_data(end_date, start_date=None, timeout=60)` 方法
2. WHEN 只传入 end_date 时，THE KaipanlaCrawler SHALL 返回单日新增新高数量
3. WHEN 传入 start_date 和 end_date 时，THE KaipanlaCrawler SHALL 返回日期范围的 Series 对象
4. THE 返回数据 SHALL 包含每日新增百日新高的股票数量
5. THE KaipanlaCrawler SHALL 正确解析API返回的 x 字段数据格式（"20260116_478_127_0"）
6. THE KaipanlaCrawler SHALL 自动转换日期格式为 YYYY-MM-DD

### 需求 3：连板梯队实时追踪

**用户故事：** 作为短线交易者，我希望获取每日连板梯队情况，以便识别市场最强势的个股和题材。

#### 验收标准

1. THE KaipanlaCrawler SHALL 提供 `get_consecutive_limit_up(date=None, timeout=60)` 方法
2. THE KaipanlaCrawler SHALL 返回包含以下信息的字典：
   - date: 日期
   - max_consecutive: 最高连板高度
   - max_consecutive_stocks: 最高板个股名称（多个用 `/` 分隔）
   - max_consecutive_concepts: 最高板个股题材（多个用 `/` 分隔，同一个股的多个题材用 `、` 分隔）
   - ladder: 完整连板梯队数据（2连板、3连板、4连板等）
3. THE KaipanlaCrawler SHALL 自动从高到低搜索连板数据（最多尝试到20连板）
4. THE ladder 字段 SHALL 包含每只股票的：股票代码、股票名称、连板天数、题材、概念
5. WHEN 当日无连板数据时，THE KaipanlaCrawler SHALL 返回 max_consecutive=0
6. THE KaipanlaCrawler SHALL 正确合并题材和概念字段

### 需求 4：板块连板梯队监控

**用户故事：** 作为板块轮动研究者，我希望获取板块维度的连板梯队，以便识别热点板块和资金流向。

#### 验收标准

1. THE KaipanlaCrawler SHALL 提供 `get_sector_limit_up_ladder(date=None, timeout=60)` 方法
2. WHEN date 参数为 None 时，THE KaipanlaCrawler SHALL 获取实时数据
3. WHEN date 参数为 "YYYY-MM-DD" 时，THE KaipanlaCrawler SHALL 获取历史数据
4. THE 实时数据 SHALL 使用 API: `https://apphwhq.longhuvip.com/w1/api/index.php`
5. THE 历史数据 SHALL 使用 API: `https://apphis.longhuvip.com/w1/api/index.php` 并传入 Date 参数
6. THE 返回数据 SHALL 包含：
   - date: 日期
   - is_realtime: 是否为实时数据
   - sectors: 板块列表
7. THE sectors 列表 SHALL 包含每个板块的：
   - sector_code: 板块代码
   - sector_name: 板块名称
   - limit_up_count: 涨停数量
   - stocks: 涨停股票列表（包含股票代码、名称、连板天数）
8. THE KaipanlaCrawler SHALL 正确解析 API 响应中的 List 字段（大写）
9. THE KaipanlaCrawler SHALL 正确处理 TDType 字段：
   - 0: 特殊情况（从 Tips 字段解析连板天数，如 "5天4板"）
   - 1: 首板
   - 2: 2连板
   - N: N连板
10. THE KaipanlaCrawler SHALL 使用正则表达式解析 Tips 字段中的连板信息

### 需求 5：板块分时数据获取

**用户故事：** 作为日内交易者，我希望获取板块的分时数据，以便监控板块实时走势和资金流向。

#### 验收标准

1. THE KaipanlaCrawler SHALL 提供 `get_sector_intraday(sector_code, date=None)` 方法
2. WHEN date 为 None 时，THE KaipanlaCrawler SHALL 获取当日实时分时数据
3. WHEN date 为 "YYYY-MM-DD" 时，THE KaipanlaCrawler SHALL 获取历史分时数据
4. THE 返回数据 SHALL 为 DataFrame，包含：
   - 时间、价格、涨跌幅、成交量、成交额
5. THE KaipanlaCrawler SHALL 正确解析分时数据的时间格式
6. THE KaipanlaCrawler SHALL 处理盘前和盘后数据

### 需求 6：个股分时数据获取

**用户故事：** 作为日内交易者，我希望获取个股的分时数据和主力资金流向，以便判断个股强弱和资金动向。

#### 验收标准

1. THE KaipanlaCrawler SHALL 提供 `get_stock_intraday(stock_code, date=None)` 方法
2. THE 返回数据 SHALL 包含：
   - 基本信息：股票代码、名称、最新价、涨跌幅等
   - 分时数据：时间、价格、成交量、成交额
   - 主力资金：主力净流入、超大单、大单、中单、小单流入流出
3. THE KaipanlaCrawler SHALL 正确处理6位股票代码（不含市场前缀）
4. THE KaipanlaCrawler SHALL 返回完整的分时数据点（通常为241个点）

### 需求 7：异动个股实时监控

**用户故事：** 作为短线交易者，我希望实时获取异动个股信息，以便快速捕捉交易机会。

#### 验收标准

1. THE KaipanlaCrawler SHALL 提供 `get_abnormal_stocks()` 方法
2. THE 返回数据 SHALL 区分盘中异动和收盘异动
3. THE 返回数据 SHALL 包含：
   - 股票代码、名称、最新价、涨跌幅
   - 异动类型、异动时间、异动原因
4. THE KaipanlaCrawler SHALL 只在交易时间内返回有效数据
5. WHEN 非交易时间时，THE KaipanlaCrawler SHALL 返回空 DataFrame

### 需求 8：多空风向标识别

**用户故事：** 作为市场情绪研究者，我希望获取多头空头风向标，以便判断市场情绪方向。

#### 验收标准

1. THE KaipanlaCrawler SHALL 提供 `get_sentiment_indicator(plate_id="801225", stocks=None, timeout=60)` 方法
2. THE KaipanlaCrawler SHALL 返回包含以下信息的字典：
   - date: 日期
   - plate_id: 板块ID
   - bullish_codes: 多头风向标股票代码列表（前3只）
   - bearish_codes: 空头风向标股票代码列表（后3只）
   - all_stocks: 所有股票代码列表
3. THE KaipanlaCrawler SHALL 支持自定义股票列表
4. THE KaipanlaCrawler SHALL 使用默认股票列表（27只代表性个股）
5. THE KaipanlaCrawler SHALL 正确解析 API 返回的 List 字段

### 需求 9：涨停原因板块分析

**用户故事：** 作为题材研究者，我希望获取涨停原因板块数据，以便分析市场热点和题材轮动。

#### 验收标准

1. THE KaipanlaCrawler SHALL 提供 `get_sector_ranking(date=None, index=0, timeout=60)` 方法
2. THE 返回数据 SHALL 包含：
   - summary: 市场概况（涨停数、跌停数、上涨家数、下跌家数、涨跌比）
   - sectors: 板块列表
3. THE sectors 列表 SHALL 包含每个板块的：
   - sector_code: 板块代码
   - sector_name: 板块名称
   - stock_count: 涨停股票数量
   - stocks: 涨停股票详细列表
4. THE stocks 列表 SHALL 包含：
   - 股票代码、名称、涨停价、成交额、流通市值、总市值
   - 连板天数、连板描述、连板次数
   - 概念标签、封单额、涨停时间
   - 主力资金、主题、涨停原因、是否首板
5. THE KaipanlaCrawler SHALL 支持分页获取（通过 index 参数）

### 需求 10：向后兼容的独立接口

**用户故事：** 作为现有用户，我希望保留原有的独立接口，以便不影响现有代码的运行。

#### 验收标准

1. THE KaipanlaCrawler SHALL 保留以下独立接口：
   - `get_market_sentiment(date=None)`: 获取涨跌统计数据
   - `get_market_index(date=None)`: 获取大盘指数数据
   - `get_limit_up_ladder(date=None)`: 获取连板梯队数据
   - `get_sharp_withdrawal(date=None)`: 获取大幅回撤股票数据
2. THE 独立接口 SHALL 返回与原有格式一致的数据
3. THE 独立接口 SHALL 与统一接口共享底层实现

### 需求 11：错误处理与容错机制

**用户故事：** 作为系统使用者，我希望系统具备完善的错误处理机制，以便在网络异常或数据异常时不会崩溃。

#### 验收标准

1. THE KaipanlaCrawler SHALL 捕获所有网络请求异常
2. WHEN 请求失败时，THE KaipanlaCrawler SHALL 打印错误信息并返回空数据
3. THE KaipanlaCrawler SHALL 支持自定义超时时间（默认60秒）
4. THE KaipanlaCrawler SHALL 禁用 SSL 证书验证警告
5. THE KaipanlaCrawler SHALL 禁用代理以提高连接稳定性
6. WHEN API 返回 errcode != "0" 时，THE KaipanlaCrawler SHALL 识别为错误响应
7. THE KaipanlaCrawler SHALL 对缺失字段进行默认值填充

### 需求 12：数据格式标准化

**用户故事：** 作为数据分析师，我希望所有接口返回的数据格式统一规范，以便进行后续处理。

#### 验收标准

1. THE KaipanlaCrawler SHALL 统一使用 pandas DataFrame 或 Series 返回表格数据
2. THE KaipanlaCrawler SHALL 统一使用 dict 返回结构化数据
3. THE 日期格式 SHALL 统一为 "YYYY-MM-DD"
4. THE 股票代码 SHALL 统一为6位数字（不含市场前缀）
5. THE 数值字段 SHALL 正确转换为 int 或 float 类型
6. THE 百分比字段 SHALL 统一为小数形式（如 0.05 表示 5%）
7. THE 字符串字段 SHALL 去除首尾空格

### 需求 13：性能优化

**用户故事：** 作为高频使用者，我希望系统具备良好的性能，以便快速获取数据。

#### 验收标准

1. THE KaipanlaCrawler SHALL 复用 HTTP 连接以减少连接开销
2. THE KaipanlaCrawler SHALL 使用 gzip 压缩以减少传输数据量
3. THE KaipanlaCrawler SHALL 支持批量日期查询以减少请求次数
4. THE KaipanlaCrawler SHALL 在获取连板梯队时智能搜索（找到最高板后继续获取低板）
5. THE KaipanlaCrawler SHALL 避免重复请求相同数据

### 需求 14：文档与测试

**用户故事：** 作为新用户，我希望有完善的文档和测试用例，以便快速上手使用。

#### 验收标准

1. THE KaipanlaCrawler SHALL 为每个公开方法提供详细的 docstring
2. THE docstring SHALL 包含：功能描述、参数说明、返回值说明、使用示例
3. THE 项目 SHALL 提供独立的功能说明文档（Markdown格式）
4. THE 项目 SHALL 提供测试脚本验证每个功能
5. THE 测试脚本 SHALL 包含：基本功能测试、边界条件测试、错误处理测试
6. THE 测试脚本 SHALL 输出清晰的测试结果和数据示例

## 非功能性需求

### 可靠性

1. THE KaipanlaCrawler SHALL 在网络波动时自动重试（最多3次）
2. THE KaipanlaCrawler SHALL 在数据异常时返回空数据而非抛出异常
3. THE KaipanlaCrawler SHALL 记录所有错误日志以便排查问题

### 可维护性

1. THE 代码 SHALL 遵循 PEP 8 编码规范
2. THE 代码 SHALL 使用类型注解提高可读性
3. THE 代码 SHALL 采用模块化设计，便于扩展新功能
4. THE 配置参数 SHALL 集中管理，便于调整

### 兼容性

1. THE KaipanlaCrawler SHALL 支持 Python 3.7+
2. THE KaipanlaCrawler SHALL 兼容 Windows、Linux、macOS 系统
3. THE KaipanlaCrawler SHALL 最小化外部依赖（仅依赖 requests、pandas、urllib3）

### 安全性

1. THE KaipanlaCrawler SHALL 不存储用户敏感信息
2. THE KaipanlaCrawler SHALL 使用随机 DeviceID 避免被识别
3. THE KaipanlaCrawler SHALL 遵守目标网站的访问频率限制

## 实现状态

### 已完成功能 ✅

1. ✅ 统一交易数据接口 (`get_daily_data`)
2. ✅ 百日新高数据追踪 (`get_new_high_data`)
3. ✅ 连板梯队实时追踪 (`get_consecutive_limit_up`)
4. ✅ 板块连板梯队监控 (`get_sector_limit_up_ladder`)
5. ✅ 板块分时数据获取 (`get_sector_intraday`)
6. ✅ 个股分时数据获取 (`get_stock_intraday`)
7. ✅ 异动个股实时监控 (`get_abnormal_stocks`)
8. ✅ 多空风向标识别 (`get_sentiment_indicator`)
9. ✅ 涨停原因板块分析 (`get_sector_ranking`)
10. ✅ 向后兼容的独立接口
11. ✅ 错误处理与容错机制
12. ✅ 数据格式标准化
13. ✅ 完整的文档和测试用例

### 待优化功能 🔄

1. 🔄 自动重试机制（当前仅有超时控制）
2. 🔄 请求频率限制（避免被封禁）
3. 🔄 数据缓存机制（减少重复请求）
4. 🔄 异步请求支持（提高批量查询性能）

## 更新日志

- **2026-01-20**: 完成核心功能开发
  - 实现连板梯队获取功能
  - 实现板块连板梯队获取功能（支持历史和实时）
  - 完成所有测试用例和文档
