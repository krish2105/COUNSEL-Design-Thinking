/* One place that knows the API is a different origin in development.
 * next.config.ts rewrites /api/* onto the FastAPI service, so nothing else in
 * the app needs to know a port number. */

const ROLE_HEADER = "X-Counsel-Role";

/* Phase A resolves role from a header the caller asserts about itself; see
 * services/api/core/rbac.py for why that is adequate here and what replaces it. */
export type Role = "viewer" | "analyst" | "admin";

async function call<T>(path: string, init: RequestInit = {}, role: Role = "analyst"): Promise<T> {
  const res = await fetch(`/api${path}`, {
    ...init,
    headers: { [ROLE_HEADER]: role, ...(init.headers ?? {}) },
  });
  if (!res.ok) {
    const detail = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(typeof detail.detail === "string" ? detail.detail : res.statusText);
  }
  return res.json() as Promise<T>;
}

export type DocumentRow = {
  doc_id: string;
  filename: string;
  media_type: string;
  n_chars: number;
  n_chunks: number;
  n_findings: number;
  ingested_at: string;
};

export type UploadResult = {
  doc_id: string;
  filename: string;
  n_chunks: number;
  languages: string[];
  trust: string;
  injection_findings: { n: number; high: number; patterns: string[] };
};

export type Hit = {
  chunk_id: string;
  doc_id: string;
  text: string;
  start: number;
  end: number;
  lang: string;
  score: number;
  rank_bm25: number | null;
  rank_vec: number | null;
  trust: string;
};

export type Finding = {
  pattern: string;
  severity: "high" | "medium";
  start: number;
  end: number;
  excerpt: string;
};

export type Seat = {
  id: string;
  title: string;
  accountable_for: string;
  values: string[];
  blind_spots: string[];
  evidence_standards: string[];
  tools: string[];
};

export type SessionState = {
  session_id: string;
  question: string;
  stage: string;
  rules: string[];
  round_no: number;
  closed: boolean;
  n_turns: number;
  chain_intact: boolean;
};

export type Frame =
  | { kind: "round_open"; round_no: number; speakers: string[]; stage: string; rules: string[] }
  | { kind: "speaking"; seat: string; text: string; signed: false }
  | { kind: "turn"; turn_id: string; speaker: string; text: string; provider: string; model: string; sig: string; signed: true }
  | { kind: "flag"; turn_id: string; rule: string; severity: string; excerpt: string; why: string }
  | { kind: "done"; n_turns: number; n_flags: number; chain_intact: boolean };

/* SSE over POST, which EventSource cannot do — it is GET-only. Reading the
 * body stream directly is the standard way round that, and it also lets the
 * caller abort mid-flight.
 *
 * Every long operation in COUNSEL goes through here, and not for the progress
 * bar. Measured: five seats scoring two options takes ~103s, and the Next.js
 * rewrite returns 500 at exactly 30 — as would Render's gateway, or Vercel's.
 * A stream keeps the connection alive because frames keep arriving. */
async function stream(
  path: string,
  onFrame: (f: Record<string, unknown>) => void,
  init: RequestInit = {},
  signal?: AbortSignal,
): Promise<void> {
  const res = await fetch(`/api${path}`, {
    method: "POST",
    ...init,
    headers: { "X-Counsel-Role": "analyst", ...(init.headers ?? {}) },
    signal,
  });
  if (!res.ok || !res.body) throw new Error(`stream failed: ${res.status}`);

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let event = "";

  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    const lines = buffer.split("\n");
    buffer = lines.pop() ?? "";
    for (const line of lines) {
      if (line.startsWith("event: ")) event = line.slice(7).trim();
      else if (line.startsWith("data: ") && event) {
        onFrame({ kind: event, ...JSON.parse(line.slice(6)) });
        event = "";
      }
      // ": ping" keep-alive comments are ignored by falling through.
    }
  }
}

export const streamRound = (
  sessionId: string,
  onFrame: (f: Frame) => void,
  signal?: AbortSignal,
) => stream(`/sessions/${sessionId}/rounds/stream`, (f) => onFrame(f as Frame), {}, signal);

export type ScoreFrame =
  | { kind: "scoring_open"; options: string[]; n_seats: number; evidence: string[] }
  | { kind: "scored"; option: string; seat: string; confidence: number; weakest_on: string;
      desirability: number; feasibility: number; viability: number; depends_on: string[] }
  | { kind: "ranked"; ranked: Ranked[] }
  | { kind: "done"; n_scores: number };

export const streamScores = (
  sessionId: string,
  options: string[],
  onFrame: (f: ScoreFrame) => void,
  signal?: AbortSignal,
) =>
  stream(
    `/sessions/${sessionId}/scores/stream`,
    (f) => onFrame(f as ScoreFrame),
    { headers: { "Content-Type": "application/json" }, body: JSON.stringify({ options }) },
    signal,
  );

export type MemoFrame =
  | { kind: "memo_open"; n_evidence: number; n_options: number }
  | { kind: "drafted"; recommendation: string; margin: number; n_cited: number;
      n_uncited: number; ungrounded: boolean }
  | { kind: "dissent"; seat: string; agrees: boolean }
  | ({ kind: "done" } & MemoResult);

