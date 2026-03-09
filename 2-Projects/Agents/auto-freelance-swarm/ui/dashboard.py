"""
Streamlit 人工审核界面
提供可视化的任务管理和审核功能
"""

import os
import sys
import json
import asyncio
import logging
from pathlib import Path
from datetime import datetime

import streamlit as st
import requests
from typing import Dict, Any, List, Optional

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# API基础URL
API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000")


# 页面配置
st.set_page_config(
    page_title="Auto-Freelance Swarm",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)


def init_session_state():
    """初始化会话状态"""
    if "tasks" not in st.session_state:
        st.session_state.tasks = []
    
    if "current_project" not in st.session_state:
        st.session_state.current_project = None
    
    if "workflow_status" not in st.session_state:
        st.session_state.workflow_status = "idle"


def call_api(endpoint: str, method: str = "GET", data: dict = None) -> dict:
    """调用API"""
    url = f"{API_BASE_URL}{endpoint}"
    
    try:
        if method == "GET":
            response = requests.get(url, timeout=30)
        elif method == "POST":
            response = requests.post(url, json=data, timeout=60)
        elif method == "DELETE":
            response = requests.delete(url, timeout=10)
        else:
            return {"error": "不支持的HTTP方法"}
        
        return response.json()
    except requests.exceptions.ConnectionError:
        return {"error": "无法连接到API服务，请确保API服务正在运行"}
    except Exception as e:
        return {"error": str(e)}


def main():
    """主函数"""
    init_session_state()
    
    # 标题
    st.title("🤖 Auto-Freelance Swarm")
    st.markdown("### 多智能体副业协作系统")
    
    # 侧边栏
    with st.sidebar:
        st.header("系统状态")
        
        # API连接状态
        try:
            health = call_api("/health")
            if "error" not in health:
                st.success("✅ API服务正常运行")
            else:
                st.error(f"❌ {health['error']}")
        except:
            st.error("❌ 无法连接到API服务")
        
        st.divider()
        
        # 功能导航
        st.subheader("功能导航")
        page = st.radio(
            "选择功能",
            ["项目发现", "项目分析", "代码生成", "代码审查", "项目验收", "任务管理"]
        )
        
        st.divider()
        
        # 设置
        st.subheader("设置")
        api_url = st.text_input("API地址", value=API_BASE_URL)
        if api_url != API_BASE_URL:
            st.warning("请重启应用以应用新设置")
    
    # 根据选择的页面显示内容
    if page == "项目发现":
        show_project_discovery()
    elif page == "项目分析":
        show_project_analysis()
    elif page == "代码生成":
        show_code_generation()
    elif page == "代码审查":
        show_code_review()
    elif page == "项目验收":
        show_qa_check()
    elif page == "任务管理":
        show_task_management()


def show_project_discovery():
    """项目发现页面"""
    st.header("🔍 项目发现")
    st.markdown("扫描各大自由职业平台，发现潜在项目机会")
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        # 扫描按钮
        if st.button("🔄 扫描项目", type="primary"):
            with st.spinner("正在扫描平台..."):
                result = call_api("/projects/scan", method="POST")
                
                if "error" in result:
                    st.error(result["error"])
                else:
                    st.success(f"扫描完成，发现 {len(result.get('projects', []))} 个项目")
                    st.session_state.projects = result.get("projects", [])
    
    with col2:
        # 刷新按钮
        if st.button("↻ 刷新"):
            st.rerun()
    
    # 显示项目列表
    if "projects" in st.session_state and st.session_state.projects:
        st.subheader(f"推荐项目 ({len(st.session_state.projects)})")
        
        for i, project in enumerate(st.session_state.projects):
            with st.expander(f"{i+1}. {project.get('title', '未命名')} - 评分: {project.get('score', 0)}"):
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    st.markdown(f"**平台**: {project.get('platform', '未知')}")
                    st.markdown(f"**预算**: {project.get('budget', '未标注')}")
                    st.markdown(f"**描述**: {project.get('description', '无描述')[:200]}...")
                
                with col2:
                    if st.button(f"选择", key=f"select_{i}"):
                        st.session_state.current_project = project
                        st.success("已选择项目")
                        st.rerun()
    else:
        st.info("点击上方按钮扫描项目")


