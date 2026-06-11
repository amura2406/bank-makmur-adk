import { defineConfig, devices } from '@playwright/test';

process.env.VITE_API_URL = process.env.VITE_API_URL || 'http://127.0.0.1:8080';

/**
 * See https://playwright.dev/docs/test-configuration.
 */
export default defineConfig({
  testDir: './e2e',
  /* Run tests in files in parallel */
  fullyParallel: true,
  /* Fail the build on CI if you accidentally left test.only in the source code. */
  forbidOnly: !!process.env.CI,
  /* Retry on CI only */
  retries: process.env.CI ? 2 : 0,
  /* Opt out of parallel tests on CI. */
  workers: process.env.CI ? 1 : undefined,
  /* Reporter to use. See https://playwright.dev/docs/test-reporters */
  reporter: 'html',
  /* Shared settings for all the projects below. See https://playwright.dev/docs/api/class-testoptions. */
  use: {
    /* Base URL to use in actions like `await page.goto('/')`. */
    baseURL: 'http://127.0.0.1:5173',

    /* Collect trace when retrying a failed test. See https://playwright.dev/docs/trace-viewer */
    trace: 'on-first-retry',
  },

  /* Configure projects for major browsers */
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],

  /* Run your local dev server before starting the tests */
  webServer: [
    {
      command: 'npm run dev',
      url: 'http://127.0.0.1:5173',
      reuseExistingServer: !process.env.CI,
      env: {
        VITE_API_URL: 'http://127.0.0.1:8080',
      },
      timeout: 120000,
    },
    {
      command: 'uv run uvicorn app.fast_api_app:app --host 127.0.0.1 --port 8080',
      url: 'http://127.0.0.1:8080/docs',
      reuseExistingServer: !process.env.CI,
      cwd: '../app',
      env: {
        INTEGRATION_TEST: 'TRUE',
        MOCK_API_URL: 'http://127.0.0.1:8000',
        ALLOW_ORIGINS: '*',
      },
      timeout: 120000,
    },
    {
      command: 'uv run python -m mock_api.populate && uv run uvicorn mock_api.main:app --host 127.0.0.1 --port 8000',
      url: 'http://127.0.0.1:8000/docs',
      reuseExistingServer: !process.env.CI,
      cwd: '..',
      env: {
        PYTHONPATH: '.',
      },
      timeout: 120000,
    },
  ],
});
