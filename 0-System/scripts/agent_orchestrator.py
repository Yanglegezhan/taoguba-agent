"""
基于 Anthropic "Building Effective Agents" 的智能体编排器
支持多种工作流模式和自主智能体
"""

import asyncio
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, TypeVar, Generic
from concurrent.futures import ThreadPoolExecutor
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================================
# 基础类型定义
# ============================================================================

class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"


class Priority(Enum):
    CRITICAL = 10
    HIGH = 5
    NORMAL = 1
    LOW = 0.5


@dataclass
class Task:
    """任务定义"""
    id: str
    name: str
    func: Callable[..., Any]
    args: tuple = field(default_factory=tuple)
    kwargs: dict = field(default_factory=dict)
    priority: Priority = Priority.NORMAL
    status: TaskStatus = TaskStatus.PENDING
    result: Any = None
    error: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    dependencies: List[str] = field(default_factory=list)


@dataclass
class WorkflowStep:
    """工作流步骤"""
    id: str
    name: str
    task: Task
    next_steps: List[str] = field(default_factory=list)
    condition: Optional[Callable[[Any], bool]] = None


# ============================================================================
# 工作流模式实现
# ============================================================================

class WorkflowPattern(ABC):
    """工作流模式抽象基类"""

    @abstractmethod
    async def execute(self, context: Dict[str, Any]) -> Any:
        pass


class PromptChaining(WorkflowPattern):
    """
    提示链模式
    适用场景：任务可分解为固定子任务，每个子任务使用前一步输出作为输入
    权衡：延迟换取更高准确性
    """

    def __init__(self, steps: List[Callable[[Any], Any]],
                 gating_threshold: float = 0.8):
        self.steps = steps
        self.gating_threshold = gating_threshold

    async def execute(self, context: Dict[str, Any]) -> Any:
        result = context.get("input")

        for i, step in enumerate(self.steps):
            logger.info(f"执行提示链步骤 {i+1}/{len(self.steps)}")

            # 执行当前步骤
            result = await asyncio.to_thread(step, result)

            # 门控检查（如果有置信度分数）
            if isinstance(result, dict) and "confidence" in result:
                if result["confidence"] < self.gating_threshold:
                    logger.warning(f"步骤 {i+1} 置信度低于阈值，触发回退逻辑")
                    # 可以在这里添加回退逻辑

        return result


class Routing(WorkflowPattern):
    """
    路由模式
    适用场景：不同类型输入需要专门处理路径
    实现：分类步骤检测输入类型并路由到专业提示
    """

    def __init__(self, classifier: Callable[[Any], str],
                 routes: Dict[str, Callable[[Any], Any]]):
        self.classifier = classifier
        self.routes = routes

    async def execute(self, context: Dict[str, Any]) -> Any:
        input_data = context.get("input")

        # 分类
        route_key = await asyncio.to_thread(self.classifier, input_data)
        logger.info(f"路由分类结果: {route_key}")

        # 路由到对应处理器
        handler = self.routes.get(route_key)
        if not handler:
            raise ValueError(f"未找到路由处理器: {route_key}")

        return await asyncio.to_thread(handler, input_data)


class Parallelization(WorkflowPattern):
    """
    并行化模式
    适用场景：任务可分解为独立执行的子任务
    实现：同时执行多个LLM调用，聚合结果
    """

    def __init__(self, tasks: List[Callable[[Any], Any]],
                 aggregator: Callable[[List[Any]], Any],
                 max_workers: int = 10):
        self.tasks = tasks
        self.aggregator = aggregator
        self.max_workers = max_workers

    async def execute(self, context: Dict[str, Any]) -> Any:
        input_data = context.get("input")

        # 创建所有任务
        async def run_task(task):
            return await asyncio.to_thread(task, input_data)

        # 并行执行
        logger.info(f"并行执行 {len(self.tasks)} 个任务")
        results = await asyncio.gather(
            *[run_task(task) for task in self.tasks],
            return_exceptions=True
        )

        # 处理异常
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"任务 {i} 失败: {result}")
                processed_results.append(None)
            else:
                processed_results.append(result)

        # 聚合结果
        return await asyncio.to_thread(self.aggregator, processed_results)


class OrchestratorWorkers(WorkflowPattern):
    """
    编排器-工作者模式
    适用场景：无法预测所需子任务的复杂任务
    实现：中心编排器动态分解任务并分配给工作者
    """

    def __init__(self, orchestrator: Callable[[Any, List[Any]], List[Dict]],
                 workers: Dict[str, Callable[[Any], Any]],
                 max_rounds: int = 10):
        self.orchestrator = orchestrator
        self.workers = workers
        self.max_rounds = max_rounds

    async def execute(self, context: Dict[str, Any]) -> Any:
        input_data = context.get("input")
        results = []

        for round_num in range(self.max_rounds):
            logger.info(f"编排器-工作者第 {round_num + 1}/{self.max_rounds} 轮")

            # 编排器分析当前状态并生成子任务
            plan = await asyncio.to_thread(
                self.orchestrator, input_data, results
            )

            if not plan or len(plan) == 0:
                logger.info("编排器指示任务完成")
                break

            # 执行子任务
            round_results = []
            for task in plan:
                worker_name = task.get("worker")
                task_input = task.get("input")

                worker = self.workers.get(worker_name)
                if not worker:
                    logger.error(f"未找到工作者: {worker_name}")
                    continue

                result = await asyncio.to_thread(worker, task_input)
                round_results.append({
                    "worker": worker_name,
                    "input": task_input,
                    "output": result
                })

            results.extend(round_results)

        return results


