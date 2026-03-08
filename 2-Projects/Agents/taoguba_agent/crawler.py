"""
淘股吧爬虫 - 简化版
"""
import asyncio
import re
import os
from datetime import datetime
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup


class TaoGuBaCrawler:
    """淘股吧爬虫"""

    BASE_URL = "https://www.tgb.cn"

    def __init__(self, cookie_str: str = None):
        self.cookie_str = cookie_str or os.getenv("TAOGUBA_COOKIE", "")
        self._browser = None
        self._playwright = None

    async def _init_browser(self):
        """初始化浏览器"""
        if self._playwright is None:
            self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.launch(
                channel='chrome',
                headless=True
            )
        return self._browser

    async def _close_browser(self):
        """关闭浏览器"""
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()

    def _parse_cookies(self):
        """解析Cookie字符串"""
        cookies = []
        for item in self.cookie_str.split(';'):
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

    async def fetch_post_with_comments(self, post_url: str, max_pages: int = None) -> dict:
        """
        获取帖子及所有评论
        注意：调用前需要先调用 _init_browser() 初始化浏览器

        Args:
            post_url: 帖子URL
            max_pages: 最大页数，None表示无上限（获取全部）
        """
        context = await self._browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        )

        # 添加Cookie
        cookies = self._parse_cookies()
        if cookies:
            await context.add_cookies(cookies)

        page = await context.new_page()

        try:
            all_comments = []
            seen = set()
            post_title = ""

            # 遍历分页
            page_num = 1
            empty_pages = 0  # 连续空页计数

            while True:
                # 检查是否达到最大页数限制
                if max_pages is not None and page_num > max_pages:
                    print(f"      达到最大页数限制 {max_pages}")
                    break

                # 构造分页URL
                if page_num == 1:
                    url = post_url
                else:
                    url = f"{post_url}-{page_num}"

                print(f"      加载第 {page_num} 页...", end=" ")
                await page.goto(url, wait_until='domcontentloaded', timeout=30000)
                await page.wait_for_timeout(2000)

                # 获取页面内容
                html = await page.content()
                soup = BeautifulSoup(html, 'lxml')

                # 提取标题（仅第一页）
                if page_num == 1:
                    title_elem = soup.select_one('h1') or soup.select_one('.title')
                    post_title = title_elem.get_text(strip=True) if title_elem else "未知标题"

                # 提取评论
                comment_items = soup.select('.comment-data')
                page_new = 0

                for item in comment_items:
                    user_el = item.select_one('.comment-data-user')
                    text_el = item.select_one('.comment-data-text')
                    time_el = item.select_one('.comment-data-time') or item.select_one('.time')

                    if user_el and text_el:
                        author = user_el.get_text(strip=True).split('\n')[0]
                        content = text_el.get_text(strip=True)

                        # 提取时间
                        time_str = ""
                        if time_el:
                            time_str = time_el.get_text(strip=True)

                        # 去重
                        key = f"{author}:{content[:100]}"
                        if content and key not in seen:
                            seen.add(key)
                            all_comments.append({
                                'author': author,
                                'content': content,
                                'time_str': time_str
                            })
                            page_new += 1

                print(f"新增 {page_new} 条")

                # 连续3页无新内容则停止
                if page_new == 0:
                    empty_pages += 1
                    if empty_pages >= 3:
                        print(f"      连续 {empty_pages} 页无新内容，停止获取")
                        break
                else:
                    empty_pages = 0

                page_num += 1

            return {
                'title': post_title,
                'url': post_url,
                'comments': all_comments,
                'total': len(all_comments)
            }

        finally:
            await page.close()
            await context.close()
            await self._close_browser()

    async def get_user_posts(self, uid: str, limit: int = 20,
                             start_time: datetime = None,
                             end_time: datetime = None) -> list[dict]:
        """
        获取用户帖子列表 - 调用前需要先初始化浏览器

        Args:
            uid: 用户ID
            limit: 最大获取数量
            start_time: 开始时间（只获取此时间后发布的帖子）
            end_time: 结束时间（只获取此时间前发布的帖子）
        """
        context = await self._browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        )

        cookies = self._parse_cookies()
        if cookies:
            await context.add_cookies(cookies)

        page = await context.new_page()

        try:
            url = f"{self.BASE_URL}/blog/{uid}"
            await page.goto(url, wait_until='domcontentloaded', timeout=30000)
            await page.wait_for_timeout(2000)

            html = await page.content()
            soup = BeautifulSoup(html, 'lxml')

            posts = []
            seen_ids = set()

            # 查找帖子链接和时间
            for item in soup.select('a[href^="a/"], a[href^="/a/"]'):
                href = item.get('href', '').strip()
                if not href:
                    continue

                # 标准化链接
                if href.startswith('/'):
                    href = href[1:]

                # 提取帖子ID
                match = re.match(r'^a/([a-zA-Z0-9]+)', href)
                if not match:
                    continue

                post_id = match.group(1)
                if post_id in seen_ids:
                    continue
                seen_ids.add(post_id)

                title = item.get_text(strip=True)
                title = re.sub(r'\[(精|原|红包)\]', '', title).strip()

                # 尝试获取帖子时间（从父元素或相邻元素）
                post_time = None
                parent = item.parent
                if parent:
                    # 尝试在父元素中找时间
                    time_elem = parent.select_one('.time, .post-time, .date, [class*="time"]')
                    if time_elem:
                        time_str = time_elem.get_text(strip=True)
                        post_time = self._parse_post_time(time_str)

                if title and len(title) >= 3:
                    post_data = {
                        'id': post_id,
                        'title': title,
                        'url': f"{self.BASE_URL}/{href}",
                        'post_time': post_time
                    }

                    # 时间筛选
                    if start_time and end_time and post_time:
                        if start_time <= post_time <= end_time:
                            posts.append(post_data)
                    else:
                        posts.append(post_data)

                if len(posts) >= limit:
                    break

            return posts

        finally:
            await page.close()
            await context.close()

    def _parse_post_time(self, time_str: str) -> datetime:
        """解析帖子时间"""
        if not time_str:
            return None

        time_str = time_str.strip()
        now = datetime.now()

        # 尝试各种格式
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
                    return datetime(now.year, month, day, hour, minute)
                elif ptype == 'time_only':
                    hour, minute = map(int, match.groups())
                    return now.replace(hour=hour, minute=minute, second=0, microsecond=0)

        return None

