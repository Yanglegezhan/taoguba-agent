# 配置文件更新说明

## 更新日期
2026-02-13

## 更新内容

根据 `kaipanla_crawler/kaipanla_crawler.py` 中的实际API方法，更新了以下配置模板文件：

1. `config/data_source_config.yaml.template`
2. `config/agent_config.yaml.template`

## 主要变更

### 1. data_source_config.yaml.template

#### Kaipanla配置更新

**原配置问题**：
- 将Kaipanla配置为Web API（`base_url: "http://api.kaipanla.com"`）
- 实际上Kaipanla是本地Python模块，不是Web服务

**新配置**：
```yaml
kaipanla:
  enabled: true
  module_path: "kaipanla_crawler/kaipanla_crawler.py"  # 本地文件路径
  class_name: "KaipanlaCrawler"  # 类名
  timeout: 1600  # 某些API需要较长超时时间（秒）
  retry_times: 3
```

#### API方法映射

添加了完整的API方法映射，按照三个Stage的需求分类：

**Stage1 数据采集（收盘后）**：
- `get_daily_data` - 获取交易日数据（涨停数、跌停数、连板梯队等）
- `get_market_sentiment` - 获取涨跌统计
- `get_market_index` - 获取大盘指数
- `get_limit_up_ladder` - 获取连板梯队
- `get_consecutive_limit_up` - 获取连板梯队详情（最高连板、各连板个股）
- `get_sharp_withdrawal` - 获取大幅回撤股票
- `get_sector_ranking` - 获取涨停原因板块
- `get_new_high_data` - 获取百日新高数据
- `get_sector_strength` - 获取板块强度
- `get_sector_strength_ndays` - 获取N日板块强度排名
- `get_longhubang_stock_list` - 获取龙虎榜

**Stage2 隔夜数据采集（早盘前7:00-9:00）**：
- `get_plate_news` - 获取板块新闻
- `get_sector_constituent_stocks` - 获取板块成分股

**Stage3 竞价监测（9:15-9:25）**：
- `get_realtime_market_mood` - 获取实时市场情绪（涨停家数、跌停家数、涨跌比）
- `get_realtime_actual_limit_up_down` - 获取实时实际涨跌停数
- `get_realtime_board_stocks` - 获取指定连板股票（首板/二板/三板等）
- `get_realtime_all_boards_stocks` - 获取所有连板股票
- `get_realtime_index_trend` - 获取实时指数趋势（昨日涨停今表现等）
- `get_realtime_sharp_withdrawal` - 获取实时大幅回撤
- `get_realtime_rise_fall_analysis` - 获取实时涨跌分析（炸板率等）
- `get_sector_limit_up_ladder` - 获取板块连板梯队
- `get_market_limit_up_ladder` - 获取全市场连板梯队
- `get_sector_capital_data` - 获取板块资金数据
- `get_sector_bidding_anomaly` - 获取板块竞价异动

**分时数据（支持历史和实时）**：
- `get_sector_intraday` - 获取板块分时数据
- `get_stock_intraday` - 获取个股分时数据
- `get_stock_big_order_intraday` - 获取个股大单净额分时
- `get_index_intraday` - 获取大盘指数分时
- `get_sector_volume_turnover` - 获取板块成交量/成交额

### 2. agent_config.yaml.template

#### Stage1 配置更新

添加了数据采集API映射：
```yaml
data_collection:
  daily_data_api: "get_daily_data"
  limit_up_ladder_api: "get_consecutive_limit_up"
  sector_ranking_api: "get_sector_ranking"
  sharp_withdrawal_api: "get_sharp_withdrawal"
  new_high_api: "get_new_high_data"
  sector_strength_api: "get_sector_strength"
  longhubang_api: "get_longhubang_stock_list"
```

#### Stage2 配置更新

添加了隔夜数据采集API映射：
```yaml
overnight_data_collection:
  plate_news_api: "get_plate_news"
  sector_stocks_api: "get_sector_constituent_stocks"
  external_markets:
    us_stocks: true  # 使用AKShare获取美股数据
    futures: true    # 使用AKShare获取期货数据
    a50_index: true  # 使用AKShare获取A50指数
```

#### Stage3 配置更新

添加了完整的竞价监测API映射：
```yaml
auction_monitoring:
  market_mood_api: "get_realtime_market_mood"
  actual_limit_up_down_api: "get_realtime_actual_limit_up_down"
  board_stocks_api: "get_realtime_board_stocks"
  all_boards_api: "get_realtime_all_boards_stocks"
  index_trend_api: "get_realtime_index_trend"
  sharp_withdrawal_api: "get_realtime_sharp_withdrawal"
  rise_fall_analysis_api: "get_realtime_rise_fall_analysis"
  sector_ladder_api: "get_sector_limit_up_ladder"
  market_ladder_api: "get_market_limit_up_ladder"
  sector_capital_api: "get_sector_capital_data"
  bidding_anomaly_api: "get_sector_bidding_anomaly"
  stock_intraday_api: "get_stock_intraday"
  sector_intraday_api: "get_sector_intraday"
  big_order_api: "get_stock_big_order_intraday"
```

