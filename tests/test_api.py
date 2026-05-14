"""Tests for the FastAPI backend endpoints."""

import pytest
from fastapi.testclient import TestClient

from apps.api.main import app
from apps.api.store import model_store


@pytest.fixture
def client():
    model_store._data.clear()
    return TestClient(app)


class TestHealth:
    def test_health_endpoint(self, client):
        resp = client.get("/api/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"


class TestBenchmarks:
    def test_get_benchmarks(self, client):
        resp = client.get("/api/benchmarks")
        assert resp.status_code == 200
        data = resp.json()
        assert "benchmarks" in data
        assert "CapEx" in data["benchmarks"]

    def test_put_and_get_overrides(self, client):
        overrides = [{"key": "CapEx|EPC Cost ($/W)", "min_val": 1.40, "max_val": 1.90}]
        resp = client.put("/api/benchmarks", json=overrides)
        assert resp.status_code == 200
        assert resp.json()["saved"] == 1

        resp2 = client.get("/api/benchmarks")
        assert "CapEx|EPC Cost ($/W)" in resp2.json()["overrides"]

    def test_delete_resets(self, client):
        overrides = [{"key": "CapEx|EPC Cost ($/W)", "min_val": 1.40}]
        client.put("/api/benchmarks", json=overrides)
        resp = client.delete("/api/benchmarks")
        assert resp.status_code == 200
        resp2 = client.get("/api/benchmarks")
        assert resp2.json()["overrides"] == {}


class TestModels:
    def test_upload_requires_file(self, client):
        resp = client.post("/api/models/upload")
        assert resp.status_code == 422  # missing file

    def test_get_missing_model(self, client):
        resp = client.get("/api/models/nonexistent")
        assert resp.status_code == 404

    def test_delete_missing_model(self, client):
        resp = client.delete("/api/models/nonexistent")
        assert resp.status_code == 404


class TestReview:
    def test_review_missing_model(self, client):
        resp = client.post("/api/review", json={"model_id": "bad"})
        assert resp.status_code == 404


class TestWalk:
    def test_walk_missing_models(self, client):
        resp = client.post(
            "/api/walk",
            json={
                "m1_id": "bad1",
                "m2_id": "bad2",
                "m1_label": "M1",
                "m2_label": "M2",
            },
        )
        assert resp.status_code == 404


def _fake_model_result(fingerprint: str = "abc12345", projects: dict | None = None):
    """Build a minimal model_store-compatible result dict for router tests.

    Bypasses load_pricing_model — we want to exercise router logic without
    constructing a real xlsx. The projects dict shape matches what
    data_loader.load_pricing_model produces.
    """
    from lib.rows import ROW_DC_MW, ROW_LEVERED_PT_IRR, ROW_NPP, ROW_PROJECT_NUMBER

    default_projects = {
        6: {
            "name": "Alpha",
            "toggle": True,
            "col_letter": "F",
            "data": {
                ROW_PROJECT_NUMBER: 1,
                ROW_DC_MW: 5.0,
                ROW_NPP: 0.15,
                ROW_LEVERED_PT_IRR: 0.18,
                4: "Alpha",
                18: "IL",
            },
            "rate_comps": {},
            "dscr_schedule": {},
        }
    }
    return {
        "projects": projects if projects is not None else default_projects,
        "ops_sandbox": {},
        "rate_curves": {},
        "_row_map": {},
        "fingerprint": fingerprint,
    }


class TestReviewRouter:
    """Happy-path + edge cases for /api/review."""

    def test_review_returns_projects_and_portfolio(self, client):
        mid = model_store.put(_fake_model_result(), "test.xlsx")
        resp = client.post("/api/review", json={"model_id": mid})
        assert resp.status_code == 200
        data = resp.json()
        assert "projects" in data
        assert "portfolio" in data

    def test_review_respects_project_ids_filter(self, client):
        mid = model_store.put(_fake_model_result(), "test.xlsx")
        # Filter to a non-existent project id → empty result
        resp = client.post(
            "/api/review",
            json={
                "model_id": mid,
                "project_ids": ["999"],
            },
        )
        assert resp.status_code == 200
        assert resp.json()["projects"] == []


class TestWalkRouter:
    """Happy-path /api/walk with stored models."""

    def test_walk_returns_xlsx_bytes(self, client):
        m1 = model_store.put(_fake_model_result(fingerprint="same"), "m1.xlsx")
        m2 = model_store.put(_fake_model_result(fingerprint="same"), "m2.xlsx")
        resp = client.post(
            "/api/walk",
            json={
                "m1_id": m1,
                "m2_id": m2,
                "m1_label": "A",
                "m2_label": "B",
            },
        )
        assert resp.status_code == 200
        assert "spreadsheetml" in resp.headers["content-type"]
        assert len(resp.content) > 0
        # Summary header must be present and parseable.
        import json

        summary = json.loads(resp.headers["X-Walk-Summary"])
        assert summary["n_matched"] == 1

    def test_walk_template_drift_surfaces_in_summary(self, client):
        m1 = model_store.put(_fake_model_result(fingerprint="one"), "m1.xlsx")
        m2 = model_store.put(_fake_model_result(fingerprint="two"), "m2.xlsx")
        resp = client.post(
            "/api/walk",
            json={
                "m1_id": m1,
                "m2_id": m2,
                "m1_label": "A",
                "m2_label": "B",
            },
        )
        import json

        summary = json.loads(resp.headers["X-Walk-Summary"])
        assert "template_drift" in summary


class TestBenchmarksRouter:
    """Coverage for the benchmark override round-trip that test_api didn't have."""

    def test_get_benchmarks_has_expected_categories(self, client):
        resp = client.get("/api/benchmarks")
        assert resp.status_code == 200
        data = resp.json()
        for cat in ("CapEx", "Revenue", "Incentives & Tax"):
            assert cat in data["benchmarks"]

    def test_override_round_trip(self, client):
        override_key = "CapEx|EPC Cost ($/W)"
        resp = client.put(
            "/api/benchmarks",
            json=[
                {"key": override_key, "min_val": 1.60, "max_val": 1.70},
            ],
        )
        assert resp.status_code == 200
        assert resp.json()["saved"] == 1
        resp = client.get("/api/benchmarks")
        assert resp.status_code == 200
        overrides = resp.json()["overrides"]
        assert override_key in overrides
        assert overrides[override_key]["min"] == 1.60

    def test_override_delete(self, client):
        client.put(
            "/api/benchmarks",
            json=[
                {"key": "CapEx|EPC Cost ($/W)", "min_val": 1.60, "max_val": 1.70},
            ],
        )
        resp = client.delete("/api/benchmarks")
        assert resp.status_code == 200
        resp = client.get("/api/benchmarks")
        assert resp.json()["overrides"] == {}


class TestExportRouter:
    """Coverage for /api/export review summary xlsx."""

    def test_export_empty_projects_returns_xlsx(self, client):
        resp = client.post(
            "/api/export",
            json={
                "model_label": "M1",
                "reviewer": "tester",
                "bible_label": "Q1 26",
                "projects": [],
            },
        )
        assert resp.status_code == 200
        assert "spreadsheetml" in resp.headers["content-type"]
        assert len(resp.content) > 0

    def test_export_single_project_has_name_and_verdict(self, client):
        resp = client.post(
            "/api/export",
            json={
                "model_label": "M1",
                "reviewer": "tester",
                "bible_label": "Q1 26",
                "projects": [
                    {
                        "name": "Alpha",
                        "verdict": "CLEAN",
                        "nppPerW": 0.15,
                        "irrPct": 18.0,
                        "equityK": 500,
                        "findings": [],
                    }
                ],
            },
        )
        assert resp.status_code == 200
        # Parse the returned xlsx and spot-check the project name cell.
        import io

        import openpyxl

        wb = openpyxl.load_workbook(io.BytesIO(resp.content))
        all_cells = [
            str(c.value)
            for ws in wb.worksheets
            for row in ws.iter_rows()
            for c in row
            if c.value is not None
        ]
        assert any("Alpha" in s for s in all_cells)


class TestModelsRouterHappyPath:
    def test_get_model_after_put(self, client):
        mid = model_store.put(_fake_model_result(), "test.xlsx")
        resp = client.get(f"/api/models/{mid}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["model_id"] == mid
        assert data["project_count"] == 1

    def test_delete_model_after_put(self, client):
        mid = model_store.put(_fake_model_result(), "test.xlsx")
        resp = client.delete(f"/api/models/{mid}")
        assert resp.status_code == 200
        assert resp.json()["deleted"] is True
        # Subsequent get should 404.
        resp2 = client.get(f"/api/models/{mid}")
        assert resp2.status_code == 404
