# Anthropic 智能体编排/调度框架使用指南

基于 Anthropic 研究文章 "Building Effective Agents" 的实现

---

## 目录

1. [核心概念](#核心概念)
2. [工作流模式](#工作流模式)
3. [自主智能体](#自主智能体)
4. [快速开始](#快速开始)
5. [配置详解](#配置详解)
6. [最佳实践](#最佳实践)

---

## 核心概念

### 构建模块

Anthropic 推荐将工作流构建为**组件**组合：

- **LLM 调用**：基础构建块
- **工具调用**：与外部系统交互
- **记忆系统**：短期和长期记忆
- **防护栏**：安全和质量检查

### 工作流 vs 智能体

| 维度 | 工作流 (Workflow) | 智能体 (Agent) |
|------|------------------|---------------|
| 控制 | 预定义路径 | 自主决策 |
| 可预测性 | 高 | 较低 |
| 适用场景 | 明确步骤、质量要求高 | 需要灵活性、规模庞大 |
| 延迟 | 通常较低 | 可能较高 |

---

## 工作流模式

### 1. 提示链 (Prompt Chaining)

```python
from agent_orchestrator import PromptChaining

# 定义处理步骤
def step_1_extract(input_data):
    # 提取关键信息
    return {"extracted": input_data["text"][:100]}

def step_2_analyze(extracted_data):
    # 分析提取的数据
    return {"analysis": f"分析结果: {extracted_data['extracted']}"}

def step_3_format(analysis_data):
    # 格式化最终输出
    return {"final": analysis_data["analysis"]}

# 创建提示链
chain = PromptChaining(
    steps=[step_1_extract, step_2_analyze, step_3_format],
    gating_threshold=0.8  # 置信度阈值
)

# 执行
result = await chain.execute({"input": {"text": "要处理的文本..."}})
```

**使用场景**：
- 每个子任务使用前一步输出作为输入
- 需要门控检查的场景
- 延迟可接受但质量要求高

---

### 2. 路由 (Routing)

```python
from agent_orchestrator import Routing

# 定义分类器
def classifier(input_data):
    """根据输入类型返回路由键"""
    query = input_data.get("query", "")

    if "技术" in query or "代码" in query:
        return "technical"
    elif "账单" in query or "付款" in query:
        return "billing"
    else:
        return "general"

# 定义路由处理器
def technical_handler(data):
    return {"response": "技术团队回复: ...", "type": "technical"}

def billing_handler(data):
    return {"response": "账单团队回复: ...", "type": "billing"}

def general_handler(data):
    return {"response": "通用回复: ...", "type": "general"}

# 创建路由
router = Routing(
    classifier=classifier,
    routes={
        "technical": technical_handler,
        "billing": billing_handler,
        "general": general_handler
    }
)

# 执行
result = await router.execute({"input": {"query": "技术问题..."}})
```

**使用场景**：
- 不同类型输入需要专门处理
- 可以构建更专业的提示
- 优化成本和性能

---

### 3. 并行化 (Parallelization)

```python
from agent_orchestrator import Parallelization

# 定义并行任务
def analyze_sentiment(data):
    """情感分析"""
    return {"sentiment": "positive", "score": 0.9}

def extract_entities(data):
    """实体提取"""
    return {"entities": ["公司A", "产品B"]}

def check_moderation(data):
    """内容审核"""
    return {"flagged": False, "categories": []}

def analyze_topics(data):
    """主题分析"""
    return {"topics": ["科技", "创新"]}

# 聚合函数
def aggregate_results(results):
    """聚合所有分析结果"""
    return {
        "sentiment": results[0],
        "entities": results[1],
        "moderation": results[2],
        "topics": results[3],
        "analysis_complete": True
    }

# 创建并行化工作流
parallel = Parallelization(
    tasks=[
        analyze_sentiment,
        extract_entities,
        check_moderation,
        analyze_topics
    ],
    aggregator=aggregate_results,
    max_workers=4
)

# 执行
result = await parallel.execute({"input": "要分析的文本..."})
```

**使用场景**：
- 任务可分解为独立子任务
- 需要同时执行多个LLM调用
- 延迟是关键因素

---

### 4. 编排器-工作者 (Orchestrator-Workers)

```python
from agent_orchestrator import OrchestratorWorkers

# 编排器函数
def orchestrator(input_data, previous_results):
    """分析当前状态，生成子任务计划"""

    # 如果是第一轮，根据输入创建初始任务
    if not previous_results:
        return [
            {"worker": "researcher", "input": {"topic": input_data["topic"]}},
            {"worker": "analyst", "input": {"data": "需要分析的数据"}}
        ]

    # 分析之前的结果，决定下一步
    completed_workers = [r["worker"] for r in previous_results]

    # 如果研究和分析都完成了，进行合成
    if "researcher" in completed_workers and "analyst" in completed_workers and "synthesizer" not in completed_workers:
        # 收集之前的结果
        research_result = next(r for r in previous_results if r["worker"] == "researcher")
        analysis_result = next(r for r in previous_results if r["worker"] == "analyst")

        return [
            {
                "worker": "synthesizer",
                "input": {
                    "research": research_result["output"],
                    "analysis": analysis_result["output"]
                }
            }
        ]

    # 如果合成了，任务完成
    if "synthesizer" in completed_workers:
        return []  # 空列表表示任务完成

    # 其他情况，继续等待
    return []

# 定义工作者
def researcher(data):
    """研究工作者"""
    return {"findings": f"关于 {data['topic']} 的研究结果..."}

def analyst(data):
    """分析工作者"""
    return {"analysis": f"数据分析结果: {data['data']}"}

def synthesizer(data):
    """综合工作者"""
    return {
        "final_report": f"综合报告:\n研究: {data['research']}\n分析: {data['analysis']}"
    }

# 创建编排器-工作者系统
ow_system = OrchestratorWorkers(
    orchestrator=orchestrator,
    workers={
        "researcher": researcher,
        "analyst": analyst,
        "synthesizer": synthesizer
    },
    max_rounds=10
)

# 执行
result = await ow_system.execute({"input": {"topic": "AI发展趋势"}})
```

**使用场景**：
- 无法预测所需子任务的复杂任务
- 需要动态分解和分配
- 每个工作者可告知编排器需要额外子任务

---

### 5. 评估器-优化器 (Evaluator-Optimizer)

```python
from agent_orchestrator import EvaluatorOptimizer

# 生成器函数
def generator(input_data, feedback):
    """生成响应，可选地使用前一轮反馈"""

    # 基础提示
    base_prompt = f"根据以下要求生成内容: {input_data['requirements']}"

    # 如果有反馈，使用它来改进
    if feedback:
        suggestions = "\n".join(feedback.get("suggestions", []))
        base_prompt += f"\n\n根据之前的反馈改进:\n{suggestions}"

    # 生成内容（这里应该是实际的LLM调用）
    generated_content = f"生成的内容基于: {base_prompt[:100]}..."

    return {
        "content": generated_content,
        "metadata": {"prompt_used": base_prompt}
    }

# 评估器函数
def evaluator(generated_result):
    """评估生成的响应，返回分数和建议"""

    content = generated_result.get("content", "")

    # 评估标准（实际实现中应该更复杂）
    checks = {
        "completeness": len(content) > 50,
        "clarity": "..." not in content,
        "relevance": "生成的" in content
    }

    # 计算分数
    score = sum(checks.values()) / len(checks)

    # 生成改进建议
    suggestions = []
    if not checks["completeness"]:
        suggestions.append("内容太短，请提供更多细节")
    if not checks["clarity"]:
        suggestions.append("内容被截断，请确保完整性")
    if not checks["relevance"]:
        suggestions.append("内容可能不相关，请确保符合要求")

    # 判断是否通过
    passed = score >= 0.8 and len(suggestions) == 0

    return {
        "score": score,
        "passed": passed,
        "checks": checks,
        "suggestions": suggestions
    }

# 创建评估器-优化器系统
eo_system = EvaluatorOptimizer(
    generator=generator,
    evaluator=evaluator,
    max_iterations=5,
    improvement_threshold=0.05
)

# 执行
result = await eo_system.execute({
    "input": {
        "requirements": "生成一份关于AI伦理的简要报告"
    }
})
```

**使用场景**：
- 有明确评估标准
- 迭代优化有价值
- 人类反馈可用

---

## 自主智能体

### 工具使用模式

```python
class AutonomousAgent:
    """
    自主智能体实现
    基于 Anthropic 的 Computer Use 模式
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.tools = self._register_tools()
        self.memory = []
        self.max_iterations = config.get("max_iterations", 100)

    def _register_tools(self) -> Dict[str, Callable]:
        """注册可用工具"""
        return {
            "search": self._tool_search,
            "calculate": self._tool_calculate,
            "read_file": self._tool_read_file,
            "write_file": self._tool_write_file,
            "execute_command": self._tool_execute_command
        }

    async def run(self, task: str) -> Dict[str, Any]:
        """
        REPL 风格的执行循环
        Read (观察), Evaluate (思考), Print (行动), Loop
        """
        iteration = 0
        context = {"task": task, "completed": False}

        while iteration < self.max_iterations and not context["completed"]:
            # 1. 观察当前状态
            observation = self._observe(context)

            # 2. 思考并决定下一步行动
            action = await self._think(observation, context)

            # 3. 执行行动
            result = await self._act(action)

            # 4. 更新上下文
            self._update_context(context, action, result)

            # 5. 自我反思
            await self._reflect(context)

            iteration += 1

        return context

    def _observe(self, context: Dict) -> Dict:
        """观察当前环境状态"""
        return {
            "current_step": context.get("step", 0),
            "last_action": context.get("last_action"),
            "memory_size": len(self.memory)
        }

    async def _think(self, observation: Dict, context: Dict) -> Dict:
        """
        思考并决定下一步行动
        这里应该是实际的 LLM 调用
        """
        # 示例：简单的规则决策
        if context.get("step", 0) == 0:
            return {
                "type": "tool_call",
                "tool": "search",
                "input": {"query": context["task"]}
            }
        else:
            return {
                "type": "complete",
                "result": "任务完成"
            }

    async def _act(self, action: Dict) -> Any:
        """执行行动"""
        action_type = action.get("type")

        if action_type == "tool_call":
            tool_name = action.get("tool")
            tool_input = action.get("input", {})
            tool = self.tools.get(tool_name)
            if tool:
                return await tool(**tool_input)

        elif action_type == "complete":
            return action.get("result")

        return None

    def _update_context(self, context: Dict, action: Dict, result: Any):
        """更新上下文"""
        context["last_action"] = action
        context["last_result"] = result
        context["step"] = context.get("step", 0) + 1

        # 添加到记忆
        self.memory.append({
            "action": action,
            "result": result,
            "timestamp": time.time()
        })

    async def _reflect(self, context: Dict):
        """
        自我反思
        检查进度并决定是否需要调整计划
        """
        # 示例：简单的完成检查
        if context.get("step", 0) >= 5:
            context["completed"] = True

    # 工具实现
    async def _tool_search(self, query: str) -> Dict:
        return {"results": f"搜索 '{query}' 的结果"}

    async def _tool_calculate(self, expression: str) -> Dict:
        try:
            result = eval(expression)  # 注意：实际使用时要安全处理
            return {"result": result}
        except Exception as e:
            return {"error": str(e)}

    async def _tool_read_file(self, path: str) -> Dict:
        try:
            with open(path, 'r') as f:
                return {"content": f.read()}
        except Exception as e:
            return {"error": str(e)}

    async def _tool_write_file(self, path: str, content: str) -> Dict:
        try:
            with open(path, 'w') as f:
                f.write(content)
            return {"success": True}
        except Exception as e:
            return {"error": str(e)}

    async def _tool_execute_command(self, command: str) -> Dict:
        import subprocess
        try:
            result = subprocess.run(
                command, shell=True, capture_output=True, text=True
            )
            return {
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode
            }
        except Exception as e:
            return {"error": str(e)}


# 使用示例
async def example_autonomous_agent():
    """自主智能体使用示例"""

    config = {
        "max_iterations": 50,
        "tools": ["search", "calculate", "read_file", "write_file"]
    }

    agent = AutonomousAgent(config)

    # 执行任务
    result = await agent.run(
        "分析 data.txt 文件中的数据，计算平均值，并生成报告"
    )

    print(f"任务完成: {result}")


if __name__ == "__main__":
    asyncio.run(example_autonomous_agent())
