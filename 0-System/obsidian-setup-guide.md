# Claude Code + Obsidian 第二大脑配置

> 基于 Noah Brier 的工作流，将 Claude Code 与 Obsidian 集成，打造 AI 驱动的第二大脑。

---

## 核心架构

```
┌─────────────┐     Tailscale VPN      ┌──────────────────┐
│   手机      │ ◄────────────────────► │   家中电脑       │
│  (Termius)  │                        │  ┌───────────┐   │
└─────────────┘                        │  │  Obsidian │   │
                                       │  │   金库    │   │
                                       │  └─────┬─────┘   │
                                       │        │         │
                                       │  ┌─────▼─────┐   │
                                       │  │Claude Code│   │
                                       │  │(第二大脑) │   │
                                       │  └───────────┘   │
                                       └──────────────────┘
```

---

## 目录结构

```
D:/pythonProject2/          # Obsidian 金库根目录
├── .obsidian/              # Obsidian 配置
├── .claude/                # Claude Code 配置
│   ├── skills/             # 自定义 Skills
│   └── hooks/              # 自定义 Hooks
├── 0-System/               # 系统核心
│   ├── about-me/           # 个人画像
│   ├── context.md          # 本周上下文
│   └── status.md           # 当前状态
├── 1-Inbox/                # 收集箱
├── 2-Projects/             # 进行中的项目
├── 3-Thinking/             # 认知沉淀
├── 4-Assets/               # 可复用资产
└── 5-Archive/              # 历史归档
```

---

## 快速开始

### 1. 在 Obsidian 中打开金库

1. 下载并安装 Obsidian: https://obsidian.md
2. 打开 Obsidian → "打开本地仓库"
3. 选择 `D:\pythonProject2` 文件夹

### 2. 配置 Git 同步

```bash
# 配置 Git 用户信息
git config user.name "你的名称"
git config user.email "你的邮箱"

# 首次提交
git add .
git commit -m "Initial commit: Obsidian vault setup"

# 可选：连接到远程仓库
git remote add origin <你的远程仓库URL>
git push -u origin main
```

### 3. 安装 Obsidian 插件

打开 Obsidian → 设置 → 第三方插件 → 浏览社区插件：
- **Obsidian Git**: 自动 Git 同步
- **Templater**: 模板系统
- **Dataview**: 数据查询

### 4. 配置 Obsidian Git 自动同步

在 Obsidian 中：
1. 安装并启用 "Obsidian Git" 插件
2. 设置 → Obsidian Git
3. 配置：
   - Auto backup: 开启
   - Auto backup interval: 10 分钟
   - Commit message: `vault backup: {{date}}`

---

## Claude Code 集成

### 启动 Claude Code

始终在 Obsidian 金库根目录启动 Claude Code：

```bash
cd D:\pythonProject2
claude
```

这样 Claude Code 可以访问你的全部笔记。

### 常用命令

```bash
# 搜索笔记
/搜索 关键词

# 基于笔记生成内容
根据 3-Thinking/中的笔记，写一篇关于 XXX 的文章

# 整理收集箱
整理 1-Inbox/ 中的内容，归档到相应位置

# 创建项目笔记
在 2-Projects/ 创建新项目 "XXX"
```

---

## 移动端接入 (Tailscale + Termius)

### Windows 配置

#### 1. 安装 Tailscale

1. 下载：https://tailscale.com/download
2. 安装并登录
3. 获取 Windows 设备的 Tailscale IP (例如: `100.x.x.x`)

#### 2. 配置 Windows SSH 服务器

```powershell
# 以管理员运行 PowerShell
Add-WindowsCapability -Online -Name OpenSSH.Server~~~~0.0.1.0

# 启动 SSH 服务
Start-Service sshd
Set-Service -Name sshd -StartupType 'Automatic'

# 配置防火墙
New-NetFirewallRule -Name 'OpenSSH-Server-In-TCP' -Enabled True -Direction Inbound -Protocol TCP -Action Allow -LocalPort 22
```

#### 3. 手机端配置

