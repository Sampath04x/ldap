import { test, expect } from '@playwright/test'

const BASE = process.env.BASE_URL ?? 'http://localhost:3000'

test.describe('Diagnostic Workflow', () => {
  test('search user → open detail → run diagnostic → see result', async ({ page }) => {
    // 1. Load landing page
    await page.goto(BASE)
    await expect(page.locator('input[placeholder*="Search"]')).toBeVisible()
    
    // 2. Search for seed-deterministic user
    await page.fill('input[placeholder*="Search"]', 'usr_0000001')
    await page.keyboard.press('Enter')
    await page.waitForURL('**/search**')
    
    // 3. Click first user result
    const firstUser = page.locator('[data-testid="search-result-user"]').first()
    await expect(firstUser).toBeVisible({ timeout: 10000 })
    await firstUser.click()
    await page.waitForURL('**/users/**')
    
    // 4. Verify user detail page
    await expect(page.locator('[data-testid="user-display-name"]')).toBeVisible()
    await expect(page.locator('[data-testid="status-badge-active"]')).toBeVisible()
    
    // 5. Click Run Diagnostic
    await page.click('[data-testid="run-diagnostic-btn"]')
    await page.waitForURL('**/diagnostics**')
    
    // 6. Select healthy firewall fw-0001 and run
    await page.waitForSelector('[data-testid="firewall-select"]')
    await page.selectOption('[data-testid="firewall-select"]', { label: 'fw-0001.corp.internal' })
    await page.click('[data-testid="run-diagnostic-submit"]')
    
    // 7. Wait for result & assert HEALTHY status
    await expect(page.locator('[data-testid="diagnostic-overall-status"]')).toBeVisible({ timeout: 15000 })
    await expect(page.locator('[data-testid="diagnostic-overall-status"]')).toContainText('HEALTHY')
    
    // 8. Verify checks are shown
    await expect(page.locator('[data-testid="diagnostic-check"]').first()).toBeVisible()
    await expect(page.locator('[data-testid="diagnostic-summary"]')).toBeVisible()
  })
  
  test('search firewall roster', async ({ page }) => {
    await page.goto(`${BASE}/search?q=fw-0001&type=firewall`)
    await expect(page.locator('[data-testid="search-result-firewall"]').first()).toBeVisible({ timeout: 10000 })
  })
})
