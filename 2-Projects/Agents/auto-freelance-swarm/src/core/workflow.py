"""
核心工作流模块
使用LangGraph实现多智能体协作流程
"""

import os
import asyncio
import logging
from typing import Dict, Any, List, Optional, TypedDict
from datetime import datetime
from pathlib import Path
from enum import Enum

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.sqlite import SqliteSaver

from ..agents import (
    ScoutAgent,
    AnalystAgent,
    CoderAgent,
    ReviewerAgent,
    QAAgent
)

logger = logging.getLogger(__name__)


class WorkflowState(TypedDict):
    """工作流状态定义"""
    # 项目信息
    project_id: str
    project_name: str
    project_path: str
    
    # Scout阶段
    scout_result: Optional[Dict]
    selected_project: Optional[Dict]
    bid_content: Optional[str]
    bid_approved: bool
    
    # Analyst阶段
    analysis_report: Optional[str]
    project_specs: Optional[Dict]
    analysis_approved: bool
    
    # Coder阶段
    code_result: Optional[Dict]
    code_files: Optional[List]
    code_approved: bool
    
    # Reviewer阶段
    review_result: Optional[Dict]
    review_approved: bool
    revision_count: int
    
    # QA阶段
    qa_result: Optional[Dict]
    final_approved: bool
    
    # 状态
    current_step: str
    status: str  # pending, running, waiting_approval, completed, failed
    error: Optional[str]
    
    # 时间戳
    created_at: str
    updated_at: str


