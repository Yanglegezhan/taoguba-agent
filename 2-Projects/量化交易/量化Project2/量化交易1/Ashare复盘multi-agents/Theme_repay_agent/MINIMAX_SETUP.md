# MiniMax API 配置完成

## 配置日期：2026-03-06

---

## 修改内容

### 1. 添加 MiniMax 支持 (`src/llm/llm_analyzer.py`)

**修改 1：添加 MiniMax 到支持的提供商列表**
```python
SUPPORTED_PROVIDERS = {
    'openai': 'https://api.openai.com/v1/chat/completions',
    'zhipu': 'https://open.bigmodel.cn/api/paas/v4/chat/completions',
    'qwen': 'https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation',
    'deepseek': 'https://api.deepseek.com/v1/chat/completions',
    'minimax': 'https://api.minimaxi.com/v1/chat/completions'  # ✅ 新增
}
```

**修改 2：禁用 SSL 验证（MiniMax 需要）**
```python
def _create_session(self) -> requests.Session:
    session = requests.Session()

    # MiniMax 需要禁用 SSL 验证
    if self.provider == 'minimax':
        session.verify = False
        # 禁用警告
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    return session
```

**修改 3：支持 MiniMax 的 OpenAI 兼容调用**
```python
if self.provider in ['openai', 'zhipu', 'deepseek', 'minimax']:
    return self._call_openai_compatible(prompt, temp, max_tok)
```

### 2. 配置文件 (`config/config.yaml`)

```yaml
llm:
  provider: "minimax"
  api_key: "sk-api-NNAPJoPm9lQsAJORcLOOK60cSjemgaE2xgVjz3lVOutlLbXNbLBM1-TbU-evTlGdtSgLSgCZi7aXsi_YEPLiKlHYod0mc2r16x3Y7UE1tfQ241WZEJz_Pow"
  model_name: "MiniMax-M2.5"
  temperature: 0.3
  timeout: 180
```

---

## 关键发现

与 sentiment_replay_agent 对比发现：

| 项目 | URL | SSL验证 |
|-----|-----|---------|
| 错误配置 | `https://api.minimaxi.chat/v1` | 启用 |
| **正确配置** | `https://api.minimaxi.com/v1` | **禁用** |

**MiniMax 调用的两个关键点**：
1. URL 必须是 `api.minimaxi.com`（不是 .chat）
2. 必须禁用 SSL 验证 (`verify=False`)

---

## 测试结果

```
提供商: minimax
API URL: https://api.minimaxi.com/v1/chat/completions
模型: MiniMax-M2.5
Session verify: False

测试 API 调用...
[DEBUG] 调用API: https://api.minimaxi.com/v1/chat/completions
[DEBUG] 模型: MiniMax-M2.5

[LLM原始输出]
你好！我是MiniMax-M2.5，一个由MiniMax开发的AI助手...

响应成功!
```

✅ **MiniMax API 调用成功！**

---

## 使用方法

现在可以直接运行分析，使用 MiniMax-M2.5 模型：

```bash
python theme_cli.py --date 2026-03-05
```

系统会自动使用 MiniMax API 进行情绪周期分析和持续性评估。

---

## 支持的所有提供商

| 提供商 | 状态 | 说明 |
|-------|------|------|
| zhipu | ✅ | 智谱 AI |
| openai | ✅ | OpenAI GPT |
| qwen | ✅ | 通义千问 |
| deepseek | ✅ | DeepSeek |
| **minimax** | ✅ **新增** | **MiniMax-M2.5** |
