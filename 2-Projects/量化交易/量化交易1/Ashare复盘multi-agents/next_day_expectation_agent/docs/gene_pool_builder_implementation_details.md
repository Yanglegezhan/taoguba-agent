# 基因池构建器实现细节文档

## 1. 整体架构

### 1.1 核心职责
`GenePoolBuilder` 类负责识别和构建个股基因池，包括：
- 扫描连板梯队个股
- 识别炸板股（使用开盘啦的反包板数据接口）
- 识别辨识度个股（使用开盘啦的板块风向标接口）
- 识别趋势股（筛选同花顺热股前50）
- 构建统一的基因池数据结构

### 1.2 依赖关系
```
GenePoolBuilder
├── KaipanlaClient (数据获取)
│   ├── get_market_limit_up_ladder() - 获取炸板股
│   ├── get_sentiment_indicator() - 获取板块风向标
│   ├── get_ths_hot_rank() - 获取同花顺热股
│   └── get_continuous_limit_up_stocks() - 获取连板股
├── TechnicalCalculator (技术位计算)
└── Logger (日志记录)
```

## 2. 核心方法详解

### 2.1 scan_continuous_limit_up() - 扫描连板梯队

**职责**：扫描当日所有连板个股

**实现逻辑**：
1. 调用 `kaipanla_client.get_continuous_limit_up_stocks(date)` 获取连板数据
2. 遍历数据，为每只个股创建 `Stock` 对象
3. 返回连板个股列表

**数据来源**：开盘啦API - 连板梯队接口

**关键代码**：
```python
continuous_data = self.kaipanla_client.get_continuous_limit_up_stocks(date)
stocks = []
for _, row in continuous_data.iterrows():
    stock = self._create_stock_from_row(row, date)
    if stock:
        stocks.append(stock)
```

### 2.2 identify_failed_limit_up() - 识别炸板股（已修正）

**职责**：识别当日炸板股（曾涨停但未封住的个股）

**修正前的错误实现**：
- 使用涨幅7%-9.9%筛选
- 问题：不准确，无法真正识别炸板行为

**修正后的正确实现**：
1. 调用 `kaipanla_client.get_market_limit_up_ladder(date)` 获取全市场连板梯队数据
2. 从返回数据中提取 `broken_stocks`（反包板股票列表）
3. 将反包板数据转换为 `Stock` 对象列表
4. 返回炸板股列表

**数据来源**：开盘啦API - 全市场连板梯队接口的 `broken_stocks` 字段

**关键代码**：
```python
ladder_data = self.kaipanla_client.get_market_limit_up_ladder(date)
broken_stocks_data = ladder_data.get('broken_stocks', [])

failed_stocks = []
for stock_data in broken_stocks_data:
    stock = Stock(
        code=stock_data.get('stock_code', ''),
        name=stock_data.get('stock_name', ''),
        date=date,
        consecutive_days=stock_data.get('consecutive_days', 0),
        is_failed_limit_up=True,
        tips=stock_data.get('tips', '')
    )
    failed_stocks.append(stock)
```

**返回数据结构**：
```python
{
    'stock_code': '000001',
    'stock_name': '平安银行',
    'consecutive_days': 2,  # 连板天数
    'tips': '2天2板',  # 提示信息
    'is_broken': True  # 是否炸板
}
```

### 2.3 identify_recognition_stocks() - 识别辨识度个股（已修正）

**职责**：识别具有辨识度的个股（板块风向标）

**修正前的错误实现**：
- 使用成交额和换手率筛选
- 问题：无法真正识别板块风向标

**修正后的正确实现**：
1. 调用 `kaipanla_client.get_ths_hot_rank()` 获取同花顺热股前50（目前接口返回前20）
2. 调用 `kaipanla_client.get_sentiment_indicator(plate_id)` 获取板块风向标
3. 从风向标数据中提取 `bullish_codes`（多头风向标股票代码列表，前3只）
4. 筛选：风向标个股 且 在同花顺热股前50
5. 返回辨识度个股列表

**数据来源**：
- 开盘啦API - 板块风向标接口（`get_sentiment_indicator`）
- 同花顺热榜接口（`get_ths_hot_rank`）

**关键代码**：
```python
# 1. 获取同花顺热股
ths_hot_stocks = self.kaipanla_client.get_ths_hot_rank()
hot_stock_names = set(ths_hot_stocks.values)

# 2. 获取板块风向标
sentiment_data = self.kaipanla_client.get_sentiment_indicator(plate_id)
bullish_codes = sentiment_data.get('bullish_codes', [])

# 3. 筛选：风向标 且 在热股列表
recognition_stocks = []
for stock_code in bullish_codes:
    # 检查是否在热股列表中
    if stock_name in hot_stock_names:
        recognition_stocks.append(stock)
```

