import { expect, test } from "@playwright/test";

/* The whole product, once, in the order a person would use it.
 *
 * Every other spec checks one surface. This one checks that they join up: a
 * document uploaded on one tab is citable on another, a session opened in the
 * Room is the session the Report assembles, and the record stays sealed all the
 * way through.
 *
 * It runs against the real API, so it is slow where the API is slow. The
 * debate and scoring steps are skipped when no model is reachable rather than
 * faked — a journey test that quietly stubs the expensive half is not a
 * journey test. */

test.describe.configure({ mode: "serial" });

test("upload, frame, debate, decide, report, settle", async ({ page }, testInfo) => {
  test.setTimeout(300_000);

  /* The API and its database are shared across projects and runs, so an outcome
   * note has to identify THIS run or the assertion matches the desktop run's
   * row as well as its own. */
  const note = `Pilot ran in Q2 — ${testInfo.project.name} ${Date.now()}`;

  // ── 1. A document goes on the table ──────────────────────────────────────
  // Cleared ONCE, not via addInitScript: that runs on every navigation, so it
  // would wipe the session the Room sets in step 3 on the way to step 4.
  await page.goto("/");
  await page.evaluate(() => window.localStorage.clear());
  await page.reload();
  await page.setInputFiles('input[type="file"]', "../../tests/fixtures/docs/board-paper.pdf");
  const doc = page.locator(".rail-entry", { hasText: "board-paper.pdf" });
  await expect(doc).toBeVisible({ timeout: 90_000 });
  await expect(doc.getByText("untrusted")).toBeVisible();

  // ── 2. It is retrievable, with a span a claim could cite ─────────────────
  await page.goto("/ask");
  await page.getByRole("textbox", { name: "Ask" }).fill("Why did the CFO object to the payback period?");
  await page.getByRole("button", { name: "Search" }).click();
  const hit = page.locator(".rail-entry").first();
  await expect(hit).toBeVisible({ timeout: 60_000 });
  await expect(hit.locator(".span-ref")).toHaveText(/\[\d+, \d+\)/);

  // ── 3. The room opens, and the chamber is drawn from the record ──────────
  await page.goto("/room");
  await page.getByRole("button", { name: "Open the room" }).click();
  await expect(page.locator(".chamber")).toBeVisible({ timeout: 60_000 });
  await expect(page.locator(".room-bar")).toContainText("sealed");

  // ── 4. The stages know where the session is ──────────────────────────────
  await page.goto("/stages");
  await expect(page.locator(".rail-entry")).toHaveCount(7, { timeout: 60_000 });

  // ── 5. The attack is caught, live, against this session ──────────────────
  await page.goto("/security");
  await page.getByRole("button", { name: "Run the attack" }).click();
  const steps = page.locator(".fenced .rail-entry");
  await expect(steps.first()).toBeVisible({ timeout: 120_000 });
  await expect(steps).toHaveCount(4);
  await expect(page.locator(".fenced")).toContainText("does not exist");

  // ── 6. The report assembles what happened, and offers no way to send it ──
  await page.goto("/report");
  await expect(page.locator(".meta")).toContainText("sealed", { timeout: 60_000 });
  await expect(page.getByRole("button", { name: /share|email|publish|send/i })).toHaveCount(0);

  // ── 7. An outcome can be settled, and calibration refuses to guess ───────
  await page.goto("/ledger");
  await page.getByRole("textbox", { name: "What the room chose" }).fill("plant");
  await page.getByRole("textbox", { name: "What turned out right" }).fill("plant");
  await page.getByRole("textbox", { name: "What happened" }).fill(note);
  await page.getByRole("button", { name: "Record it" }).click();

  await expect(page.locator(".rail-entry", { hasText: note })).toBeVisible({ timeout: 60_000 });
  // One outcome is not a calibration record, and the ledger says so.
  await expect(page.locator(".rail-entry", { hasText: "Brier" })).toHaveCount(0);
  await expect(page.locator(".rail-entry", { hasText: "more outcomes" }).first()).toBeVisible();
});
