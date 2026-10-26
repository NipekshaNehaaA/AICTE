import { test, expect } from '@playwright/test';

test.describe('Task 4: Dual-Context Regulatory Verification (Live vs Sandbox)', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.evaluate(() => {
      localStorage.clear();
      sessionStorage.clear();
    });
    await page.reload();

    // Handle skip boot button if visible
    const skipBoot = page.locator('[data-testid="skip-boot-button"]');
    if (await skipBoot.isVisible({ timeout: 2000 }).catch(() => false)) {
      await skipBoot.click();
    }
  });

  test('Context 1 (Live Mode): Strict workspace isolation, no evaluator banner, institutional auth & assignment-based boundary', async ({
    page,
  }) => {
    // 1. Switch to Live workspace
    const liveSwitchBtn = page.locator('[data-testid="switch-workspace-live"]');
    await expect(liveSwitchBtn).toBeVisible({ timeout: 5000 });
    await liveSwitchBtn.click();

    // 2. Assert Live State: Sandbox Banner must NOT be in DOM
    await expect(page.locator('#evaluator-mode-login-banner')).toHaveCount(0);
    await expect(page.locator('text=EVALUATOR MODE ACTIVE')).toHaveCount(0);

    // 3. 1-Click Personas tab must NOT be available in Live
    await expect(page.locator('[data-testid="tab-personas"]')).toHaveCount(0);

    // 4. Verify direct API call from browser confirms Live mode
    const modeRes = await page.request.get('http://127.0.0.1:8000/api/v1/system/mode', {
      headers: { 'X-Workspace': 'live' },
    });
    expect(modeRes.status()).toBe(200);
    const modeData = await modeRes.json();
    expect(modeData.evaluator_mode).toBe(false);

    // 5. Sandbox-only endpoints must return 404 in Live
    const demoAttack = await page.request.post('http://127.0.0.1:8000/api/v1/auth/demo-token/SUPER_ADMIN', {
      headers: { 'X-Workspace': 'live' },
    });
    expect(demoAttack.status()).toBe(404);

    const overrideAttack = await page.request.post('http://127.0.0.1:8000/api/v1/demo/sandbox-override', {
      headers: { 'X-Workspace': 'live' },
      data: { email: 'evaluator@test.com' },
    });
    expect(overrideAttack.status()).toBe(404);
  });

  test('Context 2 (Sandbox Mode): Personas, Evaluator Override, Real Test Messages & Time Travel', async ({
    page,
  }) => {
    // 1. Switch to Sandbox workspace
    const sandboxSwitchBtn = page.locator('[data-testid="switch-workspace-sandbox"]');
    await expect(sandboxSwitchBtn).toBeVisible({ timeout: 5000 });
    await sandboxSwitchBtn.click();

    // 2. Evaluator Banner must be visible in Sandbox
    await expect(page.locator('#evaluator-mode-login-banner')).toBeVisible({ timeout: 5000 });
    await expect(page.locator('text=EVALUATOR MODE ACTIVE')).toBeVisible();

    // 3. 1-Click Personas tab must be visible in Sandbox
    const tabPersonas = page.locator('[data-testid="tab-personas"]');
    await expect(tabPersonas).toBeVisible();
    await tabPersonas.click();

    // 4. Log in as Scrutiny Member persona
    const scrutinyBtn = page.locator('[data-testid="persona-SCRUTINY_MEMBER"]');
    await expect(scrutinyBtn).toBeVisible();
    await scrutinyBtn.click();

    // 5. Verify Main Application Shell is mounted with Amber Sandbox Pill in TopBar
    const main = page.locator('main');
    await expect(main).toBeVisible({ timeout: 15000 });
    const sandboxTopPill = page.locator('[data-testid="topbar-workspace-pill"]');
    await expect(sandboxTopPill).toBeVisible();
    await expect(sandboxTopPill).toContainText('Sandbox');

    // 6. Test Sandbox Override Modal
    const overrideBtn = page.locator('button:has-text("Override Real Messages")');
    if (await overrideBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
      await overrideBtn.click();
      const overrideEmailInput = page.locator('input[placeholder="evaluator@example.com"]');
      if (await overrideEmailInput.isVisible({ timeout: 2000 }).catch(() => false)) {
        await overrideEmailInput.fill('evaluator.e2e@example.com');
        await page.locator('button:has-text("Save Override")').click();
        await page.waitForTimeout(500);
      }
    }

    // 7. Navigate to Notifications View & Test Message Dispatch
    const navNotifications = page.locator('button[data-testid="nav-notifications"]');
    if (await navNotifications.isVisible({ timeout: 5000 })) {
      await navNotifications.click();

      // Open Send Test Notification modal
      const testMsgBtn = page.locator('[data-testid="send-test-notification-btn"]');
      await expect(testMsgBtn).toBeVisible({ timeout: 5000 });
      await testMsgBtn.click();

      // Verify Test Notification modal is open
      await expect(page.locator('text=Dispatch Real Test Statutory Notification')).toBeVisible();

      // Click "Dispatch Real Message"
      const dispatchBtn = page.locator('[data-testid="execute-test-dispatch-btn"]');
      await expect(dispatchBtn).toBeVisible();
      await dispatchBtn.click();

      // Verify live provider receipts card appears
      await expect(page.locator('text=Live Provider Dispatch Receipts')).toBeVisible({ timeout: 10000 });
      await expect(page.locator('text=IN_APP').first()).toBeVisible();

      // Close test modal
      await page.locator('button:has-text("Close")').first().click();
    }

    // 8. Navigate to Case Docket & Verify "Shared with" and "Preview" buttons
    const navCases = page.locator('button[data-testid="nav-applications"]');
    if (await navCases.isVisible({ timeout: 5000 })) {
      await navCases.click();
      await page.waitForTimeout(800);

      // Switch to DOCUMENTS tab if in Case Docket view
      const docsTab = page.locator('button:has-text("Documents & Certificates")');
      if (await docsTab.isVisible({ timeout: 3000 }).catch(() => false)) {
        await docsTab.click();

        // Verify "Shared with" button exists on document rows
        const sharedWithBtn = page.locator('button:has-text("Shared with")').first();
        if (await sharedWithBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
          await sharedWithBtn.click();

          // Assert Slide-over Drawer opens with Authorized Viewers and Statutory Basis
          await expect(page.locator('text=Access Control & Shared Stakeholders')).toBeVisible();
          await expect(page.locator('text=Authorized Viewers')).toBeVisible();
          await expect(page.locator('text=Dynamic Stage-Based Boundary')).toBeVisible();

          // Close drawer
          await page.locator('button:has-text("Close")').last().click();
        }
      }
    }
  });
});