/* Streamed for the same reason scoring is: assembling a memo is two model
 * phases and takes ~41s, and a 41-second synchronous response returns 500 at
 * exactly 30s through the Next rewrite. See services/api/routers/decisions.py.
 */
export const streamMemo = (
  sessionId: string,
  onFrame: (f: MemoFrame) => void,
  signal?: AbortSignal,
) => stream(`/sessions/${sessionId}/memo/stream`, (f) => onFrame(f as MemoFrame), {}, signal);

export type Ranked = { option: string; total: number; mean_confidence: number; supporters: string[] };
export type FlipRow = {
  evidence_id: string; summary: string; winner_before: string; winner_after: string;
  margin_before: number; margin_after: number; seats_affected: string[];
};
export type Counterfactual = {
  verdict: string; winner: string | null; margin: number;
  flips: FlipRow[];
  sensitivity: { seat: string; grounded_share: number; depends_on: string[]; ungrounded: boolean }[];
  method: string;
};
export type MemoResult = {
  markdown: string; recommendation: string; n_cited: number; n_uncited: number;
  ungrounded: boolean; unanimous_dissent: boolean; margin: number;
  dissents: { seat: string; title: string; position: string; would_change_my_mind: string }[];
};
export type Calibration = {
  minimum_outcomes: number; coin_flip_baseline: number;
  scored: { seat: string; score: number; n_outcomes: number; mean_confidence: number; hit_rate: number; reading: string }[];
  pending: { seat: string; n_outcomes: number; needs: number }[];
  outcomes: { session_id: string; question: string; chosen: string; actual: string; notes: string; recorded_at: string }[];
  note: string;
};

export const api = {
  seats: () => call<Seat[]>("/sessions/seats", {}, "viewer"),
  openSession: (question: string, stage: string) =>
    call<SessionState>("/sessions", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question, stage }),
    }),
  session: (id: string) => call<SessionState>(`/sessions/${id}`, {}, "viewer"),
  interject: (id: string, text: string) =>
    call<{ turn_id: string; speaker: string; text: string }>(`/sessions/${id}/interject`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
    }),
  advanceStage: (id: string, stage: string) =>
    call<SessionState>(`/sessions/${id}/stage`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ stage }),
    }),
  addEvidence: (id: string, items: { evidence_id: string; summary: string; source: string }[]) =>
    call<unknown[]>(`/sessions/${id}/evidence`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(items),
    }),
  score: (id: string, options: string[]) =>
    call<{ ranked: Ranked[]; scores: Record<string, unknown[]> }>(`/sessions/${id}/scores`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ options }),
    }),
  counterfactual: (id: string) =>
    call<Counterfactual>(`/sessions/${id}/counterfactual`, {}, "viewer"),
  memo: (id: string) => call<MemoResult>(`/sessions/${id}/memo`, { method: "POST" }),
  outcome: (id: string, chosen: string, actual: string, notes: string) =>
    call<{ recorded: boolean }>(`/sessions/${id}/outcome`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ chosen, actual, notes }),
    }),
  calibration: () => call<Calibration>("/ledger", {}, "viewer"),
  chamber: (id: string) =>
    call<import("@/components/chamber/Chamber").ChamberData>(
      `/sessions/${id}/chamber`, {}, "viewer",
    ),
  framings: (id: string) =>
    call<{ framings: Record<string, unknown> }>(`/sessions/${id}/framings`, { method: "POST" }),
  ideas: (id: string) =>
    call<{ ideas: Record<string, unknown> }>(`/sessions/${id}/ideas`, { method: "POST" }),
  artefacts: (id: string) =>
    call<{
      artefacts: Record<string, Record<string, unknown> | null>;
      evidence: { evidence_id: string; summary: string; source: string }[];
      stage_rules: Record<string, string[]>;
    }>(`/sessions/${id}/artefacts`, {}, "viewer"),
  verify: (id: string) =>
    call<{ intact: boolean; broken_turns: string[]; n_turns: number }>(`/sessions/${id}/verify`, {}, "viewer"),
  health: () => call<Record<string, unknown>>("/healthz", {}, "viewer"),
  documents: () => call<DocumentRow[]>("/documents", {}, "viewer"),
  upload: (file: File) => {
    const body = new FormData();
    body.append("file", file);
    return call<UploadResult>("/documents", { method: "POST", body });
  },
  retrieve: (q: string, limit = 8) =>
    call<{ query: string; degraded: string[]; hits: Hit[] }>(
      "/retrieve",
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ q, limit }),
      },
      "viewer",
    ),
  redteam: (sessionId: string) =>
    call<{
      document: { doc_id: string; n_chunks: number; ingested: boolean; why_not_refused: string };
      detected: { n_findings: number; patterns: string[] };
      structural: { tool_it_asked_for: string; publish_tools_in_registry: string[]; verdict: string };
      citation_gate: { injected_claim: string; reached_the_memo: boolean; why: string };
      honest_limit: string;
    }>(`/security/redteam`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: sessionId }),
    }),
  scan: (text: string) =>
    call<{
      summary: { n: number; high: number; patterns: string[] };
      findings: Finding[];
      wrapped_preview: string;
    }>(
      "/security/scan",
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text, source: "pasted text" }),
      },
      "viewer",
    ),
};
