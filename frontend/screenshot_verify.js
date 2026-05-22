#!/usr/bin/env node
/**
 * QuantDesk 前端页面截图验证脚本
 * 截取所有主要页面并保存到 screenshots/ 目录
 */

const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const SCREENSHOT_DIR = path.join(__dirname, 'screenshots');
if (!fs.existsSync(SCREENSHOT_DIR)) {
  fs.mkdirSync(SCREENSHOT_DIR, { recursive: true });
}

// 伪造 JWT token
const FAKE_JWT = (
  'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.' +
  'eyJzdWIiOiJ0ZXN0LXVzZXItMTIzIiwiZW1haWwiOiJ0ZXN0QGV4YW1wbGUuY29tIiwiZXhwIjo5OTk5OTk5OTk5fQ.' +
  'fakesignature'
);

const PAGES = [
  ['landing', '/', false],
  ['login', '/login', false],
  ['dashboard_strategies', '/dashboard', true],
  ['dashboard_ai', '/dashboard?tab=ai', true],
  ['dashboard_backtests', '/dashboard?tab=backtests', true],
  ['dashboard_settings', '/dashboard?tab=settings', true],
  ['admin', '/admin', true],
  ['agent_tokens', '/settings/agent-tokens', true],
  ['onboarding', '/onboarding', true],
  ['strategy_editor_new', '/strategy/new/edit', true],
  ['strategy_optimize', '/strategy/123/optimize', true],
  ['strategy_wfa', '/strategy/123/wfa', true],
  ['strategy_backtest_result', '/strategy/123/backtest/abc456', true],
];

async function screenshotPage(page, name, pagePath, needsLogin) {
  const url = `http://localhost:3000${pagePath}`;
  console.log(`  [${name}] ${url}`);

  try {
    if (needsLogin) {
      await page.goto('http://localhost:3000/login', { waitUntil: 'networkidle', timeout: 10000 });
      await page.evaluate((token) => {
        localStorage.setItem('token', token);
      }, FAKE_JWT);
    }

    await page.goto(url, { waitUntil: 'networkidle', timeout: 15000 });
    await page.waitForTimeout(800);

    // 滚动到顶部
    await page.evaluate(() => window.scrollTo(0, 0));
    await page.waitForTimeout(200);

    const filepath = path.join(SCREENSHOT_DIR, `${name}.png`);
    await page.screenshot({ path: filepath, fullPage: true });
    console.log(`    -> ${filepath}`);
    return true;
  } catch (e) {
    console.log(`    ERROR: ${e.message}`);
    try {
      const filepath = path.join(SCREENSHOT_DIR, `${name}_error.png`);
      await page.screenshot({ path: filepath, fullPage: true });
      console.log(`    -> error screenshot: ${filepath}`);
    } catch {}
    return false;
  }
}

async function main() {
  console.log('QuantDesk 截图验证');
  console.log(`输出目录: ${SCREENSHOT_DIR}`);
  console.log(`页面数: ${PAGES.length}`);
  console.log('');

  const browser = await chromium.launch({
    headless: true,
    executablePath: '/usr/bin/google-chrome',
  });
  const context = await browser.newContext({
    viewport: { width: 1440, height: 900 },
    deviceScaleFactor: 1,
  });

  const results = [];
  for (const [name, pagePath, needsLogin] of PAGES) {
    const page = await context.newPage();
    const ok = await screenshotPage(page, name, pagePath, needsLogin);
    results.push([name, ok]);
    await page.close();
  }

  await browser.close();

  console.log('');
  console.log('='.repeat(50));
  console.log('截图结果汇总:');
  for (const [name, ok] of results) {
    const status = ok ? 'OK' : 'FAIL';
    console.log(`  [${status}] ${name}`);
  }
  const okCount = results.filter(([, ok]) => ok).length;
  console.log(`  总计: ${okCount}/${results.length} 成功`);
  console.log('='.repeat(50));

  process.exit(okCount === results.length ? 0 : 1);
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