class WorkflowStatus(str, Enum):
    """工作流状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    WAITING_APPROVAL = "waiting_approval"
    COMPLETED = "completed"
    FAILED = "failed"


class FreelanceWorkflow:
    """
    自由职业多智能体工作流
    
    完整流程:
    1. Scout: 发现项目 -> 用户确认
    2. Analyst: 分析需求 -> 用户确认
    3. Coder: 生成代码 -> 用户确认
    4. Reviewer: 审查代码 -> 循环修复
    5. QA: 验收检查 -> 用户最终确认
    """
    
    def __init__(
        self,
        llm_provider,
        config: Dict[str, Any],
        workspace_path: str = "./workspace"
    ):
        self.llm_provider = llm_provider
        self.config = config
        self.workspace_path = Path(workspace_path)
        
        # 初始化智能体
        self.agents = {
            "scout": ScoutAgent(
                config.get("agents", {}).get("scout", {}),
                llm_provider
            ),
            "analyst": AnalystAgent(
                config.get("agents", {}).get("analyst", {}),
                llm_provider
            ),
            "coder": CoderAgent(
                config.get("agents", {}).get("coder", {}),
                llm_provider,
                str(workspace_path)
            ),
            "reviewer": ReviewerAgent(
                config.get("agents", {}).get("reviewer", {}),
                llm_provider
            ),
            "qa": QAAgent(
                config.get("agents", {}).get("qa", {}),
                llm_provider
            )
        }
        
        # 创建工作流图
        self.graph = self._build_graph()
        
        # 检查点保存器
        self.checkpointer = SqliteSaver.from_conn_string(":memory:")
        
        logger.info("工作流初始化完成")
    
    def _build_graph(self) -> StateGraph:
        """构建工作流图"""
        
        workflow = StateGraph(WorkflowState)
        
        # 添加节点
        workflow.add_node("scout", self._scout_node)
        workflow.add_node("analyst", self._analyst_node)
        workflow.add_node("coder", self._coder_node)
        workflow.add_node("reviewer", self._reviewer_node)
        workflow.add_node("qa", self._qa_node)
        
        # 添加边
        workflow.set_entry_point("scout")
        
        # Scout -> Analyst (需要用户确认)
        workflow.add_edge("scout", "analyst")
        
        # Analyst -> Coder (需要用户确认)
        workflow.add_edge("analyst", "coder")
        
        # Coder -> Reviewer
        workflow.add_edge("coder", "reviewer")
        
        # Reviewer -> Coder (如果需要修复) 或 QA
        workflow.add_conditional_edges(
            "reviewer",
            self._should_fix_code,
            {
                "fix": "coder",
                "qa": "qa"
            }
        )
        
        # QA -> 结束
        workflow.add_edge("qa", END)
        
        return workflow.compile()
    
    async def _scout_node(self, state: WorkflowState) -> WorkflowState:
        """Scout节点: 发现项目"""
        logger.info("执行 Scout 节点")
        
        try:
            # 调用Scout Agent
            result = await self.agents["scout"].execute(
                input_data="all",
                context={"config": self.config}
            )
            
            state["scout_result"] = result
            state["selected_project"] = result.get("projects", [{}])[0] if result.get("projects") else None
            state["status"] = WorkflowStatus.WAITING_APPROVAL.value
            state["current_step"] = "scout"
            state["updated_at"] = datetime.now().isoformat()
            
        except Exception as e:
            logger.error(f"Scout节点执行失败: {e}")
            state["status"] = WorkflowStatus.FAILED.value
            state["error"] = str(e)
        
        return state
    
    async def _analyst_node(self, state: WorkflowState) -> WorkflowState:
        """Analyst节点: 分析项目需求"""
        logger.info("执行 Analyst 节点")
        
        try:
            project_info = state.get("selected_project", {})
            
            # 调用Analyst Agent
            result = await self.agents["analyst"].execute(
                input_data=project_info,
                context={"config": self.config}
            )
            
            state["analysis_report"] = result.get("analysis_report")
            state["project_specs"] = result.get("extracted_info")
            state["status"] = WorkflowStatus.WAITING_APPROVAL.value
            state["current_step"] = "analyst"
            state["updated_at"] = datetime.now().isoformat()
            
        except Exception as e:
            logger.error(f"Analyst节点执行失败: {e}")
            state["status"] = WorkflowStatus.FAILED.value
            state["error"] = str(e)
        
        return state
    
    async def _coder_node(self, state: WorkflowState) -> WorkflowState:
        """Coder节点: 生成代码"""
        logger.info("执行 Coder 节点")
        
        try:
            specs = state.get("analysis_report", "")
            project_name = f"project_{state.get('project_id', datetime.now().strftime('%Y%m%d%H%M%S'))}"
            
            # 调用Coder Agent
            result = await self.agents["coder"].execute(
                input_data={
                    "specs": specs,
                    "project_name": project_name
                },
                context={"config": self.config}
            )
            
            state["code_result"] = result
            state["project_path"] = result.get("project_path")
            state["code_files"] = result.get("files", [])
            state["status"] = WorkflowStatus.WAITING_APPROVAL.value
            state["current_step"] = "coder"
            state["updated_at"] = datetime.now().isoformat()
            
        except Exception as e:
            logger.error(f"Coder节点执行失败: {e}")
            state["status"] = WorkflowStatus.FAILED.value
            state["error"] = str(e)
        
        return state
    
    async def _reviewer_node(self, state: WorkflowState) -> WorkflowState:
        """Reviewer节点: 审查代码"""
        logger.info("执行 Reviewer 节点")
        
        try:
project_path = state.get("project_path", "")
            
            # 调用Reviewer Agent
            result = await self.agents["reviewer"].execute(
                input_data={
                    "project_path": project_path,
                    "files": state.get("code_files", [])
                },
                context={"config": self.config}
            )
            
            state["review_result"] = result
            state["revision_count"] = state.get("revision_count", 0) + 1
            
            # 检查是否需要修复
            if result.get("needs_fix"):
                state["status"] = WorkflowStatus.WAITING_APPROVAL.value
            else:
                state["status"] = WorkflowStatus.RUNNING.value
            
            state["current_step"] = "reviewer"
            state["updated_at"] = datetime.now().isoformat()
            
        except Exception as e:
            logger.error(f"Reviewer节点执行失败: {e}")
            state["status"] = WorkflowStatus.FAILED.value
            state["error"] = str(e)
        
        return state
    
    async def _qa_node(self, state: WorkflowState) -> WorkflowState:
        """QA节点: 验收检查"""
        logger.info("执行 QA 节点")
        
        try:
            project_path = state.get("project_path", "")
            specs = state.get("analysis_report", "")
            
            # 调用QA Agent
            result = await self.agents["qa"].execute(
                input_data={
                    "specs": specs,
                    "project_path": project_path,
                    "files": state.get("code_files", [])
                },
                context={"config": self.config}
            )
            
            state["qa_result"] = result
            
            if result.get("passed"):
                state["status"] = WorkflowStatus.WAITING_APPROVAL.value
            else:
                state["status"] = WorkflowStatus.FAILED.value
            
            state["current_step"] = "qa"
            state["updated_at"] = datetime.now().isoformat()
            
        except Exception as e:
            logger.error(f"QA节点执行失败: {e}")
            state["status"] = WorkflowStatus.FAILED.value
            state["error"] = str(e)
        
        return state
    
    def _should_fix_code(self, state: WorkflowState) -> str:
        """判断是否需要修复代码"""
        
        review_result = state.get("review_result", {})
        
        # 如果需要修复且修复次数少于3次，返回fix
        if review_result.get("needs_fix") and state.get("revision_count", 0) < 3:
            return "fix"
        
        # 否则进入QA
        return "qa"
    
    async def run_scout(self, state: WorkflowState) -> WorkflowState:
        """运行Scout阶段"""
        return await self._scout_node(state)
    
    async def run_analyst(self, state: WorkflowState) -> WorkflowState:
        """运行Analyst阶段"""
        return await self._analyst_node(state)
    
    async def run_coder(self, state: WorkflowState) -> WorkflowState:
        """运行Coder阶段"""
        return await self._coder_node(state)
    
    async def run_reviewer(self, state: WorkflowState) -> WorkflowState:
        """运行Reviewer阶段"""
        return await self._reviewer_node(state)
    
    async def run_qa(self, state: WorkflowState) -> WorkflowState:
        """运行QA阶段"""
        return await self._qa_node(state)
    
    def approve_step(self, state: WorkflowState, approved: bool) -> WorkflowState:
        """批准步骤"""
        
        state["updated_at"] = datetime.now().isoformat()
        
        if approved:
            state["status"] = WorkflowStatus.RUNNING.value
            
            # 根据当前步骤设置下一个步骤的批准状态
            if state["current_step"] == "scout":
                state["bid_approved"] = True
            elif state["current_step"] == "analyst":
                state["analysis_approved"] = True
            elif state["current_step"] == "coder":
                state["code_approved"] = True
            elif state["current_step"] == "reviewer":
                state["review_approved"] = True
            elif state["current_step"] == "qa":
                state["final_approved"] = True
        else:
            # 拒绝
            state["status"] = WorkflowStatus.FAILED.value
            state["error"] = "用户拒绝"
        
        return state
    
    def get_next_step(self, current_step: str) -> Optional[str]:
        """获取下一步"""
        
        steps = {
            "scout": "analyst",
            "analyst": "coder",
            "coder": "reviewer",
            "reviewer": "qa",
            "qa": None
        }
        
        return steps.get(current_step)


async def run_workflow_demo(llm_provider, config: Dict[str, Any]):
    """
    运行工作流演示
    
    这是一个简化的演示，展示如何手动运行各个阶段
    """
    workspace_path = "./workspace"
    
    # 创建智能体
    scout = ScoutAgent(config.get("agents", {}).get("scout", {}), llm_provider)
    analyst = AnalystAgent(config.get("agents", {}).get("analyst", {}), llm_provider)
    coder = CoderAgent(config.get("agents", {}).get("coder", {}), llm_provider, workspace_path)
    reviewer = ReviewerAgent(config.get("agents", {}).get("reviewer", {}), llm_provider)
    qa = QAAgent(config.get("agents", {}).get("qa", {}), llm_provider)
    
    print("=" * 50)
    print("开始工作流演示")
    print("=" * 50)
    
    # 阶段1: Scout
    print("\n[阶段1] Scout - 发现项目")
    print("-" * 30)
    scout_result = await scout.execute("all")
    print(f"发现项目数: {scout_result.get('projects_matched', 0)}")
    
    if scout_result.get("projects"):
        selected = scout_result["projects"][0]
        print(f"推荐项目: {selected.get('title')}")
        print(f"预算: {selected.get('budget')}")
        print(f"评分: {selected.get('score')}")
    
    # 模拟用户确认
    print("\n请确认是否接单 (y/n): ", end="")
    # 假设确认
    confirmed = True
    
    if confirmed:
        # 阶段2: Analyst
        print("\n[阶段2] Analyst - 分析项目")
        print("-" * 30)
        analysis = await analyst.execute(selected if selected else {"title": "测试项目", "description": "这是一个测试项目"})
        print(f"分析报告长度: {len(analysis.get('analysis_report', ''))} 字符")
        print("分析完成!")
        
        # 阶段3: Coder
        print("\n[阶段3] Coder - 生成代码")
        print("-" * 30)
        code_result = await coder.execute({
            "specs": analysis.get("analysis_report", "这是一个测试项目"),
            "project_name": "demo_project"
        })
        print(f"生成文件数: {code_result.get('files_created', 0)}")
        print(f"项目路径: {code_result.get('project_path')}")
        
        # 阶段4: Reviewer
        print("\n[阶段4] Reviewer - 审查代码")
        print("-" * 30)
        review = await reviewer.execute({
            "project_path": code_result.get("project_path"),
            "files": code_result.get("files", [])
        })
        print(f"审查文件数: {review.get('files_reviewed', 0)}")
        print(f"发现问题数: {review.get('total_issues', 0)}")
        print(f"代码评分: {review.get('file_reviews', [{}])[0].get('lines', 0)} 行")
        
        # 阶段5: QA
        print("\n[阶段5] QA - 验收检查")
        print("-" * 30)
        qa_result = await qa.execute({
            "specs": analysis.get("analysis_report"),
            "project_path": code_result.get("project_path"),
            "files": code_result.get("files", [])
        })
        print(f"验收结果: {'通过' if qa_result.get('passed') else '不通过'}")
        print(f"检查通过: {qa_result.get('checks_passed', 0)}/{len(qa_result.get('checks', []))}")
    
    print("\n" + "=" * 50)
    print("工作流演示完成")
    print("=" * 50)
