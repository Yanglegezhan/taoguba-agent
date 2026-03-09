# 工作流模式选择指南

基于 Anthropic 研究文章 "Building Effective Agents" 的决策框架

---

## 快速决策流程图

```
开始
 │
 ├─ 任务是否可以分解为固定子任务？
 │   ├─ 是 ── 每个子任务使用前一步输出作为输入？
 │   │          ├─ 是 ── 需要门控检查？
 │   │          │          ├─ 是 ──► 提示链 (Prompt Chaining)
 │   │          │          └─ 否 ──► 提示链（简化版）
 │   │          └─ 否 ── 子任务可以并行执行？
 │   │                     ├─ 是 ──► 并行化 (Parallelization)
 │   │                     └─ 否 ──► 重新评估任务分解
 │   └─ 否 ── 需要动态分解任务？
 │             ├─ 是 ── 工作者可以要求额外子任务？
 │             │          ├─ 是 ──► 编排器-工作者 (Orchestrator-Workers)
 │             │          └─ 否 ── 有明确评估标准且需要迭代优化？
 │             │                     ├─ 是 ──► 评估器-优化器 (Evaluator-Optimizer)
 │             │                     └─ 否 ──► 自主智能体 (Autonomous Agent)
 │             └─ 否 ── 不同类型输入需要专门处理？
 │                       ├─ 是 ──► 路由 (Routing)
 │                       └─ 否 ──► 简单链式或提示链
```

---

## 模式对比矩阵

| 模式 | 适用场景 | 延迟 | 准确性 | 复杂度 | 成本 |
|------|---------|------|--------|--------|------|
| **提示链** | 固定步骤、门控检查 | 中等 | 高 | 低 | 中 |
| **路由** | 分类处理 | 低 | 高 | 低 | 低 |
| **并行化** | 独立子任务 | **低** | 中 | 中 | **高** |
| **编排器-工作者** | 动态分解 | 高 | 高 | **高** | 高 |
| **评估器-优化器** | 迭代优化 | **高** | **最高** | 中 | **高** |
| **自主智能体** | 开放性问题 | 变化大 | 变化大 | **最高** | 变化大 |

---

## 详细模式指南

### 1. 提示链 (Prompt Chaining)

**何时使用**：
- ✅ 任务可分解为固定子任务序列
- ✅ 每个子任务使用前一步的输出作为输入
- ✅ 需要在特定步骤进行门控检查
- ✅ 愿意用延迟换取更高的准确性

**何时不使用**：
- ❌ 子任务可以并行执行
- ❌ 步骤之间的依赖关系复杂或不固定
- ❌ 延迟是关键因素

**最佳实践**：
```python
# 好的做法：明确的步骤和门控
steps = [
    extract_requirements,  # 提取需求
    validate_requirements, # 验证（门控）
    generate_solution,     # 生成方案
    validate_solution      # 最终验证
]

# 避免：模糊的步骤定义
steps = [
    process_step_1,  # 不清晰
    process_step_2,
    process_step_3
]
```

---

### 2. 路由 (Routing)

**何时使用**：
- ✅ 不同类型输入需要专门处理
- ✅ 分类逻辑清晰可定义
- ✅ 有多个专门的提示/模型可用
- ✅ 希望优化成本（小模型处理简单任务）

**何时不使用**：
- ❌ 分类本身就很复杂
- ❌ 所有输入类型都可以使用同一个强大模型处理
- ❌ 分类错误会导致严重后果

**最佳实践**：
```python
# 好的做法：清晰的分类和专门的处理
def classifier(input_data):
    query = input_data["query"]

    # 使用简单规则或专门的小模型分类
    if contains_technical_terms(query):
        return "technical"
    elif is_billing_related(query):
        return "billing"
    else:
        return "general"

# 专门的处理函数
def handle_technical(data):
    # 使用技术领域专家模型
    return technical_model.process(data)

# 避免：复杂的嵌套分类
def bad_classifier(data):
    if condition_a and condition_b or condition_c:
        if nested_condition:
            return "type_a"
        else:
            return "type_b"
    # ... 过于复杂
```

---

### 3. 并行化 (Parallelization)

**何时使用**：
- ✅ 任务可分解为完全独立的子任务
- ✅ 延迟是关键因素
- ✅ 需要同时执行多个LLM调用
- ✅ 有聚合函数可以合并结果

**何时不使用**：
- ❌ 子任务之间有依赖关系
- ❌ 成本是主要限制（并行会增加成本）
- ❌ 难以定义聚合逻辑

