"""COUNSEL's API.

Nothing here reaches the outside world on COUNSEL's behalf. It reads documents
a person uploaded, it reads public search results, and it writes to a local
SQLite file. There is no endpoint that posts, publishes, emails or executes,
and that is a design constraint rather than an unimplemented feature: the
project's promise is that a boardroom of agents can argue without any of them
being able to act.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from services.api import __version__
from services.api.core.killswitch import KillSwitchEngaged
from services.api.core.settings import settings
from services.api.routers import admin, documents, health, research, security

app = FastAPI(
    title="COUNSEL",
    version=__version__,
    description=(
        "Five mandates argue a real decision with live public data. "
        "No agent has a side-effect tool; nothing is ever published or executed externally."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings().cors_origins.split(",") if o.strip()],
    allow_credentials=False,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(documents.router)
app.include_router(research.router)
app.include_router(security.router)
app.include_router(admin.router)


@app.exception_handler(KillSwitchEngaged)
async def killswitch_handler(_request, exc: KillSwitchEngaged):
    from fastapi.responses import JSONResponse

    return JSONResponse(status_code=503, content={"detail": str(exc), "killswitch": True})
