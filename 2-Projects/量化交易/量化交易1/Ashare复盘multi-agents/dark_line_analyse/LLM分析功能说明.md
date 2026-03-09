# LLM 分析功能说明

## 概述

在 `dark_line_analyse` 系统中，**大语言模型（LLM）确实起到了重要的分析作用**，但它是作为**可选的深度解读层**存在的。

## LLM 在分析流程中的位置

### 完整分析流程

```
1. 数据获取 (开盘啦/Tushare/AKShare)
   ↓
2. 数据增强 (基础信息、财务数据)
   ↓
3. 统计学分析 (地域、企业性质、市值、PB等)
   ↓
4. 命名语义分析 (吉祥命名、相似命名、前缀模式)
   ↓
5. 暗线检测 (基于统计显著性)
   ↓
6. 【LLM 深度解读】← 可选，需要配置 API Key
   ↓
7. 报告生成 (JSON + Markdown)
```

## LLM 的触发条件

LLM 分析**仅在以下条件全部满足时**才会执行：

1. ✅ **检测到暗线** - `dark_lines` 列表不为空
2. ✅ **LLM 配置存在** - `config.yaml` 中有 LLM 配置
3. ✅ **API Key 已配置** - 有有效的 API Key

### 代码逻辑（src/agent.py）

```python
# 6. LLM解读（可选）
llm_interpretation = None
if dark_lines and llm_config and llm_config.api_key:
    try:
        self.logger.info("Running LLM interpretation...")
        llm_interpretation = self.llm_analyzer.analyze_dark_lines(
            dark_lines=dark_lines,
            stat_analysis=stat_analysis,
            naming_analysis=naming_results
        )
    except Exception as e:
        self.logger.warning(f"LLM interpretation failed: {e}")
```

## LLM 的分析内容

### 输入给 LLM 的信息

1. **检测到的暗线列表**
   - 暗线标题
   - 暗线类型
   - 描述
   - 置信度

2. **统计分析摘要**
   - 涨停数量
   - 破净比例
   - 显著省份
   - 显著企业性质

3. **命名特征统计**
   - 命名特征计数
   - 命名特征占比

### LLM 的分析任务

基于专业的提示词模板（`prompts/dark_line_analysis.md`），LLM 会：

1. **解读暗线类型**
   - 地域集聚型
   - 企业性质主题型
   - PB价值主题型
   - 命名模式型
   - 技术形态型
   - 概念聚集型

2. **判断题材性质**
   - 事件驱动
   - 政策驱动
   - 情绪驱动
   - 资金驱动

3. **评估持续性**
   - 短期（1-3天）
   - 中期（1-2周）
   - 长期（1个月以上）

4. **识别关键驱动因素**
   - 列出2-3个主要驱动因素

5. **提示主要风险**
   - 列出2-3个主要风险点

6. **给出操作建议**
   - 具体的操作建议

7. **置信度评估**
   - 0.0 - 1.0 的置信度分数

### LLM 输出格式

```json
{
  "interpretation_type": "企业性质主题",
  "theme_nature": "资金驱动",
  "sustainability": "短期",
  "key_drivers": [
    "小市值民企活跃度提升",
    "资金偏好低价小盘股"
  ],
  "risks": [
    "样本量较小，可能为偶然因素",
    "缺乏基本面支撑"
  ],
  "recommendations": [
    "关注连板高度和成交量",
    "注意及时止盈"
  ],
  "confidence": 0.75,
  "reasoning": "详细推理过程..."
}
```

## LLM 在报告中的体现

### JSON 报告

```json
{
  "meta": {...},
  "statistical_summary": {...},
  "naming_features": {...},
  "dark_lines": [...],
  "llm_interpretation": {
    "interpretation_type": "...",
    "theme_nature": "...",
    "sustainability": "...",
    "key_drivers": [...],
    "risks": [...],
    "recommendations": [...],
    "confidence": 0.85,
    "reasoning": "..."
  }
}
```

### Markdown 报告

