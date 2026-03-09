"""
获取淘股吧Cookie工具
使用Playwright自动登录并获取Cookie
"""
import asyncio
import json
import time
from playwright.async_api import async_playwright


async def get_taoguba_cookies():
    """获取淘股吧Cookie"""
    print("=" * 60)
    print("淘股吧Cookie获取工具")
    print("=" * 60)
    print("\n请在弹出的浏览器中完成登录...")
    print("提示：建议使用手机验证码登录，更稳定")
    print("\n登录完成后，脚本将在60秒后自动获取Cookie")
    print()

    async with async_playwright() as p:
        # 启动浏览器
        browser = await p.chromium.launch(
            headless=False,  # 显示浏览器窗口
            args=['--disable-blink-features=AutomationControlled']
        )

        context = await browser.new_context(
            viewport={'width': 1280, 'height': 800}
        )

        page = await context.new_page()

        # 访问登录页面
        await page.goto("https://www.taoguba.com.cn/login", wait_until="networkidle")

        print("浏览器已打开，请完成登录...")
        print("60秒后将自动获取Cookie...")
        print()

        # 等待用户登录完成
        for i in range(60, 0, -1):
            print(f"\r倒计时: {i} 秒...", end="", flush=True)
            await asyncio.sleep(1)
        print("\n")

        # 获取所有Cookie
        cookies = await context.cookies()

        if not cookies:
            print("未获取到Cookie，请检查是否登录成功")
            await browser.close()
            return None

        # 转换为JSON字符串
        cookies_json = json.dumps(cookies, indent=2, ensure_ascii=False)

        # 转换为请求头格式的字符串
        cookie_str = "; ".join([f"{c['name']}={c['value']}" for c in cookies])

        print("\n" + "=" * 60)
        print("获取成功！以下是Cookie信息：")
        print("=" * 60)
        print("\n【JSON格式】（保存到 taoguba_cookies.json）：")
        print(cookies_json)

        print("\n【请求头格式】（设置到环境变量 TAOGUBA_COOKIE）：")
        print(cookie_str[:300] + "..." if len(cookie_str) > 300 else cookie_str)

        # 保存到文件
        with open("taoguba_cookies.json", "w", encoding="utf-8") as f:
            f.write(cookies_json)

        with open("taoguba_cookies.txt", "w", encoding="utf-8") as f:
            f.write(cookie_str)

        print("\n" + "=" * 60)
        print("Cookie已保存到：")
        print("  - taoguba_cookies.json")
        print("  - taoguba_cookies.txt")
        print("=" * 60)

        # 验证登录状态
        try:
            await page.goto("https://www.taoguba.com.cn/user/home", wait_until="networkidle")
            title = await page.title()
            if "登录" not in title and "error" not in title.lower():
                print("\n登录验证成功！")
            else:
                print("\n可能未登录成功，请检查Cookie是否有效")
        except:
            print("\n验证登录状态时出错")

        await browser.close()

        return cookie_str


if __name__ == "__main__":
    try:
        cookie = asyncio.run(get_taoguba_cookies())
        if cookie:
            print("\n" + "=" * 60)
            print("请复制 taoguba_cookies.txt 中的内容")
            print("设置到 GitHub Secrets 的 TAOGUBA_COOKIE")
            print("=" * 60)
    except KeyboardInterrupt:
        print("\n\n已取消")
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()
