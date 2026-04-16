"""Tests for the Full Bible Mapping feature."""
import pytest
from lib.mockup_view import _build_full_mapping, _categorize_audit_row
from lib.bible_audit import audit_project
from lib.rows import (
    ROW_STATE, ROW_UTILITY, ROW_PROGRAM_A, ROW_EPC_WRAPPED,
    ROW_DC_MW, ROW_INSURANCE, ROW_NPP, ROW_FMV_IRR,
)


class TestCategorizeAuditRow:
    def test_capex_row(self):
        assert _categorize_audit_row(118) == "CapEx"

    def test_opex_row(self):
        assert _categorize_audit_row(225) == "OpEx"

    def test_revenue_row(self):
        assert _categorize_audit_row(157) == "Revenue"

    def test_tax_row(self):
        assert _categorize_audit_row(597) == "Incentives & Tax"

    def test_insurance_row(self):
        assert _categorize_audit_row(296) == "OpEx"

    def test_unknown_row(self):
        assert _categorize_audit_row(9999) == "Other"


class TestBuildFullMapping:
    def test_returns_grouped_categories(self):
        audit = audit_project({
            ROW_STATE: "IL", ROW_UTILITY: "Ameren", ROW_PROGRAM_A: "ABP",
            ROW_EPC_WRAPPED: 1.65, ROW_DC_MW: 5.0,
            225: 4750, 226: 2000, 296: 4815, 597: 0.40, 602: 0.97,
        })
        mapping = _build_full_mapping(audit)
        assert isinstance(mapping, list)
        assert all("category" in g and "rows" in g for g in mapping)
        # Should have multiple categories
        cats = [g["category"] for g in mapping]
        assert "CapEx" in cats or "OpEx" in cats

    def test_includes_ok_rows(self):
        audit = audit_project({
            ROW_STATE: "IL", ROW_UTILITY: "Ameren", ROW_PROGRAM_A: "ABP",
            ROW_EPC_WRAPPED: 1.65, ROW_DC_MW: 5.0,
            225: 4750, 296: 4815,
        })
        mapping = _build_full_mapping(audit)
        all_rows = [r for g in mapping for r in g["rows"]]
        ok_rows = [r for r in all_rows if r["status"] == "OK"]
        # Should include at least some OK rows
        assert len(ok_rows) >= 1

    def test_each_row_has_required_fields(self):
        audit = audit_project({ROW_STATE: "IL", ROW_DC_MW: 5.0, ROW_EPC_WRAPPED: 1.65})
        mapping = _build_full_mapping(audit)
        for group in mapping:
            for row in group["rows"]:
                assert "row" in row
                assert "label" in row
                assert "status" in row
                assert "expected" in row
                assert "actual" in row

    def test_rows_sorted_by_row_number(self):
        audit = audit_project({
            ROW_STATE: "IL", ROW_DC_MW: 5.0,
            ROW_EPC_WRAPPED: 1.65, 119: 0.10, 122: 0.05, 123: 0.06,
        })
        mapping = _build_full_mapping(audit)
        for group in mapping:
            row_nums = [r["row"] for r in group["rows"]]
            assert row_nums == sorted(row_nums), f"{group['category']} not sorted"

    def test_empty_audit_returns_empty(self):
        mapping = _build_full_mapping({"rows": {}})
        assert mapping == []

    def test_category_order_is_canonical(self):
        audit = audit_project({
            ROW_STATE: "IL", ROW_DC_MW: 5.0,
            ROW_EPC_WRAPPED: 1.65, 225: 4750, 597: 0.40,
            157: 0.10,
        })
        mapping = _build_full_mapping(audit)
        cats = [g["category"] for g in mapping]
        # CapEx should come before Revenue, Revenue before OpEx
        if "CapEx" in cats and "Revenue" in cats:
            assert cats.index("CapEx") < cats.index("Revenue")
        if "Revenue" in cats and "OpEx" in cats:
            assert cats.index("Revenue") < cats.index("OpEx")


class TestWalkFallbackMatching:
    """Tests for walk_builder fallback matching when Project # is unavailable."""

    def test_name_fallback_when_no_project_numbers(self):
        from lib.walk_builder import match_projects
        from lib.rows import ROW_DC_MW

        m1 = {6: {"name": "Joel", "toggle": True, "data": {ROW_DC_MW: 5.0}, "rate_comps": {}, "dscr_schedule": {}}}
        m2 = {6: {"name": "Joel", "toggle": True, "data": {ROW_DC_MW: 5.0}, "rate_comps": {}, "dscr_schedule": {}}}
        matched = match_projects(m1, m2)
        # Should match by name since no Project # exists
        assert len(matched) >= 1
        assert matched[0]["name"] == "Joel"

    def test_positional_fallback(self):
        from lib.walk_builder import match_projects
        from lib.rows import ROW_DC_MW

        # Both models have projects at same column positions but no proj #
        m1 = {
            6: {"name": "A", "toggle": True, "data": {ROW_DC_MW: 5.0}, "rate_comps": {}, "dscr_schedule": {}},
            7: {"name": "B", "toggle": True, "data": {ROW_DC_MW: 3.0}, "rate_comps": {}, "dscr_schedule": {}},
        }
        m2 = {
            6: {"name": "A", "toggle": True, "data": {ROW_DC_MW: 5.0}, "rate_comps": {}, "dscr_schedule": {}},
            7: {"name": "B", "toggle": True, "data": {ROW_DC_MW: 3.0}, "rate_comps": {}, "dscr_schedule": {}},
        }
        matched = match_projects(m1, m2)
        assert len(matched) == 2


class TestExportEndpoint:
    """Tests for the review export API endpoint."""

    def test_export_produces_xlsx(self):
        from fastapi.testclient import TestClient
        from apps.api.main import app

        client = TestClient(app)
        body = {
            "model_label": "Test Model",
            "reviewer": "Test Reviewer",
            "bible_label": "Q1 '26",
            "projects": [{
                "name": "Joel",
                "verdict": "REVIEW",
                "nppPerW": 0.15,
                "irrPct": 18.0,
                "equityK": -50,
                "approved": False,
                "findings": [{
                    "field": "EPC",
                    "status": "OFF",
                    "bible": "$1.65",
                    "model": "$1.80",
                    "impact": -75000,
                    "action": "flag",
                    "note": "Check with developer",
                }],
            }],
        }
        resp = client.post("/api/export", json=body)
        assert resp.status_code == 200
        assert "spreadsheetml" in resp.headers["content-type"]
        assert len(resp.content) > 1000  # valid xlsx has content
