# LLM集成层实现文档

## 概述

本文档描述了LLM集成层的实现，包括Gemini客户端、重试机制、错误处理和规则引擎降级方案。

## 实现的组件

### 1. GeminiClient (gemini_client.py)

Gemini-2.0-Flash模型的客户端封装。

**主要功能：**
- 初始化配置（API密钥、模型参数）
- 文本生成（generate）
- 带重试的生成（generate_with_retry）
- 结构化响应生成（generate_structured）
- 多轮对话（chat）
- 配置更新（update_config）

**配置参数：**
- `api_key`: Gemini API密钥
- `model_name`: 模型名称（默认：gemini-2.0-flash-exp）
- `temperature`: 温度参数（0.0-1.0，默认：0.7）
- `max_tokens`: 最大生成token数（默认：2048）
- `top_p`: nucleus sampling参数（默认：0.95）
- `top_k`: top-k sampling参数（默认：40）
- `timeout`: 请求超时时间（秒，默认：30）
- `max_retries`: 最大重试次数（默认：3）

**使用示例：**
```python
from src.llm import GeminiClient

client = GeminiClient(
    api_key="your_api_key",
    temperature=0.7,
    max_tokens=2048
)

response = client.generate("分析今日市场情绪")
```

### 2. LLMManager (llm_manager.py)

LLM调用的统一管理器，提供重试、错误处理和降级功能。

**主要功能：**
- 统一的LLM调用接口（call）
- 自动重试机制（指数退避）
- 超时处理
- 错误日志记录
- 自动降级到规则引擎
- 批量调用（call_batch）
- 状态监控（get_status）
- 统计信息（成功率、平均耗时等）

**状态枚举：**
- `AVAILABLE`: LLM可用
- `DEGRADED`: 使用降级方案
- `UNAVAILABLE`: 完全不可用

**返回格式：**
```python
{
    "response": str,      # 生成的响应
    "status": str,        # "success", "fallback", "error"
    "source": str,        # "gemini", "rule_based", "none"
    "retries": int,       # 重试次数
    "elapsed": float,     # 耗时（秒）
    "error": str          # 错误信息（如果有）
}
```

**使用示例：**
```python
from src.llm import create_llm_manager

manager = create_llm_manager()

result = manager.call(
    prompt="分析市场情绪",
    task_type="market_sentiment",
    context={"limit_up_count": 45, "index_change": 1.2}
)

print(result["response"])
print(f"Status: {result['status']}, Source: {result['source']}")
```

### 3. RuleBasedEngine (rule_based_engine.py)

基于规则的分析引擎，作为LLM不可用时的降级方案。

**支持的任务类型：**
1. `market_sentiment`: 市场情绪分析
2. `theme_detection`: 题材检测
3. `baseline_expectation`: 基准预期计算
4. `expectation_score`: 超预期分值计算
5. `decision_navigation`: 决策导航
6. `general`: 通用分析

**规则说明：**

#### 市场情绪分析
基于以下指标判断：
- 涨停家数
- 跌停家数
- 指数涨跌幅
- 成交量比

判断逻辑：
- 强势：涨停>50 且 指数>1% 且 量比>1.2
- 偏强：涨停>30 且 指数>0.5%
- 弱势：跌停>30 且 指数<-1%
- 偏弱：跌停>20 或 指数<-0.5%

#### 题材检测
基于关键词匹配：
- AI: ["人工智能", "AI", "大模型", "ChatGPT", "算力"]
- 新能源: ["新能源", "光伏", "锂电", "储能", "氢能"]
- 半导体: ["芯片", "半导体", "集成电路", "晶圆"]
- 数字经济: ["数字经济", "数据要素", "算力", "云计算"]
- 军工: ["军工", "国防", "航空", "航天"]
- 医药: ["医药", "生物医药", "创新药", "医疗器械"]
- 消费: ["消费", "白酒", "食品", "零售"]
- 地产: ["地产", "房地产", "建筑"]
- 金融: ["银行", "保险", "券商", "金融"]

