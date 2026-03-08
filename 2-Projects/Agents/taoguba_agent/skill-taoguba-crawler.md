# 淘股吧帖子爬取技能

> 使用 Playwright + Cookie 登录方式爬取淘股吧单个帖子及其所有评论

---

## 技能概述

本技能用于自动化爬取淘股吧指定帖子的全部评论内容，支持分页遍历和Cookie持久化。

## 前置条件

- Python 3.8+
- Playwright 已安装 (`pip install playwright`)
- Playwright 浏览器已安装 (`playwright install chromium`)
- 淘股吧账号已注册

## 文件结构

```
taoguba_agent/
├── .env.local              # 环境变量配置（账号密码、Cookie）
├── fetch_all.py            # 主爬取脚本
├── taoguba_cookies.json    # Cookie 持久化文件
└── taoguba_cookies.txt     # Cookie 字符串格式
```

---

## 完整流程

### 步骤 1: 配置账号信息

编辑 `.env.local` 文件：

```bash
# 淘股吧账号配置
TAOGBA_USERNAME=你的用户名
TAOGBA_PASSWORD=你的密码

# 当前Cookie（首次可为空，登录后会自动更新）
TAOGUBA_COOKIE=
```

### 步骤 2: 获取登录Cookie

#### 2.1 自动登录获取Cookie

```python
# 使用 Playwright 模拟登录获取最新Cookie
from playwright.sync_api import sync_playwright

def get_cookies():
    with sync_playwright() as p:
        browser = p.chromium.launch(channel='chrome', headless=False)
        page = browser.new_page()

        # 访问登录页
        page.goto('https://sso.tgb.cn/web/login/index')

        # 点击"账号登录"标签
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
        page.evaluate(f'''() => {{
            const accountInput = document.querySelector('input[placeholder*="手机号/笔名"]');
            const passwordInput = document.querySelector('input[type="password"]');
            if (accountInput) accountInput.value = '{'阳斩'}';
            if (passwordInput) passwordInput.value = '{'Chen0624'}';
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
        return cookies
```

#### 2.2 更新Cookie到配置文件

```python
# 保存Cookie到 .env.local
import os
from dotenv import load_dotenv

def update_cookie(new_cookie):
    load_dotenv('.env.local')

    # 读取原文件
    with open('.env.local', 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # 更新Cookie行
    with open('.env.local', 'w', encoding='utf-8') as f:
        for line in lines:
            if line.startswith('TAOGUBA_COOKIE='):
                f.write(f'TAOGUBA_COOKIE={new_cookie}\n')
            else:
                f.write(line)
```

### 步骤 3: 爬取帖子评论

#### 3.1 关键代码结构

```python
import asyncio
from playwright.async_api import async_playwright

async def fetch_post_comments(post_url, output_file):
    """
    爬取指定帖子的所有评论

    Args:
        post_url: 帖子URL，如 https://www.tgb.cn/a/2pUTHRHi2tY
        output_file: 输出文件路径
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(channel='chrome', headless=True)
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        )

        # 加载Cookie（关键步骤）
        cookies = parse_cookies_from_env()  # 从.env读取并解析
        await context.add_cookies(cookies)

        page = await context.new_page()
        all_comments = []
        seen = set()

        # 遍历分页（1-50页，根据总评论数调整）
        for page_num in range(1, 51):
            try:
                # 重要：正确的分页URL格式
                if page_num == 1:
                    url = post_url
                else:
                    # 格式: /a/2pUTHRHi2tY-2, /a/2pUTHRHi2tY-3
                    url = f'{post_url}-{page_num}'

                await page.goto(url, wait_until='domcontentloaded', timeout=30000)
                await page.wait_for_timeout(3000)

                # 提取评论
                comments = await page.query_selector_all('.comment-data')
                page_new_count = 0

                for comment in comments:
                    try:
                        user_el = await comment.query_selector('.comment-data-user')
                        text_el = await comment.query_selector('.comment-data-text')

                        if user_el and text_el:
                            author = await user_el.text_content()
                            content = await text_el.text_content()
                            author = author.strip().split('\n')[0] if author else '未知'
                            content = content.strip() if content else ''

                            # 去重（作者+内容前100字符）
                            key = f"{author}:{content[:100]}"
                            if content and key not in seen:
                                seen.add(key)
                                all_comments.append({
                                    'author': author,
                                    'content': content
                                })
                                page_new_count += 1
                    except:
                        pass

                print(f"第 {page_num} 页: 提取 {len(comments)} 条，新增 {page_new_count} 条")

                # 连续2页无新内容则停止
                if page_new_count == 0 and page_num > 2:
                    break

            except Exception as e:
                print(f"第 {page_num} 页出错: {e}")
                continue

        # 保存结果
        save_comments_to_markdown(all_comments, output_file)
        await browser.close()
```

