const { chromium } = require('playwright');
const path = require('path');

const DIR = '/home/robin/桌面/quantdesk/frontend/screenshots';
const FAKE_JWT = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0LXVzZXItMTIzIiwiZW1haWwiOiJ0ZXN0QGV4YW1wbGUuY29tIiwiZXhwIjo5OTk5OTk5OTk5fQ.fakesignature';

const PAGES = [
  ['strategy_editor_new', '/strategy/new/edit'],
  ['strategy_optimize', '/strategy/123/optimize'],
  ['strategy_wfa', '/strategy/123/wfa'],
  ['strategy_backtest_result', '/strategy/123/backtest/abc456'],
];

async function main() {
  const browser = await chromium.launch({ headless: true, executablePath: '/usr/bin/google-chrome' });
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });

  for (const [name, p] of PAGES) {
    const page = await ctx.newPage();
    await page.goto('http://localhost:3000/login', { waitUntil: 'networkidle', timeout: 10000 });
    await page.evaluate((t) => localStorage.setItem('token', t), FAKE_JWT);
    await page.goto('http://localhost:3000' + p, { waitUntil: 'networkidle', timeout: 15000 });
    await page.waitForTimeout(800);
    await page.screenshot({ path: path.join(DIR, name + '.png'), fullPage: true });
    console.log('OK: ' + name);
    await page.close();
  }
  await browser.close();
}
main().catch(e => { console.error(e); process.exit(1); });
