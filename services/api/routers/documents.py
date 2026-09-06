"""Upload, list, and see what a document tried to do."""

from __future__ import annotations

import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from services.api import deps
from services.api.core.rbac import Scope, require
from services.api.rag.ingest import findings_for, ingest
from services.api.rag.untrusted import summarise

router = APIRouter(prefix="/documents", tags=["documents"])

MAX_UPLOAD_BYTES = 20 * 1024 * 1024


@router.post("", dependencies=[Depends(require(Scope.SESSION_WRITE))])
async def upload(file: UploadFile = File(...)) -> dict[str, object]:
    raw = await file.read()
    if len(raw) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, f"file exceeds {MAX_UPLOAD_BYTES // 1024 // 1024} MB")
    if not file.filename:
        raise HTTPException(400, "file has no name, so its type cannot be determined")

    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / Path(file.filename).name
        path.write_bytes(raw)
        try:
            doc_id, chunks = ingest(path, conn=deps.db(), embedder=deps.embedder())
        except ValueError as exc:
            raise HTTPException(415, str(exc)) from exc

    findings = findings_for(doc_id, conn=deps.db())
    return {
        "doc_id": doc_id,
        "filename": Path(file.filename).name,
        "n_chunks": len(chunks),
        "languages": sorted({c.lang for c in chunks}),
        "trust": "untrusted",
        "injection_findings": summarise(
            [
                type("F", (), {"severity": f["severity"], "pattern": f["pattern"]})()
                for f in findings
            ]
        ),
    }


@router.get("", dependencies=[Depends(require(Scope.READ))])
def list_documents() -> list[dict[str, object]]:
    rows = (
        deps.db()
        .execute(
            "SELECT d.doc_id, d.filename, d.media_type, d.n_chars, d.ingested_at, "
            "  (SELECT COUNT(*) FROM chunks c WHERE c.doc_id = d.doc_id) AS n_chunks, "
            "  (SELECT COUNT(*) FROM doc_findings f WHERE f.doc_id = d.doc_id) AS n_findings "
            "FROM documents d ORDER BY d.ingested_at DESC"
        )
        .fetchall()
    )
    return [dict(r) for r in rows]


@router.get("/{doc_id}/findings", dependencies=[Depends(require(Scope.READ))])
def document_findings(doc_id: str) -> list[dict[str, object]]:
    return findings_for(doc_id, conn=deps.db())
