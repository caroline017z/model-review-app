"""Unit tests for the audit engine's tolerance + status logic."""
import pytest
from lib.bible_audit import _exact_check, _range_check


class TestExactCheck:
    def test_exact_numeric_match_ok(self):
        status, _ = _exact_check(1.65, 1.65, 0.01)
        assert status == "OK"

    def test_within_tolerance_ok(self):
        status, _ = _exact_check(1.70, 1.65, 0.10)
        assert status == "OK"

    def test_outside_tolerance_off(self):
        status, note = _exact_check(1.22, 1.65, 0.10)
        assert status == "OFF"
        # Note format: "−0.43 vs bible 1.65" (either sign glyph acceptable)
        assert "0.43" in note or "0.4300" in note

    def test_missing_actual(self):
        status, _ = _exact_check(None, 0.40, 0.0)
        assert status == "MISSING"

    def test_sentinel_expected_triggers_review(self):
        status, note = _exact_check(0.40, "S-SFA", 0.0)
        assert status == "REVIEW"
        assert "S-SFA" in note

    # --- H1: percent / fraction normalization ---
    def test_pct_vs_fraction_with_unit_hint(self):
        # Model stores ITC as whole percent (40), bible as decimal (0.40)
        status, _ = _exact_check(40, 0.40, 0.001, unit="%")
        assert status == "OK"

    def test_pct_vs_fraction_without_unit_hint(self):
        # Magnitude heuristic fallback still catches the mismatch.
        status, _ = _exact_check(40, 0.40, 0.001)
        assert status == "OK"

    def test_fraction_vs_pct_with_unit_hint(self):
        status, _ = _exact_check(0.40, 40, 0.001, unit="%")
        assert status == "OK"

    def test_true_ten_pp_miss_still_flags(self):
        # Model 50%, bible 40% — real 10pp miss, not a unit glitch.
        status, note = _exact_check(50, 0.40, 0.001, unit="%")
        assert status == "OFF"
        assert "0.1" in note  # diff = 0.10 after normalization


class TestExactCheckPctRows:
    """Tests for deterministic PCT_ROWS normalization."""

    def test_known_pct_row_normalizes(self):
        # Row 597 (ITC) is in PCT_ROWS: 40 vs 0.40 should be OK
        status, _ = _exact_check(40, 0.40, 0.001, row=597)
        assert status == "OK"

    def test_known_pct_row_fraction_vs_fraction(self):
        status, _ = _exact_check(0.40, 0.40, 0.001, row=597)
        assert status == "OK"

    def test_known_pct_row_real_mismatch(self):
        # 30% vs 40% = real 10pp miss
        status, _ = _exact_check(30, 0.40, 0.001, row=597)
        assert status == "OFF"

    def test_small_fraction_edge_case(self):
        # Row 158 (Escalator) in PCT_ROWS: 0.015 vs 0.015 should be OK
        status, _ = _exact_check(0.015, 0.015, 0.001, row=158)
        assert status == "OK"

    def test_escalator_pct_vs_fraction(self):
        # 1.5 (whole %) vs 0.015 (fraction) — row-based normalization handles this
        status, _ = _exact_check(1.5, 0.015, 0.001, row=158)
        assert status == "OK"


class TestRangeCheck:
    def test_inside_range(self):
        spec = {"min": 1.55, "max": 1.75}
        status, _ = _range_check(1.65, spec)
        assert status == "OK"

    def test_below_min(self):
        status, _ = _range_check(1.40, {"min": 1.55, "max": 1.75})
        assert status == "OUT"

    def test_above_max(self):
        status, _ = _range_check(2.00, {"min": 1.55, "max": 1.75})
        assert status == "OUT"

    def test_missing_blank(self):
        status, _ = _range_check(None, {"min": 1.55, "max": 1.75})
        assert status == "MISSING"


class TestAuditProjectEndToEnd:
    """Integration test for the full audit_project orchestration."""

    def test_minimal_project_produces_findings(self):
        from lib.bible_audit import audit_project
        from lib.rows import ROW_STATE, ROW_UTILITY, ROW_PROGRAM_A, ROW_EPC_WRAPPED
        proj_data = {
            ROW_STATE: "IL",
            ROW_UTILITY: "Ameren",
            ROW_PROGRAM_A: "Community",
            ROW_EPC_WRAPPED: 1.65,
        }
        result = audit_project(proj_data)
        assert "rows" in result
        assert "summary" in result
        assert isinstance(result["summary"], dict)
        # Should have findings for at least some rows
        assert len(result["rows"]) > 0
        # Summary should count statuses
        for status in ("OK", "OFF", "OUT", "MISSING", "REVIEW"):
            assert status in result["summary"]

    def test_missing_state_still_works(self):
        from lib.bible_audit import audit_project
        proj_data = {}
        result = audit_project(proj_data)
        assert "rows" in result
        # Should not crash, but most things will be MISSING
        assert result["summary"]["MISSING"] >= 0


