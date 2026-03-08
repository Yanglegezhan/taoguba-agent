"""
淘股吧CLI - 定时获取博主干货并推送飞书
"""
import argparse
import asyncio
import json
import os
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional
from dotenv import load_dotenv

# 加载环境变量
load_dotenv('.env.local')

from crawler import TaoGuBaCrawler
from filter import filter_comments, generate_ganhuo_doc, extract_quotes
from notifier import send_to_feishu, format_for_feishu
from llm_extractor import LLMExtractor


# ============ Obsidian 保存 ============
def save_to_obsidian(content: str, filename: str, subdir: str = "淘股吧干货") -> str:
    """
    保存报告到 Obsidian

    Args:
        content: 报告内容
        filename: 文件名
        subdir: 子目录

    Returns:
        保存的文件路径
    """
    # 确定 Obsidian  vault 路径
    base_paths = [
        Path("D:/pythonProject2/第二大脑"),
        Path("D:/pythonProject2"),
        Path.home() / "Documents/Obsidian",
    ]

    vault_path = None
    for path in base_paths:
        if path.exists():
            vault_path = path
            break

    if not vault_path:
        print("  [警告] 未找到 Obsidian vault 路径")
        return None

    # 创建目标目录
    target_dir = vault_path / "1-Inbox" / subdir
    target_dir.mkdir(parents=True, exist_ok=True)

    # 保存文件
    file_path = target_dir / filename
    file_path.write_text(content, encoding='utf-8')

    print(f"  [OK] 已保存到 Obsidian: {file_path}")
    return str(file_path)


# ============ 博主配置 ============
BLOGGERS = {
    "小土堆爆金币": {"uid": "9259508", "tags": ["短线", "情绪"]},
    "玫瑰超短": {"uid": "11668853", "tags": ["超短", "龙头"]},
    "主升龙头空空龙": {"uid": "13186975", "tags": ["龙头战法", "超预期"]},
    "偶特慢慢": {"uid": "1752875", "tags": ["趋势", "波段"]},
    "楚楚伊人": {"uid": "6688134", "tags": ["情绪周期", "复盘"]},
}


# ============ 交易日判断 ============
def is_trading_day(date: datetime = None) -> bool:
    """判断是否为交易日（简化版，不含节假日）"""
    date = date or datetime.now()
    # 周末为非交易日
    if date.weekday() >= 5:  # 5=周六, 6=周日
        return False
    # 这里可以添加节假日判断
    return True


# ============ 评论时间筛选 ============
def parse_comment_time(time_str: str, base_date: datetime = None) -> datetime:
    """
    解析评论时间字符串
    支持格式: "2026-03-07 12:30" 或 "03-07 12:30" 或 "12:30"
    """
    if not time_str:
        return None

    base_date = base_date or datetime.now()
    time_str = time_str.strip()

    # 尝试完整格式: 2026-03-07 12:30
    patterns = [
        (r'(\d{4})-(\d{1,2})-(\d{1,2})\s+(\d{1,2}):(\d{2})', 'full'),
        (r'(\d{1,2})-(\d{1,2})\s+(\d{1,2}):(\d{2})', 'month_day'),
        (r'(\d{1,2}):(\d{2})', 'time_only'),
    ]

    for pattern, ptype in patterns:
        match = re.match(pattern, time_str)
        if match:
            if ptype == 'full':
                year, month, day, hour, minute = map(int, match.groups())
                return datetime(year, month, day, hour, minute)
            elif ptype == 'month_day':
                month, day, hour, minute = map(int, match.groups())
                year = base_date.year
                return datetime(year, month, day, hour, minute)
            elif ptype == 'time_only':
                hour, minute = map(int, match.groups())
                return base_date.replace(hour=hour, minute=minute, second=0, microsecond=0)

    return None


def extract_time_from_author(author_str: str) -> str:
    """
    从作者字符串中提取时间
    例如: "小土堆爆金币楼主2026-03-01 15:56只看TA" -> "2026-03-01 15:56"
    """
    if not author_str:
        return ""

    # 匹配时间格式: 2026-03-01 15:56 或 03-01 15:56
    patterns = [
        r'(\d{4}-\d{1,2}-\d{1,2}\s+\d{1,2}:\d{2})',  # 完整格式
        r'(\d{1,2}-\d{1,2}\s+\d{1,2}:\d{2})',        # 月日格式
    ]

    for pattern in patterns:
        match = re.search(pattern, author_str)
        if match:
            return match.group(1)

    return ""


