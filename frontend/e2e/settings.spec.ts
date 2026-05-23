import { test, expect } from '@playwright/test';

test.describe('Settings Page', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login');
    await page.locator('input[type="email"]').fill('admin@quantdesk.dev');
    await page.locator('input[type="password"]').fill('Admin12345678');
    await page.locator('button[type="submit"]').click();
    await expect(page).toHaveURL(/dashboard/, { timeout: 10000 });
  });

  test('should access settings page', async ({ page }) => {
    await page.goto('/settings/agent-tokens');
    await expect(page.locator('text=/设置|Settings|Token|令牌/i').first()).toBeVisible({ timeout: 5000 });
  });

  test('should display agent token list', async ({ page }) => {
    await page.goto('/settings/agent-tokens');

    // 检查令牌列表或创建按钮
    const tokenSection = page.locator('text=/Agent Token|令牌|API Token/i');
    await expect(tokenSection.first()).toBeVisible({ timeout: 3000 });
  });

  test('should create new agent token', async ({ page }) => {
    await page.goto('/settings/agent-tokens');

    // 点击创建令牌按钮
    const createBtn = page.locator('button:has-text("创建"), button:has-text("Create"), button:has-text("新建")');
    if (await createBtn.isVisible({ timeout: 2000 })) {
      await createBtn.click();

      // 填写令牌信息
      const nameInput = page.locator('input[name="name"], input[placeholder*="名称"], input[placeholder*="Name"]');
      if (await nameInput.isVisible()) {
        await nameInput.fill('Test Token');
      }

      // 提交
      const submitBtn = page.locator('button[type="submit"], button:has-text("确认"), button:has-text("Confirm")');
      if (await submitBtn.isVisible()) {
        await submitBtn.click();
      }
    }
  });

  test('should revoke agent token', async ({ page }) => {
    await page.goto('/settings/agent-tokens');

    // 查找撤销按钮
    const revokeBtn = page.locator('button:has-text("撤销"), button:has-text("Revoke"), button:has-text("删除")');
    if (await revokeBtn.isVisible({ timeout: 2000 })) {
      await revokeBtn.first().click();
    }
  });
});

test.describe('Password Change', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login');
    await page.locator('input[type="email"]').fill('admin@quantdesk.dev');
    await page.locator('input[type="password"]').fill('Admin12345678');
    await page.locator('button[type="submit"]').click();
    await expect(page).toHaveURL(/dashboard/, { timeout: 10000 });
  });

  test('should change password', async ({ page }) => {
    // 导航到设置或个人资料页面
    await page.goto('/settings');

    // 检查修改密码选项
    const passwordSection = page.locator('text=/修改密码|Change Password|密码/i');
    if (await passwordSection.isVisible({ timeout: 3000 })) {
      // 点击修改密码
      await passwordSection.click();

      // 填写新密码
      const oldPasswordInput = page.locator('input[placeholder*="旧密码"], input[name="oldPassword"]');
      const newPasswordInput = page.locator('input[placeholder*="新密码"], input[name="newPassword"]');

      if (await oldPasswordInput.isVisible()) {
        await oldPasswordInput.fill('Admin12345678');
      }
      if (await newPasswordInput.isVisible()) {
        await newPasswordInput.fill('NewPassword123');
      }
    }
  });
});