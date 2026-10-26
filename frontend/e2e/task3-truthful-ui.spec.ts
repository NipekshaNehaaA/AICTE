import { test, expect } from '@playwright/test';

async function loginAs(page: any, role: string) {
  await page.goto('/');

  // Handle System Boot page if active
  const skipButton = page.locator('[data-testid="skip-boot-button"]');
  if (await skipButton.isVisible({ timeout: 2000 }).catch(() => false)) {
    await skipButton.click();
  }

  // Ensure Evaluator Mode is ON to activate 1-Click Personas
  const evalBtn = page.locator('button:has-text("Evaluator Mode:")');
  if (await evalBtn.isVisible({ timeout: 2000 }).catch(() => false)) {
    const text = await evalBtn.innerText();
    if (text.includes('OFF')) {
      await evalBtn.click();
    }
  }

  // Switch to 1-Click Personas tab
  const tabPersonas = page.locator('[data-testid="tab-personas"]');
  await expect(tabPersonas).toBeVisible({ timeout: 10000 });
  await tabPersonas.click();

  // Click target persona
  const personaButton = page.locator(`[data-testid="persona-${role}"]`);
  await expect(personaButton).toBeVisible({ timeout: 5000 });
  await personaButton.click();
}

test.describe('Task 3: Truthful UI Data & Role-Aware Landing', () => {
  test('Institution User lands on institution tracker and displays dynamic institution name/PID', async ({ page }) => {
    await loginAs(page, 'INSTITUTION_USER');

    // Verify user is logged in
    await expect(page.locator('text=Dr. Ramesh Kumar')).toBeVisible({ timeout: 10000 });

    // 1. Verify NO hardcoded R.V. College of Engineering in DOM
    const bodyText = await page.textContent('body');
    expect(bodyText).not.toContain('R.V. College of Engineering');
    expect(bodyText).not.toContain('PID: 1-109283741');

    // 2. Verify dynamic institution name and PID in sidebar
    await expect(page.locator('text=Apex Institute of Technology').first()).toBeVisible();
    await expect(page.locator('text=PID: 1-10000001').first()).toBeVisible();

    // 3. Verify Institution User lands on their own dashboard (NOT national command center)
    await expect(page.locator('text=Compliance Health Score')).toBeVisible();
    await expect(page.locator('text=National Command & Control')).not.toBeVisible();
  });

  test('Officer lands on applications queue and does not display institution name', async ({ page }) => {
    await loginAs(page, 'REGIONAL_OFFICER');

    // Verify logged in
    await expect(page.locator('text=Dr. K. S. Venkatesh')).toBeVisible({ timeout: 10000 });

    // 1. Verify Officer landed on applications queue (active tab is applications)
    await expect(page.locator('text=Approval Workflow & Application Routing')).toBeVisible({ timeout: 8000 });

    // 2. Verify officer footer in sidebar does NOT display institution name or PID
    const sidebar = page.locator('aside');
    await expect(sidebar).toBeVisible();
    const sidebarText = await sidebar.textContent();
    expect(sidebarText).not.toContain('Apex Institute of Technology');
    expect(sidebarText).not.toContain('PID: 1-10000001');
  });

  test('Auditor lands on audit ledger', async ({ page }) => {
    await loginAs(page, 'AUDITOR');

    // Verify logged in and landed on audit ledger
    await expect(page.locator('text=Smt. Priya Balan')).toBeVisible({ timeout: 10000 });
    await expect(page.locator('text=Immutable Cryptographic Audit Trail')).toBeVisible({ timeout: 8000 });
  });
});