def filter_comments_by_time(
    comments: list[dict],
    start_time: datetime,
    end_time: datetime,
    base_date: datetime = None,
    strict_date: bool = False
) -> list[dict]:
    """
    按时间范围筛选评论

    Args:
        comments: 评论列表，每项包含 'author' 字段（从中提取时间）
        start_time: 开始时间
        end_time: 结束时间
        base_date: 基础日期（用于解析只有时间的评论）
        strict_date: 是否严格按照指定日期筛选（True=只保留指定日期的评论）

    Returns:
        筛选后的评论列表
    """
    filtered = []
    base_date = base_date or datetime.now()

    for comment in comments:
        # 从作者字段中提取时间
        author = comment.get('author', '')
        time_str = extract_time_from_author(author)

        if not time_str:
            # 尝试从time_str字段获取
            time_str = comment.get('time_str', '')

        comment_time = parse_comment_time(time_str, base_date)

        if comment_time:
            # 如果启用严格日期筛选，只保留指定日期的评论
            if strict_date:
                # 检查日期是否在 start_time 和 end_time 之间
                if comment_time.date() < start_time.date() or comment_time.date() > end_time.date():
                    continue

            # 检查时间是否在范围内（按小时:分钟）
            comment_hour_min = comment_time.hour * 60 + comment_time.minute
            start_hour_min = start_time.hour * 60 + start_time.minute
            end_hour_min = end_time.hour * 60 + end_time.minute

            if start_hour_min <= comment_hour_min <= end_hour_min:
                comment['parsed_time'] = comment_time
                comment['time_str'] = time_str
                filtered.append(comment)
        # 无法解析时间的评论，不保留

    return filtered


# ============ 时间窗口计算 ============
def get_time_window(report_type: str, now: datetime = None) -> tuple:
    """
    计算时间窗口

    Returns:
        (start_time, end_time, label)
    """
    now = now or datetime.now()
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)

    if report_type == "pre_market":
        # 盘前：00:00 - 09:00
        start = today
        end = today.replace(hour=9, minute=0)
        return start, end, "盘前干货"

    elif report_type == "intraday":
        # 盘中：09:00 - 15:00
        start = today.replace(hour=9, minute=0)
        end = today.replace(hour=15, minute=0)
        return start, end, "盘中干货"

    elif report_type == "hourly":
        # 二小时干货：当前小时前2小时
        end = now.replace(minute=0, second=0, microsecond=0)
        start = end - timedelta(hours=2)
        return start, end, f"{start.strftime('%H:%M')}-{end.strftime('%H:%M')}干货"

    elif report_type == "daily":
        # 日总结：00:00 - 24:00
        start = today
        end = today + timedelta(days=1)
        return start, end, "本日干货总结"

    else:
        raise ValueError(f"未知的报告类型: {report_type}")


def get_next_run_time(report_type: str, now: datetime = None) -> datetime:
    """计算下次运行时间"""
    now = now or datetime.now()

    if report_type == "pre_market":
        # 明天9:00
        next_day = now + timedelta(days=1)
        return next_day.replace(hour=9, minute=0, second=0, microsecond=0)

    elif report_type == "intraday":
        # 今天15:00（如果已过则是明天15:00）
        target = now.replace(hour=15, minute=0, second=0, microsecond=0)
        if now >= target:
            target += timedelta(days=1)
        return target

    elif report_type == "hourly":
        # 下一个偶数小时
        current_hour = now.hour
        next_hour = current_hour + (2 - current_hour % 2)
        if next_hour >= 24:
            next_day = now + timedelta(days=1)
            return next_day.replace(hour=0, minute=0, second=0, microsecond=0)
        return now.replace(hour=next_hour, minute=0, second=0, microsecond=0)

    elif report_type == "daily":
        # 明天0:00
        next_day = now + timedelta(days=1)
        return next_day.replace(hour=0, minute=0, second=0, microsecond=0)

    return now


