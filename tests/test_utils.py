"""Tests for utils.py — safe_float and formatting edge cases."""
from utils import safe_float, fmt_row_val, fmt_delta


class TestSafeFloat:
    def test_none_returns_none(self):
        assert safe_float(None) is None

    def test_empty_string_returns_none(self):
        assert safe_float("") is None

    def test_numeric_string(self):
        assert safe_float("3.14") == 3.14

    def test_integer(self):
        assert safe_float(42) == 42.0

    def test_float_passthrough(self):
        assert safe_float(1.65) == 1.65

    def test_non_numeric_string(self):
        assert safe_float("hello") is None

    def test_boolean_true(self):
        # Python's float(True) == 1.0 — verify we allow it
        assert safe_float(True) == 1.0


class TestFmtRowVal:
    def test_none_returns_dash(self):
        assert fmt_row_val(None, 118) == "\u2014"

    def test_pct_row_fraction(self):
        # Row 597 (ITC) is in PCT_ROWS
        result = fmt_row_val(0.40, 597)
        assert "40" in result

    def test_dpw_row(self):
        # Row 118 is in DPW_ROWS
        result = fmt_row_val(1.65, 118)
        assert "1.650" in result

    def test_int_row(self):
        # Row 15 (COD year) is in INT_ROWS
        result = fmt_row_val(2027, 15)
        assert "2,027" in result


class TestFmtDelta:
    def test_none_returns_dash(self):
        assert fmt_delta(None) == "\u2014"

    def test_negative_gets_parens(self):
        result = fmt_delta(-0.05)
        assert "(" in result and ")" in result

    def test_positive_no_parens(self):
        result = fmt_delta(0.05)
        assert "(" not in result
