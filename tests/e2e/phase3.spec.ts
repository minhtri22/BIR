import { expect, test } from '@playwright/test';

test('upload source -> run static analysis -> candidate opens evidence source', async ({ page }) => {
  await page.goto('/');

  await page.getByLabel('Email').fill('admin@example.com');
  await page.getByLabel('Password').fill('phase1-e2e-password');
  await page.getByRole('button', { name: 'Sign in' }).click();

  const projectName = `Phase 3 Static Extraction ${Date.now()}`;
  await page.getByLabel('Project name').fill(projectName);
  await page.getByLabel('Legacy system').fill('ORDER_MAINFRAME');
  await page.getByRole('button', { name: 'Create project' }).click();
  await expect(page.getByRole('listitem').filter({ hasText: projectName })).toBeVisible();

  await page.getByLabel('Source file').setInputFiles({
    name: 'analysis.cbl',
    mimeType: 'text/plain',
    buffer: Buffer.from(
      [
        '* Approve large orders',
        'IF ORDER-AMOUNT > 1000',
        "MOVE 'APPROVED' TO ORDER-STATUS.",
        "CALL 'PAYRISK'.",
        '*> TODO verify external dependency'
      ].join('\n')
    )
  });
  await page.getByRole('button', { name: 'Upload source' }).click();
  await expect(page.getByRole('listitem').filter({ hasText: 'analysis.cbl' })).toBeVisible();

  await page.getByRole('button', { name: 'Run static analysis' }).click();
  const candidate = page.getByRole('button').filter({ hasText: 'Conditional rule at line 2' });
  await expect(candidate).toBeVisible({ timeout: 10_000 });
  await candidate.click();

  await expect(page.locator('.source-code .is-highlighted')).toContainText('IF ORDER-AMOUNT > 1000');
});