# ============ 内容获取 ============
async def fetch_blogger_content(
    blogger_name: str,
    blogger_config: dict,
    start_time: datetime,
    end_time: datetime,
    cookie: str
) -> List[Dict]:
    """
    获取博主在指定时间段内的帖子及评论

    Returns:
        [{"post": {}, "comments": [], "ganhuo": {}}, ...]
    """
    print(f"\n  正在获取: {blogger_name} (UID: {blogger_config['uid']})")

    crawler = TaoGuBaCrawler(cookie)
    results = []

    try:
        # 初始化浏览器
        await crawler._init_browser()

        # 获取用户帖子列表（获取最近10篇）
        posts = await crawler.get_user_posts(blogger_config["uid"], limit=10)
        print(f"    找到 {len(posts)} 篇帖子")

        for post in posts:
            try:
                title = post['title'][:30] if post.get('title') else '未知标题'
                print(f"    处理帖子: {title}...")
            except:
                print(f"    处理帖子: [标题编码错误]...")

            # 获取帖子详情和评论（获取全部页数）
            post_data = await crawler.fetch_post_with_comments(
                post['url'],
                max_pages=None  # 无上限，获取全部评论
            )

            print(f"      帖子总评论: {len(post_data['comments'])} 条")

            # 按时间筛选评论（只保留指定时间段内的）
            time_filtered_comments = filter_comments_by_time(
                post_data['comments'],
                start_time,
                end_time,
                base_date=start_time,  # 使用开始时间作为基础日期
                strict_date=True  # 严格按照指定日期筛选
            )

            print(f"      时间筛选 ({start_time.strftime('%m-%d %H:%M')} ~ {end_time.strftime('%H:%M')}): {len(time_filtered_comments)} 条")

            # 显示几条评论的时间示例
            if time_filtered_comments:
                print(f"      评论时间示例:")
                for i, c in enumerate(time_filtered_comments[:3]):
                    print(f"        - {c.get('author', '未知')[:20]}: {c.get('time_str', '无时间')}")

            # 如果没有符合时间的评论，跳过此帖子
            if not time_filtered_comments:
                print(f"      跳过: 无该时段评论")
                continue

            # 过滤干货评论
            filter_result = filter_comments(time_filtered_comments)

            print(f"      干货筛选: {len(filter_result['kept'])} 条")

            if len(filter_result['kept']) > 0:
                results.append({
                    "blogger": blogger_name,
                    "post": {
                        "title": post_data['title'],
                        "url": post['url'],
                    },
                    "total_comments": len(time_filtered_comments),
                    "kept_comments": len(filter_result['kept']),
                    "categories": filter_result['categories'],
                    "ganhuo": filter_result
                })

    except Exception as e:
        print(f"    错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await crawler._close_browser()

    print(f"    完成: 找到 {len(results)} 个有效帖子")
    return results


# ============ LLM 提取 ============
async def extract_with_llm(
    all_blogger_data: Dict[str, List[Dict]],
    start_time: datetime,
    end_time: datetime
) -> str:
    """
    使用 LLM 提取干货

    Returns:
        Markdown 格式的 LLM 提取报告
    """
    print("\n  正在使用 LLM 提取干货...")

    extractor = LLMExtractor()
    blogger_reports = {}
    time_range = f"{start_time.strftime('%Y-%m-%d %H:%M')} ~ {end_time.strftime('%H:%M')}"

    for blogger_name, posts in all_blogger_data.items():
        if not posts:
            continue

        print(f"    提取 {blogger_name} 的干货...")

        for post_data in posts:
            post = post_data['post']
            ganhuo = post_data['ganhuo']

            # 获取保留的评论
            comments = ganhuo.get('kept', [])

            if not comments:
                continue

            # 使用 LLM 提取
            try:
                result = extractor.extract_ganhuo(
                    blogger_name=blogger_name,
                    post_title=post['title'],
                    comments=comments,
                    time_range=time_range
                )

                blogger_reports[blogger_name] = result
                print(f"      提取完成: {len(result['ganhuo_points'])}条干货, {len(result['yuan_points'])}条预案")

            except Exception as e:
                print(f"      LLM 提取失败: {e}")
                blogger_reports[blogger_name] = {
                    "ganhuo_points": [],
                    "yuan_points": [],
                    "summary": f"提取失败: {e}"
                }

    # 整合所有博主报告
    if blogger_reports:
        report_md = extractor.merge_blogger_reports(blogger_reports, time_range)
        return report_md
    else:
        return "无内容"


# ============ 报告生成 ============
def generate_report(
    report_type: str,
    start_time: datetime,
    end_time: datetime,
    all_blogger_data: Dict[str, List[Dict]]
) -> str:
    """生成Markdown格式报告"""

    time_label = end_time.strftime("%m月%d日 %H:%M")

    lines = [
        f"# 淘股吧{report_type} - {time_label}",
        "",
        f"**时间范围**: {start_time.strftime('%m-%d %H:%M')} ~ {end_time.strftime('%m-%d %H:%M')}",
        f"**博主**: {', '.join(all_blogger_data.keys())}",
        "",
        "---",
        "",
    ]

    # 统计信息
    total_posts = sum(len(posts) for posts in all_blogger_data.values())
    total_ganhuo = sum(
        sum(p['kept_comments'] for p in posts)
        for posts in all_blogger_data.values()
    )

    lines.extend([
        "## 统计",
        "",
        f"- 涉及帖子: {total_posts}篇",
        f"- 干货评论: {total_ganhuo}条",
        "",
    ])

    # 各博主详情
    for blogger_name, posts in all_blogger_data.items():
        if not posts:
            continue

        lines.extend([
            f"## {blogger_name}",
            "",
        ])

        for post_data in posts:
            post = post_data['post']
            ganhuo = post_data['ganhuo']

            lines.extend([
                f"### {post['title']}",
                f"[{post['url']}]({post['url']})",
                "",
                f"**评论**: {post_data['total_comments']}条 | **干货**: {post_data['kept_comments']}条",
                "",
            ])

            # 分类统计
            if post_data['categories']:
                lines.append("**分类**:")
                for cat, comments in sorted(post_data['categories'].items()):
                    lines.append(f"- {cat}: {len(comments)}条")
                lines.append("")

            # 经典语录
            quotes = extract_quotes(ganhuo['kept'], blogger_name)
            if quotes:
                lines.append("**精华观点**:")
                for q in quotes[:3]:
                    lines.append(f"> {q}")
                lines.append("")

            # 各分类精选
            for cat_name, comments in sorted(post_data['categories'].items())[:3]:
                lines.append(f"**{cat_name}** ({len(comments)}条):")
                for c in comments[:2]:  # 每类2条
                    author = c.get('author', '未知')
                    content = c.get('content', '')
                    time_str = c.get('time_str', '')
                    if len(content) > 100:
                        content = content[:100] + "..."
                    time_info = f" [{time_str}]" if time_str else ""
                    lines.append(f"• **{author}**{time_info}: {content}")
                lines.append("")

            lines.append("---")
            lines.append("")

    return '\n'.join(lines)


def generate_summary_for_feishu(
    report_type: str,
    start_time: datetime,
    end_time: datetime,
    all_blogger_data: Dict[str, List[Dict]]
) -> str:
    """生成飞书推送格式（详细版）"""

    time_label = end_time.strftime("%m月%d日 %H:%M")

    lines = [
        f"## {report_type} - {time_label}",
        "",
        f"**时间**: {start_time.strftime('%H:%M')} ~ {end_time.strftime('%H:%M')}",
        "",
    ]

    # 统计
    total_posts = sum(len(posts) for posts in all_blogger_data.values())
    total_ganhuo = sum(
        sum(p['kept_comments'] for p in posts)
        for posts in all_blogger_data.values()
    )

    lines.extend([
        f"**统计**: {len(all_blogger_data)}位博主 | {total_posts}篇帖子 | {total_ganhuo}条干货",
        "",
        "---",
        "",
    ])

    # 各博主详情
    for blogger_name, posts in all_blogger_data.items():
        if not posts:
            continue

        lines.append(f"**【{blogger_name}】**")
        lines.append("")

        for post_data in posts:
            post = post_data['post']
            ganhuo = post_data['ganhuo']

            # 帖子标题和链接
            lines.append(f"**{post['title'][:40]}**")
            lines.append(f"[查看原文]({post['url']})")
            lines.append(f"*评论: {post_data['total_comments']}条 | 干货: {post_data['kept_comments']}条*")
            lines.append("")

            # 分类统计
            cats = list(post_data['categories'].keys())
            if cats:
                cat_summary = ' | '.join([f"{cat}({len(post_data['categories'][cat])}条)" for cat in cats[:5]])
                lines.append(f"**分类**: {cat_summary}")
                lines.append("")

            # 精选语录（博主自己的精华观点）
            quotes = extract_quotes(ganhuo['kept'], blogger_name)
            if quotes:
                lines.append("**精华观点**:")
                for q in quotes[:3]:
                    lines.append(f"> {q[:80]}...")
                lines.append("")

            # 各分类精选内容
            for cat_name, comments in sorted(post_data['categories'].items())[:2]:
                lines.append(f"**{cat_name}**:")
                for c in comments[:2]:  # 每类2条
                    author = c.get('author', '未知')
                    content = c.get('content', '')
                    # 清理作者名中的时间信息
                    author_clean = author.split('2026-')[0] if '2026-' in author else author[:15]
                    if len(content) > 80:
                        content = content[:80] + "..."
                    lines.append(f"• {author_clean}: {content}")
                lines.append("")

            lines.append("---")
            lines.append("")

    return '\n'.join(lines)


# ============ 核心流程 ============
async def run_report(report_type: str, push: bool = True, use_llm: bool = False):
    """运行报告生成流程"""

    print(f"\n{'='*60}")
    print(f"开始生成报告: {report_type}")
    if use_llm:
        print("[LLM 模式] 将使用大模型提取干货")
    print(f"{'='*60}")

    # 计算时间窗口
    start_time, end_time, label = get_time_window(report_type)
    print(f"\n时间窗口: {start_time.strftime('%Y-%m-%d %H:%M')} ~ {end_time.strftime('%Y-%m-%d %H:%M')}")
    print(f"报告标签: {label}")

    # 获取Cookie
    cookie = os.getenv("TAOGUBA_COOKIE", "")
    if not cookie:
        print("错误: 未设置TAOGUBA_COOKIE")
        return

    # 获取各博主内容
    all_blogger_data = {}

    # 只初始化一次浏览器
    crawler = None

    for blogger_name, config in BLOGGERS.items():
        try:
            # 每个博主独立获取，浏览器在fetch_blogger_content内部管理
            data = await fetch_blogger_content(
                blogger_name, config,
                start_time, end_time,
                cookie
            )
            if data:
                all_blogger_data[blogger_name] = data
        except Exception as e:
            print(f"\n  [错误] 获取 {blogger_name} 失败: {e}")
            continue

    if not all_blogger_data:
        print("\n[警告] 本时段无新内容")
        return

    # 生成基础报告
    print("\n正在生成基础报告...")
    report_md = generate_report(label, start_time, end_time, all_blogger_data)

    # 保存基础报告
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    safe_label = label.replace(":", "").replace("-", "_").replace(" ", "_")
    filename = f"report_{safe_label}_{timestamp}.md"

    Path(filename).write_text(report_md, encoding='utf-8')
    print(f"[OK] 基础报告已保存: {filename}")

    # 如果使用 LLM，生成 LLM 提取报告
    llm_filename = None
    if use_llm:
        print("\n正在使用 LLM 提取干货...")
        llm_report = await extract_with_llm(all_blogger_data, start_time, end_time)

        if llm_report and llm_report != "无内容":
            llm_filename = f"report_{safe_label}_LLM_{timestamp}.md"
            Path(llm_filename).write_text(llm_report, encoding='utf-8')
            print(f"[OK] LLM 报告已保存: {llm_filename}")
        else:
            print("[警告] LLM 提取无内容")

    # 推送飞书
    if push:
        print("\n正在推送飞书...")

        # 选择推送内容
        if use_llm and llm_filename and Path(llm_filename).exists():
            # 推送 LLM 提取的报告
            feishu_content = Path(llm_filename).read_text(encoding='utf-8')
            title_suffix = "(LLM智能提取)"
        else:
            # 推送普通报告
            feishu_content = generate_summary_for_feishu(
                label, start_time, end_time, all_blogger_data
            )
            title_suffix = ""

        success = send_to_feishu(
            content=feishu_content,
            title=f"{label}{title_suffix} - {end_time.strftime('%m月%d日 %H:%M')}",
            webhook=os.getenv("FEISHU_WEBHOOK")
        )

        if success:
            print("[OK] 推送成功")
        else:
            print("[FAIL] 推送失败")

    print(f"{'='*60}\n")


# ============ CLI命令 ============
def cmd_report(args):
    """生成指定类型报告"""
    asyncio.run(run_report(args.type, push=args.push, use_llm=args.llm))


def cmd_schedule(args):
    """启动定时调度"""
    print("启动定时调度...")
    print("按 Ctrl+C 停止")

    import time

    while True:
        now = datetime.now()

        # 判断报告类型
        if now.hour == 9 and now.minute < 5:
            # 09:00 盘前报告
            asyncio.run(run_report("pre_market"))
            sleep_until = now.replace(hour=15, minute=0, second=0)

        elif now.hour == 15 and now.minute < 5:
            # 15:00 盘中报告
            asyncio.run(run_report("intraday"))
            sleep_until = now.replace(hour=16, minute=0, second=0)

        elif now.hour >= 16 and now.hour < 24:
            # 16:00-00:00 每2小时
            if now.hour % 2 == 0 and now.minute < 5:
                asyncio.run(run_report("hourly"))
            sleep_until = now + timedelta(hours=2)
            sleep_until = sleep_until.replace(minute=0, second=0)

        elif now.hour == 0 and now.minute < 5:
            # 00:00 日总结
            asyncio.run(run_report("daily"))
            sleep_until = now.replace(hour=9, minute=0, second=0)

        else:
            # 非交易时间，等待到下一个整点
            sleep_until = now + timedelta(hours=1)
            sleep_until = sleep_until.replace(minute=0, second=0)

        # 计算等待时间
        wait_seconds = (sleep_until - datetime.now()).total_seconds()
        if wait_seconds > 0:
            print(f"\n下次运行: {sleep_until.strftime('%Y-%m-%d %H:%M')}")
            print(f"等待 {wait_seconds/60:.0f} 分钟...")
            time.sleep(min(wait_seconds, 60))  # 最多等1分钟，然后重新检查


def cmd_now(args):
    """立即获取当前时间段内容"""
    now = datetime.now()

    # 判断当前应该运行什么类型
    if now.hour < 9:
        report_type = "pre_market"
    elif now.hour < 15:
        report_type = "intraday"
    elif now.hour < 24:
        report_type = "hourly"
    else:
        report_type = "daily"

    asyncio.run(run_report(report_type, push=args.push, use_llm=args.llm))


def cmd_test(args):
    """测试获取指定博主"""
    blogger_name = args.blogger

    if blogger_name not in BLOGGERS:
        print(f"错误: 未知博主 {blogger_name}")
        print(f"可用博主: {', '.join(BLOGGERS.keys())}")
        return

    config = BLOGGERS[blogger_name]
    cookie = os.getenv("TAOGUBA_COOKIE", "")

    print(f"测试获取博主: {blogger_name}")
    print(f"UID: {config['uid']}")

    async def test():
        crawler = TaoGuBaCrawler(cookie)
        await crawler._init_browser()
        try:
            posts = await crawler.get_user_posts(config["uid"], limit=5)
            print(f"\n获取到 {len(posts)} 篇帖子:")
            for p in posts:
                print(f"  - {p['title']}")
        finally:
            await crawler._close_browser()

    asyncio.run(test())


def cmd_custom(args):
    """获取指定时间范围的干货"""
    # 解析时间参数
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

    try:
        # 支持格式: HH:MM 或 YYYY-MM-DD HH:MM
        if ' ' in args.start:
            # 完整日期时间格式
            start_time = datetime.strptime(args.start, "%Y-%m-%d %H:%M")
        else:
            # 仅时间格式，使用今天日期
            start_parts = args.start.split(':')
            start_time = today.replace(hour=int(start_parts[0]), minute=int(start_parts[1]))

        if ' ' in args.end:
            end_time = datetime.strptime(args.end, "%Y-%m-%d %H:%M")
        else:
            end_parts = args.end.split(':')
            end_time = today.replace(hour=int(end_parts[0]), minute=int(end_parts[1]))
    except (ValueError, IndexError):
        print("错误: 时间格式应为 HH:MM 或 YYYY-MM-DD HH:MM，例如 12:00 或 2026-03-01 12:00")
        return

    print(f"\n{'='*60}")
    print(f"自定义时间范围: {args.start} ~ {args.end}")
    if args.blogger:
        print(f"指定博主: {args.blogger}")
    print(f"{'='*60}")

    cookie = os.getenv("TAOGUBA_COOKIE", "")
    if not cookie:
        print("错误: 未设置TAOGUBA_COOKIE")
        return

    # 确定要获取的博主列表
    if args.blogger:
        if args.blogger not in BLOGGERS:
            print(f"错误: 未知博主 {args.blogger}")
            print(f"可用博主: {', '.join(BLOGGERS.keys())}")
            return
        target_bloggers = {args.blogger: BLOGGERS[args.blogger]}
    else:
        target_bloggers = BLOGGERS

    async def run_custom():
        all_blogger_data = {}

        for blogger_name, config in target_bloggers.items():
            try:
                data = await fetch_blogger_content(
                    blogger_name, config,
                    start_time, end_time,
                    cookie
                )
                if data:
                    all_blogger_data[blogger_name] = data
            except Exception as e:
                print(f"\n  [错误] 获取 {blogger_name} 失败: {e}")
                continue

        if not all_blogger_data:
            print("\n[警告] 本时段无新内容")
            return

        # 生成报告
        label = f"{args.start}-{args.end}干货"
        report_md = generate_report(label, start_time, end_time, all_blogger_data)

        # 保存报告
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        blogger_suffix = f"_{args.blogger}" if args.blogger else ""
        filename = f"report_custom_{args.start.replace(':', '')}_{args.end.replace(':', '')}{blogger_suffix}_{timestamp}.md"

        Path(filename).write_text(report_md, encoding='utf-8')
        print(f"[OK] 报告已保存: {filename}")

        # 如果使用LLM，进行智能提取
        llm_report = None
        llm_filename = None
        if args.llm:
            print("\n  正在使用 LLM 提取干货...")
            llm_report = await extract_with_llm(all_blogger_data, start_time, end_time)

            if llm_report and llm_report != "无内容":
                llm_filename = f"report_custom_LLM{blogger_suffix}_{timestamp}.md"
                Path(llm_filename).write_text(llm_report, encoding='utf-8')
                print(f"[OK] LLM 报告已保存: {llm_filename}")
            else:
                print("[警告] LLM 提取无内容")

        # 推送飞书
        if args.push:
            print(f"\n正在推送飞书...")

            # 选择推送内容
            if args.llm and llm_report and llm_report != "无内容":
                feishu_content = llm_report
                title_suffix = "(LLM智能提取)"
            else:
                feishu_content = generate_summary_for_feishu(
                    label, start_time, end_time, all_blogger_data
                )
                title_suffix = ""

            success = send_to_feishu(
                content=feishu_content,
                title=f"{label}{title_suffix} - {end_time.strftime('%m月%d日 %H:%M')}",
                webhook=os.getenv("FEISHU_WEBHOOK")
            )

            if success:
                print("[OK] 推送成功")
            else:
                print("[FAIL] 推送失败")

        # 保存到 Obsidian
        print("\n  正在保存到 Obsidian...")
        safe_label_for_file = label.replace(":", "").replace("-", "_").replace(" ", "_")
        if llm_report and llm_report != "无内容":
            obsidian_filename = f"{timestamp}_淘股吧_{safe_label_for_file}_LLM提取.md"
            save_to_obsidian(llm_report, obsidian_filename)
        else:
            obsidian_filename = f"{timestamp}_淘股吧_{safe_label_for_file}.md"
            save_to_obsidian(report_md, obsidian_filename)

        return filename

    filename = asyncio.run(run_custom())
    print(f"{'='*60}\n")

    # 输出报告内容
    if filename and Path(filename).exists():
        print("\n" + "="*60)
        print("报告内容预览:")
        print("="*60 + "\n")
        content = Path(filename).read_text(encoding='utf-8')
        print(content)


def cmd_batch(args):
    """批量获取2小时分段的干货"""
    try:
        base_date = datetime.strptime(args.date, "%Y-%m-%d")
    except ValueError:
        print("错误: 日期格式应为 YYYY-MM-DD，例如 2026-03-07")
        return

    print(f"\n{'='*60}")
    print(f"批量获取 {args.date} 的2小时分段干货")
    if args.blogger:
        print(f"指定博主: {args.blogger}")
    print(f"{'='*60}")

    # 生成2小时时间段列表
    time_slots = []
    for hour in range(args.start_hour, args.end_hour, 2):
        start_time = base_date.replace(hour=hour, minute=0)
        end_time = base_date.replace(hour=hour+2, minute=0)
        if end_time.hour > args.end_hour:
            end_time = base_date.replace(hour=args.end_hour, minute=0)
        time_slots.append((start_time, end_time))

    print(f"\n将获取 {len(time_slots)} 个时段:")
    for i, (start, end) in enumerate(time_slots, 1):
        print(f"  {i}. {start.strftime('%H:%M')} - {end.strftime('%H:%M')}")
    print()

    # 依次获取每个时段
    for i, (start_time, end_time) in enumerate(time_slots, 1):
        print(f"\n{'='*60}")
        print(f"[{i}/{len(time_slots)}] 获取 {start_time.strftime('%H:%M')} - {end_time.strftime('%H:%M')}")
        print(f"{'='*60}")

        # 构造模拟的 args 对象
        class Args:
            pass

        mock_args = Args()
        mock_args.start = start_time.strftime("%Y-%m-%d %H:%M")
        mock_args.end = end_time.strftime("%Y-%m-%d %H:%M")
        mock_args.blogger = args.blogger
        mock_args.push = args.push
        mock_args.llm = args.llm

        # 调用 custom 命令
        try:
            cmd_custom(mock_args)
        except Exception as e:
            print(f"\n[错误] 获取 {start_time.strftime('%H:%M')} - {end_time.strftime('%H:%M')} 失败: {e}")
            continue

    print(f"\n{'='*60}")
    print("批量获取完成")
    print(f"{'='*60}")


def main():
    parser = argparse.ArgumentParser(
        description="淘股吧CLI - 定时获取博主干货",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 立即获取当前时段内容
  python main.py now --push

  # 使用LLM智能提取并推送
  python main.py now --push --llm

  # 生成指定类型报告
  python main.py report --type pre_market --push

  # 启动定时调度
  python main.py schedule

  # 测试获取指定博主
  python main.py test --blogger "主升龙头空空龙"

  # 获取指定时间范围（如12:00-13:00）
  python main.py custom --start 12:00 --end 13:00 --push --llm

  # 获取指定博主在指定时间范围
  python main.py custom --start "2026-03-07 08:00" --end "2026-03-07 10:00" --blogger "主升龙头空空龙" --push --llm

  # 获取所有博主2小时分段（08:00-10:00, 10:00-12:00等）
  python main.py batch --date "2026-03-07" --push --llm
        """
    )

    parser.add_argument("--push", action="store_true", help="推送到飞书")
    parser.add_argument("--llm", action="store_true", help="使用LLM智能提取干货")

    subparsers = parser.add_subparsers(dest="command", help="子命令")

    # now 命令
    now_parser = subparsers.add_parser("now", help="立即获取当前时段内容")
    now_parser.set_defaults(func=cmd_now)

    # report 命令
    report_parser = subparsers.add_parser("report", help="生成指定类型报告")
    report_parser.add_argument(
        "--type",
        choices=["pre_market", "intraday", "hourly", "daily"],
        default="hourly",
        help="报告类型"
    )
    report_parser.set_defaults(func=cmd_report)

    # schedule 命令
    schedule_parser = subparsers.add_parser("schedule", help="启动定时调度")
    schedule_parser.set_defaults(func=cmd_schedule)

    # test 命令
    test_parser = subparsers.add_parser("test", help="测试获取指定博主")
    test_parser.add_argument("--blogger", required=True, help="博主名称")
    test_parser.set_defaults(func=cmd_test)

    # custom 命令 - 自定义时间范围
    custom_parser = subparsers.add_parser("custom", help="获取指定时间范围的干货")
    custom_parser.add_argument("--start", required=True, help="开始时间 (HH:MM 或 YYYY-MM-DD HH:MM)")
    custom_parser.add_argument("--end", required=True, help="结束时间 (HH:MM 或 YYYY-MM-DD HH:MM)")
    custom_parser.add_argument("--blogger", help="指定博主名称（只获取该博主）")
    custom_parser.set_defaults(func=cmd_custom)

    # batch 命令 - 批量获取2小时分段
    batch_parser = subparsers.add_parser("batch", help="批量获取2小时分段的干货")
    batch_parser.add_argument("--date", required=True, help="日期 (YYYY-MM-DD)")
    batch_parser.add_argument("--blogger", help="指定博主名称")
    batch_parser.add_argument("--start-hour", type=int, default=9, help="开始小时 (默认9)")
    batch_parser.add_argument("--end-hour", type=int, default=21, help="结束小时 (默认21)")
    batch_parser.set_defaults(func=cmd_batch)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == "__main__":
    main()
