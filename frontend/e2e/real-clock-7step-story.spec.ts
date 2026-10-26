import { test, expect } from '@playwright/test';

test.describe('Task 5: Real-Clock 7-Step Story E2E (Evaluator Mode OFF & Multi-Role Proof)', () => {
  test('Complete production portal verification with Evaluator Mode OFF and role transitions', async ({
    page,
  }) => {
    // -----------------------------------------------------------------------
    // PART 1: Production Portal Integrity (Evaluator Mode OFF)
    // -----------------------------------------------------------------------
    await page.goto('/');

    // Handle initial boot sequence if present
    const skipBoot = page.locator('[data-testid="skip-boot-button"]');
    if (await skipBoot.isVisible({ timeout: 2000 }).catch(() => false)) {
      await skipBoot.click();
    }

    // Ensure Evaluator Mode is OFF
    const evalButton = page.locator('button:has-text("Evaluator Mode:")');
    if (await evalButton.isVisible({ timeout: 3000 }).catch(() => false)) {
      const btnText = await evalButton.innerText();
      if (btnText.includes('ON')) {
        await evalButton.click();
        await expect(evalButton).toContainText('OFF');
      }
    }

    // Assert zero demo leaks on login page: 1-click personas tab must NOT exist
    await expect(page.locator('[data-testid="tab-personas"]')).toHaveCount(0);
    await expect(page.locator('text=1-Click Personas')).toHaveCount(0);
    await expect(page.locator('text=Quick fill credentials')).toHaveCount(0);

    // -----------------------------------------------------------------------
    // PART 2: Institution User Direct Password Login & Truthful Dashboard
    // -----------------------------------------------------------------------
    const emailInput = page.locator('input[type="email"]');
    const passwordInput = page.locator('input[type="password"]');
    await emailInput.fill('principal.110000001@fictional-aicte.edu.in');
    await passwordInput.fill('DemoPassword@123');
    await page.locator('button[type="submit"]:has-text("Sign In with Password")').click();

    // Verify main app renders
    const main = page.locator('main');
    await expect(main).toBeVisible({ timeout: 15000 });

    // Verify Institution User lands on Institution Tracker (Role-aware landing)
    await expect(page.locator('text=Compliance Health Score')).toBeVisible({ timeout: 8000 });
    await expect(page.locator('text=Apex Institute of Technology').first()).toBeVisible();
    await expect(page.locator('text=PID: 1-10000001').first()).toBeVisible();

    // Verify zero demo leaks in DOM while logged in as Institution User
    const instBodyText = await page.textContent('body');
    expect(instBodyText).not.toContain('R.V. College of Engineering');
    expect(instBodyText).not.toContain('EVALUATOR MODE ACTIVE');
    expect(instBodyText).not.toContain('Simulation Clock');
    expect(instBodyText).not.toContain('One-Click Scripted Scenario');

    // Sign out
    const logoutBtn = page.locator('button:has-text("Sign Out")');
    if (await logoutBtn.isVisible({ timeout: 2000 }).catch(() => false)) {
      await logoutBtn.click();
    } else {
      const signOutIcon = page.locator('button[title*="Sign Out"], button:has-text("Logout"), aside button:has-text("Sign Out")');
      if (await signOutIcon.first().isVisible({ timeout: 2000 }).catch(() => false)) {
        await signOutIcon.first().click();
      } else {
        await page.goto('/');
      }
    }

    // -----------------------------------------------------------------------
    // PART 3: Statutory Officer MFA Guard under Evaluator Mode OFF
    // -----------------------------------------------------------------------
    const emailOfficer = page.locator('input[type="email"]');
    await expect(emailOfficer).toBeVisible({ timeout: 8000 });

    // Attempting login as an AICTE Officer triggers statutory MFA TOTP verification
    await emailOfficer.fill('ro.swro@aicte-india.org');
    await page.locator('input[type="password"]').fill('DemoPassword@123');
    await page.locator('button[type="submit"]:has-text("Sign In with Password")').click();

    // Verify that production statutory MFA is strictly enforced
    await expect(page.locator('h3:has-text("Two-Factor Authentication")')).toBeVisible({ timeout: 10000 });
    await expect(page.locator('text=Enter 6-Digit Confirmation Code')).toBeVisible({ timeout: 5000 });

    // -----------------------------------------------------------------------
    // PART 4: Evaluator Mode Demonstration for Multi-Role Verification
    // -----------------------------------------------------------------------
    // Reset back to main login
    await page.goto('/');
    const skipBoot2 = page.locator('[data-testid="skip-boot-button"]');
    if (await skipBoot2.isVisible({ timeout: 2000 }).catch(() => false)) {
      await skipBoot2.click();
    }

    // Toggle Evaluator Mode ON to enable demonstration transitions
    const evalBtn = page.locator('button:has-text("Evaluator Mode:")');
    await expect(evalBtn).toBeVisible({ timeout: 5000 });
    await evalBtn.click();
    await expect(evalBtn).toContainText('ON');

    // Switch to 1-Click Personas tab
    const tabPersonas = page.locator('[data-testid="tab-personas"]');
    await expect(tabPersonas).toBeVisible({ timeout: 8000 });
    await tabPersonas.click();

    // 1. Regional Officer Persona
    const personaRO = page.locator('[data-testid="persona-REGIONAL_OFFICER"]');
    await expect(personaRO).toBeVisible();
    await personaRO.click();

    // Verify Officer lands on Applications Queue
    await expect(page.locator('text=Approval Workflow & Application Routing')).toBeVisible({ timeout: 15000 });
    // Officer sidebar footer must NOT display institution name or PID
    const officerSidebar = page.locator('aside');
    await expect(officerSidebar).toBeVisible();
    const officerSidebarText = await officerSidebar.textContent();
    expect(officerSidebarText).not.toContain('Apex Institute of Technology');
    expect(officerSidebarText).not.toContain('PID: 1-10000001');

    // Sign out to switch persona
    await page.goto('/');
    if (await skipBoot.isVisible({ timeout: 2000 }).catch(() => false)) {
      await skipBoot.click();
    }
    await page.locator('[data-testid="tab-personas"]').click();

    // 2. Auditor Persona
    const personaAuditor = page.locator('[data-testid="persona-AUDITOR"]');
    await expect(personaAuditor).toBeVisible();
    await personaAuditor.click();

    // Verify Auditor lands directly on Audit Ledger
    await expect(page.locator('text=Immutable Cryptographic Audit Trail')).toBeVisible({ timeout: 15000 });
    await expect(page.locator('button:has-text("Verify Chain")')).toBeVisible({ timeout: 8000 });
  });
});
