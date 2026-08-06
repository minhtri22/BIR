import { expect, test } from '@playwright/test';

test('login -> create project -> project appears in list', async ({ page }) => {
  await page.goto('/');

  await page.getByLabel('Email').fill('admin@example.com');
  await page.getByLabel('Password').fill('phase1-e2e-password');
  await page.getByRole('button', { name: 'Sign in' }).click();

  await expect(page.getByRole('heading', { name: 'Projects' })).toBeVisible();

  const projectName = `Phase 1 Foundation ${Date.now()}`;
  await page.getByLabel('Project name').fill(projectName);
  await page.getByLabel('Legacy system').fill('ORDER_MAINFRAME');
  await page.getByRole('button', { name: 'Create project' }).click();

  await expect(page.getByRole('listitem').filter({ hasText: projectName })).toBeVisible();
});

