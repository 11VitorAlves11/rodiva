import { defineConfig, devices } from "@playwright/test";

/**
 * End-to-end tests run against a real stack: the API, the database and the app,
 * exactly as `docker compose -f docker-compose.dev.yml up` brings them up.
 *
 * They are kept out of `npm test` — vitest owns `src/**` and needs no services —
 * so a unit run stays fast and offline. `npm run test:e2e` runs these.
 */
const baseURL = process.env.E2E_BASE_URL ?? "http://localhost:5173";

export default defineConfig({
  testDir: "./e2e",
  // A journey that leaves records behind cannot share a household with another
  // one running at the same time, so each file gets its own worker and its own
  // freshly registered account.
  fullyParallel: false,
  workers: 1,
  retries: process.env.CI ? 1 : 0,
  timeout: 60_000,
  expect: { timeout: 10_000 },
  reporter: process.env.CI ? [["github"], ["list"]] : [["list"]],
  use: {
    baseURL,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
});
