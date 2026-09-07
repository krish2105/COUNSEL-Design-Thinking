import { defineConfig, devices } from "@playwright/test";

/* The live smoke suite. No webServer: the point is that nothing local is
 * running — the deployed Vercel app and the deployed Render API answer on their
 * own or the test fails. */
export default defineConfig({
  testDir: "./e2e-live",
  fullyParallel: false,
  workers: 1,
  reporter: [["list"]],
  use: { trace: "retain-on-failure" },
  projects: [
    { name: "desktop", use: { ...devices["Desktop Chrome"], viewport: { width: 1280, height: 900 } } },
  ],
});
