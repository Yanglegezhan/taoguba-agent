# 设计文档 - 开盘啦数据爬虫API

## 概述

开盘啦数据爬虫系统是一个基于Python的A股市场数据采集工具，通过逆向工程开盘啦APP的API接口，提供完整的市场数据获取能力。系统采用面向对象设计，提供统一、易用的API接口，支持实时和历史数据查询。

## 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                     KaipanlaCrawler                         │
│                    (主爬虫类)                                │
└─────────────────────────────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
        ▼                   ▼                   ▼
┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│  数据采集层   │   │  数据处理层   │   │  接口封装层   │
└──────────────┘   └──────────────┘   └──────────────┘
        │                   │                   │
        ▼                   ▼                   ▼
┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│ HTTP请求管理  │   │ 数据解析转换  │   │ 统一数据接口  │
│ 错误处理     │   │ 格式标准化   │   │ 向后兼容接口  │
│ 超时控制     │   │ 类型转换     │   │ 便捷查询方法  │
└──────────────┘   └──────────────┘   └──────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────┐
│                    开盘啦APP API                             │
│  - 历史数据API: apphis.longhuvip.com                        │
│  - 实时数据API: apphwhq.longhuvip.com                       │
└─────────────────────────────────────────────────────────────┘
```

## 核心组件设计

### 1. KaipanlaCrawler 主类

```python
class KaipanlaCrawler:
    """开盘啦数据爬虫主类
    
    职责：
    - 管理API连接和请求
    - 提供统一的数据获取接口
    - 处理错误和异常情况
    - 标准化数据格式
    """
    
    def __init__(self):
        """初始化爬虫
        
        设置：
        - base_url: 历史数据API地址
        - sector_base_url: 实时数据API地址
        - headers: HTTP请求头（模拟APP请求）
        - sector_headers: 实时数据请求头
        """
        self.base_url = "https://apphis.longhuvip.com/w1/api/index.php"
        self.sector_base_url = "https://apphwhq.longhuvip.com/w1/api/index.php"
        self.headers = {...}  # 模拟APP请求头
        self.sector_headers = {...}  # 实时数据请求头
```

### 2. 数据采集层设计

#### 2.1 HTTP请求管理

```python
def _request(self, data_params, date, timeout=60):
    """统一的HTTP请求方法
    
    功能：
    - 构造请求参数（包含设备ID、版本号等）
    - 发送POST请求到历史数据API
    - 处理响应和异常
    - 返回JSON数据
    
    参数：
    - data_params: 业务参数（a, c等）
    - date: 查询日期
    - timeout: 超时时间（默认60秒）
    
    返回：
    - dict: API响应的JSON数据
    - {}: 请求失败时返回空字典
    
    错误处理：
    - 捕获所有异常并打印错误信息
    - 禁用SSL验证警告
    - 禁用代理以提高稳定性
    """
```

#### 2.2 API接口映射

| 功能 | API参数 | 数据源 |
|------|---------|--------|
| 涨跌统计 | a=HisZhangFuDetail, c=HisHomeDingPan | 历史API |
| 大盘指数 | a=GetZsReal, c=StockL2History | 历史API |
| 连板梯队 | a=ZhangTingExpression, c=HisHomeDingPan | 历史API |
| 大幅回撤 | a=SharpWithdrawal, c=HisHomeDingPan | 历史API |
| 百日新高 | a=GetDayNewHigh_W28, c=StockNewHigh | 历史API |
| 连板个股 | a=DailyLimitPerformance, c=HisHomeDingPan | 历史API |
| 板块连板梯队 | a=GetYTFP_BKHX, c=FuPanLa | 历史/实时API |
| 板块分时 | a=GetZsMinute, c=ZhiShuRanking | 实时API |
| 个股分时 | a=GetStockMinute, c=StockL2History | 历史API |
| 异动个股 | a=GetYiDongStock, c=FuPanLa | 实时API |
| 风向标 | a=PlateIntroduction_Info, c=ZhiShuRanking | 实时API |
| 板块排名 | a=GetPlateInfo_w38, c=DailyLimitResumption | 实时API |

### 3. 数据处理层设计

#### 3.1 数据解析策略

```python
# 策略1: 单日数据聚合
def _get_single_day_data(self, date):
    """聚合多个API的数据到单日记录
    
    流程：
    1. 并行请求4个API（涨跌统计、大盘指数、连板梯队、大幅回撤）
    2. 提取关键字段
    3. 合并为单个字典
    4. 返回完整的单日数据
    """

# 策略2: 日期范围数据批量获取
def get_daily_data(self, end_date, start_date=None):
    """支持单日和日期范围查询
    
    逻辑：
    - 只传end_date: 调用_get_single_day_data返回Series
    - 传start_date和end_date: 循环调用_get_single_day_data返回DataFrame
    - 自动过滤非交易日（涨停数=0的日期）
    """

