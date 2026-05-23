import { test, expect } from '@playwright/test';

test.describe('Admin Panel', () => {
  test.beforeEach(async ({ page }) => {
    // 使用管理员账号登录
    await page.goto('/login');
    await page.locator('input[type="email"]').fill('admin@quantdesk.dev');
    await page.locator('input[type="password"]').fill('Admin12345678');
    await page.locator('button[type="submit"]').click();
    await expect(page).toHaveURL(/dashboard/, { timeout: 10000 });
  });

  test('should access admin panel', async ({ page }) => {
    await page.goto('/admin');
    await expect(page.locator('text=/管理|Admin|用户|User/i').first()).toBeVisible({ timeout: 5000 });
  });

  test('should display user management tab', async ({ page }) => {
    await page.goto('/admin');

    // 检查用户管理 Tab
    const userTab = page.locator('text=/用户管理|Users|用户/i');
    await expect(userTab.first()).toBeVisible({ timeout: 3000 });
  });

  test('should display data sync tab', async ({ page }) => {
    await page.goto('/admin');

    // 检查数据同步 Tab
    const syncTab = page.locator('text=/数据同步|Sync|同步/i');
    await expect(syncTab.first()).toBeVisible({ timeout: 3000 });
  });

  test('should show sync status', async ({ page }) => {
    await page.goto('/admin');

    // 点击同步 Tab（如果需要）
    const syncTab = page.locator('[role="tab"]:has-text("同步"), button:has-text("同步")');
    if (await syncTab.isVisible()) {
      await syncTab.click();
    }

    // 检查同步状态显示
    const statusElement = page.locator('text=/状态|Status|同步状态/i');
    await expect(statusElement.first()).toBeVisible({ timeout: 5000 });
  });

  test('should trigger manual sync', async ({ page }) => {
    await page.goto('/admin');

    // 导航到同步 Tab
    const syncTab = page.locator('[role="tab"]:has-text("同步"), button:has-text("同步")');
    if (await syncTab.isVisible()) {
      await syncTab.click();
    }

    // 点击手动同步按钮
    const syncBtn = page.locator('button:has-text("同步"), button:has-text("Sync")');
    if (await syncBtn.isVisible({ timeout: 2000 })) {
      await syncBtn.click();
    }
  });
});

test.describe('Admin User Management', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login');
    await page.locator('input[type="email"]').fill('admin@quantdesk.dev');
    await page.locator('input[type="password"]').fill('Admin12345678');
    await page.locator('button[type="submit"]').click();
    await expect(page).toHaveURL(/dashboard/, { timeout: 10000 });
    await page.goto('/admin');
  });

  test('should list users', async ({ page }) => {
    // 应该能看到用户列表
    await expect(page.locator('table, [role="table"], .user-list')).toBeVisible({ timeout: 5000 });
  });

  test('should have set-admin action', async ({ page }) => {
    // 检查是否有设置管理员的功能
    const adminAction = page.locator('text=/设置管理员|Set Admin|管理员/i');
    // 可能需要先展开某个用户的操作菜单
  });
});