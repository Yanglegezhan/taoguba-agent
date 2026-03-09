# 安装和使用 pywencai

## 快速开始

### 1. 安装 pywencai

```bash
pip install pywencai
```

### 2. 测试安装

```bash
python test_wencai_hot_stocks.py
```

### 3. 在项目中使用

修改 Stage1 Agent 配置，启用问财数据源：

```python
# 在 stage1_agent.py 或配置文件中
config = {
    'use_wencai': True,        # 优先使用问财
    'wencai_fallback': True    # kaipanla失败时回退到问财
}

agent = Stage1Agent(config=config)
```

## 详细说明

### 安装选项

#### 选项1: 使用 pip（推荐）

```bash
pip install pywencai
```

#### 选项2: 从源码安装

```bash
git clone https://github.com/zsrl/pywencai.git
cd pywencai
pip install -e .
```

#### 选项3: 指定版本

```bash
pip install pywencai==1.0.0
```

### 验证安装

运行以下 Python 代码验证：

```python
import pywencai

# 测试查询
df = pywencai.get(query="同花顺热度排名前10", loop=True)
print(df)
```

### 常见问题

#### 问题1: pip install 失败

**错误信息**：
```
ERROR: Could not find a version that satisfies the requirement pywencai
```

**解决方案**：
1. 更新 pip：`python -m pip install --upgrade pip`
2. 检查 Python 版本（需要 Python 3.7+）
3. 尝试使用国内镜像：
   ```bash
   pip install pywencai -i https://pypi.tuna.tsinghua.edu.cn/simple
   ```

#### 问题2: 导入失败

**错误信息**：
```
ModuleNotFoundError: No module named 'pywencai'
```

**解决方案**：
1. 确认安装成功：`pip list | grep pywencai`
2. 检查 Python 环境是否正确
3. 重新安装：`pip uninstall pywencai && pip install pywencai`

#### 问题3: 查询返回空数据

**可能原因**：
- 网络连接问题
- 查询语句不正确
- 问财服务器限制

**解决方案**：
1. 检查网络连接
2. 尝试简化查询语句
3. 添加延迟：`time.sleep(1)`
4. 使用 kaipanla 作为备选

### 使用示例

#### 示例1: 获取热门股（基础）

```python
import pywencai

# 查询同花顺热度排名前50
df = pywencai.get(query="同花顺热度排名前50", loop=True)

# 显示结果
print(f"获取到 {len(df)} 只股票")
print(df[['股票代码', '股票名称']].head(10))
```

#### 示例2: 获取指定日期的热门股

```python
import pywencai

# 查询指定日期的热门股
df = pywencai.get(query="2026-02-13，同花顺热度排名前50", loop=True)
print(df)
```

#### 示例3: 在基因池构建器中使用

```python
from stage1.gene_pool_builder import GenePoolBuilder

# 创建构建器（启用问财）
builder = GenePoolBuilder(config={
    'use_wencai': True,
    'wencai_fallback': True
})

# 构建基因池
gene_pool = builder.build_gene_pool(date="2026-02-13")

# 查看辨识度个股
for stock in gene_pool.recognition_stocks:
    print(f"{stock.hot_rank}. {stock.name}")
```

#### 示例4: 直接使用 WencaiClient

```python
from data_sources.wencai_client import WencaiClient

# 初始化客户端
client = WencaiClient()

# 方法1: 获取简化格式（与 kaipanla 兼容）
hot_stocks = client.get_hot_stocks_simple(max_rank=20)
for rank, name in hot_stocks.items():
    print(f"{rank}. {name}")

# 方法2: 获取完整数据（含股票代码）
df = client.get_hot_stocks_with_codes(max_rank=20)
print(df)

# 方法3: 获取原始数据
df_raw = client.get_hot_stocks(max_rank=20)
print(df_raw.columns)  # 查看所有列
```

### 配置建议

根据不同场景选择合适的配置：

#### 场景1: 开发调试（推荐问财）

```python
config = {
    'use_wencai': True,        # 优先使用问财（速度快）
    'wencai_fallback': True    # 保留回退选项
}
```

**优点**：速度快，便于快速迭代

#### 场景2: 生产环境（推荐 kaipanla）

```python
config = {
    'use_wencai': False,       # 优先使用 kaipanla（数据准确）
    'wencai_fallback': True    # 失败时回退到问财
}
```

**优点**：数据准确性高，有备选方案

#### 场景3: 无浏览器环境（纯问财）

```python
config = {
    'use_wencai': True,        # 使用问财
    'wencai_fallback': False   # 不使用 kaipanla
}
```

**优点**：无需浏览器驱动，适合服务器环境

### 性能优化

#### 1. 缓存结果

```python
import functools
import time

@functools.lru_cache(maxsize=128)
def get_hot_stocks_cached(date, max_rank):
    client = WencaiClient()
    return client.get_hot_stocks_simple(max_rank=max_rank, date=date)

# 使用缓存
hot_stocks = get_hot_stocks_cached("2026-02-13", 50)
```

#### 2. 批量查询

```python
# 一次查询获取更多数据，避免多次请求
df = client.get_hot_stocks(max_rank=100)

# 然后在本地筛选
top_20 = df.head(20)
top_50 = df.head(50)
```

#### 3. 异步查询（高级）

```python
import asyncio
import concurrent.futures

def fetch_hot_stocks(date):
    client = WencaiClient()
    return client.get_hot_stocks_simple(max_rank=50, date=date)

# 并行查询多个日期
dates = ["2026-02-10", "2026-02-11", "2026-02-12", "2026-02-13"]
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
    results = list(executor.map(fetch_hot_stocks, dates))
```

### 下一步

1. 安装 pywencai：`pip install pywencai`
2. 运行测试：`python test_wencai_hot_stocks.py`
3. 查看集成文档：`WENCAI_INTEGRATION.md`
4. 在项目中启用问财数据源

### 相关资源

- pywencai GitHub: https://github.com/zsrl/pywencai
- 问财官网: https://www.iwencai.com/
- 项目文档: `WENCAI_INTEGRATION.md`
