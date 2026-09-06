import { expect, test } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

/* The Room, without running a real round: five seats on a local model take
 * roughly 45 seconds, which is covered by the API tests instead. What is
 * checked here is what only a browser can check — that each seat's dissent
 * shows in its own colour, and that the blind spots are readable before a
 * reader weighs anything the room said. */

test("every seat's rail carries its own colour", async ({ page }) => {
  await page.goto("/room");
  const seats = ["cfo", "cmo", "coo", "ethics", "devil"];

  const colours = await Promise.all(
    seats.map(async (seat) => {
      const entry = page.locator(`.rail-entry[data-seat="${seat}"]`).first();
      await expect(entry).toBeVisible({ timeout: 30_000 });
      return entry.evaluate((el) => getComputedStyle(el, "::before").backgroundColor);
    }),
  );

  expect(new Set(colours).size, `seats share a colour: ${colours}`).toBe(seats.length);
  expect(colours.every((c) => c && c !== "rgba(0, 0, 0, 0)")).toBe(true);
});

test("each seat publishes at least two blind spots", async ({ page }) => {
  await page.goto("/room");
  for (const seat of ["cfo", "cmo", "coo", "ethics", "devil"]) {
    const items = page.locator(`.rail-entry[data-seat="${seat}"] .blind-spots li`);
    await expect(items.first()).toBeVisible({ timeout: 30_000 });
    expect(await items.count()).toBeGreaterThanOrEqual(2);
  }
});

test("opening a room seals an opening turn and reports the stage rules", async ({ page }) => {
  await page.goto("/room");
  await page.getByRole("button", { name: "Open the room" }).click();

  const bar = page.locator(".room-bar");
  await expect(bar).toBeVisible({ timeout: 30_000 });
  await expect(bar).toContainText("Decide");
  await expect(bar).toContainText("sealed");
  await expect(page.getByRole("button", { name: "Run a round" })).toBeVisible();
});

test("the Chair box appears only once a room is open", async ({ page }) => {
  await page.goto("/room");
  await expect(page.getByRole("textbox", { name: "Speak as Chair" })).toHaveCount(0);
  await page.getByRole("button", { name: "Open the room" }).click();
  await expect(page.getByRole("textbox", { name: "Speak as Chair" })).toBeVisible({
    timeout: 30_000,
  });
});

test("the room has no critical accessibility violations", async ({ page }) => {
  await page.goto("/room");
  await expect(page.locator(".rail-entry").first()).toBeVisible({ timeout: 30_000 });
  const results = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
    .analyze();
  const serious = results.violations.filter((v) => ["critical", "serious"].includes(v.impact ?? ""));
  expect(serious, serious.map((v) => v.id).join(", ")).toEqual([]);
});

test("the room survives RTL without overflowing", async ({ page }) => {
  await page.goto("/room");
  await page.getByRole("button", { name: "ع", exact: true }).click();
  await expect.poll(() => page.evaluate(() => document.documentElement.dir)).toBe("rtl");
  await expect(page.locator(".rail-entry").first()).toBeVisible({ timeout: 30_000 });
  expect(
    await page.evaluate(() => {
      const el = document.documentElement;
      return el.scrollWidth <= el.clientWidth + 1;
    }),
  ).toBe(true);
});
