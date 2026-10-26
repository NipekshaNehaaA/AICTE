import { test, expect } from '@playwright/test';

test.describe('Production Portal Integrity: Login Page Security', () => {
  test('in production mode the login page has no Evaluator toggle, and clicking around cannot enable it', async ({
    page,
  }) => {
    // 1. Visit root page
    await page.goto('/');

    // Handle initial boot sequence if visible
    const skipBoot = page.locator('[data-testid="skip-boot-button"]');
    if (await skipBoot.isVisible({ timeout: 2000 }).catch(() => false)) {
      await skipBoot.click();
    }

    // Switch to Live workspace for production integrity assertion
    const liveSwitch = page.locator('[data-testid="switch-workspace-live"]');
    if (await liveSwitch.isVisible({ timeout: 2000 }).catch(() => false)) {
      await liveSwitch.click();
    }

    // 2. Assert NO Evaluator toggle button anywhere on the login page
    await expect(page.locator('button:has-text("Evaluator Mode:")')).toHaveCount(0);
    await expect(page.locator('button:has-text("Disable Evaluator Mode")')).toHaveCount(0);
    await expect(page.locator('#evaluator-mode-login-banner')).toHaveCount(0);
    await expect(page.locator('#evaluator-mode-banner')).toHaveCount(0);
    await expect(page.locator('text=EVALUATOR MODE ACTIVE')).toHaveCount(0);

    // 3. Assert 1-Click Personas and demo quick fill buttons do NOT exist
    await expect(page.locator('[data-testid="tab-personas"]')).toHaveCount(0);
    await expect(page.locator('text=1-Click Personas')).toHaveCount(0);
    await expect(page.locator('text=Quick fill credentials')).toHaveCount(0);

    // 4. Click around tabs (signup, verify, forgot password, back to login)
    const signupTab = page.locator('button:has-text("Institution Sign-Up")');
    if (await signupTab.isVisible()) {
      await signupTab.click();
      await expect(page.locator('button:has-text("Evaluator Mode:")')).toHaveCount(0);
      await expect(page.locator('text=EVALUATOR MODE ACTIVE')).toHaveCount(0);
    }

    const forgotTab = page.locator('button:has-text("Forgot Password")');
    if (await forgotTab.isVisible()) {
      await forgotTab.click();
      await expect(page.locator('button:has-text("Evaluator Mode:")')).toHaveCount(0);
      await expect(page.locator('text=EVALUATOR MODE ACTIVE')).toHaveCount(0);
    }

    const loginTab = page.locator('button:has-text("Institutional Login")');
    if (await loginTab.isVisible()) {
      await loginTab.click();
      await expect(page.locator('button:has-text("Evaluator Mode:")')).toHaveCount(0);
      await expect(page.locator('text=EVALUATOR MODE ACTIVE')).toHaveCount(0);
    }

    // 5. Direct API attack from browser context must return 404
    const apiAttack = await page.request.post('http://127.0.0.1:8000/api/v1/system/evaluator-mode', {
      data: { enabled: true },
    }).catch(() => null);
    if (apiAttack) {
      expect(apiAttack.status()).toBe(404);
    }

    // Mode check must return only evaluator_mode: false
    const modeResp = await page.request.get('http://127.0.0.1:8000/api/v1/system/mode').catch(() => null);
    if (modeResp) {
      const modeData = await modeResp.json();
      expect(modeData).toEqual({ evaluator_mode: false });
    }
  });
});
