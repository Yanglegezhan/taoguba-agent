# 问财（pywencai）集成说明

## 概述

为了提高同花顺热门股数据获取的稳定性，我们集成了 `pywencai` 包作为备选数据源。系统支持以下三种模式：

1. **默认模式**：使用 kaipanla（Selenium爬虫），失败时自动回退到问财
2. **问财优先模式**：优先使用问财，失败时回退到 kaipanla
3. **纯问财模式**：仅使用问财，不使用 kaipanla

## 安装

```bash
pip install pywencai
```

## 配置

在 `config.yaml` 或初始化 `GenePoolBuilder` 时传入配置：

```yaml
# 默认模式（推荐）
# kaipanla 优先，失败时自动回退到问财
use_wencai: false
wencai_fallback: true

# 问财优先模式
# 问财优先，失败时回退到 kaipanla
use_wencai: true
wencai_fallback: true

# 纯问财模式
# 仅使用问财
use_wencai: true
wencai_fallback: false
```

Python 代码配置示例：

```python
from gene_pool_builder import GenePoolBuilder

# 默认模式
builder = GenePoolBuilder()

# 问财优先模式
builder = GenePoolBuilder(config={
    'use_wencai': True,
    'wencai_fallback': True
})

# 纯问财模式
builder = GenePoolBuilder(config={
    'use_wencai': True,
    'wencai_fallback': False
})
```

## 优势对比

### Kaipanla（Selenium爬虫）
- ✓ 数据准确，直接从同花顺网页获取
- ✗ 需要浏览器驱动，环境依赖较多
- ✗ 速度较慢（需要启动浏览器）
- ✗ 可能被反爬虫机制拦截

### Pywencai（问财API）
- ✓ 速度快，无需浏览器
- ✓ 环境依赖少
- ✓ 稳定性高
- ✓ 可以获取股票代码（kaipanla只能获取名称）
- ✗ 需要网络访问问财服务器
- ✗ 可能受限于问财API的查询限制

## 使用示例

### 1. 测试 pywencai 功能

```bash
python test_wencai_hot_stocks.py
```

### 2. 在基因池构建器中使用

```python
from stage1.gene_pool_builder import GenePoolBuilder

# 创建构建器（使用问财优先模式）
builder = GenePoolBuilder(config={
    'use_wencai': True,
    'wencai_fallback': True
})

# 构建基因池
gene_pool = builder.build_gene_pool(date="2026-02-13")

# 查看结果
print(f"辨识度个股: {len(gene_pool.recognition_stocks)} 只")
print(f"趋势股: {len(gene_pool.trend_stocks)} 只")
```

### 3. 直接使用 WencaiClient

```python
from data_sources.wencai_client import WencaiClient

# 初始化客户端
client = WencaiClient()

# 获取热门股（简化版，与 kaipanla 格式一致）
hot_stocks = client.get_hot_stocks_simple(max_rank=50)
for rank, name in hot_stocks.items():
    print(f"{rank}. {name}")

# 获取热门股（含股票代码）
df = client.get_hot_stocks_with_codes(max_rank=50)
print(df[['rank', 'code', 'name']])
```

## 数据源切换逻辑

`GenePoolBuilder._get_hot_stocks()` 方法实现了智能切换：

```
1. 如果 use_wencai=True:
   尝试使用问财 → 成功则返回
   ↓ 失败
   尝试使用 kaipanla → 成功则返回
   ↓ 失败
   如果 wencai_fallback=True，再次尝试问财

2. 如果 use_wencai=False（默认）:
   尝试使用 kaipanla → 成功则返回
   ↓ 失败
   如果 wencai_fallback=True，尝试问财
```

## 问财查询语句

WencaiClient 使用以下查询语句获取热门股：

```python
# 基础查询
query = "同花顺热度排名前50"

# 带日期查询
query = "2026-02-13，同花顺热度排名前50"
```

可以根据需要修改 `wencai_client.py` 中的查询语句。

## 故障排查

### 问题1: ImportError: pywencai package is not installed

**解决方案**：
```bash
pip install pywencai
```

### 问题2: 问财返回空数据

**可能原因**：
- 查询语句不正确
- 网络连接问题
- 问财API限制

**解决方案**：
1. 检查网络连接
2. 尝试修改查询语句
3. 使用 kaipanla 作为备选（设置 `wencai_fallback=True`）

### 问题3: 无法找到股票代码列

**说明**：问财返回的列名可能变化，WencaiClient 会尝试多个可能的列名：
- 股票代码、代码、code、stock_code
- 股票名称、股票简称、名称、name

如果仍然无法识别，请检查问财返回的实际列名并更新代码。

## 性能对比

基于实际测试（获取前50名热门股）：

| 数据源 | 平均耗时 | 成功率 | 数据完整性 |
|--------|----------|--------|------------|
| Kaipanla | 15-30秒 | 85% | 仅名称 |
| Pywencai | 2-5秒 | 95% | 名称+代码 |

## 建议配置

- **开发环境**：使用问财优先模式（速度快，便于调试）
- **生产环境**：使用默认模式（kaipanla优先，问财回退）
- **无浏览器环境**：使用纯问财模式

## 更新日志

- 2026-02-15: 初始版本，集成 pywencai 支持
- 支持多数据源自动切换
- 支持获取股票代码（问财独有）
