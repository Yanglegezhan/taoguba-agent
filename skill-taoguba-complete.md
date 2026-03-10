# 淘股吧帖子爬取与干货提取完整流程

> 端到端技能：从爬取帖子评论到筛选提取干货的完整工作流

---

## 技能概述

本技能提供完整的淘股吧帖子处理流程，包括：
1. **爬取**：自动化爬取帖子及所有评论（支持分页）
2. **筛选**：过滤无效评论，保留高质量内容
3. **提取**：结构化提取干货内容
4. **输出**：生成Markdown格式的干货总结

---

## 前置条件

```bash
# Python依赖
pip install playwright python-dotenv

# 安装浏览器
playwright install chromium
```

## 文件结构

```
taoguba_agent/
├── skill-taoguba-complete.md    # 本技能文档
├── fetch_all.py                 # 爬取脚本
├── extract_ganhuo.py            # 干货提取脚本
├── .env.local                   # 账号配置
├── taoguba_cookies.json         # Cookie文件
└── output/                      # 输出目录
    ├── raw_帖子名_原始评论.md      # 原始爬取结果
    └── 帖子名_干货提取.md          # 干货提取结果
```

---

## 第一阶段：爬取帖子评论

### 步骤1：配置环境

编辑 `.env.local`：

```bash
# 淘股吧账号配置
TAOGBA_USERNAME=你的用户名
TAOGBA_PASSWORD=你的密码

# Cookie（首次为空，登录后自动填充）
TAOGUBA_COOKIE=
```

### 步骤2：获取Cookie（首次使用）

```python
# get_cookie.py
from playwright.sync_api import sync_playwright
import os

def get_and_save_cookies():
    """自动登录并获取Cookie"""
    with sync_playwright() as p:
        browser = p.chromium.launch(channel='chrome', headless=False)
        page = browser.new_page()

        # 访问登录页
        page.goto('https://sso.tgb.cn/web/login/index')

        # 点击"账号登录"
        page.evaluate('''() => {
            const spans = document.querySelectorAll('span');
            for (const span of spans) {
                if (span.textContent.trim() === '账号登录') {
                    span.click();
                    return 'clicked';
                }
            }
        }''')
        page.wait_for_timeout(1000)

        # 填写账号密码
        username = os.getenv('TAOGBA_USERNAME', '')
        password = os.getenv('TAOGBA_PASSWORD', '')

        page.evaluate(f'''() => {{
            const accountInput = document.querySelector('input[placeholder*="手机号/笔名"]');
            const passwordInput = document.querySelector('input[type="password"]');
            if (accountInput) accountInput.value = '{username}';
            if (passwordInput) passwordInput.value = '{password}';
        }}''')

        # 点击登录
        page.evaluate('''() => {
            const allElements = document.querySelectorAll('button, div, span, a');
            for (const el of allElements) {
                if (el.textContent.trim() === '登录') {
                    el.click();
                    break;
                }
            }
        }''')

        page.wait_for_timeout(3000)

        # 获取Cookie
        cookies = page.evaluate('() => document.cookie')
        browser.close()

        # 保存到.env.local
        update_env_cookie(cookies)
        return cookies

def update_env_cookie(cookie_str):
    """更新.env.local中的Cookie"""
    with open('.env.local', 'r', encoding='utf-8') as f:
        lines = f.readlines()

    with open('.env.local', 'w', encoding='utf-8') as f:
        for line in lines:
            if line.startswith('TAOGUBA_COOKIE='):
                f.write(f'TAOGUBA_COOKIE={cookie_str}\n')
            else:
                f.write(line)

if __name__ == '__main__':
    get_and_save_cookies()
```

### 步骤3：爬取评论