class TestRCCoverageAudit:
    """RC1-RC6 three-model active/term audit.

    Belfast 1 carried two model busts that the audit must catch:
      - RC5 active on equity when nominally dormant for community solar
      - RC1 term = 25yr against system life = 30yr (5yr revenue gap)
    Combined ~$0.90/W phantom NPP accretion. These tests pin the audit
    to those flag conditions plus the three-model active-state divergence
    case (override block governs when Match toggle is OFF).
    """

    def _build_belfast_like_proj(self):
        """Synthetic proj_data reproducing Belfast 1's RC config bust."""
        from lib.rows import (
            ROW_STATE, ROW_UTILITY, ROW_PROGRAM_A, ROW_EPC_WRAPPED, ROW_SYSTEM_LIFE,
        )
        return {
            ROW_STATE: "MD",
            ROW_UTILITY: "Delmarva",
            ROW_PROGRAM_A: "Community",
            ROW_EPC_WRAPPED: 1.65,
            ROW_SYSTEM_LIFE: 30,
            "_debt_match_equity": "Yes",
            "_appraisal_match_equity": "Yes",
            "_rate_comps": {
                1: {
                    "name": "GH25 Energy", "custom_generic": "Generic",
                    "energy_rate": 0.085, "term": 25,  # BUST: 25 vs 30 system life
                    "discount": 0.225,
                    "equity_on": 1.0, "debt_on": 1.0, "appraisal_on": 1.0,
                },
                2: {
                    "name": "Contracted REC", "custom_generic": "Generic",
                    "energy_rate": 0.020, "term": 30, "discount": 0.0,
                    "equity_on": 1.0, "debt_on": 1.0, "appraisal_on": 1.0,
                },
                4: {
                    "name": "GH25 Appraisal", "custom_generic": "Generic",
                    "energy_rate": 0.100, "term": 30, "discount": 0.0,
                    "equity_on": 0.0, "debt_on": 0.0, "appraisal_on": 1.0,
                },
                5: {
                    "name": "Phantom RC5", "custom_generic": "Generic",
                    "energy_rate": 0.05, "term": 30, "discount": 0.0,
                    "equity_on": 1.0, "debt_on": 1.0, "appraisal_on": 1.0,
                },
            },
        }

    def test_term_shortfall_flags_off(self):
        """RC1 active with term 25yr vs 30yr system life → OFF."""
        from lib.bible_audit import audit_project
        result = audit_project(self._build_belfast_like_proj())
        rc1 = next(r for r in result["rc_coverage"] if r["idx"] == 1)
        assert rc1["status"] == "OFF"
        assert any("shorter than system life" in i for i in rc1["issues"])

    def test_dormant_rc5_active_flags_review(self):
        """RC5 active on equity → REVIEW (atypical but not always a bust)."""
        from lib.bible_audit import audit_project
        result = audit_project(self._build_belfast_like_proj())
        rc5 = next(r for r in result["rc_coverage"] if r["idx"] == 5)
        # RC5 is also active on debt/appraisal in the synthetic input — no
        # active-state divergence, so it lands at REVIEW from the dormant-slot
        # check, not OFF.
        assert rc5["status"] == "REVIEW"
        assert any("atypical" in i for i in rc5["issues"])

    def test_clean_project_passes_audit(self):
        """RC1 with full 30yr term + no phantom RC5 → OK on RC1."""
        from lib.bible_audit import audit_project
        proj = self._build_belfast_like_proj()
        proj["_rate_comps"][1]["term"] = 30
        del proj["_rate_comps"][5]
        result = audit_project(proj)
        rc1 = next(r for r in result["rc_coverage"] if r["idx"] == 1)
        assert rc1["status"] == "OK"
        assert rc1["issues"] == []

    def test_active_state_divergence_flags_when_match_off(self):
        """Debt RC active diverges from equity AND Match=OFF → OFF."""
        from lib.bible_audit import audit_project
        proj = self._build_belfast_like_proj()
        proj["_debt_match_equity"] = "No"
        # RC1 active on equity but off on debt with Match=No → divergence
        proj["_rate_comps"][1]["debt_on"] = 0.0
        proj["_rate_comps"][1]["term"] = 30  # silence the unrelated term flag
        del proj["_rate_comps"][5]            # silence the unrelated RC5 review
        result = audit_project(proj)
        rc1 = next(r for r in result["rc_coverage"] if r["idx"] == 1)
        assert rc1["status"] == "OFF"
        assert any("Debt active" in i and "Equity active" in i for i in rc1["issues"])

    def test_active_state_divergence_silent_when_match_on(self):
        """Match=Yes → debt/appraisal toggles dormant → no divergence flag."""
        from lib.bible_audit import audit_project
        proj = self._build_belfast_like_proj()
        proj["_debt_match_equity"] = "Yes"
        proj["_rate_comps"][1]["debt_on"] = 0.0  # would diverge if Match=No
        proj["_rate_comps"][1]["term"] = 30
        del proj["_rate_comps"][5]
        result = audit_project(proj)
        rc1 = next(r for r in result["rc_coverage"] if r["idx"] == 1)
        # Term clean + RC5 absent + Match=Yes suppresses divergence → OK
        assert rc1["status"] == "OK"

    def test_match_toggles_surfaced_in_result(self):
        from lib.bible_audit import audit_project
        result = audit_project(self._build_belfast_like_proj())
        toggles = result["rc_match_toggles"]
        assert toggles["debt_match_equity"] is True
        assert toggles["appraisal_match_equity"] is True

    def test_missing_rate_comps_returns_empty_coverage(self):
        from lib.bible_audit import audit_project
        result = audit_project({})
        assert result["rc_coverage"] == []
