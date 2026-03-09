"""
API后端模块
提供REST API接口供前端调用
"""

import os
import json
import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from contextlib import asynccontextmanager

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 全局变量
workflow = None
llm_provider = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    global workflow, llm_provider
    
    # 启动时初始化
    logger.info("正在初始化系统...")
    
    # 加载配置
    config = load_config()
    
    # 初始化LLM提供者
    llm_provider = init_llm_provider(config)
    
    # 初始化工作流
    workspace_path = config.get("workspace", {}).get("root", "./workspace")
    from src.core.workflow import FreelanceWorkflow
    workflow = FreelanceWorkflow(llm_provider, config, workspace_path)
    
    logger.info("系统初始化完成")
    
    yield
    
    # 关闭时清理
    logger.info("系统关闭")


def load_config() -> Dict[str, Any]:
    """加载配置"""
    config_path = Path(__file__).parent.parent.parent / "config" / "settings.yaml"
    
    if config_path.exists():
        import yaml
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    return {}


def init_llm_provider(config: Dict[str, Any]):
    """初始化LLM提供者"""
    from openai import AsyncOpenAI
    
    # 从环境变量获取API Key
    api_key = os.environ.get("OPENAI_API_KEY", "")
    
    if not api_key:
        logger.warning("未设置OPENAI_API_KEY")
        return None
    
    base_url = config.get("llm", {}).get("openai_base_url", "https://api.openai.com/v1")
    
    return AsyncOpenAI(api_key=api_key, base_url=base_url)


# 创建FastAPI应用
app = FastAPI(
    title="Auto-Freelance Swarm API",
    description="多智能体协作系统API",
    version="0.1.0",
    lifespan=lifespan
)


# 数据模型
class ProjectInfo(BaseModel):
    """项目信息"""
    title: str
    description: str
    budget: Optional[str] = None
    platform: Optional[str] = None


class ApprovalRequest(BaseModel):
    """审批请求"""
    project_id: str
    approved: bool
    feedback: Optional[str] = None


class ProjectSpecs(BaseModel):
    """项目规格"""
    specs: str
    project_name: Optional[str] = None


# 存储当前任务状态
tasks: Dict[str, Dict[str, Any]] = {}


@app.get("/")
async def root():
    """根路径"""
    return {
        "message": "Auto-Freelance Swarm API",
        "version": "0.1.0",
        "status": "running"
    }


@app.get("/health")
async def health():
    """健康检查"""
    return {"status": "healthy"}


@app.post("/projects/scan")
async def scan_projects():
    """扫描项目"""
    global tasks
    
    try:
        # 创建任务
        task_id = f"task_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        tasks[task_id] = {
            "id": task_id,
            "status": "running",
            "current_step": "scout",
            "created_at": datetime.now().isoformat()
        }
        
        # 运行Scout
        if workflow:
            result = await workflow.agents["scout"].execute("all")
            
            tasks[task_id]["status"] = "completed"
            tasks[task_id]["projects"] = result.get("projects", [])
            tasks[task_id]["scout_result"] = result
            
            return {
                "task_id": task_id,
                "status": "completed",
                "projects": result.get("projects", [])[:10]
            }
        
        raise HTTPException(status_code=500, detail="工作流未初始化")
    
    except Exception as e:
        logger.error(f"扫描项目失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/projects/{project_id}/analyze")
async def analyze_project(project_id: str, project_info: ProjectInfo):
    """分析项目"""
    global tasks
    
    try:
        task_id = f"task_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        tasks[task_id] = {
            "id": task_id,
            "project_id": project_id,
            "status": "running",
            "current_step": "analyst",
            "project_info": project_info.dict(),
            "created_at": datetime.now().isoformat()
        }
        
        # 运行Analyst
        if workflow:
            result = await workflow.agents["analyst"].execute(
                project_info.dict()
            )
            
            tasks[task_id]["status"] = "completed"
            tasks[task_id]["analysis_report"] = result.get("analysis_report")
            tasks[task_id]["extracted_info"] = result.get("extracted_info")
            
            return {
                "task_id": task_id,
                "status": "completed",
                "analysis_report": result.get("analysis_report"),
                "extracted_info": result.get("extracted_info")
            }
        
        raise HTTPException(status_code=500, detail="工作流未初始化")
    
    except Exception as e:
        logger.error(f"分析项目失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/projects/generate-code")
async def generate_code(specs: ProjectSpecs):
    """生成代码"""
    global tasks
    
    try:
        task_id = f"task_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        project_name = specs.project_name or f"project_{task_id}"
        
        tasks[task_id] = {
            "id": task_id,
            "status": "running",
            "current_step": "coder",
            "project_name": project_name,
            "created_at": datetime.now().isoformat()
        }
        
        # 运行Coder
        if workflow:
            result = await workflow.agents["coder"].execute({
                "specs": specs.specs,
                "project_name": project_name
            })
            
            tasks[task_id]["status"] = "completed"
            tasks[task_id]["project_path"] = result.get("project_path")
            tasks[task_id]["files"] = result.get("files", [])
            
            return {
                "task_id": task_id,
                "status": "completed",
                "project_path": result.get("project_path"),
                "files": result.get("files", [])
            }
        
        raise HTTPException(status_code=500, detail="工作流未初始化")
    
    except Exception as e:
        logger.error(f"生成代码失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/projects/{task_id}/review")
async def review_code(task_id: str):
    """审查代码"""
    global tasks
    
    try:
        task = tasks.get(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")
        
        project_path = task.get("project_path")
        if not project_path:
            raise HTTPException(status_code=400, detail="未生成代码")
        
        # 运行Reviewer
        if workflow:
            result = await workflow.agents["reviewer"].execute({
                "project_path": project_path,
                "files": task.get("files", [])
            })
            
            task["review_result"] = result
            task["status"] = "completed"
            
            return {
                "task_id": task_id,
                "status": "completed",
                "total_issues": result.get("total_issues", 0),
                "needs_fix": result.get("needs_fix", False),
                "report": result.get("report")
            }
        
        raise HTTPException(status_code=500, detail="工作流未初始化")
    
    except Exception as e:
        logger.error(f"审查代码失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/projects/{task_id}/qa")
async def qa_check(task_id: str):
    """QA验收"""
    global tasks
    
    try:
        task = tasks.get(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")
        
        project_path = task.get("project_path")
        specs = task.get("analysis_report", "")
        
        if not project_path:
            raise HTTPException(status_code=400, detail="未生成代码")
        
        # 运行QA
        if workflow:
            result = await workflow.agents["qa"].execute({
                "project_path": project_path,
                "specs": specs,
                "files": task.get("files", [])
            })
            
            task["qa_result"] = result
            task["status"] = "completed"
            
            return {
                "task_id": task_id,
                "status": "completed",
                "passed": result.get("passed", False),
                "checks_passed": result.get("checks_passed", 0),
                "checks_failed": result.get("checks_failed", 0),
                "report": result.get("report")
            }
        
        raise HTTPException(status_code=500, detail="工作流未初始化")
    
    except Exception as e:
        logger.error(f"QA检查失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/tasks")
async def list_tasks():
    """列出所有任务"""
    return {"tasks": list(tasks.values())}


@app.get("/tasks/{task_id}")
async def get_task(task_id: str):
    """获取任务详情"""
    task = tasks.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    return task


@app.delete("/tasks/{task_id}")
async def delete_task(task_id: str):
    """删除任务"""
    if task_id in tasks:
        del tasks[task_id]
        return {"status": "deleted"}
    raise HTTPException(status_code=404, detail="任务不存在")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
