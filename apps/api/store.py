"""In-memory model store with TTL expiry."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any


class ModelStore:
    """Simple dict-based store for uploaded model results.

    Models expire after `ttl` seconds. Max `maxsize` models stored.
    No external dependencies (no cachetools required).
    """

    def __init__(self, maxsize: int = 20, ttl: int = 3600):
        self._data: dict[str, dict[str, Any]] = {}
        self._maxsize = maxsize
        self._ttl = ttl

    def _evict_expired(self) -> None:
        now = datetime.now(timezone.utc)
        expired = [
            k for k, v in self._data.items()
            if (now - v["uploaded_at"]).total_seconds() > self._ttl
        ]
        for k in expired:
            del self._data[k]

    def put(self, result: dict, filename: str) -> str:
        """Store a parsed model result. Returns a new model_id (UUID)."""
        self._evict_expired()
        # Evict oldest if at capacity
        while len(self._data) >= self._maxsize:
            oldest = min(self._data, key=lambda k: self._data[k]["uploaded_at"])
            del self._data[oldest]
        model_id = uuid.uuid4().hex[:12]
        self._data[model_id] = {
            "filename": filename,
            "result": result,
            "uploaded_at": datetime.now(timezone.utc),
        }
        return model_id

    def get(self, model_id: str) -> dict | None:
        """Retrieve a stored model, or None if expired/missing."""
        self._evict_expired()
        entry = self._data.get(model_id)
        return entry if entry else None

    def delete(self, model_id: str) -> bool:
        """Remove a model. Returns True if it existed."""
        return self._data.pop(model_id, None) is not None

    def list_ids(self) -> list[str]:
        self._evict_expired()
        return list(self._data.keys())


# Singleton store instance
model_store = ModelStore()