def show_project_analysis():
    """项目分析页面"""
    st.header("📊 项目分析")
    st.markdown("深入分析项目需求，生成详细规格说明书")
    
    # 检查是否有选中的项目
    if not st.session_state.get("current_project"):
        st.warning("请先在「项目发现」中选择一个项目")
        return
    
    project = st.session_state.current_project
    
    st.subheader("当前项目")
    st.info(f"**{project.get('title', '未命名')}**")
    
    # 分析按钮
    if st.button("📝 分析项目", type="primary"):
        with st.spinner("正在分析项目需求..."):
            result = call_api(
                f"/projects/{project.get('id', 'unknown')}/analyze",
                method="POST",
                data=project
            )
            
            if "error" in result:
                st.error(result["error"])
            else:
                st.success("分析完成！")
                st.session_state.analysis_report = result.get("analysis_report")
                st.session_state.extracted_info = result.get("extracted_info")
    
    # 显示分析报告
    if "analysis_report" in st.session_state:
        st.subheader("项目规格说明书")
        st.markdown(st.session_state.analysis_report)
        
        # 批准按钮
        col1, col2 = st.columns([1, 1])
        
        with col1:
            if st.button("✅ 批准并继续", type="primary"):
                st.session_state.workflow_status = "coder"
                st.success("已批准，进入代码生成阶段")
                st.rerun()
        
        with col2:
            if st.button("❌ 拒绝"):
                st.error("项目被拒绝")
                st.session_state.current_project = None
                st.rerun()


def show_code_generation():
    """代码生成页面"""
    st.header("⚙️ 代码生成")
    st.markdown("根据项目规格说明书生成代码")
    
    # 检查是否有分析报告
    if "analysis_report" not in st.session_state:
        st.warning("请先完成「项目分析」")
        return
    
    st.subheader("生成配置")
    
    project_name = st.text_input("项目名称", value="my_project")
    
    # 生成按钮
    if st.button("🚀 生成代码", type="primary"):
        with st.spinner("正在生成代码..."):
            result = call_api(
                "/projects/generate-code",
                method="POST",
                data={
                    "specs": st.session_state.analysis_report,
                    "project_name": project_name
                }
            )
            
            if "error" in result:
                st.error(result["error"])
            else:
                st.success("代码生成完成！")
                st.session_state.code_result = result
                st.session_state.project_path = result.get("project_path")
    
    # 显示生成结果
    if "code_result" in st.session_state:
        result = st.session_state.code_result
        
        st.subheader("生成结果")
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("生成文件数", result.get("files_created", 0))
        with col2:
            st.metric("项目路径", result.get("project_path", "N/A"))
        
        # 文件列表
        if result.get("files"):
            st.subheader("生成的文件")
            for f in result["files"]:
                st.write(f"- {f.get('name')} ({f.get('type')})")
        
        # 批准按钮
        col1, col2 = st.columns([1, 1])
        
        with col1:
            if st.button("✅ 批准并审查", type="primary"):
                st.session_state.workflow_status"
                st.success = "reviewer("已批准，进入代码审查阶段")
                st.rerun()
        
        with col2:
            if st.button("🔄 重新生成"):
                st.session_state.code_result = None
                st.rerun()