**最佳实践**：
```python
# 好的做法：独立的任务和清晰的聚合
def task_1(data):
    # 独立任务：情感分析
    return analyze_sentiment(data)

def task_2(data):
    # 独立任务：实体提取
    return extract_entities(data)

def task_3(data):
    # 独立任务：主题分类
    return classify_topics(data)

def aggregate(results):
    # 清晰定义如何合并结果
    return {
        "sentiment": results[0],
        "entities": results[1],
        "topics": results[2],
        "timestamp": datetime.now()
    }

# 避免：相互依赖的"并行"任务
# 错误示例
def bad_task_1(data):
    result = process_a(data)
    return result

def bad_task_2(data):
    # 错误：依赖 task_1 的结果
    task_1_result = get_task_1_result()  # 这会阻塞
    return process_b(task_1_result)
```

---

### 4. 编排器-工作者 (Orchestrator-Workers)

**何时使用**：
- ✅ 无法预先确定子任务
- ✅ 需要动态分解复杂任务
- ✅ 工作者可以根据结果请求额外子任务
- ✅ 输出质量比延迟更重要

**何时不使用**：
- ❌ 步骤可以预先确定（使用提示链更简单）
- ❌ 延迟是关键因素
- ❌ 分解逻辑本身就很复杂

**最佳实践**：
```python
# 好的做法：动态任务生成和灵活的工作者
def orchestrator(input_data, previous_results):
    """
    分析当前状态并生成下一步任务
    """
    # 根据已完成的结果决定下一步
    if not previous_results:
        # 初始分解
        return [
            {"worker": "researcher", "input": {"topic": input_data["topic"]}},
            {"worker": "requirement_analyst", "input": {"doc": input_data["doc"]}}
        ]

    # 分析已完成的工作
    completed_types = {r["worker"] for r in previous_results}

    # 动态决定下一步
    if "researcher" in completed_types and "requirement_analyst" in completed_types:
        if "gap_analyzer" not in completed_types:
            # 发现需要进一步分析差距
            return [
                {"worker": "gap_analyzer", "input": {"previous_results": previous_results}}
            ]
        elif "solution_designer" not in completed_types:
            return [
                {"worker": "solution_designer", "input": {"previous_results": previous_results}}
            ]

    # 所有必要步骤完成
    return []

# 定义灵活的工作者
def researcher(data):
    # 研究工作
    return {"findings": [...]}

def gap_analyzer(data):
    # 分析差距
    return {"gaps": [...]}

# 避免：过于复杂的编排逻辑
def bad_orchestrator(input_data, previous_results):
    # 错误：嵌套条件过多，难以理解和维护
    if condition_a:
        if condition_b:
            if condition_c:
                return [...]
            else:
                return [...]
        else:
            return [...]
    # ... 过于复杂
```

---

### 5. 评估器-优化器 (Evaluator-Optimizer)

**何时使用**：
- ✅ 有明确评估标准
- ✅ 迭代优化可以明显提升质量
- ✅ 可以获得反馈（人工或自动）
- ✅ 延迟不是关键约束

**何时不使用**：
- ❌ 评估标准模糊或主观
- ❌ 迭代不会明显提升质量
- ❌ 延迟是关键因素

**最佳实践**：
```python
# 好的做法：明确的评估标准和有针对性改进
def generator(input_data, feedback):
    """
    生成内容，使用反馈进行改进
    """
    prompt = f"根据要求生成: {input_data['requirements']}"

    if feedback:
        # 有针对性地应用反馈
        suggestions = feedback.get("suggestions", [])
        prompt += "\n\n改进建议:\n"
        for suggestion in suggestions:
            prompt += f"- {suggestion}\n"

        # 参考之前的评分
        previous_score = feedback.get("score", 0)
        prompt += f"\n之前评分: {previous_score}/1.0，请针对性改进"

    # 生成内容
    return {
        "content": generate_with_llm(prompt),
        "generation_params": {...}
    }

def evaluator(generated_result):
    """
    明确、多维度的评估
    """
    content = generated_result.get("content", "")

    # 多维度评估
    dimensions = {
        "completeness": {
            "score": check_completeness(content),
            "weight": 0.3
        },
        "accuracy": {
            "score": check_accuracy(content),
            "weight": 0.3
        },
        "clarity": {
            "score": check_clarity(content),
            "weight": 0.2
        },
        "format": {
            "score": check_format(content),
            "weight": 0.2
        }
    }

    # 计算加权总分
    total_score = sum(
        d["score"] * d["weight"]
        for d in dimensions.values()
    )

    # 生成具体改进建议
    suggestions = []
    for dim_name, dim_data in dimensions.items():
        if dim_data["score"] < 0.8:
            suggestions.append(get_improvement_suggestion(dim_name, content))

    # 是否通过
    passed = total_score >= 0.9 and len(suggestions) <= 1

    return {
        "score": total_score,
        "passed": passed,
        "dimensions": dimensions,
        "suggestions": suggestions
    }

# 避免：模糊的评估标准
def bad_evaluator(result):
    # 错误：过于主观，没有明确标准
    return {
        "score": 0.8,  # 没有说明为什么
        "passed": True,  # 没有明确通过标准
        "suggestions": ["改进一下"]  # 太模糊，没有针对性
    }
```

