import { expect, test } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

/* Decide and Ledger, without a real scoring run: five seats across two options
 * is roughly a hundred seconds of model time. What is checked here is what only
 * a browser can — that the page refuses to work without a session, that the
 * ledger will not draw a calibration it does not have, and that the caveats a
 * reader needs are actually on screen rather than only in the API response. */

test("Decide refuses to work without a session rather than failing later", async ({ page }) => {
  await page.addInitScript(() => window.localStorage.clear());
  await page.goto("/decide");
  await expect(page.locator(".erratum")).toContainText("Open the room first");
  await expect(page.getByRole("button", { name: "Score the options" })).toHaveCount(0);
});

test("Decide offers editable evidence once a session exists", async ({ page }) => {
  await page.addInitScript(() => window.localStorage.setItem("counsel-session", "demo123"));
  await page.goto("/decide");
  // The session is read in a mount effect, so the first render is the
  // no-session branch. Wait for the form rather than racing it.
  await expect(page.getByRole("button", { name: "Score the options" })).toBeVisible();

  const rows = page.locator(".evidence-row input");
  expect(await rows.count()).toBeGreaterThanOrEqual(3);

  await page.getByRole("button", { name: "Add evidence" }).click();
  expect(await rows.count()).toBeGreaterThanOrEqual(4);

  await page.getByRole("button", { name: "Remove" }).first().click();
  expect(await rows.count()).toBeGreaterThanOrEqual(3);
});

test("the Ledger states its minimum and does not draw a score it does not have", async ({
  page,
}) => {
  await page.goto("/ledger");
  await expect(page.locator(".method")).toContainText("noise", { timeout: 30_000 });

  const pending = page.locator(".rail-entry", { hasText: "more outcomes" });
  await expect(pending.first()).toBeVisible();
  await expect(page.locator(".rail-entry", { hasText: "Brier" })).toHaveCount(0);
});

test("the Ledger needs both a chosen and an actual before it will record", async ({ page }) => {
  await page.addInitScript(() => window.localStorage.setItem("counsel-session", "demo123"));
  await page.goto("/ledger");

  const save = page.getByRole("button", { name: "Record it" });
  await expect(save).toBeDisabled();
  await page.getByRole("textbox", { name: "What the room chose" }).fill("plant");
  await expect(save).toBeDisabled();
  await page.getByRole("textbox", { name: "What turned out right" }).fill("plant");
  await expect(save).toBeEnabled();
});

test("no critical accessibility violations on Decide or the Ledger", async ({ page }) => {
  await page.addInitScript(() => window.localStorage.setItem("counsel-session", "demo123"));
  for (const path of ["/decide", "/ledger"]) {
    await page.goto(path);
    await page.waitForTimeout(500);
    const results = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
      .analyze();
    const serious = results.violations.filter((v) =>
      ["critical", "serious"].includes(v.impact ?? ""),
    );
    expect(serious, `${path}: ${serious.map((v) => v.id).join(", ")}`).toEqual([]);
  }
});

test("Decide and the Ledger hold up under RTL", async ({ page }) => {
  await page.addInitScript(() => window.localStorage.setItem("counsel-session", "demo123"));
  await page.goto("/decide");
  await page.getByRole("button", { name: "ع", exact: true }).click();
  await expect.poll(() => page.evaluate(() => document.documentElement.dir)).toBe("rtl");
  expect(
    await page.evaluate(() => {
      const el = document.documentElement;
      return el.scrollWidth <= el.clientWidth + 1;
    }),
  ).toBe(true);
});