## Kaipanla API 关键特性

### 1. 超时时间
- 大部分API默认超时：300秒
- 某些API（如板块新闻、龙虎榜）需要更长超时：1600秒
- 配置中设置为1600秒以适应最长的API调用

### 2. 历史数据 vs 实时数据
许多API支持两种模式：
- **历史数据**：传入 `date` 参数（格式：YYYY-MM-DD）
- **实时数据**：不传 `date` 参数或传 `None`

示例：
```python
# 历史数据
data = crawler.get_stock_intraday("002498", "2026-01-16")

# 实时数据
data = crawler.get_stock_intraday("002498")
```

### 3. 连板类型参数
`get_realtime_board_stocks(board_type)` 的 `board_type` 参数：
- 1: 首板
- 2: 二板
- 3: 三板
- 4: 四板
- 5: 五板及以上

### 4. 指数代码
`get_realtime_index_trend(stock_id)` 的特殊指数：
- "801900": 昨日涨停今日表现
- "801903": 昨日断板今日表现

## 使用建议

### 1. 导入Kaipanla模块
```python
import sys
sys.path.append("kaipanla_crawler")
from kaipanla_crawler import KaipanlaCrawler

crawler = KaipanlaCrawler()
```

### 2. Stage1 数据采集示例
```python
# 获取单日交易数据
daily_data = crawler.get_daily_data("2026-02-12")

# 获取连板梯队详情
ladder = crawler.get_consecutive_limit_up("2026-02-12")
print(f"最高连板: {ladder['max_consecutive']}连板")
print(f"龙头股: {ladder['max_consecutive_stocks']}")

# 获取涨停原因板块
sectors = crawler.get_sector_ranking("2026-02-12")
for sector in sectors['sectors']:
    print(f"{sector['sector_name']}: {sector['stock_count']}只涨停")
```

### 3. Stage2 数据采集示例
```python
# 获取板块新闻
news = crawler.get_plate_news("801225", index=0, page_size=30)

# 获取板块成分股
stocks = crawler.get_sector_constituent_stocks("801225", date="2026-02-12")
```

### 4. Stage3 竞价监测示例
```python
# 获取实时市场情绪
mood = crawler.get_realtime_market_mood()
print(f"涨停: {mood['涨停家数']}家")
print(f"跌停: {mood['跌停家数']}家")

# 获取首板股票
first_board = crawler.get_realtime_board_stocks(board_type=1)
print(f"首板股票: {len(first_board)}只")

# 获取个股分时数据
intraday = crawler.get_stock_intraday("002498")
print(f"主力净流入: {intraday['total_main_inflow'] / 1e8:.2f}亿")
```

## 需求映射

配置更新覆盖了以下需求：

- **需求0**: 数据源配置与管理
- **需求1**: 生成静态复盘报告（Stage1）
- **需求2**: 构建个股基因库（Stage1）
- **需求3**: 计算个股技术位（Stage1）
- **需求4**: 接入隔夜外部变量（Stage2）
- **需求5**: 生成个股基准预期（Stage2）
- **需求6**: 捕捉突发新题材（Stage2）
- **需求7-15**: 竞价监测相关（Stage3）
- **需求15A-15E**: 附加票池监控（Stage3）
- **需求15F-15G**: 决策导航推演（Stage3）

## 下一步工作

1. 复制模板文件并填写实际配置：
   ```bash
   cp config/data_source_config.yaml.template config/data_source_config.yaml
   cp config/agent_config.yaml.template config/agent_config.yaml
   ```

2. 根据实际需求调整参数（如阈值、权重等）

3. 实现数据源管理器（DataSourceManager）来加载和使用这些配置

4. 实现各个Agent的数据采集模块，调用配置中指定的API方法

## 注意事项

1. **Kaipanla是本地模块**：不要尝试通过HTTP请求访问，应该直接导入Python类
2. **超时时间**：某些API需要较长时间，建议设置1600秒超时
3. **代理配置**：AKShare需要禁用代理，在调用前设置 `proxies={'http': None, 'https': None}`
4. **数据格式**：不同API返回的数据格式不同，需要根据实际返回值进行解析
5. **错误处理**：实现数据源降级机制，当Kaipanla失败时切换到AKShare或东方财富

## 参考文档

- Kaipanla API源码：`kaipanla_crawler/kaipanla_crawler.py`
- 需求文档：`.kiro/specs/next-day-core-stock-expectation-analysis/requirements.md`
- 设计文档：`.kiro/specs/next-day-core-stock-expectation-analysis/design.md`
