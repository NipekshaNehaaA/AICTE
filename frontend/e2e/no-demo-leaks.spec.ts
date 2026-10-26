import { test, expect } from '@playwright/test';

test.describe('Task 2: Production Portal Integrity (Evaluator Mode OFF)', () => {
  test('Assert zero demo hints, 1-click personas, time-travel, or demo labels anywhere in the DOM', async ({
    page,
  }) => {
    // 1. Visit root page
    await page.goto('/');

    // Handle initial boot sequence if visible
    const skipBoot = page.locator('[data-testid="skip-boot-button"]');
    if (await skipBoot.isVisible({ timeout: 2000 }).catch(() => false)) {
      await skipBoot.click();
    }

    // 2. Ensure Live workspace is active
    const liveSwitch = page.locator('[data-testid="switch-workspace-live"]');
    if (await liveSwitch.isVisible({ timeout: 2000 }).catch(() => false)) {
      await liveSwitch.click();
    }

    // 3. Verify Login View has zero demo leaks
    // 1-Click Personas tab must NOT exist
    await expect(page.locator('[data-testid="tab-personas"]')).toHaveCount(0);
    await expect(page.locator('text=1-Click Personas')).toHaveCount(0);
    await expect(page.locator('text=Quick fill credentials')).toHaveCount(0);

    // Email and Password should not be pre-filled with demo credentials
    const emailInput = page.locator('input[type="email"]');
    const passwordInput = page.locator('input[type="password"]');
    await expect(emailInput).toHaveValue('');
    await expect(passwordInput).toHaveValue('');

    // 4. Log in using institution user credentials (direct password login)
    await emailInput.fill('principal.110000001@fictional-aicte.edu.in');
    await passwordInput.fill('DemoPassword@123');
    await page.locator('button[type="submit"]:has-text("Sign In with Password")').click();

    // 5. Verify Main Application Shell is visible
    const main = page.locator('main');
    await expect(main).toBeVisible({ timeout: 15000 });

    // 6. Assert Evaluator Mode Banner is NOT in DOM
    await expect(page.locator('#evaluator-mode-banner')).toHaveCount(0);
    await expect(page.locator('text=EVALUATOR MODE ACTIVE')).toHaveCount(0);

    // 7. Assert Time-Travel controls are NOT in DOM
    await expect(page.locator('button:has-text("+1d")')).toHaveCount(0);
    await expect(page.locator('button:has-text("+7d")')).toHaveCount(0);
    await expect(page.locator('button:has-text("+30d")')).toHaveCount(0);
    await expect(page.locator('text=Simulation Clock')).toHaveCount(0);

    // 8. Assert Demo Script button and quick launch banners are NOT in DOM
    await expect(page.locator('button:has-text("Demo Script")')).toHaveCount(0);
    await expect(page.locator('text=One-Click Scripted Scenario')).toHaveCount(0);

    // 9. Assert 1-Click Role Switcher is NOT interactive/present in top bar
    await expect(page.locator('[data-testid="role-menu-button"]')).toHaveCount(0);
    await expect(page.locator('text=(Demo Only)')).toHaveCount(0);
    await expect(page.locator('text=Role Switcher')).toHaveCount(0);

    // 10. Assert "Sample values" banner is NOT in DOM
    await expect(page.locator('text=Sample values, configurable')).toHaveCount(0);

    // 11. Assert dev jargon is NOT present anywhere in DOM
    await expect(page.locator('text=Task 2 Real Engine')).toHaveCount(0);
    await expect(page.locator('text=Email Mock')).toHaveCount(0);
    await expect(page.locator('text=SMS Mock')).toHaveCount(0);
    await expect(page.locator('text=WhatsApp Mock')).toHaveCount(0);
    await expect(page.locator('text=SMTP Mock')).toHaveCount(0);
    await expect(page.locator('button:has-text("Simulate Tampering")')).toHaveCount(0);
  });
});