class EvaluatorOptimizer(WorkflowPattern):
    """
    评估器-优化器模式
    适用场景：有明确评估标准且迭代优化有价值的场景
    实现：循环中一个提示生成响应，另一个评估并提供反馈
    """

    def __init__(self, generator: Callable[[Any, Optional[Dict]], Any],
                 evaluator: Callable[[Any], Dict],
                 max_iterations: int = 5,
                 improvement_threshold: float = 0.05):
        self.generator = generator
        self.evaluator = evaluator
        self.max_iterations = max_iterations
        self.improvement_threshold = improvement_threshold

    async def execute(self, context: Dict[str, Any]) -> Any:
        input_data = context.get("input")
        feedback = None
        best_result = None
        best_score = 0.0

        for iteration in range(self.max_iterations):
            logger.info(f"评估器-优化器第 {iteration + 1}/{self.max_iterations} 轮")

            # 生成响应
            result = await asyncio.to_thread(
                self.generator, input_data, feedback
            )

            # 评估响应
            evaluation = await asyncio.to_thread(self.evaluator, result)
            score = evaluation.get("score", 0.0)
            passed = evaluation.get("passed", False)

            logger.info(f"评估分数: {score}, 通过: {passed}")

            # 记录最佳结果
            if score > best_score:
                best_score = score
                best_result = result

            # 检查是否通过
            if passed:
                logger.info("评估通过，停止迭代")
                return result

            # 准备下一轮反馈
            improvement = score - (feedback.get("previous_score", 0.0) if feedback else 0.0)
            if improvement < self.improvement_threshold and iteration > 0:
                logger.warning(f"改进幅度 {improvement} 低于阈值，停止迭代")
                break

            feedback = {
                "evaluation": evaluation,
                "score": score,
                "previous_score": score,
                "improvement": improvement,
                "suggestions": evaluation.get("suggestions", [])
            }

        logger.info(f"达到最大迭代次数，返回最佳结果 (分数: {best_score})")
        return best_result or result


# ============================================================================
# 任务调度器
# ============================================================================

