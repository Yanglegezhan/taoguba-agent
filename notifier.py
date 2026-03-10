"""
飞书通知
"""
import os
import json
import requests


def send_to_feishu(content: str, title: str = "淘股吧干货推送", webhook: str = None) -> bool:
    """
    发送消息到飞书

    Args:
        content: Markdown格式内容
        title: 标题
        webhook: 飞书Webhook地址

    Returns:
        是否发送成功
    """
    webhook = webhook or os.getenv("FEISHU_WEBHOOK", "")

    if not webhook:
        print("警告: 未配置飞书Webhook")
        return False

    # 截断内容（飞书限制）
    if len(content) > 8000:
        content = content[:8000] + "\n\n... (内容已截断)"

    payload = {
        "msg_type": "interactive",
        "card": {
            "config": {
                "wide_screen_mode": True
            },
            "header": {
                "title": {
                    "tag": "plain_text",
                    "content": title
                },
                "template": "blue"
            },
            "elements": [
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": content
                    }
                }
            ]
        }
    }

    try:
        response = requests.post(
            webhook,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=30
        )

        if response.status_code == 200:
            result = response.json()
            if result.get("code") == 0:
                print("飞书推送成功")
                return True
            else:
                print(f"飞书推送失败: {result}")
                return False
        else:
            print(f"飞书推送失败: HTTP {response.status_code}")
            return False

    except Exception as e:
        print(f"飞书推送异常: {e}")
        return False


def format_for_feishu(filter_result: dict, post_title: str, post_url: str) -> str:
    """格式化为飞书消息"""
    kept = filter_result['kept']
    categories = filter_result['categories']

    lines = [
        f"## 📊 {post_title}",
        "",
        f"🔗 [查看原文]({post_url})",
        f"📈 筛选: {len(kept)} 条干货 / {len(kept) + filter_result['removed_count']} 条评论",
        "",
        "---",
        "",
    ]

    # 各分类数量
    lines.append("**分类统计**:")
    for cat_name in sorted(categories.keys()):
        count = len(categories[cat_name])
        lines.append(f"- {cat_name}: {count}条")
    lines.append("")
    lines.append("---")
    lines.append("")

    # 每个分类显示前3条
    for cat_name in sorted(categories.keys())[:5]:  # 最多5个分类
        cat_comments = categories[cat_name]
        lines.append(f"**{cat_name}** ({len(cat_comments)}条)")
        lines.append("")

        for c in cat_comments[:3]:  # 每个分类3条
            author = c.get('author', '未知')
            content = c.get('content', '')

            # 截断
            if len(content) > 150:
                content = content[:150] + "..."

            lines.append(f"• **{author}**: {content}")
            lines.append("")

    return '\n'.join(lines)
