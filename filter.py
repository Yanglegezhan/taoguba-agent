"""
评论过滤与干货提取
"""
import re

# 过滤规则
FILTER_CONFIG = {
    # 完全排除的无意义内容
    'exclude_exact': {
        '1', '2', '3', '6', '66', '666', '6666', '888', '999',
        '来了', '来了来了', '前排', '前排了', '沙发', '板凳',
        '龙一', '龙二', '龙三', '龙哥', '龙师', '龙王',
        '先赞后看', '先赞', '赞', '赞赞赞', '已赞',
        '打卡', '报道', '报到', '到了', '到了到了',
        '发财', '牛逼', '牛', '厉害', '太强了',
        '谢谢', '感谢', '学到了', '学习', '学',
        '不错', '好的', '收到', '明白', '了解',
        '围观', '看看', '占楼', '占座', '占位',
        '催播', '打赏', '支持', '顶', '顶顶',
    },

    # 包含这些词排除
    'exclude_contains': [
        '先赞后看月入百万',
        '先赞后看日入百万',
        '点赞点赞',
        '催播催播',
    ],

    # 干货关键词（优先级排序）
    'keywords': {
        '核心心法': ['择时大于一切', '空仓', '管住手', '大道至简', '确定性', '审美'],
        '超预期': ['超预期', '符合预期', '不及预期', '正常预期'],
        '辨识度': ['辨识度', '前排', '后排', '核心', '龙头', '杂毛', '跟风'],
        '买卖点': ['打板', '竞价', '半路', '扫板', '排板', '板上确认'],
        '炸板处理': ['炸板', '烂板', '回封', '封单', '撤单'],
        '板块分析': ['板块', '回流', '轮动', '分歧', '一致', '分化'],
        '盘口': ['主动', '被动', '带动', '引导', '点火', '封单', '放量', '缩量'],
        '心态': ['yy', '幻想', '贪婪', '恐惧', '犹豫', '知行合一', '跟随'],
        '量化': ['量化', '平推', '套利', '收割'],
        '大盘': ['回暖日', '变盘日', '支撑位', '压力位', '成交量'],
    }
}


def should_keep(comment: dict) -> tuple[bool, str]:
    """
    判断评论是否值得保留

    Returns:
        (是否保留, 原因)
    """
    author = comment.get('author', '')
    content = comment.get('content', '').strip()

    # 长度检查
    if len(content) < 10:
        return False, 'too_short'

    # 完全匹配排除
    if content in FILTER_CONFIG['exclude_exact']:
        return False, 'exclude_exact'

    # 包含排除
    for exclude in FILTER_CONFIG['exclude_contains']:
        if exclude in content:
            return False, 'exclude_contains'

    # 博主回复优先保留
    if author == '主升龙头空空龙':
        return True, 'author_priority'

    # 检查干货关键词
    for category, keywords in FILTER_CONFIG['keywords'].items():
        for keyword in keywords:
            if keyword in content:
                return True, f'keyword:{category}'

    # 默认排除
    return False, 'no_keywords'


def classify_comment(content: str) -> list[str]:
    """对评论进行分类"""
    categories = []

    for category, keywords in FILTER_CONFIG['keywords'].items():
        if any(kw in content for kw in keywords):
            categories.append(category)

    return categories if categories else ['其他']


def extract_quotes(comments: list[dict], author: str = '主升龙头空空龙') -> list[str]:
    """提取经典语录（简短精华）"""
    quotes = []

    for comment in comments:
        if comment.get('author') == author:
            content = comment.get('content', '')
            # 提取50-100字符的精华句
            sentences = re.split(r'[。！？\n]', content)
            for s in sentences:
                s = s.strip()
                if 20 < len(s) < 100:
                    quotes.append(s)

    return quotes[:30]  # 最多30条


def filter_comments(comments: list[dict]) -> dict:
    """
    过滤评论并分类

    Returns:
        {
            'kept': [保留的评论],
            'removed_count': 移除数量,
            'categories': {分类: [评论]}
        }
    """
    kept = []
    removed_count = 0
    categories = {}

    for comment in comments:
        keep, reason = should_keep(comment)

        if keep:
            comment['keep_reason'] = reason
            comment['categories'] = classify_comment(comment.get('content', ''))
            kept.append(comment)

            # 按分类组织
            for cat in comment['categories']:
                if cat not in categories:
                    categories[cat] = []
                categories[cat].append(comment)
        else:
            removed_count += 1

    return {
        'kept': kept,
        'removed_count': removed_count,
        'categories': categories
    }


def generate_ganhuo_doc(post_title: str, post_url: str, filter_result: dict) -> str:
    """生成干货提取文档"""
    kept = filter_result['kept']
    categories = filter_result['categories']
    quotes = extract_quotes(kept)

    lines = [
        f"# {post_title} - 干货提取",
        "",
        f"> 来源: {post_url}",
        f"> 原始评论: {len(kept) + filter_result['removed_count']} 条",
        f"> 筛选后: {len(kept)} 条",
        "",
        "---",
        "",
        "## 一、经典语录",
        "",
    ]

    for q in quotes[:20]:
        lines.append(f"> {q}")
        lines.append("")

    lines.extend([
        "---",
        "",
        "## 二、分类干货",
        "",
    ])

    # 按分类输出
    for cat_name in sorted(categories.keys()):
        cat_comments = categories[cat_name]
        lines.append(f"### {cat_name} ({len(cat_comments)}条)")
        lines.append("")

        # 每个分类最多显示10条
        for c in cat_comments[:10]:
            author = c.get('author', '未知')
            content = c.get('content', '')

            lines.append(f"**{author}**:")
            # 截断过长内容
            if len(content) > 200:
                content = content[:200] + "..."
            lines.append(content)
            lines.append("")

    lines.extend([
        "---",
        "",
        "## 三、完整保留评论",
        "",
    ])

    for idx, c in enumerate(kept, 1):
        author = c.get('author', '未知')
        content = c.get('content', '')
        lines.append(f"### {idx}. {author}")
        lines.append("")
        lines.append(content)
        lines.append("")

    return '\n'.join(lines)