```python
# fetch_all.py
import asyncio
from playwright.async_api import async_playwright
import os
from dotenv import load_dotenv

load_dotenv()

def parse_cookies():
    """解析Cookie字符串为Playwright格式"""
    cookie_str = os.getenv('TAOGUBA_COOKIE', '')
    cookies = []
    for item in cookie_str.split(';'):
        item = item.strip()
        if '=' in item:
            name, value = item.split('=', 1)
            cookies.append({
                'name': name.strip(),
                'value': value.strip(),
                'domain': '.tgb.cn',
                'path': '/'
            })
    return cookies

async def fetch_post(post_url, output_file):
    """
    爬取帖子所有评论

    Args:
        post_url: 帖子URL，如 https://www.tgb.cn/a/2pUTHRHi2tY
        output_file: 输出文件路径
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(channel='chrome', headless=True)
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        )

        # 加载Cookie
        cookies = parse_cookies()
        await context.add_cookies(cookies)

        page = await context.new_page()
        all_comments = []
        seen = set()

        # 遍历分页（1-60页）
        for page_num in range(1, 61):
            try:
                # 重要：正确的分页URL格式
                if page_num == 1:
                    url = post_url
                else:
                    url = f'{post_url}-{page_num}'  # 格式: /a/xxx-2

                print(f"正在加载第 {page_num} 页...")
                await page.goto(url, wait_until='domcontentloaded', timeout=30000)
                await page.wait_for_timeout(3000)

                # 提取评论
                comments = await page.query_selector_all('.comment-data')
                page_new = 0

                for comment in comments:
                    try:
                        user_el = await comment.query_selector('.comment-data-user')
                        text_el = await comment.query_selector('.comment-data-text')

                        if user_el and text_el:
                            author = await user_el.text_content()
                            content = await text_el.text_content()
                            author = author.strip().split('\n')[0] if author else '未知'
                            content = content.strip() if content else ''

                            # 去重
                            key = f"{author}:{content[:100]}"
                            if content and key not in seen:
                                seen.add(key)
                                all_comments.append({'author': author, 'content': content})
                                page_new += 1
                    except:
                        pass

                print(f"第 {page_num} 页: 提取 {len(comments)} 条，新增 {page_new} 条，总计 {len(all_comments)} 条")

                # 连续2页无新内容则停止
                if page_new == 0 and page_num > 2:
                    print("连续无新内容，停止爬取")
                    break

            except Exception as e:
                print(f"第 {page_num} 页出错: {e}")
                continue

        # 保存原始结果
        title = await page.title()
        save_raw_comments(title, post_url, all_comments, output_file)

        await browser.close()
        return all_comments

def save_raw_comments(title, url, comments, output_file):
    """保存原始评论"""
    output = f"# {title}\n\n"
    output += f"**链接**: {url}\n\n"
    output += f"**评论数**: {len(comments)}条\n\n---\n\n"

    for idx, c in enumerate(comments, 1):
        output += f"### {idx}. {c['author']}\n\n{c['content']}\n\n"

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(output)

    print(f"\n原始评论已保存: {output_file}")

if __name__ == '__main__':
    # 示例使用
    post_url = 'https://www.tgb.cn/a/2pUTHRHi2tY'
    output_file = 'raw_主升龙头空空龙_原始评论.md'
    asyncio.run(fetch_post(post_url, output_file))
```

---

## 第二阶段：筛选与干货提取

### 步骤4：筛选规则

```python
# extract_ganhuo.py

# 过滤规则
FILTER_RULES = {
    # 完全排除（无意义内容）
    'exclude_exact': [
        '1', '2', '3', '666', '6666', '888', '999',
        '来了', '来了来了', '前排', '前排了', '沙发',
        '龙一', '龙二', '龙三', '龙哥', '龙师',
        '先赞后看', '先赞', '赞', '赞赞赞',
        '打卡', '报道', '报到',
        '发财', '牛逼', '牛', '厉害',
        '谢谢', '感谢', '学到了', '学习', '学',
        '不错', '好的', '收到', '明白',
    ],

    # 包含这些词排除（纯情绪）
    'exclude_contains': [
        '先赞后看月入百万',
        '先赞后看日入百万',
        '点赞', '催播', '打赏',
        '顶顶', '支持', '加油',
    ],

    # 长度过滤（少于10字符通常无意义）
    'min_length': 10,

    # 保留规则（包含这些关键词优先保留）
    'priority_keywords': [
        '超预期', '辨识度', '回暖日', '择时',
        '打板', '竞价', '炸板', '烂板',
        '板块', '前排', '后排', '龙头',
        '逻辑', '资金', '主力', '量化',
        '模式', '买点', '卖点', '仓位',
        '分歧', '一致', '回流', '轮动',
        '空仓', '管住手', '套利',
    ]
}

def should_keep_comment(author, content):
    """
    判断评论是否值得保留

    Returns:
        (bool, str): (是否保留, 保留原因/过滤原因)
    """
    content = content.strip()

    # 长度检查
    if len(content) < FILTER_RULES['min_length']:
        return False, 'too_short'

    # 完全匹配排除
    if content in FILTER_RULES['exclude_exact']:
        return False, 'exclude_exact'

    # 包含排除
    for exclude in FILTER_RULES['exclude_contains']:
        if exclude in content:
            return False, 'exclude_contains'

    # 博主回复优先保留
    if author == '主升龙头空空龙':
        return True, 'author_priority'

    # 检查是否有干货关键词
    for keyword in FILTER_RULES['priority_keywords']:
        if keyword in content:
            return True, f'keyword:{keyword}'

    # 默认排除（无关键词的一般是闲聊）
    return False, 'no_keywords'
```

