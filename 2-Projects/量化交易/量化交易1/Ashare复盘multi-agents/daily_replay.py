"""
每日复盘整合脚本

功能：
1. 运行大盘分析Agent
2. 运行情绪分析Agent
3. 整合结果存入Obsidian
4. 推送到飞书
"""

import subprocess
import sys
import json
import httpx
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional
import io
import os
import re

# 强制使用 UTF-8 编码
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# 配置
BASE_DIR = Path(__file__).parent.parent.parent  # D:\pythonProject2
INDEX_AGENT_DIR = BASE_DIR / "量化交易1/Ashare复盘multi-agents/index_replay_agent"
SENTIMENT_AGENT_DIR = BASE_DIR / "量化交易1/Ashare复盘multi-agents/sentiment_replay_agent"
OBSIDIAN_ARCHIVE = BASE_DIR / "第二大脑/1-日记/每日复盘"

FEISHU_WEBHOOK = os.environ.get("FEISHU_WEBHOOK", "https://open.feishu.cn/open-apis/bot/v2/hook/1690b295-e029-4752-ba3b-cbd3013ded56")
FEISHU_APP_ID = os.environ.get("FEISHU_APP_ID", "cli_a92d4c6f20b8dcba")
FEISHU_APP_SECRET = os.environ.get("FEISHU_APP_SECRET", "pLWa0fVSBTK56l3X4m94MbdKfjfjCIKI")

FEISHU_MSG_LIMIT = 30000
_token_cache = {"token": None, "expire_time": None}


def run_index_analysis() -> dict:
    """运行大盘分析"""
    print(f"[{datetime.now()}] 开始运行大盘分析...")

    cmd = [sys.executable, "daily_task.py"]
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"

    try:
        result = subprocess.run(
            cmd, cwd=INDEX_AGENT_DIR, capture_output=True, text=True,
            timeout=400, encoding='utf-8', errors='replace', env=env
        )

        # 查找生成的文件
        output_dir = INDEX_AGENT_DIR / "output"
        json_files = list(output_dir.glob("*.json"))
        md_files = list(output_dir.glob("*.md"))
        chart_files = list(output_dir.glob("*.png"))

        json_file = max(json_files, key=lambda f: f.stat().st_mtime) if json_files else None
        md_file = max(md_files, key=lambda f: f.stat().st_mtime) if md_files else None
        chart_file = max(chart_files, key=lambda f: f.stat().st_mtime) if chart_files else None

        print(f"[{datetime.now()}] 大盘分析完成")
        return {
            "success": json_file is not None,
            "json_file": str(json_file) if json_file else None,
            "md_file": str(md_file) if md_file else None,
            "chart_file": str(chart_file) if chart_file else None
        }
    except Exception as e:
        print(f"大盘分析失败: {e}")
        return {"success": False, "error": str(e)}


def run_sentiment_analysis() -> dict:
    """运行情绪分析"""
    print(f"[{datetime.now()}] 开始运行情绪分析...")

    cmd = [sys.executable, "daily_task.py"]
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"

    try:
        result = subprocess.run(
            cmd, cwd=SENTIMENT_AGENT_DIR, capture_output=True, text=True,
            timeout=400, encoding='utf-8', errors='replace', env=env
        )

        output_dir = SENTIMENT_AGENT_DIR / "output/sentiment"
        md_files = list((output_dir / "reports").glob("*.md")) if (output_dir / "reports").exists() else []
        chart_files = list((output_dir / "charts").glob("*.png")) if (output_dir / "charts").exists() else []

        md_file = max(md_files, key=lambda f: f.stat().st_mtime) if md_files else None
        chart_file = max(chart_files, key=lambda f: f.stat().st_mtime) if chart_files else None

        print(f"[{datetime.now()}] 情绪分析完成")
        return {
            "success": md_file is not None,
            "md_file": str(md_file) if md_file else None,
            "chart_file": str(chart_file) if chart_file else None
        }
    except Exception as e:
        print(f"情绪分析失败: {e}")
        return {"success": False, "error": str(e)}


def load_json_report(json_file: str) -> Optional[dict]:
    """加载JSON报告"""
    try:
        with open(json_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"加载JSON失败: {e}")
        return None


def load_markdown(md_file: str, remove_images: bool = False) -> Optional[str]:
    """加载Markdown报告"""
    try:
        with open(md_file, "r", encoding="utf-8") as f:
            content = f.read()
        if remove_images:
            content = re.sub(r'!\[.*?\]\(.*?\)', '', content)
            content = re.sub(r'\n{3,}', '\n\n', content)
        return content.strip()
    except Exception as e:
        print(f"加载Markdown失败: {e}")
        return None


