"""Tests for walk_builder.py — project matching, metrics, diff, and xlsx generation."""
import io
import pytest
from rows import ROW_PROJECT_NUMBER, ROW_DC_MW, ROW_NPP, ROW_FMV_IRR
from walk_builder import match_projects, extract_metrics, diff_inputs, _categorize_row, build_walk_xlsx


def _make_projects(*specs):
    """Build a fake projects dict. Each spec = (col, proj_num, name, data_overrides)."""
    projects = {}
    for col, pnum, name, overrides in specs:
        data = {ROW_PROJECT_NUMBER: pnum, ROW_DC_MW: 5.0, ROW_NPP: 0.10, ROW_FMV_IRR: 0.18}
        data.update(overrides or {})
        projects[col] = {
            "name": name, "toggle": True, "col_letter": "F",
            "data": data, "rate_comps": {}, "dscr_schedule": {},
        }
    return projects


class TestMatchProjects:
    def test_matches_by_project_number(self):
        m1 = _make_projects((6, 1, "Joel", {}), (7, 2, "Rhea", {}))
        m2 = _make_projects((6, 1, "Joel", {}), (7, 2, "Rhea", {}))
        matched = match_projects(m1, m2)
        assert len(matched) == 2
        assert matched[0]["proj_number"] == 1
        assert matched[1]["proj_number"] == 2

    def test_unmatched_projects_excluded(self):
        m1 = _make_projects((6, 1, "Joel", {}), (7, 3, "Canary", {}))
        m2 = _make_projects((6, 1, "Joel", {}), (7, 2, "Rhea", {}))
        matched = match_projects(m1, m2)
        assert len(matched) == 1
        assert matched[0]["proj_number"] == 1

    def test_empty_models_return_empty(self):
        assert match_projects({}, {}) == []

    def test_none_project_number_uses_fallback(self):
        """When project # is None, fallback matching (positional or name) kicks in."""
        m1 = _make_projects((6, None, "Unknown", {}))
        m2 = _make_projects((6, None, "Unknown", {}))
        matched = match_projects(m1, m2)
        # Fallback should match by position or name
        assert len(matched) >= 1


class TestExtractMetrics:
    def test_extracts_npp_irr_mwdc(self):
        m1 = _make_projects((6, 1, "Joel", {ROW_NPP: 0.15, ROW_FMV_IRR: 0.20, ROW_DC_MW: 10.0}))
        m2 = _make_projects((6, 1, "Joel", {ROW_NPP: 0.12, ROW_FMV_IRR: 0.18, ROW_DC_MW: 10.0}))
        matched = match_projects(m1, m2)
        metrics = extract_metrics(matched, m1, m2)
        assert len(metrics) == 1
        assert metrics[0]["m1_npp"] == 0.15
        assert metrics[0]["m2_npp"] == 0.12
        assert metrics[0]["mwdc"] == 10.0


class TestDiffInputs:
    def test_detects_numeric_difference(self):
        m1 = _make_projects((6, 1, "Joel", {118: 1.65}))
        m2 = _make_projects((6, 1, "Joel", {118: 1.75}))
        matched = match_projects(m1, m2)
        diffs = diff_inputs(matched, m1, m2)
        epc_diffs = [d for d in diffs if d["row"] == 118]
        assert len(epc_diffs) == 1
        assert epc_diffs[0]["category"] == "CapEx"

    def test_identical_values_no_diff(self):
        m1 = _make_projects((6, 1, "Joel", {118: 1.65}))
        m2 = _make_projects((6, 1, "Joel", {118: 1.65}))
        matched = match_projects(m1, m2)
        diffs = diff_inputs(matched, m1, m2)
        epc_diffs = [d for d in diffs if d["row"] == 118]
        assert len(epc_diffs) == 0

    def test_skips_identity_rows(self):
        # Row 4 (Project Name) should be skipped
        m1 = _make_projects((6, 1, "Joel", {4: "Joel"}))
        m2 = _make_projects((6, 1, "Joel", {4: "Joel Changed"}))
        matched = match_projects(m1, m2)
        diffs = diff_inputs(matched, m1, m2)
        name_diffs = [d for d in diffs if d["row"] == 4]
        assert len(name_diffs) == 0


