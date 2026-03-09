# LLM集成层快速参考

## 快速开始

### 1. 配置API密钥

在 `config/system_config.yaml` 中设置：

```yaml
llm:
  api_key: "YOUR_GEMINI_API_KEY_HERE"
```

或使用环境变量：

```bash
export GEMINI_API_KEY="your_api_key"
```

### 2. 基本使用

```python
from src.llm import get_llm_manager

# 获取LLM管理器
manager = get_llm_manager()

# 调用LLM
result = manager.call(
    prompt="分析今日市场情绪",
    task_type="market_sentiment",
    context={
        "limit_up_count": 45,
        "limit_down_count": 10,
        "index_change": 1.2
    }
)

# 使用响应
if result["status"] == "success":
    print(result["response"])
```

## 常用API

### LLMManager

```python
# 单次调用
result = manager.call(prompt, task_type, context)

# 批量调用
results = manager.call_batch(prompts, task_type=...)

# 获取状态
status = manager.get_status()

# 更新配置
manager.update_config(max_retries=5, timeout=60)

# 重置统计
manager.reset_stats()
```

### GeminiClient

```python
from src.llm import create_gemini_client

client = create_gemini_client(api_key="...")

# 生成文本
response = client.generate(prompt)

# 带重试
response = client.generate_with_retry(prompt, max_retries=5)

# 结构化输出
response = client.generate_structured(prompt, expected_format="json")

# 多轮对话
response = client.chat([
    {"role": "user", "content": "Hello"},
    {"role": "user", "content": "How are you?"}
])
```

### RuleBasedEngine

```python
from src.llm import RuleBasedEngine

engine = RuleBasedEngine()

# 分析
result = engine.analyze(prompt, task_type, context)

# 支持的任务类型
tasks = engine.get_supported_tasks()

# 添加自定义规则
engine.add_rule("custom", custom_func)
```

## 任务类型

| 任务类型 | 说明 | 必需上下文 |
|---------|------|-----------|
| `market_sentiment` | 市场情绪分析 | limit_up_count, limit_down_count, index_change, volume_ratio |
| `theme_detection` | 题材检测 | news (新闻列表) |
| `baseline_expectation` | 基准预期计算 | stock_code, board_height, yesterday_change, theme_status, market_sentiment |
| `expectation_score` | 超预期分值 | auction_amount, yesterday_amount, actual_open, expected_min, expected_max, stock_change, index_change |
| `decision_navigation` | 决策导航 | core_stocks_status, additional_pool_count, market_sentiment |
| `general` | 通用分析 | 无 |

## 响应格式

```python
{
    "response": str,      # 生成的响应文本
    "status": str,        # "success", "fallback", "error"
    "source": str,        # "gemini", "rule_based", "none"
    "retries": int,       # 重试次数
    "elapsed": float,     # 耗时（秒）
    "error": str          # 错误信息（可选）
}
```

## 配置参数

| 参数 | 默认值 | 说明 |
|-----|--------|------|
| `api_key` | "" | Gemini API密钥 |
| `model_name` | "gemini-2.0-flash-exp" | 模型名称 |
| `temperature` | 0.7 | 温度参数 (0.0-1.0) |
| `max_tokens` | 2048 | 最大token数 |
| `top_p` | 0.95 | nucleus sampling |
| `top_k` | 40 | top-k sampling |
| `timeout` | 30 | 超时时间（秒） |
| `max_retries` | 3 | 最大重试次数 |
| `enable_fallback` | true | 启用降级 |

## 错误处理

### 检查状态

```python
result = manager.call(...)

if result["status"] == "success":
    # 成功
    pass
elif result["status"] == "fallback":
    # 使用了降级方案
    logger.warning("Using fallback")
else:
    # 失败
    logger.error(f"Error: {result['error']}")
```

### 监控统计

```python
status = manager.get_status()

print(f"Success rate: {status['stats']['success_rate']:.1f}%")
print(f"Avg time: {status['stats']['avg_time']:.2f}s")
print(f"Fallback calls: {status['stats']['fallback_calls']}")
```

## 常见问题

### Q: API密钥在哪里获取？

A: 访问 https://makersuite.google.com/app/apikey 获取Gemini API密钥。

### Q: 如何禁用降级方案？

A: 在配置中设置 `enable_fallback: false` 或创建时传入参数：

```python
manager = create_llm_manager(enable_fallback=False)
```

### Q: 如何调整重试次数？

A: 在配置中设置 `max_retries` 或运行时更新：

```python
manager.update_config(max_retries=5)
```

### Q: 规则引擎的准确性如何？

A: 规则引擎基于固定阈值和历史统计，置信度约为0.5-0.7，适合作为降级方案，但不如LLM灵活。

### Q: 如何添加自定义分析规则？

A: 使用 `add_rule` 方法：

```python
def my_rule(prompt, context):
    # 自定义逻辑
    return json.dumps({"result": "..."})

engine.add_rule("my_task", my_rule)
```

## 性能优化

### 1. 批量调用

```python
# 不推荐：逐个调用
for prompt in prompts:
    result = manager.call(prompt)

# 推荐：批量调用
results = manager.call_batch(prompts)
```

### 2. 调整超时

```python
# 对于简单任务，减少超时
result = manager.call(prompt, timeout=10)

# 对于复杂任务，增加超时
result = manager.call(prompt, timeout=60)
```

### 3. 使用全局实例

```python
# 推荐：复用全局实例
manager = get_llm_manager()

# 不推荐：每次创建新实例
manager = create_llm_manager()
```

## 调试技巧

### 启用详细日志

```python
from src.common.logger import get_logger
import logging

logger = get_logger(__name__)
logger.setLevel(logging.DEBUG)
```

### 查看重试信息

```python
result = manager.call(...)
print(f"Retries: {result['retries']}")
print(f"Elapsed: {result['elapsed']:.2f}s")
```

### 测试规则引擎

```python
# 直接测试规则引擎
from src.llm import RuleBasedEngine

engine = RuleBasedEngine()
result = engine.analyze(
    prompt="",
    task_type="market_sentiment",
    context={"limit_up_count": 45, "index_change": 1.2}
)
print(result)
```