#### 3.2 Cookie解析函数

```python
def parse_cookies_from_env():
    """从环境变量解析Cookie为Playwright格式"""
    from dotenv import load_dotenv
    load_dotenv('.env.local')

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
```

#### 3.3 保存为Markdown

```python
def save_comments_to_markdown(comments, output_file):
    """保存评论为Markdown格式"""
    output = f"# 帖子标题\n\n"
    output += f"**评论数**: {len(comments)}条\n\n---\n\n"

    for idx, c in enumerate(comments, 1):
        output += f"### {idx}. {c['author']}\n\n{c['content']}\n\n"

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(output)
```

---

## 关键要点

### 1. Cookie格式要求

Playwright需要Cookie数组格式：
```python
[
    {
        'name': 'tgbuser',
        'value': '12265811',
        'domain': '.tgb.cn',  # 重要：必须包含点
        'path': '/'
    },
    # ... 其他cookie
]
```

### 2. 分页URL格式

- ❌ 错误: `https://www.tgb.cn/a/2pUTHRHi2tY?pageNo=2`
- ✅ 正确: `https://www.tgb.cn/a/2pUTHRHi2tY-2`

### 3. 去重策略

使用 `作者名 + 内容前100字符` 作为唯一键：
```python
key = f"{author}:{content[:100]}"
```

### 4. 滚动加载 vs 分页

淘股吧帖子评论使用**分页加载**而非滚动加载：
- 每页约 30-50 条评论
- 通过URL参数 `-2`, `-3` 等切换页面
- 总页数可在页面底部的分页控件查看

---

## 常见问题

### Q1: Cookie过期怎么办？

重新运行登录脚本获取最新Cookie，Cookie有效期通常为几天到几周。

### Q2: 只获取到少量评论（如30-50条）？

检查：
1. Cookie是否正确加载
2. 分页URL格式是否正确（使用 `-2` 而非 `?pageNo=2`）
3. 是否已登录（未登录时只能看到部分评论）

### Q3: 如何确定总页数？

在浏览器中访问帖子，查看底部分页控件：
```javascript
// 在控制台运行
const pagination = document.querySelector('.t_page');
console.log(pagination.innerHTML);
```

### Q4: 遇到验证码或滑块？

使用 `headless=False` 以可视化模式运行，手动处理验证。

---

## 完整脚本示例

见 `taoguba_agent/fetch_all.py`

---

## 进阶用法

### 批量爬取多个帖子

```python
posts = [
    ('https://www.tgb.cn/a/2pUTHRHi2tY', '帖子1.md'),
    ('https://www.tgb.cn/a/xxxxx', '帖子2.md'),
]

for url, output in posts:
    await fetch_post_comments(url, output)
```

### 定时自动更新

```python
import schedule
import time

def job():
    asyncio.run(fetch_post_comments(url, output))

schedule.every().day.at("09:00").do(job)

while True:
    schedule.run_pending()
    time.sleep(60)
```

---

## 参考链接

- 淘股吧: https://www.tgb.cn
- Playwright文档: https://playwright.dev/python/
- 示例帖子: https://www.tgb.cn/a/2pUTHRHi2tY
