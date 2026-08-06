import { expect, test } from '@playwright/test';

test('upload source -> inventory -> escaped source viewer', async ({ page }) => {
  await page.goto('/');

  await page.getByLabel('Email').fill('admin@example.com');
  await page.getByLabel('Password').fill('phase1-e2e-password');
  await page.getByRole('button', { name: 'Sign in' }).click();

  const projectName = `Phase 2 Ingestion ${Date.now()}`;
  await page.getByLabel('Project name').fill(projectName);
  await page.getByLabel('Legacy system').fill('ORDER_MAINFRAME');
  await page.getByRole('button', { name: 'Create project' }).click();
  await expect(page.getByRole('listitem').filter({ hasText: projectName })).toBeVisible();

  await page.getByLabel('Source file').setInputFiles({
    name: 'viewer.cbl',
    mimeType: 'text/plain',
    buffer: Buffer.from("IDENTIFICATION DIVISION.\n<script>alert('x')</script>\n")
  });
  await page.getByRole('button', { name: 'Upload source' }).click();

  await expect(page.getByRole('listitem').filter({ hasText: 'viewer.cbl' })).toBeVisible();
  await expect(page.locator('.source-code')).toContainText("<script>alert('x')</script>");
});