class TaskScheduler:
    """
    智能任务调度器
    支持优先级队列、资源限制、重试机制
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.tasks: Dict[str, Task] = {}
        self.queue: asyncio.PriorityQueue = asyncio.PriorityQueue()
        self.running: set = set()
        self.max_workers = config.get("max_workers", 10)
        self.retry_policy = config.get("retry_policy", {})
        self._shutdown = False

    async def submit(self, task: Task) -> str:
        """提交任务到调度器"""
        self.tasks[task.id] = task

        # 计算优先级分数
        priority_score = self._calculate_priority(task)

        await self.queue.put((priority_score, task.id))
        logger.info(f"任务 {task.id} 已提交，优先级: {priority_score}")

        return task.id

    def _calculate_priority(self, task: Task) -> float:
        """计算任务优先级分数（数值越小优先级越高）"""
        # 基础优先级
        base_priority = -task.priority.value

        # 等待时间因素（防止饥饿）
        wait_time = time.time() - task.created_at
        wait_bonus = -min(wait_time / 60, 5)  # 最多加5分

        # 依赖任务调整
        if task.dependencies:
            # 有依赖的任务优先级适当降低
            dep_penalty = len(task.dependencies) * 0.5
        else:
            dep_penalty = 0

        return base_priority + wait_bonus + dep_penalty

    async def run(self):
        """主调度循环"""
        workers = [asyncio.create_task(self._worker())
                  for _ in range(self.max_workers)]

        try:
            await asyncio.gather(*workers)
        except asyncio.CancelledError:
            logger.info("调度器收到取消信号")
        finally:
            await self._shutdown_gracefully()

    async def _worker(self):
        """工作线程"""
        while not self._shutdown:
            try:
                # 获取任务
                _, task_id = await asyncio.wait_for(
                    self.queue.get(), timeout=1.0
                )

                task = self.tasks.get(task_id)
                if not task or task.status != TaskStatus.PENDING:
                    continue

                # 检查依赖
                if not self._check_dependencies(task):
                    # 依赖未满足，重新放入队列
                    await self.queue.put((float('inf'), task_id))
                    continue

                # 执行任务
                await self._execute_task(task)

            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"工作线程错误: {e}")

    def _check_dependencies(self, task: Task) -> bool:
        """检查任务依赖是否满足"""
        for dep_id in task.dependencies:
            dep_task = self.tasks.get(dep_id)
            if not dep_task or dep_task.status != TaskStatus.COMPLETED:
                return False
        return True

    async def _execute_task(self, task: Task):
        """执行单个任务"""
        task.status = TaskStatus.RUNNING
        task.started_at = time.time()
        self.running.add(task.id)

        try:
            # 执行任务函数
            if asyncio.iscoroutinefunction(task.func):
                result = await task.func(*task.args, **task.kwargs)
            else:
                result = await asyncio.to_thread(
                    task.func, *task.args, **task.kwargs
                )

            task.result = result
            task.status = TaskStatus.COMPLETED
            logger.info(f"任务 {task.id} 成功完成")

        except Exception as e:
            task.error = str(e)
            logger.error(f"任务 {task.id} 失败: {e}")

            # 重试逻辑
            if task.retry_count < task.max_retries:
                task.retry_count += 1
                task.status = TaskStatus.PENDING
                retry_delay = self._calculate_retry_delay(task.retry_count)
                logger.info(f"任务 {task.id} 将在 {retry_delay}s 后重试")
                await asyncio.sleep(retry_delay)
                await self.submit(task)
            else:
                task.status = TaskStatus.FAILED

        finally:
            task.completed_at = time.time()
            self.running.discard(task.id)

    def _calculate_retry_delay(self, retry_count: int) -> float:
        """计算重试延迟（指数退避）"""
        base_delay = self.retry_policy.get("initial_delay", 1.0)
        max_delay = self.retry_policy.get("max_delay", 60.0)
        delay = base_delay * (2 ** (retry_count - 1))
        return min(delay, max_delay)

    async def _shutdown_gracefully(self):
        """优雅关闭"""
        logger.info("开始优雅关闭...")
        self._shutdown = True

        # 等待运行中的任务完成
        if self.running:
            logger.info(f"等待 {len(self.running)} 个运行中任务完成...")
            # 实际实现中应该设置超时

        logger.info("调度器已关闭")


# ============================================================================
# 智能体工厂
# ============================================================================

class AgentFactory:
    """智能体工厂，根据配置创建工作流模式实例"""

    @staticmethod
    def create_workflow(config: Dict[str, Any], pattern_type: str) -> WorkflowPattern:
        """根据类型创建工作流模式"""

        if pattern_type == "prompt_chaining":
            return PromptChaining(
                steps=config.get("steps", []),
                gating_threshold=config.get("gating_threshold", 0.8)
            )

        elif pattern_type == "routing":
            return Routing(
                classifier=config.get("classifier"),
                routes=config.get("routes", {})
            )

        elif pattern_type == "parallelization":
            return Parallelization(
                tasks=config.get("tasks", []),
                aggregator=config.get("aggregator"),
                max_workers=config.get("max_workers", 10)
            )

        elif pattern_type == "orchestrator_workers":
            return OrchestratorWorkers(
                orchestrator=config.get("orchestrator"),
                workers=config.get("workers", {}),
                max_rounds=config.get("max_rounds", 10)
            )

        elif pattern_type == "evaluator_optimizer":
            return EvaluatorOptimizer(
                generator=config.get("generator"),
                evaluator=config.get("evaluator"),
                max_iterations=config.get("max_iterations", 5),
                improvement_threshold=config.get("improvement_threshold", 0.05)
            )

        else:
            raise ValueError(f"未知的工作流模式: {pattern_type}")


# ============================================================================
# 使用示例
# ============================================================================

async def example_usage():
    """使用示例"""

    # 1. 创建调度器
    scheduler_config = {
        "max_workers": 5,
        "retry_policy": {
            "max_retries": 3,
            "initial_delay": 1.0,
            "max_delay": 60.0
        }
    }

    scheduler = TaskScheduler(scheduler_config)

    # 2. 定义任务函数
    def process_data(data: str) -> str:
        """示例数据处理函数"""
        time.sleep(1)  # 模拟处理时间
        return f"Processed: {data}"

    # 3. 创建并提交任务
    task = Task(
        id="task-001",
        name="数据处理任务",
        func=process_data,
        args=("raw data",),
        priority=Priority.HIGH,
        max_retries=2
    )

    task_id = await scheduler.submit(task)

    # 4. 启动调度器（在后台运行）
    scheduler_task = asyncio.create_task(scheduler.run())

    # 5. 等待任务完成
    await asyncio.sleep(5)

    # 查看任务状态
    completed_task = scheduler.tasks.get(task_id)
    if completed_task:
        logger.info(f"任务状态: {completed_task.status.value}")
        logger.info(f"任务结果: {completed_task.result}")

    # 6. 优雅关闭
    scheduler._shutdown = True
    await scheduler_task


if __name__ == "__main__":
    # 运行示例
    asyncio.run(example_usage())
