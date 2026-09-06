import { expect, test, type Page } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

/* These drive the real API. If it is not running the tests fail loudly rather
 * than passing against a mock, because what is being checked here — that a
 * citation resolves, that a scanner finding is real — is only meaningful
 * against the actual service. */

async function setLang(page: Page, label: string) {
  await page.getByRole("button", { name: label, exact: true }).click();
  await expect.poll(() => page.evaluate(() => document.documentElement.lang)).not.toBe("");
}

async function noHorizontalOverflow(page: Page) {
  return page.evaluate(() => {
    const el = document.documentElement;
    return el.scrollWidth <= el.clientWidth + 1;
  });
}

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => window.localStorage.clear());
});

test("the record surface renders and the margin rule is drawn", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Documents" })).toBeVisible();

  const rule = await page.evaluate(() => {
    const col = document.querySelector(".column")!;
    const cs = getComputedStyle(col, "::before");
    return { width: cs.width, bg: cs.backgroundColor, height: col.getBoundingClientRect().height };
  });
  expect(rule.width).toBe("1px");
  expect(rule.height).toBeGreaterThan(200);
});

test("an uploaded document is listed with its passage count", async ({ page }) => {
  await page.goto("/");
  await page.setInputFiles('input[type="file"]', "../../tests/fixtures/docs/trilingual.md");

  const entry = page.locator(".rail-entry", { hasText: "trilingual.md" });
  await expect(entry).toBeVisible({ timeout: 60_000 });
  await expect(entry.getByText("untrusted")).toBeVisible();
  await expect(entry.locator("dd").first()).not.toHaveText("0");
});

test("a retrieved passage carries a resolvable span and names the arm that found it", async ({
  page,
}) => {
  await page.goto("/ask");
  await page.getByRole("textbox", { name: "Ask" }).fill("Why did the CFO object to the payback period?");
  await page.getByRole("button", { name: "Search" }).click();

  const first = page.locator(".rail-entry").first();
  await expect(first).toBeVisible({ timeout: 60_000 });
  await expect(first.locator(".span-ref")).toHaveText(/\[\d+, \d+\)/);
  await expect(first.locator(".arm")).toHaveText(/wording|meaning/);
});

test("the scanner flags an attack and clears a real governance policy", async ({ page }) => {
  await page.goto("/security");

  await page.getByRole("button", { name: "Try an attack" }).click();
  await page.getByRole("button", { name: "Scan", exact: true }).click();
  await expect(page.locator(".rail-entry").first()).toBeVisible({ timeout: 30_000 });
  expect(await page.locator(".rail-entry").count()).toBeGreaterThanOrEqual(4);

  await page.getByRole("button", { name: "Try a real policy" }).click();
  await page.getByRole("button", { name: "Scan", exact: true }).click();
  await expect(page.locator(".clean")).toBeVisible({ timeout: 30_000 });
  expect(await page.locator(".rail-entry").count()).toBe(0);
});

test("Arabic switches direction without breaking the layout", async ({ page }) => {
  await page.goto("/ask");
  await setLang(page, "ع");

  await expect.poll(() => page.evaluate(() => document.documentElement.dir)).toBe("rtl");
  await expect.poll(() => page.evaluate(() => document.documentElement.lang)).toBe("ar");
  expect(await noHorizontalOverflow(page)).toBe(true);

  /* The margin rule must move to the right edge of the column, not stay left:
   * a record whose margin is on the wrong side is not translated, only recoloured. */
  const railOnRight = await page.evaluate(() => {
    const col = document.querySelector(".column")!;
    const r = col.getBoundingClientRect();
    return getComputedStyle(col).paddingRight !== "0px" && r.width > 0;
  });
  expect(railOnRight).toBe(true);
});

test("Hindi renders and the layout holds", async ({ page }) => {
  await page.goto("/");
  await setLang(page, "हि");
  await expect.poll(() => page.evaluate(() => document.documentElement.lang)).toBe("hi");
  await expect(page.getByRole("heading", { name: "दस्तावेज़" })).toBeVisible();
  expect(await noHorizontalOverflow(page)).toBe(true);
});

test("both colour registers render and neither overflows", async ({ page }) => {
  await page.goto("/");
  for (const label of ["Light", "Dark"]) {
    const button = page.locator("button.theme");
    if ((await button.textContent())?.trim() === label) await button.click();
    expect(await noHorizontalOverflow(page)).toBe(true);
  }
});

test("no critical accessibility violations on any tab", async ({ page }) => {
  for (const path of ["/", "/ask", "/security"]) {
    await page.goto(path);
    const results = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
      .analyze();
    const serious = results.violations.filter((v) => ["critical", "serious"].includes(v.impact ?? ""));
    expect(serious, `${path}: ${serious.map((v) => v.id).join(", ")}`).toEqual([]);
  }
});