---

## 选择决策树

```
┌─────────────────────────────────────────────────────────────────┐
│                    任务特征分析                                   │
└─────────────────────────────────────────────────────────────────┘
                           │
           ┌───────────────┼───────────────┐
           ▼               ▼               ▼
    ┌────────────┐  ┌────────────┐  ┌────────────┐
    │ 步骤可预测？ │  │ 需要分类？  │  │ 需要动态规划？│
    └────────────┘  └────────────┘  └────────────┘
           │               │               │
           ▼               ▼               ▼
    ┌────────────┐  ┌────────────┐  ┌────────────┐
    │ 提示链      │  │ 路由        │  │ 编排器-工作者 │
    │ Prompt     │  │ Routing    │  │ Orchestrator-│
    │ Chaining   │  │            │  │ Workers       │
    └────────────┘  └────────────┘  └────────────┘
           │               │               │
           └───────────────┴───────────────┘
                           │
                           ▼
                  ┌────────────────┐
                  │ 子任务是否独立？ │
                  └────────────────┘
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
        ┌──────────┐ ┌──────────┐ ┌──────────┐
        │ 是，可并行 │ │否，需迭代 │ │ 完全自主 │
        └──────────┘ └──────────┘ └──────────┘
              │            │            │
              ▼            ▼            ▼
        ┌──────────┐ ┌──────────┐ ┌──────────┐
        │ 并行化    │ │ 评估器-优 │ │ 自主智能体 │
        │Parallel  │ │ 化器      │ │ Agent     │
        │ization   │ │ Evaluator-│ │           │
        │          │ │ Optimizer│ │           │
        └──────────┘ └──────────┘ └──────────┘
```

---

## 常见错误和如何避免

### 错误 1：为简单任务使用复杂模式

```python
# ❌ 错误：为简单任务使用编排器-工作者
def simple_data_processing(data):
    orchestrator = OrchestratorWorkers(...)
    return orchestrator.execute({"input": data})

# ✅ 正确：使用简单的提示链
chain = PromptChaining(steps=[step1, step2])
return chain.execute({"input": data})
```

### 错误 2：忽略延迟成本

```python
# ❌ 错误：在延迟敏感场景使用评估器-优化器
evaluator_optimizer = EvaluatorOptimizer(
    max_iterations=10  # 太多迭代！
)

# ✅ 正确：限制迭代次数，设置早期停止
evaluator_optimizer = EvaluatorOptimizer(
    max_iterations=3,
    improvement_threshold=0.1  # 早停
)
```

### 错误 3：混合依赖和独立任务

```python
# ❌ 错误：在并行化中混合依赖任务
parallel = Parallelization(
    tasks=[
        task_a,
        task_b,  # 依赖 task_a 的结果！
        task_c
    ]
)

# ✅ 正确：识别依赖关系，使用编排器-工作者
orchestrator = OrchestratorWorkers(
    orchestrator=lambda ctx, results: [
        {"worker": "a", "input": ctx},
        {"worker": "b", "input": results[0] if results else None},  # 依赖 a
        {"worker": "c", "input": ctx}
    ],
    workers={"a": task_a, "b": task_b, "c": task_c}
)
```

---

## 配置调优建议

### 1. 延迟优化

```yaml
# 减少延迟的配置
workflow_patterns:
  prompt_chaining:
    enabled: true
    gating_threshold: 0.5  # 降低阈值减少等待

  parallelization:
    enabled: true
    max_workers: 20  # 增加并行度

  evaluator_optimizer:
    max_iterations: 2  # 限制迭代次数
    improvement_threshold: 0.1  # 早停
```

### 2. 质量优化

```yaml
# 提高质量的配置
workflow_patterns:
  prompt_chaining:
    enabled: true
    gating_threshold: 0.9  # 高阈值确保质量

  evaluator_optimizer:
    enabled: true
    max_iterations: 10  # 允许更多迭代
    improvement_threshold: 0.01  # 追求小改进

  orchestrator_workers:
    enabled: true
    max_rounds: 20  # 允许多轮迭代
```

### 3. 成本优化

```yaml
# 降低成本的配置
workflow_patterns:
  routing:
    enabled: true
    # 使用小模型处理简单任务
    # 大模型只处理复杂任务

  parallelization:
    enabled: false  # 并行增加token消耗

  prompt_chaining:
    enabled: true
    # 链式调用允许提前退出
```

---

## 总结

选择正确的工作流模式是成功的关键。记住 Anthropic 的核心建议：

1. **从简单开始**：先用简单的模式，只有在需要时才增加复杂度
2. **透明优于智能**：显式控制流程比让AI自己决定更可靠
3. **验证再扩展**：在小规模验证模式有效后再扩展
4. **考虑成本**：并行化和迭代优化会增加成本

---

*本指南基于 Anthropic 研究文章 "Building Effective Agents" (2024)*
