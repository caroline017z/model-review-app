"""In-memory store of bible vintages.

Phase 4 ships with an in-process store. Phase 5 (SQLite persistence) will
replace this with a real database; the public API of the store
(`save`, `get`, `list`, `set_active`, `active`) is shaped to make that
migration a drop-in.

Lifecycle
---------
- On import, the store seeds itself with the bundled Q1'26 vintage and
  marks it active. The first audit a fresh process runs uses the
  bundled record, identical to the pre-Phase-4 behavior.
- Caroline uploads a new bible via `POST /api/bible/vintages` →
  `bible_store.save(bible)` → stored under the new vintage_id.
- `bible_store.set_active(vintage_id)` switches what audits use.
- `bible_store.active()` is called by audit routers to resolve the
  bible to pass into `audit_projects(bible=...)`.

Why in-memory for Phase 4
-------------------------
Bibles are 10-20 KB structures; uploads are infrequent (quarterly +
occasional hotfixes). Holding the dict in-process is fine for one
machine + one Caroline. Restarting the API rolls back to the bundled
vintage — acceptable given the audit pipeline is deterministic and a
re-upload of the same Excel produces a byte-identical record.

Phase 5 will persist via SQLAlchemy + Alembic into SQLite at
`%APPDATA%\\38dn-review\\app.db`. At that point uploads survive restarts
and historical reviews stay pinned to their original vintage.
"""

from __future__ import annotations

import threading

from lib.audit.bible import Bible


class BibleStore:
    """Thread-safe in-memory store of bible vintages.

    Always has at least one vintage (bundled Q1'26) and exactly one
    active vintage at any time.
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._vintages: dict[str, Bible] = {}
        self._active_id: str = ""
        self._seed_bundled()

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def active(self) -> Bible:
        """Current active vintage. Always returns a Bible (never None)."""
        with self._lock:
            return self._vintages[self._active_id]

    def get(self, vintage_id: str) -> Bible | None:
        """Look up a specific vintage by ID."""
        with self._lock:
            return self._vintages.get(vintage_id)

    def list_vintages(self) -> list[dict[str, str | bool]]:
        """Vintage summaries sorted oldest → newest."""
        with self._lock:
            items: list[dict[str, str | bool]] = [
                {
                    "vintage_id": v.vintage_id,
                    "label": v.label,
                    "source": v.source,
                    "uploaded_at": v.uploaded_at,
                    "is_active": v.vintage_id == self._active_id,
                }
                for v in self._vintages.values()
            ]
        items.sort(key=lambda x: str(x["uploaded_at"]))
        return items

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    def save(self, bible: Bible, *, set_active: bool = True) -> str:
        """Store a vintage. Returns its vintage_id.

        When `set_active=True` (default), the newly-saved vintage becomes
        the active one. Pass `set_active=False` to upload-without-switch.
        """
        with self._lock:
            self._vintages[bible.vintage_id] = bible
            if set_active:
                self._active_id = bible.vintage_id
            return bible.vintage_id

    def set_active(self, vintage_id: str) -> bool:
        """Set the active vintage by ID. Returns False if not found."""
        with self._lock:
            if vintage_id not in self._vintages:
                return False
            self._active_id = vintage_id
            return True

    def delete(self, vintage_id: str) -> bool:
        """Remove a vintage. Cannot delete the active one.

        Returns False if not found OR if it's the active vintage.
        """
        with self._lock:
            if vintage_id == self._active_id:
                return False
            return self._vintages.pop(vintage_id, None) is not None

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _seed_bundled(self) -> None:
        """Initialize with the Q1'26 bundled vintage as active."""
        bundled = Bible.bundled_q1_2026()
        self._vintages[bundled.vintage_id] = bundled
        self._active_id = bundled.vintage_id


# Singleton — same pattern as `apps/api/store.py:model_store`.
bible_store = BibleStore()
