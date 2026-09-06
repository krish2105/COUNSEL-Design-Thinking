"""The controls a person needs when something is going wrong."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from services.api import deps
from services.api.core import killswitch
from services.api.core.rbac import Scope, require

router = APIRouter(prefix="/admin", tags=["admin"])


class Engage(BaseModel):
    reason: str = Field(min_length=1, max_length=280)


@router.post("/killswitch", dependencies=[Depends(require(Scope.ADMIN_WRITE))])
def engage(body: Engage) -> dict[str, object]:
    killswitch.engage(body.reason)
    return {"engaged": True, "reason": killswitch.reason()}


@router.delete("/killswitch", dependencies=[Depends(require(Scope.ADMIN_WRITE))])
def release() -> dict[str, object]:
    killswitch.release()
    return {"engaged": False}


@router.get("/quota", dependencies=[Depends(require(Scope.READ))])
def quota() -> dict[str, object]:
    return {"unit": "requests", "providers": deps.quota().snapshot()}
