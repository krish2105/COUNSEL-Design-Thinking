"""Roles, scopes, and one honest limitation.

COUNSEL has three roles because it has three genuinely different relationships
to the record:

  VIEWER   reads the record. A colleague you sent the memo to.
  ANALYST  runs sessions, uploads documents, logs outcomes. The person deciding.
  ADMIN    additionally pulls the kill switch and resets budgets.

WHAT THIS IS NOT
----------------
This is authorisation, not authentication. Phase A resolves the caller's role
from a request header, which is a claim the caller makes about itself and
trivially forgeable. That is adequate for a single-operator coursework tool
where the API is not exposed to the public internet, and it is stated here
rather than left for a reviewer to discover. Binding roles to real identities
is Phase E's work, and the scope checks below do not change when it lands —
only `current_role` does.
"""

from __future__ import annotations

from enum import StrEnum

from fastapi import Depends, Header, HTTPException, status


class Role(StrEnum):
    VIEWER = "viewer"
    ANALYST = "analyst"
    ADMIN = "admin"


class Scope(StrEnum):
    READ = "read"
    SESSION_WRITE = "session:write"
    ADMIN_WRITE = "admin:write"


ROLE_SCOPES: dict[Role, frozenset[Scope]] = {
    Role.VIEWER: frozenset({Scope.READ}),
    Role.ANALYST: frozenset({Scope.READ, Scope.SESSION_WRITE}),
    Role.ADMIN: frozenset({Scope.READ, Scope.SESSION_WRITE, Scope.ADMIN_WRITE}),
}

ROLE_HEADER = "X-Counsel-Role"


def current_role(x_counsel_role: str | None = Header(default=None)) -> Role:
    """Least privilege by default: an unrecognised or absent role is a Viewer."""
    if not x_counsel_role:
        return Role.VIEWER
    try:
        return Role(x_counsel_role.strip().lower())
    except ValueError:
        return Role.VIEWER


def scopes_for(role: Role) -> frozenset[Scope]:
    return ROLE_SCOPES[role]


def require(scope: Scope):
    """FastAPI dependency asserting the caller holds `scope`."""

    def _guard(role: Role = Depends(current_role)) -> Role:
        if scope not in ROLE_SCOPES[role]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"role '{role}' lacks scope '{scope}'",
            )
        return role

    return _guard
