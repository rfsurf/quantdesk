import { test, expect } from '@playwright/test';

test.describe('Login Flow', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login');
  });

  test('should display login form', async ({ page }) => {
    await expect(page.locator('input[type="email"]')).toBeVisible();
    await expect(page.locator('input[type="password"]')).toBeVisible();
    await expect(page.locator('button[type="submit"]')).toBeVisible();
  });

  test('should show error for invalid credentials', async ({ page }) => {
    await page.locator('input[type="email"]').fill('invalid@test.com');
    await page.locator('input[type="password"]').fill('wrongpassword');
    await page.locator('button[type="submit"]').click();

    // 等待错误提示
    await expect(page.locator('text=/登录失败|邮箱或密码错误|401/i')).toBeVisible({ timeout: 5000 });
  });

  test('should redirect to dashboard on successful login', async ({ page }) => {
    // 使用测试账号登录
    await page.locator('input[type="email"]').fill('admin@quantdesk.dev');
    await page.locator('input[type="password"]').fill('Admin12345678');
    await page.locator('button[type="submit"]').click();

    // 等待跳转到 dashboard
    await expect(page).toHaveURL(/dashboard/, { timeout: 10000 });
  });

  test('should have register link', async ({ page }) => {
    await expect(page.locator('text=/注册|Register|sign up/i')).toBeVisible();
  });
});

test.describe('Register Flow', () => {
  test('should send verification code', async ({ page }) => {
    await page.goto('/login');

    // 点击注册按钮/链接
    const registerLink = page.locator('text=/注册|Register|sign up/i').first();
    if (await registerLink.isVisible()) {
      await registerLink.click();
    }

    // 输入邮箱请求验证码
    const emailInput = page.locator('input[type="email"]');
    if (await emailInput.isVisible()) {
      await emailInput.fill('newuser@test.com');
      await page.locator('text=/发送验证码|Send Code/i').click();
    }
  });
});