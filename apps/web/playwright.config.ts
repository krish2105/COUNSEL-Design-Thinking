import { defineConfig, devices } from "@playwright/test";

/* The dev server and the API are expected to be running (`make api`, `make web`).
 * Playwright starts the web server itself so `npm run e2e` works from cold, but
 * it deliberately does NOT start the API: a browser test that silently boots a
 * backend hides the fact that the backend is a separate deployable. */
export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  workers: 1,
  reporter: process.env.CI ? "list" : [["list"]],
  use: {
    baseURL: "http://localhost:3000",
    trace: "retain-on-failure",
  },
  projects: [
    { name: "desktop", use: { ...devices["Desktop Chrome"], viewport: { width: 1280, height: 900 } } },
    { name: "mobile", use: { ...devices["Pixel 7"] } },
  ],
  webServer: {
    command: "npm run dev",
    url: "http://localhost:3000",
    reuseExistingServer: true,
    timeout: 120_000,
  },
});