**安装 Termius:**
- iOS: App Store 搜索 "Termius"
- Android: Google Play 搜索 "Termius"

**配置 Termius:**
1. 打开 Termius → 添加主机
2. 设置：
   - 别名: Home PC
   - 主机地址: 你的 Tailscale IP (100.x.x.x)
   - 端口: 22
   - 用户名: 你的 Windows 用户名
   - 密码: 你的 Windows 密码
3. 先连接 Tailscale VPN，再连接 Termius

---

## 工作流示例

### 场景 1：在外记录想法

1. 手机上打开 Obsidian App（如有）或 Termius
2. 通过 Termius 连接到家中电脑
3. 运行 `claude` 启动 Claude Code
4. 说："在 1-Inbox/ 创建新笔记，记录：xxx 想法"
5. 回家后看到笔记已同步

### 场景 2：深度研究

1. 在 Obsidian 中收集相关笔记
2. 启动 Claude Code (从金库根目录)
3. 说："基于 3-Thinking/AI 研究/ 下的笔记，帮我分析当前 AI 趋势"
4. Claude Code 读取所有笔记，生成分析报告
5. 保存到 2-Projects/ 或 3-Thinking/

### 场景 3：整理笔记

1. 说："整理 1-Inbox/ 中的内容，按主题归档"
2. Claude Code 分析笔记内容
3. 移动到相应目录
4. 自动生成链接和索引

---

## 最佳实践

### 1. 笔记命名

- 使用英文或拼音文件名（避免特殊字符）
- 格式：`主题-子主题.md` 或 `YYYYMMDD-标题.md`
- 示例：`ai-research-claude.md`, `20260304-meeting-notes.md`

### 2. 元数据模板

每个笔记开头添加 YAML 元数据：

```yaml
---
title: 笔记标题
date: 2026-03-04
tags: [标签1, 标签2]
project: 所属项目
status: active  # active, archived, draft
---
```

### 3. 双向链接

使用 Obsidian 的 `[[笔记名]]` 语法建立链接：

```markdown
这个概念来自 [[第二大脑-概念]]。

相关笔记：
- [[PARA 方法]]
- [[Claude Code 使用技巧]]
```

### 4. 每日笔记

在 `0-System/daily/` 创建每日笔记模板：

```markdown
# {{date}}

## 今日待办
- [ ]

## 记录

## 想法

## 回顾
```

---

## 故障排除

### Git 同步失败

```bash
# 查看状态
git status

# 解决冲突
git pull --rebase
git push
```

### Tailscale 连接不上

1. 确保两台设备都登录同一 Tailscale 账号
2. 检查 Windows 防火墙是否允许 Tailscale
3. 尝试 ping Tailscale IP: `ping 100.x.x.x`

### Obsidian 插件不工作

1. 检查 Obsidian 版本是否最新
2. 重新安装插件
3. 查看控制台错误 (Ctrl+Shift+I)

---

## 进阶配置

### 自定义 Claude Skills

在 `.claude/skills/` 目录创建自定义技能：

**obsidian-note.md:**
```markdown
---
name: obsidian-note
description: 创建结构化的 Obsidian 笔记
---

根据用户输入创建标准格式的 Obsidian 笔记。

1. 添加 YAML 元数据
2. 使用标准模板结构
3. 自动创建双向链接
```

### 自动化脚本

创建 `.claude/hooks/` 目录，添加自定义 hooks：

**post-save.sh:**
```bash
#!/bin/bash
# 保存笔记后自动 Git 提交
cd "$(dirname "$0")/../.."
git add -A
git commit -m "Auto: $(date +%Y%m%d-%H%M%S)"
```

---

## 资源

- **Obsidian 官方**: https://obsidian.md
- **Obsidian 中文社区**: https://forum-zh.obsidian.md
- **Claude Code 文档**: https://docs.anthropic.com/claude-code
- **Tailscale**: https://tailscale.com
- **Noah Brier 原文**: https://www.youtube.com/watch?v=U5pC6Iph0xE
