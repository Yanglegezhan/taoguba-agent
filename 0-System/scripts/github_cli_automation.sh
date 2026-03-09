#!/bin/bash
# GitHub CLI 自动化脚本
# 用于自动创建仓库、提交代码和创建 PR

set -e

# 颜色配置
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 日志函数
log() {
    local level=$1
    local message=$2
    local color=""
    case $level in
        "INFO")  color=$BLUE ;;
        "WARN")  color=$YELLOW ;;
        "ERROR") color=$RED ;;
        "SUCCESS") color=$GREEN ;;
    esac
    echo -e "${color}[$(date '+%H:%M:%S')] [$level] $message${NC}"
}

# 检查 GitHub CLI 是否安装
check_gh() {
    if ! command -v gh &> /dev/null; then
        log "ERROR" "GitHub CLI (gh) 未安装"
        echo "请安装 GitHub CLI:"
        echo "  Windows: winget install --id GitHub.cli"
        echo "  macOS: brew install gh"
        echo "  Linux: sudo apt install gh"
        exit 1
    fi
    log "SUCCESS" "GitHub CLI 已安装: $(gh --version | head -1)"
}

# 检查用户是否已登录
check_auth() {
    if ! gh auth status &> /dev/null; then
        log "WARN" "未登录 GitHub"
        echo "请运行: gh auth login"
        exit 1
    fi
    log "SUCCESS" "已登录 GitHub: $(gh api user -q .login)"
}

# 创建 GitHub 仓库
create_repo() {
    local repo_name=$1
    local visibility=${2:-"public"}
    local description=${3:-""}

    log "INFO" "创建仓库: $repo_name ($visibility)"

    if gh repo view "$repo_name" &> /dev/null; then
        log "WARN" "仓库已存在: $repo_name"
        return 0
    fi

    local flags="--$visibility"
    if [ -n "$description" ]; then
        flags="$flags --description \"$description\""
    fi

    if gh repo create "$repo_name" $flags --confirm; then
        log "SUCCESS" "仓库创建成功: https://github.com/$repo_name"
        return 0
    else
        log "ERROR" "仓库创建失败"
        return 1
    fi
}

# 推送本地代码到 GitHub
push_code() {
    local repo_name=$1
    local branch=${2:-"main"}

    log "INFO" "推送代码到 $repo_name:$branch"

    # 检查是否在 git 仓库中
    if ! git rev-parse --git-dir &> /dev/null; then
        log "ERROR" "当前目录不是 git 仓库"
        return 1
    fi

    # 添加远程仓库（如果不存在）
    if ! git remote get-url origin &> /dev/null; then
        git remote add origin "https://github.com/$repo_name.git"
        log "INFO" "添加远程仓库: origin"
    fi

    # 获取默认分支名
    local default_branch=$(git remote show origin | grep 'HEAD branch' | cut -d' ' -f5)
    if [ -z "$default_branch" ]; then
        default_branch="main"
    fi

    # 推送代码
    if git push -u origin "HEAD:$default_branch"; then
        log "SUCCESS" "代码推送成功"
        return 0
    else
        log "ERROR" "代码推送失败"
        return 1
    fi
}

# 自动提交并推送
auto_commit_push() {
    local message=$1
    local repo_name=$2

    log "INFO" "自动提交: $message"

    # 检查是否有变更
    if git diff --quiet && git diff --staged --quiet; then
        log "WARN" "没有变更需要提交"
        return 0
    fi

    # 添加所有变更
    git add -A
    log "INFO" "已暂存所有变更"

    # 提交
    if git commit -m "$message"; then
        log "SUCCESS" "提交成功: $message"
    else
        log "ERROR" "提交失败"
        return 1
    fi

    # 推送到远程（如果指定了仓库）
    if [ -n "$repo_name" ]; then
        push_code "$repo_name"
    fi

    return 0
}

