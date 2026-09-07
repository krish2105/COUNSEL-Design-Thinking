import { expect, test } from "@playwright/test";

/* Voice assignment, tested for the property that makes it worth having: the
 * CFO must sound like the CFO in every session and every replay. A voice that
 * shuffles between runs is noise, not identity. */

const VOICES = ["Zoe", "Alex", "Moira", "Daniel", "Karen", "Fred"];

function installSpeech(order: string[]) {
  const voices = order.map((name) => ({ name, lang: "en-GB" }));
  // @ts-expect-error - a minimal stand-in for the API
  window.speechSynthesis = {
    getVoices: () => voices,
    speak: () => undefined,
    cancel: () => undefined,
    addEventListener: () => undefined,
  };
  // @ts-expect-error - constructor used by lib/voice
  window.SpeechSynthesisUtterance = function () {};
}

test("the real assignment gives each seat its own voice", async ({ page }) => {
  await page.addInitScript(installSpeech, VOICES);
  await page.goto("/room");
  // Voices arrive asynchronously in every browser, so the attribute is empty
  // on first paint. Waiting for it is the behaviour, not a workaround.
  await expect
    .poll(() => page.locator(".column").getAttribute("data-voices"), { timeout: 15_000 })
    .not.toBe("");

  const raw = await page.locator(".column").getAttribute("data-voices");
  const names = (raw ?? "").split(",").map((pair) => pair.split(":")[1]);

  expect(names).toHaveLength(5);
  expect(new Set(names).size, `seats share a voice: ${names}`).toBe(5);
});

test("the assignment does not depend on the order the OS lists voices in", async ({ browser }) => {
  /* The property that makes this worth having. A voice that shuffles between
   * runs is noise rather than identity. */
  const read = async (order: string[]) => {
    const context = await browser.newContext();
    const page = await context.newPage();
    await page.addInitScript(installSpeech, order);
    await page.goto("/room");
    await expect
      .poll(() => page.locator(".column").getAttribute("data-voices"), { timeout: 15_000 })
      .not.toBe("");
    const raw = await page.locator(".column").getAttribute("data-voices");
    await context.close();
    return raw;
  };

  const forwards = await read(VOICES);
  const backwards = await read(VOICES.slice().reverse());
  expect(forwards).toBe(backwards);
  expect(forwards).toContain("cfo:");
});


test("the voice toggle is off by default and does not break where speech is absent", async ({
  page,
}) => {
  await page.addInitScript(() => {
    // A browser with no Web Speech API at all.
    // @ts-expect-error - deliberately removing the API
    delete window.speechSynthesis;
  });
  await page.goto("/room");
  await page.getByRole("button", { name: "Open the room" }).click();
  await expect(page.locator(".room-bar")).toBeVisible({ timeout: 30_000 });

  // No toggle offered, and the room still works.
  await expect(page.getByRole("button", { name: /voices|Silence/i })).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Run a round" })).toBeVisible();
});

test("the toggle appears and is off when speech is available", async ({ page }) => {
  await page.addInitScript(() => {
    // @ts-expect-error - a minimal stand-in for the API
    window.speechSynthesis = {
      getVoices: () => [{ name: "Alex", lang: "en-GB" }],
      speak: () => undefined,
      cancel: () => undefined,
      addEventListener: () => undefined,
    };
    // @ts-expect-error - constructor used by lib/voice
    window.SpeechSynthesisUtterance = function () {};
  });
  await page.goto("/room");
  await page.getByRole("button", { name: "Open the room" }).click();

  const toggle = page.getByRole("button", { name: "Give them voices" });
  await expect(toggle).toBeVisible({ timeout: 30_000 });
  await expect(toggle).toHaveAttribute("aria-pressed", "false");

  await toggle.click();
  await expect(page.getByRole("button", { name: "Silence the room" })).toHaveAttribute(
    "aria-pressed",
    "true",
  );
});