### 步骤5：干货提取与分类

```python
# extract_ganhuo.py (续)

GANHUO_CATEGORIES = {
    '心法类': [
        '择时大于一切', '空仓', '管住手', '大道至简',
        '确定性', '审美', '只做', '永远',
    ],
    '技术类': {
        '超预期': ['超预期', '符合预期', '不及预期'],
        '辨识度': ['辨识度', '前排', '后排', '核心', '龙头', '杂毛'],
        '买卖点': ['打板', '竞价', '半路', '扫板', '排板'],
        '炸板处理': ['炸板', '烂板', '回封', '封单'],
        '板块分析': ['板块', '回流', '轮动', '分歧', '一致'],
    },
    '盘口类': [
        '主动', '被动', '带动', '引导', '点火',
        '封单', '放量', '缩量', '换手',
    ],
    '心态类': [
        'YY', '幻想', '贪婪', '恐惧', '犹豫',
        '知行合一', '跟随', '预判',
    ]
}

def classify_ganhuo(content):
    """对干货内容进行分类"""
    categories = []

    for cat_name, keywords in GANHUO_CATEGORIES.items():
        if isinstance(keywords, dict):
            # 子分类
            for sub_cat, sub_keywords in keywords.items():
                if any(kw in content for kw in sub_keywords):
                    categories.append(f"{cat_name}/{sub_cat}")
        else:
            if any(kw in content for kw in keywords):
                categories.append(cat_name)

    return categories if categories else ['未分类']

def extract_quotes(comments, author_name='主升龙头空空龙'):
    """提取经典语录"""
    quotes = []

    for comment in comments:
        if comment['author'] == author_name:
            content = comment['content']
            # 提取短小精悍的句子（少于50字符）
            if len(content) < 50 and '。' in content:
                sentences = content.split('。')
                for s in sentences:
                    s = s.strip()
                    if 10 < len(s) < 50:
                        quotes.append(s)

    return quotes
```

### 步骤6：生成干货文档

```python
# extract_ganhuo.py (续)

def generate_ganhuo_doc(input_file, output_file):
    """
    从原始评论生成干货提取文档

    Args:
        input_file: 原始评论文件路径
        output_file: 干货提取输出路径
    """
    # 读取原始评论
    with open(input_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # 解析评论（简化版，实际可用正则更精确）
    import re
    pattern = r'### (\d+)\. (.+?)\n\n(.+?)(?=\n\n###|\Z)'
    matches = re.findall(pattern, content, re.DOTALL)

    comments = []
    for idx, author, text in matches:
        comments.append({
            'index': int(idx),
            'author': author.strip(),
            'content': text.strip()
        })

    print(f"共读取 {len(comments)} 条评论")

    # 筛选
    kept_comments = []
    for c in comments:
        keep, reason = should_keep_comment(c['author'], c['content'])
        if keep:
            c['categories'] = classify_ganhuo(c['content'])
            c['keep_reason'] = reason
            kept_comments.append(c)

    print(f"筛选后保留 {len(kept_comments)} 条")

    # 按分类组织
    categorized = {}
    for c in kept_comments:
        for cat in c['categories']:
            if cat not in categorized:
                categorized[cat] = []
            categorized[cat].append(c)

    # 提取经典语录
    quotes = extract_quotes(kept_comments)

    # 生成Markdown
    output = generate_markdown(categorized, quotes)

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(output)

    print(f"干货文档已生成: {output_file}")

def generate_markdown(categorized, quotes):
    """生成Markdown格式文档"""
    lines = [
        "# 帖子干货提取",
        "",
        "> 自动生成，筛选规则：排除纯点赞/打卡，保留技术讨论",
        "",
        "---",
        "",
        "## 一、经典语录",
        "",
    ]

    for q in quotes[:20]:  # 前20条
        lines.append(f"> {q}")
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("## 二、分类干货")
    lines.append("")

    # 按分类输出
    for cat_name in sorted(categorized.keys()):
        comments = categorized[cat_name]
        lines.append(f"### {cat_name} ({len(comments)}条)")
        lines.append("")

        for c in comments[:10]:  # 每类最多10条
            lines.append(f"**{c['author']}**:")
            lines.append(f"{c['content'][:200]}..." if len(c['content']) > 200 else c['content'])
            lines.append("")

    return '\n'.join(lines)

if __name__ == '__main__':
    generate_ganhuo_doc(
        'raw_主升龙头空空龙_原始评论.md',
        '主升龙头空空龙_干货提取.md'
    )
```