def create_obsidian_note(index_data: dict, sentiment_md: str, date_str: str) -> str:
    """创建Obsidian格式的整合笔记"""

    # 提取大盘分析关键信息
    current_price = index_data.get("current_price", 0)
    position = index_data.get("position_analysis", {}).get("position", "未知")
    short_term = index_data.get("short_term", {})
    long_term = index_data.get("long_term", {})
    key_support = index_data.get("key_support_today", {})
    key_resistance = index_data.get("key_resistance_today", {})

    note = f"""---
title: 每日复盘 - {date_str}
date: {date_str}
tags: [复盘, 大盘分析, 情绪分析]
project: 量化交易
status: completed
---

# 每日复盘 - {date_str}

## 一、大盘分析

### 核心指标

| 指标 | 值 |
|------|-----|
| 当前价格 | {current_price:.2f} |
| 位置判断 | {position} |
| 趋势方向 | {long_term.get('trend', '未知')} |
| 趋势强度 | {long_term.get('strength', '未知')} |

### 关键位置

| 类型 | 价格 | 原因 |
|------|------|------|
| 关键支撑 | {key_support.get('price', 0):.2f} | {key_support.get('reason', '')} |
| 关键压力 | {key_resistance.get('price', 0):.2f} | {key_resistance.get('reason', '')} |

### 短期预期

**操作建议**: {short_term.get('suggestion', '无')}

**置信度**: {short_term.get('confidence', '未知')}

**风险提示**: {short_term.get('risk_warning', '无')}

---

## 二、情绪分析

{sentiment_md if sentiment_md else '*情绪分析数据获取失败*'}

---

## 三、综合判断

### 大盘与情绪共振

"""

    # 添加共振分析
    intraday = index_data.get("intraday_analysis", {})
    trend_alignment = intraday.get("trend_alignment", "未知")

    note += f"""
**趋势一致性**: {trend_alignment}

### 操作策略

基于大盘位置（{position}）和情绪周期，建议：

1. **仓位管理**: 根据情绪周期阶段调整
2. **风险控制**: 关注关键支撑压力位
3. **观察重点**: 大盘与情绪是否形成共振

---

## 相关笔记

- [[大盘分析]]
- [[情绪分析]]
- [[交易策略]]

## 数据来源

- 大盘分析: index_replay_agent
- 情绪分析: sentiment_replay_agent
- 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""

    return note


def save_to_obsidian(note_content: str, date_str: str) -> str:
    """保存笔记到Obsidian"""
    OBSIDIAN_ARCHIVE.mkdir(parents=True, exist_ok=True)

    # 创建年度目录
    year_dir = OBSIDIAN_ARCHIVE / date_str[:4]
    year_dir.mkdir(parents=True, exist_ok=True)

    # 保存笔记
    note_path = year_dir / f"{date_str}-每日复盘.md"
    with open(note_path, "w", encoding="utf-8") as f:
        f.write(note_content)

    print(f"[{datetime.now()}] 笔记已保存到: {note_path}")
    return str(note_path)


def copy_charts_to_obsidian(index_chart: str, sentiment_chart: str, date_str: str):
    """复制图表到Obsidian附件目录"""
    import shutil

    # 创建附件目录
    attachments_dir = OBSIDIAN_ARCHIVE / "attachments"
    attachments_dir.mkdir(parents=True, exist_ok=True)

    copied = []

    if index_chart and Path(index_chart).exists():
        dest = attachments_dir / f"{date_str}-大盘K线.png"
        shutil.copy2(index_chart, dest)
        copied.append(str(dest))
        print(f"  复制大盘图表: {dest}")

    if sentiment_chart and Path(sentiment_chart).exists():
        dest = attachments_dir / f"{date_str}-情绪趋势.png"
        shutil.copy2(sentiment_chart, dest)
        copied.append(str(dest))
        print(f"  复制情绪图表: {dest}")

    return copied


# ========== 飞书推送功能 ==========

def get_feishu_token() -> Optional[str]:
    global _token_cache
    if _token_cache["token"] and _token_cache["expire_time"]:
        if datetime.now() < _token_cache["expire_time"]:
            return _token_cache["token"]

    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    try:
        response = httpx.post(url, json={
            "app_id": FEISHU_APP_ID,
            "app_secret": FEISHU_APP_SECRET
        }, timeout=30)
        result = response.json()
        if result.get("code") == 0:
            token = result["tenant_access_token"]
            _token_cache["token"] = token
            _token_cache["expire_time"] = datetime.now() + timedelta(seconds=7200-300)
            return token
    except Exception as e:
        print(f"获取Token失败: {e}")
    return None


def upload_image_to_feishu(image_path: str) -> Optional[str]:
    if not image_path or not Path(image_path).exists():
        return None

    token = get_feishu_token()
    if not token:
        return None

    try:
        with open(image_path, "rb") as f:
            image_data = f.read()

        if len(image_data) > 10 * 1024 * 1024:
            return None

        print(f"  上传图片 ({len(image_data)/1024:.1f} KB)...")

        response = httpx.post(
            "https://open.feishu.cn/open-apis/im/v1/images",
            headers={"Authorization": f"Bearer {token}"},
            files={"image_type": (None, "message"), "image": (Path(image_path).name, image_data, "image/png")},
            timeout=60
        )
        result = response.json()

        if result.get("code") == 0:
            return result["data"]["image_key"]
    except Exception as e:
        print(f"上传图片失败: {e}")
    return None


def send_image_to_feishu(image_key: str) -> bool:
    if not image_key:
        return False

    try:
        response = httpx.post(FEISHU_WEBHOOK, json={
            "msg_type": "image",
            "content": {"image_key": image_key}
        }, timeout=30)
        result = response.json()
        return result.get("code") == 0 or result.get("StatusCode") == 0
    except:
        return False


def send_card_to_feishu(md_content: str, title: str) -> bool:
    if len(md_content) > 28000:
        md_content = md_content[:28000] + "\n\n... (已截断)"

    try:
        response = httpx.post(FEISHU_WEBHOOK, json={
            "msg_type": "interactive",
            "card": {
                "header": {"title": {"tag": "plain_text", "content": title}, "template": "blue"},
                "elements": [{"tag": "markdown", "content": md_content}]
            }
        }, timeout=30)
        result = response.json()
        return result.get("code") == 0
    except:
        return False


def send_to_feishu(obsidian_note: str, charts: list):
    """发送整合报告到飞书"""
    print(f"[{datetime.now()}] 推送到飞书...")

    # 发送文字报告
    # 移除YAML frontmatter
    content = re.sub(r'^---\n.*?\n---\n', '', obsidian_note, flags=re.DOTALL)
    # 移除图片链接
    content = re.sub(r'!\[.*?\]\(.*?\)', '', content)
    content = re.sub(r'\n{3,}', '\n\n', content)

    # 分段发送
    if len(content) > FEISHU_MSG_LIMIT:
        parts = [content[i:i+FEISHU_MSG_LIMIT] for i in range(0, len(content), FEISHU_MSG_LIMIT)]
        for i, part in enumerate(parts):
            send_card_to_feishu(part, f"每日复盘 ({i+1}/{len(parts)})")
    else:
        send_card_to_feishu(content, "每日复盘")

    # 发送图表
    for chart_path in charts:
        image_key = upload_image_to_feishu(chart_path)
        if image_key:
            send_image_to_feishu(image_key)
            print(f"  图表已发送")


def main():
    print("=" * 60)
    print(f"[{datetime.now()}] 开始每日复盘整合任务")
    print("=" * 60)

    date_str = datetime.now().strftime('%Y-%m-%d')

    # 1. 运行大盘分析
    index_result = run_index_analysis()

    # 2. 运行情绪分析
    sentiment_result = run_sentiment_analysis()

    # 3. 加载数据
    index_data = None
    if index_result.get("json_file"):
        index_data = load_json_report(index_result["json_file"])

    sentiment_md = None
    if sentiment_result.get("md_file"):
        sentiment_md = load_markdown(sentiment_result["md_file"], remove_images=True)

    # 4. 创建Obsidian笔记
    if index_data:
        obsidian_note = create_obsidian_note(index_data, sentiment_md or "", date_str)
        note_path = save_to_obsidian(obsidian_note, date_str)
    else:
        print("大盘数据获取失败，跳过笔记创建")
        note_path = None
        obsidian_note = None

    # 5. 复制图表
    charts = []
    if index_result.get("chart_file") or sentiment_result.get("chart_file"):
        charts = copy_charts_to_obsidian(
            index_result.get("chart_file", ""),
            sentiment_result.get("chart_file", ""),
            date_str
        )

    # 6. 推送到飞书
    if obsidian_note:
        send_to_feishu(obsidian_note, charts)

    print("=" * 60)
    print(f"[{datetime.now()}] 任务完成")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(main())