import { test, expect } from '@playwright/test';

const DEMO_PERSONAS = [
  { role: 'REGIONAL_OFFICER', title: 'Regional Officer' },
  { role: 'REGIONAL_DIRECTOR', title: 'Regional Director' },
  { role: 'SCRUTINY_MEMBER', title: 'Scrutiny Committee Member' },
  { role: 'COMMITTEE_MEMBER', title: 'EVC Committee Expert' },
  { role: 'SAC_SHC_MEMBER', title: 'SAC/SHC Appellate Member' },
  { role: 'BUREAU_OFFICER', title: 'Bureau Officer' },
  { role: 'BUREAU_HEAD', title: 'Bureau Head' },
  { role: 'INSTITUTION_USER', title: 'Technical Institution' },
  { role: 'AUDITOR', title: 'Statutory Compliance Auditor' },
  { role: 'SUPER_ADMIN', title: 'Member Secretary' },
];

test.describe('AICTE Persona Smoke & Robustness Verification', () => {
  for (const persona of DEMO_PERSONAS) {
    test(`Persona: ${persona.role} - logs in, visits all sidebar views without console errors, 4xx/5xx or blank screen`, async ({
      page,
    }) => {
      const consoleErrors: string[] = [];
      const httpErrors: string[] = [];

      // Monitor console errors and unhandled exceptions
      page.on('console', (msg) => {
        if (msg.type() === 'error') {
          const text = msg.text();
          // Filter benign development noise if any (e.g. Next.js hydration or chrome extensions)
          if (!text.includes('Download the React DevTools') && !text.includes('favicon.ico')) {
            consoleErrors.push(text);
          }
        }
      });

      page.on('pageerror', (err) => {
        consoleErrors.push(err.message);
      });

      // Monitor HTTP network responses
      page.on('response', (res) => {
        const status = res.status();
        const url = res.url();
        // Ignore external or non-app asset 404s (e.g. favicon)
        if (status >= 400 && !url.includes('favicon.ico')) {
          httpErrors.push(`${status} ${res.statusText()} on ${url}`);
        }
      });

      // Step 1: Open Application
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

      // Step 2: Switch to 1-Click Personas tab
      const tabPersonas = page.locator('[data-testid="tab-personas"]');
      await expect(tabPersonas).toBeVisible({ timeout: 10000 });
      await tabPersonas.click();

      // Step 3: Click the target Persona button
      const personaButton = page.locator(`[data-testid="persona-${persona.role}"]`);
      await expect(personaButton).toBeVisible();
      await personaButton.click();

      // Step 4: Verify Full Application Shell loaded
      const main = page.locator('main');
      await expect(main).toBeVisible({ timeout: 10000 });
      const sidebar = page.locator('aside');
      await expect(sidebar).toBeVisible();

      // Ensure Error Boundary is not active
      const errorBoundaryTitle = page.locator('text=Application View Temporarily Interrupted');
      await expect(errorBoundaryTitle).toHaveCount(0);

      // Step 5: Enumerate and click every visible sidebar view for this persona
      const navButtons = page.locator('aside nav button[data-testid^="nav-"]');
      const count = await navButtons.count();
      expect(count).toBeGreaterThan(0);

      for (let i = 0; i < count; i++) {
        const navBtn = navButtons.nth(i);
        const navId = await navBtn.getAttribute('data-testid');
        await navBtn.click();

        // Brief wait for React component mounting and network requests
        await page.waitForTimeout(600);

        // Verify main view is visible and NOT blank
        await expect(main).toBeVisible();
        const textContent = await main.innerText();
        expect(
          textContent.trim().length,
          `View ${navId} should render meaningful content, not a blank screen`
        ).toBeGreaterThan(15);

        // Verify Error Boundary never caught an uncaught exception
        await expect(errorBoundaryTitle).toHaveCount(0);
      }

      // Step 6: Log out cleanly for next test
      const roleMenuBtn = page.locator('[data-testid="role-menu-button"]');
      if (await roleMenuBtn.isVisible()) {
        await roleMenuBtn.click();
        const logoutBtn = page.locator('[data-testid="logout-button"]');
        if (await logoutBtn.isVisible()) {
          await logoutBtn.click();
        }
      }

      // Assert no unhandled console errors or failed HTTP requests occurred
      expect(
        consoleErrors,
        `Expected 0 console errors for ${persona.role}, found: ${consoleErrors.join(', ')}`
      ).toEqual([]);

      expect(
        httpErrors,
        `Expected 0 4xx/5xx HTTP errors for ${persona.role}, found: ${httpErrors.join(', ')}`
      ).toEqual([]);
    });
  }
});