```markdown
## 四、LLM 解读

- **暗线类型**: 企业性质主题
- **题材性质**: 资金驱动
- **持续性**: 短期
- **置信度**: 0.75
- **关键驱动因素**:
  - 小市值民企活跃度提升
  - 资金偏好低价小盘股
- **主要风险**:
  - 样本量较小，可能为偶然因素
  - 缺乏基本面支撑
- **操作建议**:
  - 关注连板高度和成交量
  - 注意及时止盈
```

## 当前配置状态

### 配置文件（config/config.yaml）

```yaml
llm:
  provider: "zhipu"
  api_key: "1113a27ec2af4aac878671c73d016450.wMjkqwXELDfe4hU8"
  model_name: "glm-4.7-flash"
  temperature: 0.7
  max_tokens: null
  timeout: null
```

✅ **当前状态：已配置**
- Provider: 智谱AI (ZhipuAI)
- Model: glm-4.7-flash
- API Key: 已配置

## LLM 的价值

### 1. 深度解读

统计分析只能告诉你"什么"（哪些特征显著），LLM 能告诉你"为什么"和"怎么办"：

- **统计分析**: "民企占比77.8%，提升倍数3.5x"
- **LLM解读**: "这可能反映了资金对小市值民企的偏好，建议关注连板高度，注意及时止盈"

### 2. 综合判断

LLM 能够综合多个维度的信息，给出整体性的判断：

- 结合地域、企业性质、市值、命名等多维度
- 判断题材的性质和持续性
- 给出具体的操作建议

### 3. 风险提示

LLM 能够识别潜在风险：

- 样本量不足的风险
- 缺乏基本面支撑的风险
- 情绪过热的风险

## 没有 LLM 时的情况

如果没有配置 LLM API Key，系统仍然可以正常工作：

1. ✅ 数据获取正常
2. ✅ 统计分析正常
3. ✅ 命名分析正常
4. ✅ 暗线检测正常
5. ✅ 报告生成正常
6. ❌ 缺少 LLM 深度解读

报告中会缺少"四、LLM 解读"章节，但其他内容完整。

## 支持的 LLM 提供商

### 1. 智谱AI (ZhipuAI) - 当前使用

```yaml
llm:
  provider: "zhipu"
  api_key: "your_zhipu_api_key"
  model_name: "glm-4.7-flash"
```

**依赖**: `pip install zhipuai`

### 2. OpenAI

```yaml
llm:
  provider: "openai"
  api_key: "your_openai_api_key"
  model_name: "gpt-4"
```

**依赖**: `pip install openai`

### 3. DeepSeek

```yaml
llm:
  provider: "deepseek"
  api_key: "your_deepseek_api_key"
  model_name: "deepseek-chat"
```

**依赖**: `pip install openai`

## 测试 LLM 功能

### 快速检查

```bash
python test_llm_simple.py
```

这会检查：
- LLM 配置是否正确
- 依赖包是否安装
- API Key 是否配置
- LLM 在流程中的作用

### 完整测试

运行一次完整分析，如果检测到暗线，LLM 会自动被调用：

```bash
python dark_line_cli.py
```

查看日志中是否有：
```
Running LLM interpretation...
```

## 提示词工程

LLM 的分析质量很大程度上取决于提示词的设计。当前提示词位于：

```
prompts/dark_line_analysis.md
```

提示词包含：
- 分析框架（统计学维度、命名语义维度、技术形态维度）
- 暗线类型定义
- 输出格式要求
- 分析原则
- 持续性判断标准
- 注意事项

可以根据实际需求调整提示词以优化 LLM 的分析效果。

## 总结

### LLM 的作用

✅ **确实起到了重要的分析作用**

1. **深度解读**: 将统计结果转化为可理解的市场洞察
2. **综合判断**: 多维度信息的整合和判断
3. **风险提示**: 识别潜在风险
4. **操作建议**: 给出具体的操作建议
5. **持续性评估**: 判断题材的持续性

### LLM 的定位

- **不是必需的**: 没有 LLM，系统仍能完成基础分析
- **是增强的**: LLM 提供了更深层次的解读和建议
- **是可选的**: 可以根据需要开启或关闭

### 当前状态

✅ **LLM 功能已配置并可用**

- Provider: 智谱AI
- Model: glm-4.7-flash
- API Key: 已配置
- 当检测到暗线时，会自动调用 LLM 进行深度解读

---

*文档生成时间: 2026-02-06*