**返回数据结构**：
```python
{
    'date': '2026-02-13',
    'plate_id': '801225',
    'bullish_codes': ['000001', '000002', '000003'],  # 多头风向标（前3只）
    'bearish_codes': ['600001', '600002', '600003'],  # 空头风向标（后3只）
    'all_stocks': ['000001', '000002', ...]  # 所有股票
}
```

**筛选条件**：
- 必须是板块风向标中的多头个股（前3只）
- 必须出现在同花顺热股前50（目前接口限制为前20）

### 2.4 identify_trend_stocks() - 识别趋势股（已修正）

**职责**：识别走趋势的核心个股

**修正前的实现**：
- 使用成交额和换手率筛选
- 缺少同花顺热股前50的筛选条件

**修正后的正确实现**：
1. 调用 `kaipanla_client.get_ths_hot_rank()` 获取同花顺热股前50
2. 调用 `kaipanla_client.get_market_data(date)` 获取当日市场数据
3. 筛选：在热股列表中 且 符合趋势特征的个股
4. 使用 `_is_trend_stock()` 判断是否为趋势股
5. 返回趋势股列表

**数据来源**：
- 同花顺热榜接口（`get_ths_hot_rank`）
- 开盘啦API - 市场行情数据

**关键代码**：
```python
# 1. 获取同花顺热股
ths_hot_stocks = self.kaipanla_client.get_ths_hot_rank()
hot_stock_names = set(ths_hot_stocks.values)

# 2. 获取市场数据
market_data = self.kaipanla_client.get_market_data(date)

# 3. 筛选：在热股列表 且 符合趋势特征
trend_stocks = []
for _, row in market_data.iterrows():
    stock_name = str(row.get('名称', ''))
    
    # 检查是否在热股列表中
    if stock_name not in hot_stock_names:
        continue
    
    # 判断是否为趋势股
    stock = self._create_stock_from_row(row, date)
    if stock and self._is_trend_stock(stock, date):
        trend_stocks.append(stock)
```

**筛选条件**：
- 必须出现在同花顺热股前50（目前接口限制为前20）
- 符合趋势特征（价格在均线之上，均线多头排列等）

### 2.5 build_gene_pool() - 构建基因池

**职责**：整合所有识别结果，构建统一的基因池

**实现逻辑**：
1. 依次调用四个识别方法
2. 将所有个股合并到 `all_stocks` 字典（去重）
3. 创建 `GenePool` 对象
4. 返回基因池

**关键代码**：
```python
# 扫描各类个股
continuous_limit_up = self.scan_continuous_limit_up(date)
failed_limit_up = self.identify_failed_limit_up(date)
recognition_stocks = self.identify_recognition_stocks(date)
trend_stocks = self.identify_trend_stocks(date)

# 去重合并
all_stocks = {}
for stock in continuous_limit_up + failed_limit_up + recognition_stocks + trend_stocks:
    if stock.code not in all_stocks:
        all_stocks[stock.code] = stock

# 创建基因池
gene_pool = GenePool(
    date=date,
    continuous_limit_up=continuous_limit_up,
    failed_limit_up=failed_limit_up,
    recognition_stocks=recognition_stocks,
    trend_stocks=trend_stocks,
    all_stocks=all_stocks
)
```

## 3. 辅助方法

### 3.1 _create_stock_from_row()

**职责**：从DataFrame行创建Stock对象

**实现逻辑**：
1. 提取基础信息（代码、名称）
2. 提取数值字段（市值、价格、涨跌幅等）
3. 提取题材信息
4. 创建Stock对象

### 3.2 _is_at_support_level()

**职责**：判断个股是否处于支撑位

**当前状态**：占位符实现，返回False

**TODO**：实现支撑位判断逻辑
- 计算价格距离各均线的距离
- 识别前期高点
- 判断是否处于筹码密集区

### 3.3 _is_trend_stock()

**职责**：判断个股是否为趋势股

**当前状态**：占位符实现，返回False

**TODO**：实现趋势股判断逻辑
- 判断价格是否在均线之上
- 判断均线是否多头排列
- 判断近期涨幅是否稳定

## 4. 数据流转

```
输入：date (日期字符串)
  ↓
scan_continuous_limit_up()
  → KaipanlaClient.get_continuous_limit_up_stocks()
  → 返回连板个股列表
  ↓
identify_failed_limit_up()
  → KaipanlaClient.get_market_limit_up_ladder()
  → 提取 broken_stocks
  → 返回炸板股列表
  ↓
identify_recognition_stocks()
  → KaipanlaClient.get_ths_hot_rank()
  → KaipanlaClient.get_sentiment_indicator()
  → 筛选：风向标 且 在热股列表
  → 返回辨识度个股列表
  ↓
identify_trend_stocks()
  → KaipanlaClient.get_ths_hot_rank()
  → KaipanlaClient.get_market_data()
  → 筛选：在热股列表 且 符合趋势特征
  → 返回趋势股列表
  ↓
build_gene_pool()
  → 合并所有个股（去重）
  → 创建GenePool对象
  ↓
输出：GenePool (基因池对象)
```

