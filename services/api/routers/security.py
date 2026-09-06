"""The untrusted-content scanner, exposed so a person can watch it work.

Phase E's harness attacks this. Phase A puts it behind an endpoint because a
control nobody can see is a control nobody believes, and 'the Auditor caught it'
is a far better sentence when the audience just watched it happen to text they
typed themselves.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from services.api.core.rbac import Scope, require
from services.api.rag.untrusted import scan, summarise, wrap

router = APIRouter(prefix="/security", tags=["security"])


class Text(BaseModel):
    text: str = Field(min_length=1, max_length=20_000)
    source: str = Field(default="pasted text", max_length=120)


@router.post("/scan", dependencies=[Depends(require(Scope.READ))])
def scan_text(body: Text) -> dict[str, object]:
    findings = scan(body.text)
    return {
        "summary": summarise(findings),
        "findings": [
            {
                "pattern": f.pattern,
                "severity": f.severity,
                "start": f.span[0],
                "end": f.span[1],
                "excerpt": f.excerpt,
            }
            for f in findings
        ],
        "wrapped_preview": wrap(body.text, source=body.source)[:2000],
    }
