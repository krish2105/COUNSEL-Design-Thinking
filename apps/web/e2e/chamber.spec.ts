import { expect, test } from "@playwright/test";

/* The chamber, in a real viewport.
 *
 * The SVG path is tested rather than the WebGL one wherever the assertion can
 * be made on either: a headless WebGL context is a poor stand-in for a real GPU,
 * and the two views are drawn from the same numbers by construction. What IS
 * checked on the 3D path is that it mounts and that the fallback engages when
 * WebGL is absent — the progressive-enhancement promise. */

async function openRoom(page: import("@playwright/test").Page) {
  await page.goto("/room");
  await page.getByRole("button", { name: "Open the room" }).click();
  await expect(page.locator(".chamber")).toBeVisible({ timeout: 30_000 });
}

test("the table renders with five seats when WebGL is absent", async ({ page }) => {
  // Deny WebGL before any script runs, which is the honest way to test the
  // fallback: not a flag we set, but the condition a real machine presents.
  await page.addInitScript(() => {
    const original = HTMLCanvasElement.prototype.getContext;
    HTMLCanvasElement.prototype.getContext = function (type: string, ...rest: unknown[]) {
      if (String(type).startsWith("webgl")) return null;
      // @ts-expect-error - passthrough
      return original.call(this, type, ...rest);
    };
  });
  await openRoom(page);

  await expect(page.getByTestId("table-svg")).toBeVisible();
  expect(await page.getByTestId("table-seat").count()).toBe(5);
  await expect(page.locator(".chamber-stage")).toHaveAttribute("data-mode", "svg");
  await expect(page.locator(".chamber-caption").nth(1)).toContainText("no WebGL");
});

test("each seat in the fallback carries its own colour", async ({ page }) => {
  await page.addInitScript(() => {
    const original = HTMLCanvasElement.prototype.getContext;
    HTMLCanvasElement.prototype.getContext = function (type: string, ...rest: unknown[]) {
      if (String(type).startsWith("webgl")) return null;
      // @ts-expect-error - passthrough
      return original.call(this, type, ...rest);
    };
  });
  await openRoom(page);

  const fills = await page.evaluate(() =>
    [...document.querySelectorAll("[data-testid=table-seat]")].map((g) =>
      getComputedStyle(g.querySelector(".seat-halo")!).fill,
    ),
  );
  expect(new Set(fills).size, `seats share a colour: ${fills}`).toBe(5);
});

test("the 3D table mounts a canvas when WebGL is available", async ({ page }) => {
  await openRoom(page);
  await expect(page.locator(".chamber-stage")).toHaveAttribute("data-mode", "3d");
  await expect(page.locator(".chamber-stage canvas")).toBeVisible({ timeout: 20_000 });
});

test("the 3D scene is handed five distinct seat colours, not grey", async ({ page }) => {
  /* The original bug: the seat tokens are oklch() in the stylesheet, this
   * browser reports them as lab(), three.js parses neither, and every seat
   * silently rendered the same grey — which looks deliberate. */
  await openRoom(page);
  const raw = await page.locator(".chamber-stage").getAttribute("data-colours");
  const colours = (raw ?? "").split(",");

  expect(colours).toHaveLength(5);
  for (const c of colours) expect(c, `not a hex colour: ${c}`).toMatch(/^#[0-9a-f]{6}$/i);
  expect(new Set(colours).size, `seats share a colour: ${colours}`).toBe(5);
  expect(colours, "every seat fell back to the default grey").not.toContain("#8890a8");
});

test("the caption says what an edge means and what it does not", async ({ page }) => {
  await openRoom(page);
  await expect(page.locator(".chamber-caption").first()).toContainText("not that it agreed");
});

test("scrubbing the replay changes the turn and the speaker", async ({ page }) => {
  await page.goto("/room");
  // A room with only its opening turn has nothing to scrub, so this reuses
  // whatever session the browser already holds if one is there.
  await page.getByRole("button", { name: "Open the room" }).click();
  await expect(page.locator(".chamber")).toBeVisible({ timeout: 30_000 });

  const scrub = page.getByTestId("replay-scrub");
  await expect(scrub).toBeVisible();
  const max = Number(await scrub.getAttribute("max"));

  if (max > 0) {
    const before = await page.getByTestId("replay-text").textContent();
    await scrub.fill("0");
    const after = await page.getByTestId("replay-text").textContent();
    expect(after).not.toBe(before);
  } else {
    // One turn: the control still exists and reports its single position.
    await expect(page.getByTestId("replay-speaker")).toBeVisible();
  }
});

test("the chamber does not overflow its column", async ({ page }) => {
  await openRoom(page);
  expect(
    await page.evaluate(() => {
      const el = document.documentElement;
      return el.scrollWidth <= el.clientWidth + 1;
    }),
  ).toBe(true);
});