---

## 第三阶段：一键运行脚本

### 完整流水线

```python
# run_pipeline.py
import asyncio
import sys
from fetch_all import fetch_post
from extract_ganhuo import generate_ganhuo_doc

async def main():
    """完整流程：爬取 -> 提取"""

    # 配置
    post_url = sys.argv[1] if len(sys.argv) > 1 else 'https://www.tgb.cn/a/2pUTHRHi2tY'
    raw_file = 'output/raw_comments.md'
    ganhuo_file = 'output/ganhuo_extracted.md'

    print("=" * 50)
    print("步骤1: 爬取评论")
    print("=" * 50)
    await fetch_post(post_url, raw_file)

    print("\n" + "=" * 50)
    print("步骤2: 提取干货")
    print("=" * 50)
    generate_ganhuo_doc(raw_file, ganhuo_file)

    print("\n" + "=" * 50)
    print("完成！")
    print(f"原始评论: {raw_file}")
    print(f"干货提取: {ganhuo_file}")
    print("=" * 50)

if __name__ == '__main__':
    asyncio.run(main())
```

运行：
```bash
python run_pipeline.py https://www.tgb.cn/a/2pUTHRHi2tY
```

---

## 关键要点总结

### 1. Cookie管理
- 首次使用需运行 `get_cookie.py` 登录获取Cookie
- Cookie保存在 `.env.local`，有效期数天到数周
- 失效后重新运行获取

### 2. URL格式（重要）
- ❌ 错误: `?pageNo=2`
- ✅ 正确: `-2`
- 示例: `/a/2pUTHRHi2tY-2`

### 3. 筛选策略
| 类型 | 处理方式 | 示例 |
|------|---------|------|
| 纯数字 | 排除 | "666", "888" |
| 纯问候 | 排除 | "来了", "龙一", "打卡" |
| 纯表情 | 排除 | "👍", "牛逼" |
| 博主回复 | 保留 | 所有主升龙头空空龙的回复 |
| 含技术词 | 保留 | "超预期", "打板", "辨识度" |

### 4. 分类标签
- 心法类：择时、空仓、确定性
- 技术类：超预期、买卖点、炸板处理
- 盘口类：主动/被动、封单、放量
- 心态类：YY、知行合一、跟随

---

## 常见问题

### Q1: Cookie失效怎么办？
```bash
python get_cookie.py  # 重新获取
```

### Q2: 如何提取其他博主帖子？
修改 `run_pipeline.py` 中的URL即可，筛选规则可调整博主名称。

### Q3: 干货提取不准确？
调整 `FILTER_RULES` 中的关键词：
```python
FILTER_RULES['priority_keywords'].append('你的关键词')
```

### Q4: 爬取太慢？
- 减少 `wait_for_timeout` 时间
- 使用 `headless=True`（默认）
- 减少分页数（默认60页）

---

## 参考

- 示例帖子：https://www.tgb.cn/a/2pUTHRHi2tY
- Playwright文档：https://playwright.dev/python/
- 完整示例见：`主升龙头空空龙_3月5日_干货提取.md`
