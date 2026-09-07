/* The deployed system, driven in a real browser over the public internet.
 *
 * Deliberately NOT in e2e/. Those tests run against localhost on every `make
 * check` and must stay hermetic; this one depends on Vercel, on Render, and on
 * Render's free tier being awake, so it is a separate command a person runs
 * when they want to know whether the live thing works. Run it with
 * `npm run smoke:live` (or point COUNSEL_LIVE_URL at a preview deployment).
 *
 * The timeouts are large on purpose: a free Render instance sleeps after 15
 * minutes and takes roughly a minute to wake, so a cold first request here is
 * normal rather than a failure.
 */

import { expect, test } from "@playwright/test";

const LIVE = process.env.COUNSEL_LIVE_URL ?? "https://counsel-gray.vercel.app";

test("the crew page is served by the live API", async ({ page }) => {
  test.setTimeout(240_000);
  await page.goto(`${LIVE}/crew`);

  // Wait for the ROWS, not the heading. The heading is server-rendered and
  // appears whether or not the API ever answers, so asserting on it would pass
  // against a completely dead backend — which is exactly what it did the first
  // time this test was written.
  const rows = page.locator(".ranking tbody tr");
  await expect(rows).toHaveCount(8, { timeout: 120_000 });

  // The safety claim, read off the deployed instance rather than the repo.
  for (const text of await rows.allTextContents()) {
    expect(text.toLowerCase()).toContain("none");
  }
});

test("the scanner runs live", async ({ page }) => {
  test.setTimeout(120_000);
  await page.goto(`${LIVE}/security`);
  await page.getByRole("button", { name: "Try a real policy" }).click();
  await page.getByRole("button", { name: "Scan", exact: true }).click();
  await expect(page.locator(".clean")).toBeVisible({ timeout: 60_000 });
});

test("the chamber renders in the deployed browser", async ({ page }) => {
  test.setTimeout(180_000);
  await page.goto(`${LIVE}/room`);
  await page.getByRole("button", { name: "Open the room" }).click();
  await expect(page.locator(".chamber")).toBeVisible({ timeout: 120_000 });
  await expect(page.locator(".chamber-stage canvas")).toBeVisible({ timeout: 30_000 });

  // The five seats must be five DIFFERENT colours. Grey seats were a real bug:
  // the tokens are oklch, the browser reports lab(), and three.js parses
  // neither — so the scene silently fell back to grey in production while
  // every local test passed.
  const raw = await page.locator(".chamber-stage").getAttribute("data-colours");
  const colours = (raw ?? "").split(",");
  expect(colours).toHaveLength(5);
  for (const c of colours) expect(c, `not a hex colour: ${c}`).toMatch(/^#[0-9a-f]{6}$/i);
  expect(new Set(colours).size, `seats share a colour: ${colours}`).toBe(5);
  expect(colours, "every seat fell back to the default grey").not.toContain("#8890a8");

  await expect(page.locator(".room-bar")).toContainText("sealed");
});

test("the Board produces framings and ideas on the deployed site", async ({ page }) => {
  /* The regression this exists for: deps.llm() terminated its chain with a bare
   * StubProvider(), which cannot answer structured() at all. With no provider
   * keys the deployed service runs entirely on that stub, so this page returned
   * 500 for every framing while the Room worked and every local test passed. */
  test.setTimeout(240_000);

  // The Board needs a session, and the Room is where one is opened.
  await page.goto(`${LIVE}/room`);
  await page.getByRole("button", { name: "Open the room" }).click();
  await expect(page.locator(".room-bar")).toBeVisible({ timeout: 120_000 });

  await page.goto(`${LIVE}/board`);

  // An empty Board must SAY it is empty rather than render a page of blank.
  await expect(page.getByText(/Nothing on the board yet/i)).toBeVisible({ timeout: 30_000 });

  await page.getByRole("button", { name: "Ask for framings" }).click();
  await expect(page.locator(".entries .rail-entry, .entries > *").first()).toBeVisible({
    timeout: 120_000,
  });
  await expect(page.locator(".erratum")).toHaveCount(0);

  // Five seats, five framings — a partial answer is a failure, not a degradation.
  expect(await page.locator(".entries > *").count()).toBe(5);
});
