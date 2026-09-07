import { expect, test } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

/* Every tab the master plan lists, reachable and honest. */

const TABS = [
  ["/room", "The Room"],
  ["/stages", "Stages"],
  ["/board", "The Board"],
  ["/decide", "Decide"],
  ["/report", "Report"],
  ["/ledger", "The Ledger"],
  ["/crew", "The Crew"],
  ["/", "Documents"],
  ["/ask", "Ask"],
  ["/security", "Security"],
] as const;

test("every tab is reachable from the masthead", async ({ page }) => {
  await page.goto("/");
  for (const [href] of TABS) {
    await expect(page.locator(`.masthead nav a[href="${href}"]`)).toHaveCount(1);
  }
});

for (const [href, heading] of TABS) {
  test(`${href} renders, holds its layout and is accessible`, async ({ page }) => {
    await page.addInitScript(() => window.localStorage.setItem("counsel-session", "demo123"));
    await page.goto(href);
    await expect(page.getByRole("heading", { name: heading, level: 1 })).toBeVisible({
      timeout: 30_000,
    });

    expect(
      await page.evaluate(() => {
        const el = document.documentElement;
        return el.scrollWidth <= el.clientWidth + 1;
      }),
      `${href} overflows horizontally`,
    ).toBe(true);

    const results = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
      .analyze();
    const serious = results.violations.filter((v) =>
      ["critical", "serious"].includes(v.impact ?? ""),
    );
    expect(serious, `${href}: ${serious.map((v) => v.id).join(", ")}`).toEqual([]);
  });
}

test("the Crew tab publishes the capability table and claims no side effects", async ({ page }) => {
  await page.goto("/crew");
  await expect(page.locator(".ranking")).toBeVisible({ timeout: 30_000 });

  const rows = await page.locator(".ranking tbody tr").allTextContents();
  expect(rows.length).toBeGreaterThanOrEqual(8); // five seats + facilitator + auditor + chair
  for (const row of rows) expect(row.toLowerCase()).toContain("none");
});

test("the Stages tab shows every stage with the rules that bind it", async ({ page }) => {
  await page.addInitScript(() => window.localStorage.setItem("counsel-session", "demo123"));
  await page.goto("/stages");
  const entries = page.locator(".rail-entry");
  await expect(entries.first()).toBeVisible({ timeout: 30_000 });
  expect(await entries.count()).toBe(7);
});

test("the Report tab says COUNSEL sends the memo nowhere", async ({ page }) => {
  await page.addInitScript(() => window.localStorage.setItem("counsel-session", "demo123"));
  await page.goto("/report");
  await expect(page.locator(".method")).toContainText("does not send this anywhere", {
    timeout: 30_000,
  });
  await expect(page.getByRole("button", { name: /share|email|publish|send/i })).toHaveCount(0);
});

test("the red-team demonstration needs a session and says so", async ({ page }) => {
  await page.addInitScript(() => window.localStorage.clear());
  await page.goto("/security");
  await page.getByRole("button", { name: "Run the attack" }).click();
  await expect(page.locator(".erratum")).toContainText("Open a room first", { timeout: 15_000 });
});