class TestCategorizeRow:
    def test_capex_row(self):
        assert _categorize_row(118) == "CapEx"

    def test_revenue_row(self):
        assert _categorize_row(157) == "Revenue"

    def test_tax_row(self):
        assert _categorize_row(597) == "Incentives & Tax"

    def test_unknown_row(self):
        assert _categorize_row(9999) == "Other"


class TestBuildWalkXlsx:
    def test_produces_valid_xlsx(self):
        m1 = {"projects": _make_projects((6, 1, "Joel", {ROW_NPP: 0.15, ROW_DC_MW: 10.0}))}
        m2 = {"projects": _make_projects((6, 1, "Joel", {ROW_NPP: 0.12, ROW_DC_MW: 10.0}))}
        buf, summary = build_walk_xlsx(m1, m2, "Base Case", "Scenario 2")
        assert isinstance(buf, io.BytesIO)
        assert summary["n_matched"] == 1
        assert summary["m1_label"] == "Base Case"
        # Verify it's a valid xlsx by reading it back
        import openpyxl
        wb = openpyxl.load_workbook(buf)
        ws = wb.active
        assert ws.title == "Build Walk"
        # Check case header exists
        assert ws.cell(row=3, column=5).value == 1
        # Check project name is in the data
        assert ws.cell(row=7, column=2).value == "Joel"
        wb.close()

    def test_no_match_produces_empty_xlsx(self):
        m1 = {"projects": _make_projects((6, 1, "Joel", {}))}
        m2 = {"projects": _make_projects((6, 2, "Rhea", {}))}
        buf, summary = build_walk_xlsx(m1, m2, "M1", "M2")
        assert summary["n_matched"] == 0
        # Should still produce valid xlsx
        import openpyxl
        wb = openpyxl.load_workbook(buf)
        assert wb.active.title == "Build Walk"
        wb.close()