#### 基准预期计算
基于连板高度、题材状态、市场环境：

基础预期（连板高度）：
- 5板及以上：5%-8%
- 3-4板：3%-6%
- 1-2板：1%-4%
- 昨日涨幅>5%：0%-3%
- 其他：-2%-2%

题材调整：
- 主升期：+2%
- 退潮：-3%/-2%

市场调整：
- 强势：+1%
- 弱势：-2%/-1%

#### 超预期分值计算
三个维度：

1. 量能分值（0-100）：
   - 竞价金额/昨日全天 >= 10%: 100分
   - >= 5%: 80分
   - >= 3%: 60分
   - >= 2%: 40分
   - < 2%: 20分

2. 价格分值（0-100）：
   - 超过预期上限：80-100分
   - 在预期区间内：60分
   - 低于预期下限：<60分

3. 独立性分值（0-100）：
   - 超额涨幅 >= 5%: 100分
   - >= 3%: 80分
   - >= 1%: 60分
   - >= 0%: 40分
   - < 0%: 20分

综合分值 = 量能×40% + 价格×40% + 独立性×20%

评级：
- 优秀(>=80): 打板
- 良好(60-80): 低吸
- 一般(40-60): 观望
- 较差(<40): 撤退

#### 决策导航
基于核心股状态和附加池情况：

场景判定：
- 核心股超预期 → 整体超预期场景
- 核心股不及预期 → 分歧兑现场景
- 附加池>3只 → 高低切场景
- 其他 → 震荡整理场景

**使用示例：**
```python
from src.llm import RuleBasedEngine

engine = RuleBasedEngine()

result = engine.analyze(
    prompt="分析市场情绪",
    task_type="market_sentiment",
    context={
        "limit_up_count": 45,
        "limit_down_count": 10,
        "index_change": 1.2,
        "volume_ratio": 1.5
    }
)

print(result)  # JSON格式的分析结果
```

### 4. LLMFactory (llm_factory.py)

提供便捷的实例创建功能。

**工厂函数：**
- `create_gemini_client()`: 创建Gemini客户端
- `create_rule_based_engine()`: 创建规则引擎
- `create_llm_manager()`: 创建LLM管理器
- `get_llm_manager()`: 获取全局LLM管理器实例

**使用示例：**
```python
from src.llm import get_llm_manager

# 获取全局实例（自动从配置读取）
manager = get_llm_manager()

# 或者自定义创建
from src.llm import create_llm_manager

manager = create_llm_manager(
    api_key="your_api_key",
    temperature=0.8,
    max_retries=5
)
```

## 配置

### 配置文件

在 `config/system_config.yaml` 中配置LLM参数：

```yaml
llm:
  api_key: "YOUR_GEMINI_API_KEY_HERE"
  model_name: "gemini-2.0-flash-exp"
  temperature: 0.7
  max_tokens: 2048
  top_p: 0.95
  top_k: 40
  timeout: 30
  max_retries: 3
  enable_fallback: true
```

### 环境变量

也可以通过环境变量配置：

```bash
export GEMINI_API_KEY="your_api_key"
```

## 错误处理

### 重试机制

LLMManager实现了自动重试机制：
1. 最多重试3次（可配置）
2. 使用指数退避策略（2^attempt秒）
3. 记录每次重试的错误信息

### 超时处理

- 默认超时时间：30秒
- 超时后自动重试
- 所有重试失败后降级到规则引擎

### 降级方案

当LLM不可用时：
1. 自动切换到规则引擎
2. 使用基于规则的分析方法
3. 在响应中标注使用了降级方案
4. 记录降级统计信息

### 错误日志

所有错误都会记录到日志：
- 重试信息：WARNING级别
- 错误信息：ERROR级别
- 降级信息：WARNING级别

## 性能监控

