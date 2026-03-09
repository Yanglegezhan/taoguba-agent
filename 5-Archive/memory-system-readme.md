# 个人记忆系统

基于 PARA 方法（Project, Area, Resource, Archive）构建的知识管理系统。

## 目录结构

```
memory-system/
├── 0-System/          # 系统核心 - 状态和记忆
├── 1-Inbox/           # 收集箱 - 快速捕捉想法
├── 2-Projects/        # 项目 - 正在进行的项目
├── 3-Thinking/        # 认知沉淀 - 深度思考
├── 4-Assets/          # 可复用资产
├── 5-Archive/         # 归档 - 历史记录
├── .claude/           # Claude 配置
│   └── settings.local.json
└── CLAUDE.md          # AI 助手配置文件
```

## 快速开始

### 1. 配置基本信息

编辑 `CLAUDE.md`，设置你的名字和偏好。

### 2. 更新当前状态

编辑 `0-System/status.md`，填写你当前的状态和今日焦点。

### 3. 开始使用

每次对话时，Claude 会自动读取你的状态，了解你的上下文。

## 记忆流转流程

```
想法产生 → 1-Inbox (收集) → 2-Projects (执行) → 5-Archive (归档)
                ↓
         3-Thinking (认知沉淀) ← 4-Assets (可复用资产)
```

## 使用建议

### 每日
- 更新 `0-System/status.md` 的今日焦点
- 查看 `2-Projects/` 中项目的下一步行动

### 每周
- 把 `status.md` 的关键信息追加到 `context.md`
- 整理 `1-Inbox/`，清空或归档
- 回顾本周进展，更新项目状态

### 每月
- 复盘本月，归档已完成的项目到 `5-Archive/`
- 更新 `3-Thinking/` 中的认知沉淀

## 更多

- 详细配置说明：查看 `CLAUDE.md`
- 目录详细说明：查看各目录下的 `README.md`