# 策略3: 连板梯队智能搜索
def get_consecutive_limit_up(self, date=None, timeout=60):
    """从高到低搜索连板数据
    
    算法：
    1. 从20连板开始向下搜索
    2. 对每个连板高度发送API请求
    3. 如果返回数据非空，记录该连板高度
    4. 继续搜索直到2连板
    5. 返回最高板信息和完整梯队
    
    优化：
    - 使用PidType参数指定连板高度
    - 忽略请求失败（继续尝试下一个高度）
    - 合并题材和概念字段
    """

# 策略4: 板块连板梯队解析
def get_sector_limit_up_ladder(self, date=None, timeout=60):
    """区分历史和实时数据
    
    判断逻辑：
    - date=None: 实时数据（使用sector_base_url，不传Date参数）
    - date="YYYY-MM-DD": 历史数据（使用base_url，传Date参数）
    
    解析逻辑：
    - 遍历List字段（注意大写）
    - 解析TD字段获取连板分组
    - 处理TDType字段：
      * 0: 从Tips字段解析（正则匹配"N天M板"）
      * 1: 首板
      * N: N连板
    - 构造标准化的返回结构
    """
```

#### 3.2 数据类型转换

```python
# 数值类型转换规则
conversion_rules = {
    "涨停数": int,
    "实际涨停": int,
    "跌停数": int,
    "上涨家数": int,
    "下跌家数": int,
    "上证指数": float,
    "成交额": int,
    "连板率": lambda x: round(x, 2),
    "涨跌幅": str,  # 保留原始格式（如"+5.23%"）
}

# 日期格式转换
date_formats = {
    "input": "YYYY-MM-DD",  # 输入格式
    "api": "YYYY-MM-DD",    # API格式
    "output": "YYYY-MM-DD", # 输出格式
}

# 特殊字段处理
special_fields = {
    "百日新高": "从x字段解析：'20260116_478_127_0' -> 127",
    "连板天数": "从PidType或Tips字段解析",
    "题材概念": "合并题材和概念，用'、'和'/'分隔",
}
```

### 4. 接口封装层设计

#### 4.1 统一数据接口

```python
# 设计原则：
# 1. 单一职责：每个方法只负责一种数据类型
# 2. 参数一致：相同类型的参数使用相同的命名和格式
# 3. 返回统一：使用pandas DataFrame/Series或dict
# 4. 错误友好：返回空数据而非抛出异常

class DataInterface:
    """统一数据接口设计"""
    
    # 模式1: 单日/范围查询
    def get_daily_data(self, end_date, start_date=None):
        """
        返回类型：
        - start_date=None: pd.Series（单日）
        - start_date!=None: pd.DataFrame（范围）
        """
    
    # 模式2: 历史/实时查询
    def get_sector_limit_up_ladder(self, date=None, timeout=60):
        """
        返回类型：dict
        - date=None: 实时数据（is_realtime=True）
        - date!=None: 历史数据（is_realtime=False）
        """
    
    # 模式3: 纯实时查询
    def get_abnormal_stocks(self):
        """
        返回类型：pd.DataFrame
        - 只返回实时数据
        - 非交易时间返回空DataFrame
        """
    
    # 模式4: 结构化数据查询
    def get_consecutive_limit_up(self, date=None, timeout=60):
        """
        返回类型：dict
        - 包含多层嵌套结构
        - 便于直接访问关键信息
        """
```

#### 4.2 向后兼容接口

```python
# 保留原有独立接口，内部调用统一接口
def get_market_sentiment(self, date=None):
    """向后兼容：获取涨跌统计"""
    # 内部调用_request，返回DataFrame

def get_market_index(self, date=None):
    """向后兼容：获取大盘指数"""
    # 内部调用_request，返回DataFrame

def get_limit_up_ladder(self, date=None):
    """向后兼容：获取连板梯队"""
    # 内部调用_request，返回DataFrame

def get_sharp_withdrawal(self, date=None):
    """向后兼容：获取大幅回撤"""
    # 内部调用_request，返回DataFrame
```

## 数据流设计

### 1. 单日数据查询流程

```
用户调用
  │
  ├─> get_daily_data("2026-01-16")
  │
  └─> _get_single_day_data("2026-01-16")
        │
        ├─> _request({a: "HisZhangFuDetail", ...}, "2026-01-16")
        │     └─> 返回涨跌统计数据
        │
        ├─> _request({a: "GetZsReal", ...}, "2026-01-16")
        │     └─> 返回大盘指数数据
        │
        ├─> _request({a: "ZhangTingExpression", ...}, "2026-01-16")
        │     └─> 返回连板梯队数据
        │
        ├─> _request({a: "SharpWithdrawal", ...}, "2026-01-16")
        │     └─> 返回大幅回撤数据
        │
        └─> 合并数据 -> 返回 pd.Series