# 创建 Pull Request
create_pr() {
    local title=$1
    local body=${2:-""}
    local base_branch=${3:-"main"}
    local head_branch=${4:-""}

    log "INFO" "创建 Pull Request: $title"

    # 如果没有指定 head 分支，使用当前分支
    if [ -z "$head_branch" ]; then
        head_branch=$(git branch --show-current)
    fi

    # 检查是否已有 PR
    local existing_pr=$(gh pr list --head "$head_branch" --json number -q '.[0].number')
    if [ -n "$existing_pr" ]; then
        log "WARN" "PR 已存在: #$existing_pr"
        return 0
    fi

    # 创建 PR
    local flags="--base $base_branch --head $head_branch"
    if [ -n "$body" ]; then
        flags="$flags --body \"$body\""
    else
        flags="$flags --fill"
    fi

    if gh pr create $flags --title "$title"; then
        log "SUCCESS" "PR 创建成功"
        return 0
    else
        log "ERROR" "PR 创建失败"
        return 1
    fi
}

# 查看 PR 状态
pr_status() {
    log "INFO" "查看 Pull Request 状态"
    gh pr list --state open
}

# 合并 PR
merge_pr() {
    local pr_number=$1
    local method=${2:-"squash"}  # squash, merge, rebase

    log "INFO" "合并 PR #$pr_number ($method)"

    if gh pr merge "$pr_number" --$method --auto; then
        log "SUCCESS" "PR #$pr_number 合并成功"
        return 0
    else
        log "ERROR" "PR #$pr_number 合并失败"
        return 1
    fi
}

# 查看当前仓库信息
repo_info() {
    log "INFO" "仓库信息"

    # 当前目录的 git 信息
    if git rev-parse --git-dir &> /dev/null; then
        echo "当前分支: $(git branch --show-current)"
        echo "远程仓库: $(git remote get-url origin 2>/dev/null || echo '未设置')"
        echo "最近提交: $(git log -1 --pretty=format:'%h - %s' 2>/dev/null || echo '无提交')"
    else
        echo "当前目录不是 git 仓库"
    fi

    # GitHub 登录信息
    echo ""
    echo "GitHub 账户: $(gh api user -q .login 2>/dev/null || echo '未登录')"
}

# 显示帮助信息
show_help() {
    cat << 'EOF'
GitHub CLI 自动化脚本

用法: ./github_cli_automation.sh [命令] [参数]

命令:
  check               检查 GitHub CLI 安装和登录状态
  repo-info           显示当前仓库信息
  create-repo <name> [visibility] [description]
                      创建 GitHub 仓库 (visibility: public|private)
  push <repo_name> [branch]
                      推送代码到 GitHub
  commit-push <message> [repo_name]
                      自动提交并推送
  create-pr <title> [body] [base] [head]
                      创建 Pull Request
  pr-status           查看 PR 状态
  merge-pr <number> [method]
                      合并 PR (method: squash|merge|rebase)
  help                显示此帮助信息

示例:
  # 检查环境
  ./github_cli_automation.sh check

  # 创建仓库并推送代码
  ./github_cli_automation.sh create-repo my-project public "我的项目"
  ./github_cli_automation.sh commit-push "初始提交" my-project

  # 创建 PR 并合并
  ./github_cli_automation.sh create-pr "添加新功能" "详细描述"
  ./github_cli_automation.sh merge-pr 1 squash

EOF
}

# 主函数
main() {
    local command=$1
    shift

    case $command in
        check)
            check_gh
            check_auth
            ;;
        repo-info)
            repo_info
            ;;
        create-repo)
            create_repo "$@"
            ;;
        push)
            push_code "$@"
            ;;
        commit-push)
            auto_commit_push "$@"
            ;;
        create-pr)
            create_pr "$@"
            ;;
        pr-status)
            pr_status
            ;;
        merge-pr)
            merge_pr "$@"
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            echo "未知命令: $command"
            echo "运行 './github_cli_automation.sh help' 查看帮助"
            exit 1
            ;;
    esac
}

# 如果是直接执行（不是被 source）
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    if [ $# -eq 0 ]; then
        show_help
    else
        main "$@"
    fi
fi
