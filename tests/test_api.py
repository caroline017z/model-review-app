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
        resp = client.post("/api/walk", json={
            "m1_id": "bad1", "m2_id": "bad2",
            "m1_label": "M1", "m2_label": "M2",
        })
        assert resp.status_code == 404
