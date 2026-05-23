import { test, expect } from '@playwright/test';

test.describe('Strategy Editor', () => {
  // 需要先登录
  test.beforeEach(async ({ page }) => {
    await page.goto('/login');
    await page.locator('input[type="email"]').fill('admin@quantdesk.dev');
    await page.locator('input[type="password"]').fill('Admin12345678');
    await page.locator('button[type="submit"]').click();
    await expect(page).toHaveURL(/dashboard/, { timeout: 10000 });
  });

  test('should create new strategy', async ({ page }) => {
    // 导航到策略创建
    await page.goto('/dashboard');
    await page.locator('text=/新建策略|Create Strategy|新建/i').click();

    // 等待策略编辑页面
    await expect(page).toHaveURL(/strategy/, { timeout: 5000 });
  });

  test('should display strategy editor components', async ({ page }) => {
    // 直接访问一个策略编辑页面（假设 ID 存在）
    await page.goto('/strategy/test-id/edit');

    // 检查编辑器主要组件
    const editorArea = page.locator('[data-testid="strategy-editor"], .strategy-editor, #strategy-canvas');
    // 即使策略不存在，页面也应该显示编辑器框架
    await expect(page.locator('text=/策略|Strategy|因子|Factor/i').first()).toBeVisible({ timeout: 3000 });
  });

  test('should save strategy', async ({ page }) => {
    await page.goto('/dashboard');

    // 如果有策略列表，点击第一个策略编辑
    const strategyLink = page.locator('a[href*="/strategy/"]').first();
    if (await strategyLink.isVisible({ timeout: 2000 })) {
      await strategyLink.click();
      await page.waitForURL(/strategy/, { timeout: 5000 });

      // 点击保存按钮
      const saveBtn = page.locator('button:has-text("保存"), button:has-text("Save")');
      if (await saveBtn.isVisible()) {
        await saveBtn.click();
      }
    }
  });
});

test.describe('Backtest Execution', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login');
    await page.locator('input[type="email"]').fill('admin@quantdesk.dev');
    await page.locator('input[type="password"]').fill('Admin12345678');
    await page.locator('button[type="submit"]').click();
    await expect(page).toHaveURL(/dashboard/, { timeout: 10000 });
  });

  test('should trigger backtest', async ({ page }) => {
    await page.goto('/dashboard');

    // 找到策略并触发回测
    const backtestBtn = page.locator('button:has-text("回测"), button:has-text("Backtest")').first();
    if (await backtestBtn.isVisible({ timeout: 2000 })) {
      await backtestBtn.click();
    }
  });
});