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

export const api = {
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
