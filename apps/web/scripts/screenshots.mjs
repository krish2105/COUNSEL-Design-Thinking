/* Regenerate the README screenshots.
 *
 * Run against a LOCAL stack (`make api` and `make web`), never the deployed
 * one. The free Render instance has no provider keys and no embedder, so its
 * debate turns are deterministic stub text; a screenshot of that would show
 * placeholder output dressed up as a product. These images come from the
 * configuration the project actually claims — local Ollama for inference,
 * bge-m3 for embeddings — and the README says so under the images.
 *
 *   COUNSEL_SESSION=<id> node scripts/screenshots.mjs
 *
 * The session id matters: /report and /decide render from artefacts, so a
 * freshly opened room produces empty pages. Find one that has content with
 *
 *   sqlite3 data/counsel.db "SELECT s.session_id,
 *     (SELECT COUNT(*) FROM turns t WHERE t.session_id=s.session_id) n
 *     FROM sessions s ORDER BY n DESC LIMIT 1"
 *
 * Without COUNSEL_SESSION the script opens a fresh room, which is a fine way to
 * shoot the chamber and the crew pages and a poor way to shoot the memo.
 */

import { chromium } from "@playwright/test";
import { mkdir } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const OUT = resolve(HERE, "../../../docs/images"); // scripts -> web -> apps -> root
const BASE = process.env.COUNSEL_WEB_URL ?? "http://localhost:3000";
const SESSION = process.env.COUNSEL_SESSION ?? null;

/** Desktop, at 2x so text stays crisp once GitHub scales the image down. */
const VIEWPORT = { width: 1440, height: 900 };

/** The toggle is labelled with the register it switches TO, so the button
 *  being absent means we are already in the register we want. */
async function setTheme(page, theme) {
  const button = page.getByRole("button", {
    name: theme === "dark" ? "Dark" : "Light",
    exact: true,
  });
  if (await button.count()) {
    await button.click();
    await page.waitForTimeout(500);
  }
}

async function openRoom(page) {
  const open = page.getByRole("button", { name: "Open the room" });
  if (await open.count()) await open.click();
  await page.locator(".chamber").waitFor({ state: "visible", timeout: 30_000 });
  await page.locator(".chamber-stage canvas").waitFor({ state: "visible", timeout: 20_000 });
  // frameloop="demand": the first frame lands on invalidate, not on a clock.
  await page.waitForTimeout(3000);
}

const shots = [
  {
    name: "room-chamber",
    theme: "dark",
    async take(page) {
      await page.goto(`${BASE}/room`, { waitUntil: "networkidle" });
      await setTheme(page, "dark");
      await openRoom(page);
      return page.locator(".chamber");
    },
  },
  {
    name: "room-transcript",
    theme: "dark",
    async take(page) {
      await page.goto(`${BASE}/room`, { waitUntil: "networkidle" });
      await setTheme(page, "dark");
      await openRoom(page);
      await page.locator(".replay").scrollIntoViewIfNeeded().catch(() => {});
      return null; // viewport
    },
  },
  {
    name: "report-memo",
    theme: "light",
    async take(page) {
      await page.goto(`${BASE}/report`, { waitUntil: "networkidle" });
      await setTheme(page, "light");
      // The memo is assembled on demand; without this the page shows only the
      // button that would build it.
      const assemble = page.getByRole("button", { name: /Assemble the report/i });
      if (await assemble.count()) {
        await assemble.click();
        await page.locator(".memo").waitFor({ state: "visible", timeout: 60_000 });
      }
      await page.waitForTimeout(1500);
      return page.locator(".memo");
    },
  },
  {
    name: "decide-ranking",
    theme: "light",
    async take(page) {
      await page.goto(`${BASE}/decide`, { waitUntil: "networkidle" });
      await setTheme(page, "light");
      await page.waitForTimeout(2500);
      return page.locator(".column");
    },
  },
  {
    name: "crew-capability",
    theme: "light",
    async take(page) {
      await page.goto(`${BASE}/crew`, { waitUntil: "networkidle" });
      await setTheme(page, "light");
      await page.locator(".ranking tbody tr").first().waitFor({ timeout: 30_000 });
      return page.locator("section.fenced").last();
    },
  },
  {
    name: "crew-blindspots",
    theme: "light",
    async take(page) {
      await page.goto(`${BASE}/crew`, { waitUntil: "networkidle" });
      await setTheme(page, "light");
      await page.locator(".entries").waitFor({ timeout: 30_000 });
      return page.locator(".entries > *").first();
    },
  },
  {
    name: "security-attack",
    theme: "light",
    async take(page) {
      await page.goto(`${BASE}/security`, { waitUntil: "networkidle" });
      await setTheme(page, "light");
      const attack = page.getByRole("button", { name: /Run the attack/i });
      if (await attack.count()) {
        await attack.click();
        await page.waitForTimeout(3500);
      }
      // The four numbered defences only. Screenshotting .column clipped the
      // dissent-margin rail, which is the one element worth showing.
      return page.locator(".entries");
    },
  },
];

const browser = await chromium.launch();
await mkdir(OUT, { recursive: true });

for (const shot of shots) {
  const context = await browser.newContext({
    viewport: VIEWPORT,
    deviceScaleFactor: 2,
    colorScheme: shot.theme,
  });
  // Seeded before every navigation on purpose. addInitScript runs per
  // navigation, and writing the SAME id each time is what keeps the session
  // alive across tabs; an earlier version set it once and lost the session
  // halfway through the journey.
  if (SESSION) {
    await context.addInitScript((id) => {
      try {
        window.localStorage.setItem("counsel-session", id);
      } catch {
        /* private window with site data blocked */
      }
    }, SESSION);
  }

  const page = await context.newPage();
  try {
    const target = await shot.take(page);
    const path = `${OUT}/${shot.name}.png`;
    if (target) await target.screenshot({ path });
    else await page.screenshot({ path });
    console.log(`ok   ${shot.name}`);
  } catch (error) {
    console.log(`FAIL ${shot.name}: ${error.message.split("\n")[0]}`);
  }
  await context.close();
}

await browser.close();
console.log(`\nwritten to ${OUT}`);
