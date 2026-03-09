# 个股竞价Tick数据接口说明

## 接口名称
`get_stock_call_auction_tick(stock_code, date=None, timeout=300)`

## 功能说明
获取个股集合竞价期间（9:15:00-9:25:00）的tick数据，包括每分钟的匹配价和累计成交量。

## 数据来源
使用东方财富网API：`http://push2.eastmoney.com/api/qt/stock/details/get`

## 参数说明

### 输入参数
- `stock_code`: 股票代码
  - 支持格式1: "000002"（不带前缀）
  - 支持格式2: "SZ000002"（带市场前缀）
  - 支持格式3: "SH600519"（上海股票）
  
- `date`: 日期（可选）
  - 格式: "YYYY-MM-DD"
  - 默认: None（获取实时数据）
  - 注意: 东方财富网API可能不支持历史竞价数据
  
- `timeout`: 超时时间（秒）
  - 默认: 300秒

### 返回数据
返回一个字典，包含以下字段：

```python
{
    "stock_code": "0.000002",  # 股票代码（格式：市场代码.股票代码）
    "date": "2026-02-20",      # 日期
    "is_realtime": True,       # 是否为实时数据
    "data": DataFrame          # 竞价tick数据（DataFrame格式）
}
```

DataFrame包含以下列：
- `time`: 时间（HH:MM:SS格式），如 "09:15:00"
- `price`: 匹配价（元）
- `volume`: 累计成交量（手）

## 使用示例

### 示例1: 获取实时竞价数据

```python
from kaipanla_crawler import KaipanlaCrawler

crawler = KaipanlaCrawler()

# 获取万科A的实时竞价数据
data = crawler.get_stock_call_auction_tick("000002")

if data:
    df = data['data']
    print(f"股票: {data['stock_code']}")
    print(f"日期: {data['date']}")
    print(f"竞价tick数: {len(df)}")
    
    # 查看9:15:00的数据
    first_tick = df[df['time'] == '09:15:00']
    if not first_tick.empty:
        print(f"9:15:00 匹配价: {first_tick['price'].values[0]:.2f} 元")
        print(f"9:15:00 累计成交量: {first_tick['volume'].values[0]} 手")
```

### 示例2: 查看完整竞价数据

```python
from kaipanla_crawler import KaipanlaCrawler

crawler = KaipanlaCrawler()

# 获取贵州茅台的竞价数据
data = crawler.get_stock_call_auction_tick("600519")

if data:
    df = data['data']
    
    # 显示所有竞价tick
    print(df.to_string())
    
    # 统计信息
    print(f"\n最高匹配价: {df['price'].max():.2f} 元")
    print(f"最低匹配价: {df['price'].min():.2f} 元")
    print(f"最终成交量: {df['volume'].max()} 手")
```

### 示例3: 批量获取多只股票

```python
from kaipanla_crawler import KaipanlaCrawler

crawler = KaipanlaCrawler()

stock_codes = ["000002", "600519", "000001"]

for code in stock_codes:
    data = crawler.get_stock_call_auction_tick(code)
    
    if data and not data['data'].empty:
        df = data['data']
        
        # 获取9:15和9:25的数据
        first = df[df['time'] == '09:15:00']
        last = df[df['time'] == '09:25:00']
        
        print(f"\n股票: {code}")
        if not first.empty:
            print(f"  9:15 匹配价: {first['price'].values[0]:.2f}")
        if not last.empty:
            print(f"  9:25 匹配价: {last['price'].values[0]:.2f}")
```

## 注意事项

1. **交易时间限制**
   - 只能在交易日的9:15-9:25期间获取实时竞价数据
   - 非交易时间或盘后可能无法获取数据

2. **数据格式**
   - 返回的时间格式为 "HH:MM:SS"
   - 价格单位为元
   - 成交量单位为手（1手=100股）

3. **历史数据**
   - 东方财富网API可能不支持历史竞价数据
   - 如需历史数据，建议在交易时间实时采集并保存

4. **请求频率**
   - 接口内置了0.5秒的请求延迟
   - 避免频繁请求导致IP被封

5. **错误处理**
   - 如果返回空字典 `{}`，表示获取失败
   - 检查股票代码是否正确
   - 检查是否在交易时间内

## 数据字段说明

根据你提供的截图，竞价数据包含以下信息：

| 时间 | 匹配价 | 累计成交量 |
|------|--------|-----------|
| 09:15:00 | 10.98 | 161 |
| 09:16:00 | ... | ... |
| ... | ... | ... |
| 09:25:00 | ... | ... |

- **匹配价**: 该时刻的集合竞价匹配价格
- **累计成交量**: 从9:15开始累计的成交量

## 技术实现

接口使用东方财富网的分时成交明细API，通过以下步骤获取竞价数据：

1. 将股票代码转换为东方财富网的secid格式（市场代码.股票代码）
2. 请求分时成交明细数据
3. 筛选出9:15:00到9:25:00的数据
4. 返回DataFrame格式的结果

## 完整代码位置

接口实现位于：`kaipanla_crawler/kaipanla_crawler.py`

测试代码位于：`test_call_auction_tick.py`

## 运行测试

```bash
python test_call_auction_tick.py
```

注意：测试需要在交易时间（9:15-9:25）运行才能获取到数据。
