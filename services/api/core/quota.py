"""Budgets counted as REQUESTS, not tokens.

A token budget you cannot measure for free is theatre: the free tiers COUNSEL
runs on do not return trustworthy token accounting, and a number the project
cannot verify has no business appearing in a report. A request count is exact,
cheap, and the thing the free tiers actually rate-limit on.

Exhaustion is not an error. It degrades the chain to the next provider, which
is why `consume` returns a bool instead of raising.
"""

from __future__ import annotations

import sqlite3
import threading

from services.api.core.db import WRITE_LOCK


class Quota:
    """Per-provider request budget, optionally persisted.

    Pass a sqlite3 connection to survive a restart; without one the counts live
    for the life of the process, which is what tests want.
    """

    def __init__(self, limits: dict[str, int], conn: sqlite3.Connection | None = None) -> None:
        self._limits = dict(limits)
        self._conn = conn
        self._lock = threading.Lock()
        self._used: dict[str, int] = {}
        if conn is not None:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS quotas (provider TEXT PRIMARY KEY, used INTEGER NOT NULL)"
            )
            conn.commit()
            for provider, used in conn.execute("SELECT provider, used FROM quotas"):
                self._used[provider] = used

    def limit(self, provider: str) -> int:
        return self._limits.get(provider, 0)

    def remaining(self, provider: str) -> int:
        return max(0, self.limit(provider) - self._used.get(provider, 0))

    def consume(self, provider: str) -> bool:
        """Spend one request. Returns False when the budget is already spent."""
        with self._lock:
            if self.remaining(provider) <= 0:
                return False
            self._used[provider] = self._used.get(provider, 0) + 1
            if self._conn is not None:
                with WRITE_LOCK:
                    self._conn.execute(
                        "INSERT INTO quotas(provider, used) VALUES(?, ?) "
                        "ON CONFLICT(provider) DO UPDATE SET used = excluded.used",
                        (provider, self._used[provider]),
                    )
                    self._conn.commit()
            return True

    def reset(self, provider: str | None = None) -> None:
        with self._lock:
            if provider is None:
                self._used.clear()
            else:
                self._used.pop(provider, None)
            if self._conn is not None:
                if provider is None:
                    self._conn.execute("DELETE FROM quotas")
                else:
                    self._conn.execute("DELETE FROM quotas WHERE provider = ?", (provider,))
                self._conn.commit()

    def snapshot(self) -> dict[str, dict[str, int]]:
        return {
            p: {
                "limit": self.limit(p),
                "used": self._used.get(p, 0),
                "remaining": self.remaining(p),
            }
            for p in self._limits
        }