def show_code_review():
    """代码审查页面"""
    st.header("🔎 代码审查")
    st.markdown("审查生成的代码质量和安全性")
    
    # 检查是否有代码结果
    if "code_result" not in st.session_state:
        st.warning("请先完成「代码生成」")
        return
    
    # 审查按钮
    task_id = st.session_state.code_result.get("task_id", "unknown")
    
    if st.button("🔍 开始审查", type="primary"):
        with st.spinner("正在审查代码..."):
            result = call_api(f"/projects/{task_id}/review", method="POST")
            
            if "error" in result:
                st.error(result["error"])
            else:
                st.success("审查完成！")
                st.session_state.review_result = result
    
    # 显示审查结果
    if "review_result" in st.session_state:
        result = st.session_state.review_result
        
        st.subheader("审查结果")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("发现问题", result.get("total_issues", 0))
        with col2:
            st.metric("需要修复", "是" if result.get("needs_fix") else "否")
        with col3:
            st.metric("状态", "通过" if not result.get("needs_fix") else "需修复")
        
        # 审查报告
        if result.get("report"):
            st.subheader("详细报告")
            st.markdown(result["report"])
        
        # 操作按钮
        col1, col2 = st.columns([1, 1])
        
        with col1:
            if st.button("✅ 批准并验收", type="primary"):
                st.session_state.workflow_status = "qa"
                st.success("已批准，进入验收阶段")
                st.rerun()
        
        with col2:
            if result.get("needs_fix"):
                if st.button("🔧 修复问题"):
                    st.info("请根据审查报告手动修复问题")


def show_qa_check():
    """QA验收页面"""
    st.header("✅ 项目验收")
    st.markdown("最终验收检查，确保交付物符合要求")
    
    # 检查是否有审查结果
    if "review_result" not in st.session_state:
        st.warning("请先完成「代码审查」")
        return
    
    # 验收按钮
    task_id = st.session_state.code_result.get("task_id", "unknown")
    
    if st.button("🎯 开始验收", type="primary"):
        with st.spinner("正在进行验收检查..."):
            result = call_api(f"/projects/{task_id}/qa", method="POST")
            
            if "error" in result:
                st.error(result["error"])
            else:
                st.success("验收完成！")
                st.session_state.qa_result = result
    
    # 显示验收结果
    if "qa_result" in st.session_state:
        result = st.session_state.qa_result
        
        st.subheader("验收结果")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            passed = result.get("passed", False)
            st.metric("结果", "通过 ✅" if passed else "不通过 ❌")
        with col2:
            st.metric("检查通过", result.get("checks_passed", 0))
        with col3:
            st.metric("检查失败", result.get("checks_failed", 0))
        
        # 验收报告
        if result.get("report"):
            st.subheader("验收报告")
            st.markdown(result["report"])
        
        # 最终操作
        if result.get("passed"):
            st.balloons()
            st.success("🎉 恭喜！项目已通过所有验收检查！")
        else:
            st.error("项目未通过验收，请根据报告进行修复")


def show_task_management():
    """任务管理页面"""
    st.header("📋 任务管理")
    st.markdown("查看和管理所有任务")
    
    # 刷新按钮
    if st.button("↻ 刷新任务列表"):
        result = call_api("/tasks")
        
        if "error" not in result:
            st.session_state.tasks = result.get("tasks", [])
        else:
            st.error(result["error"])
    
    # 显示任务列表
    tasks = st.session_state.get("tasks", [])
    
    if tasks:
        st.subheader(f"任务列表 ({len(tasks)})")
        
        for task in tasks:
            with st.expander(f"{task.get('id', 'unknown')} - {task.get('status', 'unknown')}"):
                st.write(f"**当前步骤**: {task.get('current_step', 'N/A')}")
                st.write(f"**状态**: {task.get('status', 'N/A')}")
                st.write(f"**创建时间**: {task.get('created_at', 'N/A')}")
                
                if st.button(f"删除", key=f"delete_{task.get('id')}"):
                    call_api(f"/tasks/{task.get('id')}", method="DELETE")
                    st.success("任务已删除")
                    st.rerun()
    else:
        st.info("暂无任务")


if __name__ == "__main__":
    main()