```

### 2. 连板梯队查询流程

```
用户调用
  │
  ├─> get_consecutive_limit_up("2026-01-19")
  │
  └─> 循环搜索（PidType: 20 -> 2）
        │
        ├─> _request({PidType: "20", ...}, "2026-01-19")
        │     └─> 返回空 -> 继续
        │
        ├─> _request({PidType: "5", ...}, "2026-01-19")
        │     └─> 返回数据 -> 记录5连板
        │
        ├─> _request({PidType: "4", ...}, "2026-01-19")
        │     └─> 返回数据 -> 记录4连板
        │
        ├─> ... 继续搜索 ...
        │
        └─> 返回 {
              max_consecutive: 5,
              max_consecutive_stocks: "锋龙股份",
              max_consecutive_concepts: "机器人、工业4.0",
              ladder: {5: [...], 4: [...], 3: [...], 2: [...]}
            }
```

### 3. 板块连板梯队查询流程

```
用户调用
  │
  ├─> get_sector_limit_up_ladder("2026-01-16")  # 历史
  │     │
  │     └─> POST apphis.longhuvip.com
  │           data: {a: "GetYTFP_BKHX", Date: "2026-01-16", ...}
  │           │
  │           └─> 解析响应
  │                 │
  │                 ├─> 遍历 List 字段
  │                 ├─> 解析 TD 字段
  │                 ├─> 处理 TDType 字段
  │                 └─> 返回标准化数据
  │
  └─> get_sector_limit_up_ladder()  # 实时
        │
        └─> POST apphwhq.longhuvip.com
              data: {a: "GetYTFP_BKHX", ...}  # 不传Date
              │
              └─> 解析响应（同上）
```

## 错误处理设计

### 1. 异常分类

```python
# 网络异常
class NetworkError:
    - requests.exceptions.Timeout: 请求超时
    - requests.exceptions.ConnectionError: 连接失败
    - requests.exceptions.HTTPError: HTTP错误
    
    处理策略：
    - 打印错误信息
    - 返回空数据（{}或pd.DataFrame()）
    - 不抛出异常（避免中断程序）

# 数据异常
class DataError:
    - KeyError: 字段缺失
    - ValueError: 数据格式错误
    - IndexError: 索引越界
    
    处理策略：
    - 使用.get()方法安全访问字典
    - 提供默认值（0、""、[]）
    - 打印警告信息

# API异常
class APIError:
    - errcode != "0": API返回错误
    - 返回数据为空: 无数据
    
    处理策略：
    - 检查errcode字段
    - 检查关键字段是否存在
    - 返回空数据结构
```

### 2. 容错机制

```python
# 超时控制
timeout_config = {
    "default": 60,  # 默认60秒
    "configurable": True,  # 支持自定义
    "retry": False,  # 暂不支持自动重试
}

# 数据验证
validation_rules = {
    "日期格式": r"^\d{4}-\d{2}-\d{2}$",
    "股票代码": r"^\d{6}$",
    "板块代码": r"^\d+$",
}

# 默认值策略
default_values = {
    "int": 0,
    "float": 0.0,
    "str": "",
    "list": [],
    "dict": {},
    "DataFrame": pd.DataFrame(),
    "Series": pd.Series(),
}
```

## 性能优化设计

### 1. 请求优化

```python
# HTTP连接复用
session_config = {
    "keep_alive": True,  # 保持连接
    "pool_connections": 10,  # 连接池大小
    "pool_maxsize": 20,  # 最大连接数
}

# 压缩传输
compression_config = {
    "accept_encoding": "gzip",  # 启用gzip压缩
    "auto_decompress": True,  # 自动解压
}

# 代理禁用
proxy_config = {
    "http": None,  # 禁用HTTP代理
    "https": None,  # 禁用HTTPS代理
    "reason": "提高连接稳定性",
}
```

### 2. 数据处理优化

```python
# 批量查询
batch_query = {
    "method": "循环调用单日查询",
    "optimization": "可改为并发请求",
    "benefit": "减少总耗时",
}

# 智能搜索
smart_search = {
    "method": "从高到低搜索连板",
    "optimization": "找到最高板后继续搜索",
    "benefit": "获取完整梯队数据",
}

# 数据缓存
cache_strategy = {
    "status": "未实现",
    "plan": "缓存历史数据避免重复请求",
    "benefit": "提高查询速度",
}
```

## 安全性设计

### 1. 请求伪装

```python
# 模拟APP请求
headers = {
    "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 9; ...)",
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "Accept-Encoding": "gzip",
}