## 5. 错误处理机制

### 5.1 数据获取失败
- 捕获异常并记录日志
- 返回空列表或空基因池
- 不中断整个流程

### 5.2 数据格式异常
- 在 `_create_stock_from_row()` 中处理缺失字段
- 使用默认值填充
- 记录警告日志

### 5.3 API调用失败
- 在 `KaipanlaClient` 中统一处理
- 抛出异常并记录详细错误信息
- 上层捕获并决定是否继续

## 6. 设计模式

### 6.1 单一职责原则
- 每个方法只负责一种类型的个股识别
- 数据获取委托给 `KaipanlaClient`
- 技术位计算委托给 `TechnicalCalculator`

### 6.2 依赖注入
- 通过构造函数注入配置
- 支持自定义 `KaipanlaClient` 和 `TechnicalCalculator`

### 6.3 工厂模式
- `_create_stock_from_row()` 作为Stock对象的工厂方法
- 统一创建逻辑，便于维护

## 7. 性能优化

### 7.1 数据缓存
- TODO: 缓存当日市场数据，避免重复获取
- TODO: 缓存同花顺热股数据

### 7.2 并行处理
- TODO: 使用多线程并行识别各类个股
- TODO: 批量获取个股历史数据

## 8. 测试策略

### 8.1 单元测试
- 测试每个识别方法的正确性
- 使用Mock对象模拟数据源
- 测试异常处理逻辑

### 8.2 集成测试
- 测试完整的基因池构建流程
- 使用真实数据验证结果
- 测试数据去重逻辑

## 9. 修正总结

### 9.1 炸板股识别修正
**修正前**：使用涨幅7%-9.9%筛选
**修正后**：使用开盘啦的反包板数据接口（`get_market_limit_up_ladder` 的 `broken_stocks` 字段）
**优势**：
- 数据准确，直接来自开盘啦的炸板票池
- 包含连板天数等详细信息
- 无需手动判断涨幅区间

### 9.2 辨识度个股识别修正
**修正前**：使用成交额和换手率筛选
**修正后**：使用开盘啦的板块风向标接口（`get_sentiment_indicator`）
**优势**：
- 直接获取板块内的标杆个股
- 符合"板块风向标"的定义
- 结合同花顺热股前50筛选，确保辨识度

### 9.3 趋势股识别修正
**修正前**：缺少同花顺热股前50的筛选条件
**修正后**：添加同花顺热股前50的筛选条件
**优势**：
- 符合需求规格
- 确保趋势股具有市场关注度
- 避免识别冷门个股

## 10. 待完成事项

### 10.1 同花顺热榜接口扩展
- 当前接口只返回前20个股
- 需要扩展到前50个股
- 可能需要修改爬虫逻辑或增加分页

### 10.2 股票名称获取
- 板块风向标接口只返回股票代码
- 需要额外的API调用获取股票名称
- 或者维护一个代码-名称映射表

### 10.3 技术位计算
- 实现 `_is_at_support_level()` 方法
- 实现 `_is_trend_stock()` 方法
- 需要获取历史K线数据

### 10.4 性能优化
- 实现数据缓存机制
- 实现并行处理
- 优化API调用次数

## 11. API接口映射

### 11.1 KaipanlaClient新增方法

| 方法名 | 对应的kaipanla_crawler方法 | 用途 |
|--------|---------------------------|------|
| `get_market_limit_up_ladder()` | `get_market_limit_up_ladder()` | 获取炸板股数据 |
| `get_sentiment_indicator()` | `get_sentiment_indicator()` | 获取板块风向标 |
| `get_ths_hot_rank()` | `get_ths_hot_rank()` | 获取同花顺热股 |

### 11.2 数据字段映射

**炸板股数据**：
```python
{
    'stock_code': '股票代码',
    'stock_name': '股票名称',
    'consecutive_days': '连板天数',
    'tips': '提示信息（如"2天2板"）',
    'is_broken': True  # 是否炸板
}
```

**板块风向标数据**：
```python
{
    'date': '日期',
    'plate_id': '板块ID',
    'bullish_codes': ['多头风向标代码1', '代码2', '代码3'],  # 前3只
    'bearish_codes': ['空头风向标代码1', '代码2', '代码3'],  # 后3只
    'all_stocks': ['所有股票代码']
}
```

**同花顺热股数据**：
```python
pd.Series({
    1: '股票名称1',
    2: '股票名称2',
    ...
    20: '股票名称20'
})
```
