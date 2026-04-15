"""Unit tests for the audit engine's tolerance + status logic."""
import pytest
from bible_audit import _exact_check, _range_check


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