# 随机设备ID
device_id = str(uuid.uuid4())  # 每次请求生成新ID

# 版本号
version = "5.21.0.2"  # 固定版本号
```

### 2. 访问控制

```python
# 频率限制
rate_limit = {
    "status": "未实现",
    "plan": "限制每秒请求次数",
    "reason": "避免被封禁",
}

# SSL验证
ssl_config = {
    "verify": False,  # 禁用SSL验证
    "warnings": "disabled",  # 禁用警告
    "reason": "目标网站证书问题",
}
```

## 扩展性设计

### 1. 新增数据源

```python
# 步骤1: 添加API配置
new_api = {
    "url": "https://new-api.example.com",
    "headers": {...},
    "params": {...},
}

# 步骤2: 实现请求方法
def _request_new_api(self, params):
    """新API请求方法"""
    pass

# 步骤3: 实现数据解析
def _parse_new_data(self, response):
    """新数据解析方法"""
    pass

# 步骤4: 封装公开接口
def get_new_data(self, date=None):
    """新数据获取接口"""
    pass
```

### 2. 新增数据字段

```python
# 步骤1: 更新数据结构
data_structure = {
    "existing_fields": [...],
    "new_fields": ["新字段1", "新字段2"],
}

# 步骤2: 更新解析逻辑
def _get_single_day_data(self, date):
    data = {
        # 现有字段
        "涨停数": ...,
        # 新增字段
        "新字段1": ...,
        "新字段2": ...,
    }

# 步骤3: 更新文档
# 在docstring和README中添加新字段说明
```

## 测试设计

### 1. 单元测试

```python
# 测试用例设计
test_cases = {
    "test_single_day_query": {
        "input": "2026-01-16",
        "expected": "pd.Series with 18 fields",
    },
    "test_date_range_query": {
        "input": ("2026-01-10", "2026-01-16"),
        "expected": "pd.DataFrame with 5 rows",
    },
    "test_consecutive_limit_up": {
        "input": "2026-01-19",
        "expected": "dict with max_consecutive=5",
    },
    "test_sector_ladder_historical": {
        "input": "2026-01-16",
        "expected": "dict with is_realtime=False",
    },
    "test_sector_ladder_realtime": {
        "input": None,
        "expected": "dict with is_realtime=True",
    },
}
```

### 2. 集成测试

```python
# 测试脚本
test_scripts = {
    "test_consecutive_limit_up.py": "测试连板梯队功能",
    "test_sector_limit_up_ladder.py": "测试板块连板梯队功能",
}

# 测试输出
test_output = {
    "format": "清晰的表格和统计信息",
    "content": "实际数据示例",
    "validation": "数据格式和内容验证",
}
```

## 文档设计

### 1. 代码文档

```python
# Docstring格式
docstring_format = """
功能描述

Args:
    参数1: 说明
    参数2: 说明

Returns:
    返回值说明

示例:
    代码示例
"""
```

### 2. 用户文档

```markdown
# 文档结构
- 功能概述
- 函数签名
- 使用示例
- 返回数据结构
- 字段说明
- 注意事项
- 常见问题
- 更新日志
```

## 部署设计

### 1. 依赖管理

```python
# requirements.txt
dependencies = [
    "requests>=2.25.0",
    "pandas>=1.2.0",
    "urllib3>=1.26.0",
]

# 可选依赖
optional_dependencies = [
    "selenium>=4.0.0",  # 用于东方财富热榜50
]
```

### 2. 安装方式

```bash
# 方式1: 直接使用
# 将kaipanla_crawler.py放到项目目录
from kaipanla_crawler import KaipanlaCrawler

# 方式2: 作为模块安装
pip install -e .

# 方式3: 复制到site-packages
cp kaipanla_crawler.py /path/to/site-packages/
```

## 维护设计

### 1. 版本管理

```python
# 版本号规则
version_format = "MAJOR.MINOR.PATCH"

# 版本历史
versions = {
    "1.0.0": "初始版本",
    "1.1.0": "新增连板梯队功能",
    "1.2.0": "新增板块连板梯队功能",
}
```

### 2. 问题追踪

```python
# 已知问题
known_issues = {
    "issue_1": "自动重试机制未实现",
    "issue_2": "数据缓存机制未实现",
    "issue_3": "异步请求未实现",
}

# 改进计划
improvements = {
    "plan_1": "实现请求频率限制",
    "plan_2": "实现数据缓存",
    "plan_3": "实现异步请求",
}
```

## 总结

本设计文档详细描述了开盘啦数据爬虫系统的架构、组件、数据流、错误处理、性能优化、安全性、扩展性、测试和文档设计。系统采用模块化、面向对象的设计思想，提供统一、易用、可靠的API接口，满足量化研究和交易系统的数据需求。
