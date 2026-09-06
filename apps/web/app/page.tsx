"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { RailEntry } from "@/components/Rail";
import { useLang } from "@/components/Providers";
import { api, type DocumentRow } from "@/lib/api";

export default function Documents() {
  const { t } = useLang();
  const [docs, setDocs] = useState<DocumentRow[] | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const input = useRef<HTMLInputElement>(null);

  const refresh = useCallback(async () => {
    try {
      setDocs(await api.documents());
    } catch (e) {
      setError((e as Error).message);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  async function onFile(file: File) {
    setBusy(true);
    setError(null);
    try {
      await api.upload(file);
      await refresh();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
      if (input.current) input.current.value = "";
    }
  }

  return (
    <div className="column">
      <h1 className="page-title">{t.documents.title}</h1>
      <p className="lede">{t.documents.lede}</p>

      <div className="dropzone">
        <label className="drop-label">
          <input
            ref={input}
            type="file"
            accept=".pdf,.docx,.md,.markdown,.txt"
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) void onFile(file);
            }}
          />
          <span className="drop-title">{busy ? `${t.documents.uploading}…` : t.documents.drop}</span>
          <span className="drop-hint">{t.documents.dropHint}</span>
        </label>
      </div>

      {error ? <p className="erratum">{error}</p> : null}

      {docs === null ? null : docs.length === 0 ? (
        <p className="empty">{t.documents.empty}</p>
      ) : (
        <div className="entries">
          {docs.map((doc, i) => (
            <RailEntry
              key={doc.doc_id}
              mark={String(i + 1).padStart(2, "0")}
              note={doc.n_findings > 0 ? `${doc.n_findings}` : undefined}
            >
              <h2 className="entry-title">{doc.filename}</h2>
              <dl className="meta">
                <div>
                  <dt>{t.documents.chunks}</dt>
                  <dd>{doc.n_chunks}</dd>
                </div>
                <div>
                  <dt>{t.documents.findings}</dt>
                  <dd data-flagged={doc.n_findings > 0}>{doc.n_findings}</dd>
                </div>
                <div>
                  <dt>sha256</dt>
                  <dd className="hash">{doc.doc_id.slice(0, 12)}</dd>
                </div>
              </dl>
              <p className="tag">{t.documents.untrusted}</p>
            </RailEntry>
          ))}
        </div>
      )}
    </div>
  );
}
