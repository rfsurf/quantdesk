#!/usr/bin/env python3
"""
QuantDesk 前端页面截图验证脚本
截取所有主要页面并保存到 screenshots/ 目录
"""

import asyncio
import os
import base64
import json

from playwright.async_api import async_playwright

SCREENSHOT_DIR = os.path.join(os.path.dirname(__file__), "screenshots")
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

# 伪造的 JWT token（用于需要登录的页面）
# payload: {"sub":"test-user-123","email":"test@example.com","exp":9999999999}
FAKE_JWT = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
    "eyJzdWIiOiJ0ZXN0LXVzZXItMTIzIiwiZW1haWwiOiJ0ZXN0QGV4YW1wbGUuY29tIiwiZXhwIjo5OTk5OTk5OTk5fQ."
    "fakesignature"
)

PAGES = [
    # (name, path, needs_login)
    ("landing", "/", False),
    ("login", "/login", False),
    ("dashboard_strategies", "/dashboard", True),
    ("dashboard_ai", "/dashboard?tab=ai", True),
    ("dashboard_backtests", "/dashboard?tab=backtests", True),
    ("dashboard_settings", "/dashboard?tab=settings", True),
    ("admin", "/admin", True),
    ("agent_tokens", "/settings/agent-tokens", True),
    ("onboarding", "/onboarding", True),
    ("strategy_editor_new", "/strategy/new/edit", True),
    ("strategy_optimize", "/strategy/123/optimize", True),
    ("strategy_wfa", "/strategy/123/wfa", True),
    ("strategy_backtest_result", "/strategy/123/backtest/abc456", True),
]

async def screenshot_page(page, name: str, path: str, needs_login: bool):
    """对单个页面截图"""
    url = f"http://localhost:3000{path}"
    print(f"  [{name}] {url}")

    try:
        if needs_login:
            # 先注入 token 再导航
            await page.goto("http://localhost:3000/login")
            await page.evaluate(f"localStorage.setItem('token', '{FAKE_JWT}')")

        await page.goto(url, wait_until="networkidle", timeout=15000)
        # 额外等待一下让动画完成
        await asyncio.sleep(0.8)

        # 滚动到页面底部以捕获完整内容
        await page.evaluate("window.scrollTo(0, 0)")
        await asyncio.sleep(0.2)

        filepath = os.path.join(SCREENSHOT_DIR, f"{name}.png")
        await page.screenshot(path=filepath, full_page=True)
        print(f"    -> {filepath}")
        return True
    except Exception as e:
        print(f"    ERROR: {e}")
        # 即使出错也尝试截图
        try:
            filepath = os.path.join(SCREENSHOT_DIR, f"{name}_error.png")
            await page.screenshot(path=filepath, full_page=True)
            print(f"    -> error screenshot: {filepath}")
        except:
            pass
        return False


async def main():
    print(f"QuantDesk 截图验证")
    print(f"输出目录: {SCREENSHOT_DIR}")
    print(f"页面数: {len(PAGES)}")
    print()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1440, "height": 900},
            device_scale_factor=1,
        )

        results = []
        for name, path, needs_login in PAGES:
            page = await context.new_page()
            ok = await screenshot_page(page, name, path, needs_login)
            results.append((name, ok))
            await page.close()

        await browser.close()

    print()
    print("=" * 50)
    print("截图结果汇总:")
    for name, ok in results:
        status = "OK" if ok else "FAIL"
        print(f"  [{status}] {name}")
    ok_count = sum(1 for _, ok in results if ok)
    print(f"  总计: {ok_count}/{len(results)} 成功")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())
