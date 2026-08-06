import { defineConfig, devices } from '@playwright/test';

const apiEnv = {
  ...process.env,
  APP_ENV: 'development',
  AUTO_CREATE_DB: 'true',
  COOKIE_SECURE: 'false',
  DATABASE_URL: 'sqlite:///./test-tmp/e2e.db',
  DEV_SEED_EMAIL: 'admin@example.com',
  DEV_SEED_PASSWORD: 'phase1-e2e-password',
  CORS_ALLOWED_ORIGINS: 'http://127.0.0.1:15173'
};

const pythonCommand =
  process.platform === 'win32' ? '.\\.venv\\Scripts\\python.exe' : 'python';

export default defineConfig({
  testDir: './tests/e2e',
  timeout: 30_000,
  expect: {
    timeout: 5_000
  },
  use: {
    baseURL: 'http://127.0.0.1:15173',
    trace: 'retain-on-failure'
  },
  webServer: [
    {
      command: `${pythonCommand} -m uvicorn apps.api.app.main:app --host 127.0.0.1 --port 18000`,
      url: 'http://127.0.0.1:18000/api/v1/health',
      reuseExistingServer: false,
      timeout: 30_000,
      env: apiEnv
    },
    {
      command: 'npm run web:dev -- --port 15173',
      url: 'http://127.0.0.1:15173',
      reuseExistingServer: false,
      timeout: 30_000,
      env: {
        ...process.env,
        VITE_API_BASE_URL: 'http://127.0.0.1:18000/api/v1'
      }
    }
  ],
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] }
    }
  ]
});
