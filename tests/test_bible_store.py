"""In-memory BibleStore CRUD tests.

Phase 4 ships an in-process store. These tests pin the contract the
Phase 5 SQLite migration must preserve (active-vintage invariants,
list ordering, delete-active guard).
"""

from __future__ import annotations

import copy

import pytest

from apps.api.bible_store import BibleStore
from lib.audit.bible import Bible


@pytest.fixture
def store() -> BibleStore:
    """Fresh store — each test gets its own to avoid bleed."""
    return BibleStore()


@pytest.fixture
def synthetic_bible() -> Bible:
    """A Bible that's not the bundled one, with a deterministic id."""
    b = Bible.bundled_q1_2026()
    b.vintage_id = "upload-test-001"
    b.label = "Test Vintage 001"
    b.source = "test-001.xlsx"
    b.uploaded_at = "2026-05-14T10:00:00+00:00"
    return b


class TestSeed:
    def test_starts_with_bundled_active(self, store):
        active = store.active()
        assert active.vintage_id == "bundled-q1-2026"

    def test_bundled_is_listed(self, store):
        vintages = store.list_vintages()
        assert len(vintages) == 1
        assert vintages[0]["vintage_id"] == "bundled-q1-2026"
        assert vintages[0]["is_active"] is True


class TestSave:
    def test_save_and_set_active(self, store, synthetic_bible):
        vid = store.save(synthetic_bible, set_active=True)
        assert vid == "upload-test-001"
        assert store.active().vintage_id == "upload-test-001"

    def test_save_without_setting_active(self, store, synthetic_bible):
        store.save(synthetic_bible, set_active=False)
        assert store.active().vintage_id == "bundled-q1-2026"
        # But it's still retrievable
        assert store.get("upload-test-001") is not None

    def test_save_default_sets_active(self, store, synthetic_bible):
        store.save(synthetic_bible)  # default set_active=True
        assert store.active().vintage_id == "upload-test-001"


class TestGet:
    def test_get_existing(self, store):
        b = store.get("bundled-q1-2026")
        assert b is not None
        assert b.vintage_id == "bundled-q1-2026"

    def test_get_missing_returns_none(self, store):
        assert store.get("does-not-exist") is None


class TestListVintages:
    def test_sorted_oldest_first(self, store, synthetic_bible):
        store.save(synthetic_bible, set_active=False)

        second = copy.deepcopy(synthetic_bible)
        second.vintage_id = "upload-test-002"
        second.uploaded_at = "2026-05-14T11:00:00+00:00"
        store.save(second, set_active=False)

        ids = [v["vintage_id"] for v in store.list_vintages()]
        # bundled (2026-01-01) → upload-001 (10:00) → upload-002 (11:00)
        assert ids == ["bundled-q1-2026", "upload-test-001", "upload-test-002"]

    def test_active_flag_matches_state(self, store, synthetic_bible):
        store.save(synthetic_bible, set_active=True)
        vintages = store.list_vintages()
        active = [v for v in vintages if v["is_active"]]
        assert len(active) == 1
        assert active[0]["vintage_id"] == "upload-test-001"


class TestSetActive:
    def test_switch_to_existing(self, store, synthetic_bible):
        store.save(synthetic_bible, set_active=False)
        assert store.set_active("upload-test-001") is True
        assert store.active().vintage_id == "upload-test-001"

    def test_switch_to_missing_returns_false(self, store):
        assert store.set_active("does-not-exist") is False
        # Active unchanged
        assert store.active().vintage_id == "bundled-q1-2026"


class TestDelete:
    def test_delete_non_active(self, store, synthetic_bible):
        store.save(synthetic_bible, set_active=False)
        assert store.delete("upload-test-001") is True
        assert store.get("upload-test-001") is None

    def test_cannot_delete_active(self, store, synthetic_bible):
        store.save(synthetic_bible, set_active=True)
        assert store.delete("upload-test-001") is False
        # Still there
        assert store.get("upload-test-001") is not None

    def test_delete_missing_returns_false(self, store):
        assert store.delete("does-not-exist") is False
