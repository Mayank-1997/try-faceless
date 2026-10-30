/**
 * E2E UI test for the complete workflow lifecycle.
 *
 * Prerequisites:
 *   - Backend running on http://localhost:8000
 *   - Frontend running on http://localhost:3000
 *
 * Tests:
 *   1. Create project via UI → Start workflow via UI → Advance through all
 *      13 steps via UI (clicking "Next Step") → Verify each step renders →
 *      Verify completion
 *   2. Verify completed project UI state and progress visualization
 *   3. Test cancel and restart via UI
 *   4. Test retry step via UI
 */

import { test, expect, type Page } from '@playwright/test'

const API_BASE = process.env.API_BASE_URL ?? 'http://localhost:8000/api/v1'
const FRONTEND_URL = process.env.FRONTEND_URL ?? 'http://localhost:3000'

const STEP_LABELS = [
  'Initialization',
  'Research',
  'Scripting',
  'Storyboard',
  'Scene Planning',
  'Asset Generation',
  'Voice Generation',
  'Subtitles',
  'Rendering',
  'Thumbnail',
  'SEO',
  'Publishing',
  'Completed',
]

const UUID_RE = /\/projects\/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/

// ─── Helpers ───────────────────────────────────────────────

async function apiRequest(method: string, path: string, token?: string, body?: any) {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' }
  if (token) headers['Authorization'] = `Bearer ${token}`
  const resp = await fetch(`${API_BASE}${path}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  })
  const text = await resp.text()
  try {
    return { status: resp.status, data: JSON.parse(text) }
  } catch {
    return { status: resp.status, data: { raw: text } }
  }
}

async function loginUser(email: string, password: string) {
  const { data } = await apiRequest('POST', '/auth/login', undefined, { email, password })
  return data
}

function installAuthHook(page: Page, authData: any) {
  page.addInitScript((data) => {
    localStorage.setItem('auth-storage', JSON.stringify({
      state: {
        user: data.user,
        accessToken: data.access_token,
        refreshToken: data.refresh_token,
        isAuthenticated: true,
        isLoading: false,
      },
      version: 0,
    }))
  }, authData)
}

async function freshAuth(page: Page, email: string, password: string) {
  const authData = await loginUser(email, password)
  installAuthHook(page, authData)
  return { token: authData.access_token, authData }
}

async function openProject(page: Page, projectId: string, expectedTitle: string) {
  await page.goto(`${FRONTEND_URL}/projects/${projectId}`)
  await page.waitForLoadState('networkidle')
  await expect(page.locator('h1')).toContainText(expectedTitle, { timeout: 15_000 })
}

// ─── Tests ─────────────────────────────────────────────────

test.describe('Workflow E2E - Full Lifecycle', () => {
  const password = 'TestPass123!'
  let email: string
  let username: string
  let projectId: string
  let token: string

  test.beforeAll(async () => {
    const ts = Date.now()
    email = `e2e_ui_${ts}@example.com`
    username = `e2e_ui_${ts}`

    await apiRequest('POST', '/auth/register', undefined, {
      email, username, password, first_name: 'E2E', last_name: 'Tester',
    })
  })

  test('1. Create project via UI, start workflow via UI, advance through all steps via UI, verify completion', async ({ page }) => {
    test.setTimeout(180_000) // 3 minutes for 13 UI-driven steps
    const { token: tok } = await freshAuth(page, email, password)
    token = tok

    // ── Create project via UI ──
    await page.goto(`${FRONTEND_URL}/projects/new`)
    await page.waitForLoadState('networkidle')

    await page.getByText('YouTube Video').first().click()
    await page.getByRole('button', { name: 'Next' }).click()

    await page.waitForSelector('input[placeholder="My Awesome Video"]', { timeout: 10_000 })
    await page.locator('input[placeholder="My Awesome Video"]').fill('E2E UI Workflow Test')
    await page.locator('textarea[placeholder="Describe what this project is about..."]').fill('E2E test project')
    await page.getByRole('button', { name: 'Next' }).click()

    await page.waitForSelector('text=Review & Create', { timeout: 10_000 })

    const createResponsePromise = page.waitForResponse(
      (r) => r.url().includes('/projects') && !r.url().includes('/projects/') && r.request().method() === 'POST',
      { timeout: 30_000 }
    )
    await page.getByRole('button', { name: 'Create Project' }).click()
    const createResponse = await createResponsePromise
    expect([200, 201]).toContain(createResponse.status())

    await page.waitForURL(UUID_RE, { timeout: 30_000 })
    await page.waitForLoadState('networkidle')

    const url = page.url()
    projectId = url.split('/projects/')[1].split('/')[0].split('?')[0]
    console.log(`  Project ID: ${projectId}`)

    await expect(page.locator('h1')).toContainText('E2E UI Workflow Test')
    await expect(page.locator('text=draft').first()).toBeVisible()

    // ── Start workflow via UI ──
    await expect(page.getByRole('button', { name: 'Start Workflow' })).toBeVisible({ timeout: 10_000 })

    const startResponsePromise = page.waitForResponse(
      (r) => r.url().includes('/workflow/start') && r.request().method() === 'POST',
      { timeout: 15_000 }
    )
    await page.getByRole('button', { name: 'Start Workflow' }).click()
    const startResponse = await startResponsePromise
    console.log(`  Start workflow API: ${startResponse.status()}`)
    expect(startResponse.status()).toBe(200)

    // Reload to ensure UI picks up the workflow state from the API
    await page.reload()
    await page.waitForLoadState('networkidle')
    await expect(page.getByRole('button', { name: 'Next Step' })).toBeVisible({ timeout: 15_000 })

    // ── Advance through all 13 steps via UI (clicking "Next Step") ──
    for (let i = 0; i < STEP_LABELS.length - 1; i++) {
      const currentLabel = STEP_LABELS[i]
      const nextLabel = STEP_LABELS[i + 1]
      console.log(`  Step ${i + 1}/${STEP_LABELS.length}: ${currentLabel} → advancing to ${nextLabel}`)

      // Verify the current step label is visible somewhere on the page
      await expect(page.locator(`text=${currentLabel}`).first()).toBeVisible({ timeout: 15_000 })

      // Click "Next Step" to advance
      const advanceResponsePromise = page.waitForResponse(
        (r) => r.url().includes('/workflow/advance') && r.request().method() === 'POST',
        { timeout: 15_000 }
      )
      await page.getByRole('button', { name: 'Next Step' }).click()
      const advanceResponse = await advanceResponsePromise
      expect(advanceResponse.status()).toBe(200)

      // Wait for UI to update — reload to ensure fresh state
      await page.reload()
      await page.waitForLoadState('networkidle')

      // Verify the next step label is now visible
      await expect(page.locator(`text=${nextLabel}`).first()).toBeVisible({ timeout: 15_000 })
      console.log(`  ✓ UI now shows: ${nextLabel}`)
    }

    // ── Verify workflow is completed ──
    await expect(page.locator('text=Workflow Complete').first()).toBeVisible({ timeout: 15_000 })

    // ── Verify API state ──
    const { status: ps, data: pd } = await apiRequest('GET', `/projects/${projectId}`, token)
    expect(ps).toBe(200)
    expect(pd.status).toBe('completed')
    expect(pd.current_step).toBe('completed')

    const { status: ws, data: wd } = await apiRequest('GET', `/projects/${projectId}/workflow`, token)
    expect(ws).toBe(200)
    expect(wd.status).toBe('completed')
    expect(wd.completed_at).toBeTruthy()
  })

  test('2. Verify completed project UI state and progress visualization', async ({ page }) => {
    const { token: tok } = await freshAuth(page, email, password)
    token = tok

    await openProject(page, projectId, 'E2E UI Workflow Test')

    await expect(page.locator('text=completed').first()).toBeVisible({ timeout: 15_000 })
    await expect(page.getByRole('button', { name: 'Start Workflow' })).not.toBeVisible({ timeout: 5_000 })
    await expect(page.locator('text=Workflow Complete').first()).toBeVisible({ timeout: 10_000 })

    await page.waitForSelector('text=Workflow Progress', { timeout: 10_000 })
    for (const label of STEP_LABELS) {
      await expect(page.locator(`text=${label}`).first()).toBeVisible()
    }
  })

  test('3. Test cancel and restart via UI on a new project', async ({ page }) => {
    const { token: tok } = await freshAuth(page, email, password)
    token = tok

    const { data: proj } = await apiRequest('POST', '/projects', token, {
      title: 'E2E Cancel Restart Test',
      content_type: 'youtube_video',
      video_style: 'mixed',
    })
    const project2Id = proj.id

    await apiRequest('POST', `/projects/${project2Id}/workflow/start`, token)
    await apiRequest('POST', `/projects/${project2Id}/workflow/advance`, token)

    await openProject(page, project2Id, 'E2E Cancel Restart Test')
    await expect(page.getByRole('button', { name: 'Next Step' })).toBeVisible({ timeout: 15_000 })

    // ── Test Retry via UI ──
    const retryBtn = page.getByRole('button', { name: 'Retry Step' })
    await expect(retryBtn).toBeVisible()

    const retryResponsePromise = page.waitForResponse(
      (r) => r.url().includes('/workflow/retry') && r.request().method() === 'POST',
      { timeout: 15_000 }
    )
    await retryBtn.click()
    const retryResponse = await retryResponsePromise
    expect(retryResponse.status()).toBe(200)

    // Reload to ensure UI picks up the retry state
    await page.reload()
    await page.waitForLoadState('networkidle')
    await expect(page.getByRole('button', { name: 'Next Step' })).toBeVisible({ timeout: 15_000 })

    // ── Cancel workflow via UI ──
    const cancelBtn = page.getByRole('button', { name: 'Cancel Workflow' })
    await expect(cancelBtn).toBeVisible()

    const cancelResponsePromise = page.waitForResponse(
      (r) => r.url().includes('/workflow/cancel') && r.request().method() === 'POST',
      { timeout: 15_000 }
    )
    await cancelBtn.click()
    const cancelResponse = await cancelResponsePromise
    expect(cancelResponse.status()).toBe(200)

    // Reload to ensure UI picks up the cancelled state
    await page.reload()
    await page.waitForLoadState('networkidle')

    await expect(page.locator('text=cancelled').first()).toBeVisible({ timeout: 15_000 })

    const { data: projCheck } = await apiRequest('GET', `/projects/${project2Id}`, token)
    expect(projCheck.status).toBe('cancelled')

    // ── Verify "Start Workflow" button reappears (restart capability) ──
    await expect(page.getByRole('button', { name: 'Start Workflow' })).toBeVisible({ timeout: 15_000 })

    // ── Restart workflow via UI ──
    const restartResponsePromise = page.waitForResponse(
      (r) => r.url().includes('/workflow/start') && r.request().method() === 'POST',
      { timeout: 15_000 }
    )
    await page.getByRole('button', { name: 'Start Workflow' }).click()
    const restartResponse = await restartResponsePromise
    expect(restartResponse.status()).toBe(200)

    // Reload to ensure UI picks up the new workflow state
    await page.reload()
    await page.waitForLoadState('networkidle')
    await expect(page.getByRole('button', { name: 'Next Step' })).toBeVisible({ timeout: 15_000 })

    // Verify API state — project should be back to researching
    const { data: projCheck2 } = await apiRequest('GET', `/projects/${project2Id}`, token)
    expect(projCheck2.status).toBe('researching')
  })

  test('4. Test retry step via UI on a new project', async ({ page }) => {
    const { token: tok } = await freshAuth(page, email, password)
    token = tok

    const { data: proj } = await apiRequest('POST', '/projects', token, {
      title: 'E2E Retry Step Test',
      content_type: 'youtube_video',
      video_style: 'mixed',
    })
    const retryProjectId = proj.id

    await apiRequest('POST', `/projects/${retryProjectId}/workflow/start`, token)
    await apiRequest('POST', `/projects/${retryProjectId}/workflow/advance`, token)

    await openProject(page, retryProjectId, 'E2E Retry Step Test')
    await expect(page.getByRole('button', { name: 'Next Step' })).toBeVisible({ timeout: 15_000 })

    // ── Test Retry via UI ──
    const retryBtn = page.getByRole('button', { name: 'Retry Step' })
    await expect(retryBtn).toBeVisible()

    const retryResponsePromise = page.waitForResponse(
      (r) => r.url().includes('/workflow/retry') && r.request().method() === 'POST',
      { timeout: 15_000 }
    )
    await retryBtn.click()
    const retryResponse = await retryResponsePromise
    expect(retryResponse.status()).toBe(200)

    // Reload to ensure UI picks up the retry state
    await page.reload()
    await page.waitForLoadState('networkidle')
    await expect(page.getByRole('button', { name: 'Next Step' })).toBeVisible({ timeout: 15_000 })
  })
})