class TestPortedWalkSpec:
    """Regression tests for the spec ports into lib.walk_builder (FastAPI path).

    Locks in: Δ direction (M1 - M2), bool/int equality, IRR row 37, Notes
    column, Unmatched sheet, property-tax inputs-only behavior.
    Imports from lib.* explicitly because the FastAPI route uses lib/walk_builder.py.
    """

    def test_irr_uses_row_37_not_row_31(self):
        from lib.rows import ROW_LEVERED_PT_IRR
        from lib.walk_builder import match_projects as lib_match, extract_metrics as lib_extract
        assert ROW_LEVERED_PT_IRR == 37
        m1 = _make_projects((6, 1, "Joel", {ROW_LEVERED_PT_IRR: 0.18, 31: 0.99}))
        m2 = _make_projects((6, 1, "Joel", {ROW_LEVERED_PT_IRR: 0.20, 31: 0.99}))
        matched = lib_match(m1, m2)
        metrics = lib_extract(matched, m1, m2)
        assert metrics[0]["m1_irr"] == 0.18
        assert metrics[0]["m2_irr"] == 0.20

    def test_delta_direction_is_m1_minus_m2(self):
        from lib.walk_builder import build_walk_xlsx as lib_build
        m1 = {"projects": _make_projects((6, 1, "Joel", {ROW_NPP: 0.15, ROW_DC_MW: 10.0}))}
        m2 = {"projects": _make_projects((6, 1, "Joel", {ROW_NPP: 0.10, ROW_DC_MW: 10.0}))}
        buf, _ = lib_build(m1, m2, "M1", "M2")
        import openpyxl
        wb = openpyxl.load_workbook(buf)
        ws = wb["Build Walk"]
        delta_formula = ws.cell(row=7, column=7).value
        assert delta_formula is not None
        assert delta_formula.replace(" ", "") == "=E7-H7", (
            f"Expected M1-M2 formula =E7-H7, got {delta_formula!r}")
        wb.close()

    def test_bool_vs_int_toggle_not_a_diff(self):
        from lib.walk_builder import match_projects as lib_match, diff_inputs as lib_diff
        m1 = _make_projects((6, 1, "Joel", {291: True}))
        m2 = _make_projects((6, 1, "Joel", {291: 1}))
        matched = lib_match(m1, m2)
        diffs = lib_diff(matched, m1, m2)
        proptax_diffs = [d for d in diffs if d["row"] == 291]
        assert len(proptax_diffs) == 0, (
            "True vs 1 on PropTax toggle should not flag as differing")

    def test_bool_vs_int_genuine_diff_still_detected(self):
        from lib.walk_builder import match_projects as lib_match, diff_inputs as lib_diff
        m1 = _make_projects((6, 1, "Joel", {291: True}))
        m2 = _make_projects((6, 1, "Joel", {291: False}))
        matched = lib_match(m1, m2)
        diffs = lib_diff(matched, m1, m2)
        proptax_diffs = [d for d in diffs if d["row"] == 291]
        assert len(proptax_diffs) == 1

    def test_n_diff_count_in_diff_record(self):
        from lib.walk_builder import match_projects as lib_match, diff_inputs as lib_diff
        m1 = _make_projects(
            (6, 1, "A", {118: 1.65}),
            (7, 2, "B", {118: 1.65}),
            (8, 3, "C", {118: 1.65}),
        )
        m2 = _make_projects(
            (6, 1, "A", {118: 1.65}),
            (7, 2, "B", {118: 1.65}),
            (8, 3, "C", {118: 1.99}),
        )
        matched = lib_match(m1, m2)
        diffs = lib_diff(matched, m1, m2)
        epc = [d for d in diffs if d["row"] == 118]
        assert epc and epc[0]["n_diff"] == 1
        assert epc[0]["n_total"] == 3

    def test_notes_column_written(self):
        from lib.walk_builder import build_walk_xlsx as lib_build
        m1 = {"projects": _make_projects(
            (6, 1, "A", {118: 1.65}),
            (7, 2, "B", {118: 1.65}),
        )}
        m2 = {"projects": _make_projects(
            (6, 1, "A", {118: 1.65}),
            (7, 2, "B", {118: 1.99}),
        )}
        buf, _ = lib_build(m1, m2, "M1", "M2")
        import openpyxl
        wb = openpyxl.load_workbook(buf)
        ws = wb["Build Walk"]
        found = False
        for r in range(1, ws.max_row + 1):
            if ws.cell(row=r, column=2).value and "EPC" in str(ws.cell(row=r, column=2).value):
                note = ws.cell(row=r, column=10).value
                if note and "differs for 1 of 2" in str(note):
                    found = True
                    break
        assert found, "Notes column missing 'differs for 1 of 2 projects'"
        wb.close()

    def test_unmatched_sheet_when_orphans_exist(self):
        from lib.walk_builder import build_walk_xlsx as lib_build
        m1 = {"projects": _make_projects(
            (6, 1, "Matched", {}),
            (7, 99, "M1Orphan", {}),
        )}
        m2 = {"projects": _make_projects(
            (6, 1, "Matched", {}),
            (7, 88, "M2Orphan", {}),
        )}
        buf, summary = lib_build(m1, m2, "M1", "M2")
        import openpyxl
        wb = openpyxl.load_workbook(buf)
        assert "Unmatched" in wb.sheetnames
        assert summary["n_unmatched_m1"] == 1
        assert summary["n_unmatched_m2"] == 1
        un = wb["Unmatched"]
        all_strings = []
        for row in un.iter_rows(values_only=True):
            for v in row:
                if v is not None:
                    all_strings.append(str(v))
        assert any("M1Orphan" in s for s in all_strings)
        assert any("M2Orphan" in s for s in all_strings)
        wb.close()

    def test_no_unmatched_sheet_when_clean_pairing(self):
        from lib.walk_builder import build_walk_xlsx as lib_build
        m1 = {"projects": _make_projects((6, 1, "Joel", {}))}
        m2 = {"projects": _make_projects((6, 1, "Joel", {}))}
        buf, summary = lib_build(m1, m2, "M1", "M2")
        import openpyxl
        wb = openpyxl.load_workbook(buf)
        assert "Unmatched" not in wb.sheetnames
        assert summary["n_unmatched_m1"] == 0
        assert summary["n_unmatched_m2"] == 0
        wb.close()

    def test_filename_sanitization(self):
        from apps.api.routers.walk import _safe_filename_part
        assert _safe_filename_part("Macro: foo") == "Macro_foo"
        assert _safe_filename_part('a/b\\c:d?e') == "abcde"
        assert _safe_filename_part("") == "model"
        assert _safe_filename_part("   ") == "model"