LLMManager提供统计信息：

```python
status = manager.get_status()

print(status)
# {
#     "status": "available",
#     "stats": {
#         "total_calls": 100,
#         "successful_calls": 95,
#         "failed_calls": 5,
#         "fallback_calls": 3,
#         "total_retries": 8,
#         "total_time": 150.5,
#         "avg_time": 1.505,
#         "success_rate": 95.0
#     },
#     "config": {
#         "max_retries": 3,
#         "timeout": 30,
#         "enable_fallback": true
#     }
# }
```

## 最佳实践

### 1. 使用全局实例

```python
from src.llm import get_llm_manager

# 推荐：使用全局实例
manager = get_llm_manager()
```

### 2. 提供上下文数据

```python
# 为规则引擎提供足够的上下文
result = manager.call(
    prompt="分析市场情绪",
    task_type="market_sentiment",
    context={
        "limit_up_count": 45,
        "limit_down_count": 10,
        "index_change": 1.2,
        "volume_ratio": 1.5
    }
)
```

### 3. 检查响应状态

```python
result = manager.call(prompt="...")

if result["status"] == "success":
    # LLM成功响应
    process_llm_response(result["response"])
elif result["status"] == "fallback":
    # 使用了降级方案
    logger.warning("Using fallback response")
    process_rule_based_response(result["response"])
else:
    # 完全失败
    logger.error(f"LLM call failed: {result['error']}")
    handle_error()
```

### 4. 定期监控状态

```python
# 定期检查LLM状态
status = manager.get_status()

if status["stats"]["success_rate"] < 80:
    logger.warning("LLM success rate is low, check API status")

if status["stats"]["fallback_calls"] > 10:
    logger.warning("Too many fallback calls, check LLM availability")
```

### 5. 自定义规则

```python
from src.llm import RuleBasedEngine

engine = RuleBasedEngine()

# 添加自定义规则
def custom_analysis(prompt, context):
    # 自定义分析逻辑
    return json.dumps({"result": "custom"})

engine.add_rule("custom_task", custom_analysis)
```

## 测试

### 单元测试

测试文件位于 `tests/test_llm.py`（可选任务，未实现）

### 手动测试

```python
# 测试Gemini客户端
from src.llm import create_gemini_client

client = create_gemini_client(api_key="your_key")
response = client.generate("Hello, Gemini!")
print(response)

# 测试规则引擎
from src.llm import RuleBasedEngine

engine = RuleBasedEngine()
result = engine.analyze(
    prompt="",
    task_type="market_sentiment",
    context={"limit_up_count": 45, "index_change": 1.2}
)
print(result)

# 测试LLM管理器
from src.llm import create_llm_manager

manager = create_llm_manager(api_key="your_key")
result = manager.call(
    prompt="分析市场",
    task_type="market_sentiment",
    context={"limit_up_count": 45}
)
print(result)
```

## 依赖

- `google-generativeai>=0.3.0`: Gemini API客户端
- `pydantic>=2.0.0`: 配置验证
- `loguru>=0.7.0`: 日志记录

## 相关需求

- 需求22.1: 使用Gemini-2.0-Flash作为基础LLM
- 需求22.2: 支持配置API密钥
- 需求22.3: 支持配置LLM参数
- 需求22.4: 实现错误处理和重试
- 需求22.5: 最多重试3次
- 需求22.6: 记录错误日志
- 需求22.7: 配置超时时间
- 需求22.8: 提供规则引擎降级方案

## 正确性属性

**Property 25: LLM调用重试**
- 对于任何LLM调用失败（超时或错误），系统应重试最多3次
- 最终失败时使用规则引擎降级
- 验证需求: 22.5, 22.8

## 后续工作

1. 实现可选的单元测试（任务5.4）
2. 添加更多规则引擎的分析规则
3. 优化重试策略（如自适应退避）
4. 添加LLM响应缓存机制
5. 实现批量调用的并发优化
