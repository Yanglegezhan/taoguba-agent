# Auto-Freelance Swarm

🤖 多智能体副业协作系统

## 项目简介

Auto-Freelance Swarm 是一个基于大语言模型的多智能体协作系统，旨在帮助自由职业者自动化完成项目接单、分析、执行、审查和验收的完整流程。

## 系统架构

```
Agent 0 (Scout)     →  项目发现与接单
       ↓
Agent 1 (Analyst)   →  项目需求分析
       ↓
Agent 2 (Coder)     →  代码/内容生成
       ↓
Agent 3 (Reviewer)  →  代码质量审查
       ↓
Agent 4 (QA)        →  项目验收检查
       ↓
   人工审核          →  最终确认
```

## 快速开始

### 1. 环境准备

```bash
# 克隆项目
git clone <your-repo>
cd auto-freelance-swarm

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
# 复制配置模板
copy config\.env.example config\.env

# 编辑 .env 文件，填入您的API Key
# OPENAI_API_KEY=your-key-here
```

### 3. 运行演示

```bash
# 演示模式 - 展示完整工作流程
python main.py demo
```

### 4. 启动Web界面

```bash
# 启动API服务器
python main.py api

# 启动Streamlit界面 (新终端)
python main.py ui

# 或一键启动全部服务
python main.py all
```

然后访问 http://localhost:8501

## 功能说明

### Agent 0: Scout (项目发现)
- 监控多个自由职业平台
- 智能筛选高质量项目
- 评估项目接单价值

### Agent 1: Analyst (项目分析)
- 深入分析项目需求
- 生成结构化规格说明书
- 评估工作量和风险

### Agent 2: Coder (代码生成)
- 根据规格说明书生成代码
- 支持多种项目类型
- 自动创建项目结构

### Agent 3: Reviewer (代码审查)
- 静态代码分析
- 检查安全和质量问题
- 提供修复建议

### Agent 4: QA (验收检查)
- 验证功能完整性
- 检查AI生成痕迹
- 生成验收报告

## 配置说明

### 平台配置 (config/platforms.yaml)
支持配置多个接单平台：
- 程序员客栈
- 码市
- 猪八戒网
- 闲鱼
- Upwork (国际)
- Fiverr (国际)

### 智能体配置 (config/settings.yaml)
可自定义各智能体的模型、温度等参数。

## 合规与安全

⚠️ **重要提示**：

1. **账号安全**：请勿过度频繁操作，避免被平台封号
2. **自动提交**：默认关闭，建议手动确认后提交
3. **反爬策略**：已内置随机延迟和隐身模式
4. **代码安全**：所有文件操作限制在工作目录内

## 目录结构

```
auto-freelance-swarm/
├── config/              # 配置文件
│   ├── settings.yaml   # 全局配置
│   ├── platforms.yaml  # 平台配置
│   └── .env.example   # 环境变量模板
├── src/
│   ├── agents/        # 智能体实现
│   │   ├── scout_agent.py
│   │   ├── analyst_agent.py
│   │   ├── coder_agent.py
│   │   ├── reviewer_agent.py
│   │   └── qa_agent.py
│   ├── core/          # 核心逻辑
│   │   └── workflow.py
│   ├── tools/         # 工具模块
│   │   ├── file_ops.py
│   │   └── search_ops.py
│   └── api/           # API后端
│       └── main.py
├── ui/                 # Streamlit界面
│   └── dashboard.py
├── workspace/         # 工作空间
├── data/              # 数据存储
│   └── logs/
├── main.py            # 主入口
└── requirements.txt   # 依赖列表
```

## 技术栈

- **语言**: Python 3.10+
- **LLM**: OpenAI API / Anthropic API
- **编排**: LangGraph
- **后端**: FastAPI
- **界面**: Streamlit
- **数据库**: SQLite

## 许可证

MIT License
