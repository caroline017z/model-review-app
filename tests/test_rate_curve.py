"""Tests for lib.rate_curve.rate_at_cod — COD-period rate lookup.

Both walk_builder and mockup_view import from here; these tests pin the
canonical behavior so the two consumers can't drift if either is touched.
"""
from datetime import datetime

import pytest

from lib.rate_curve import rate_at_cod


def test_exact_match_year_quarter_one():
    curve = {datetime(2026, 1, 1): 0.12, datetime(2027, 1, 1): 0.13}
    rate, conf = rate_at_cod(curve, {15: 2026, 587: 1})
    assert rate == 0.12
    assert conf == "exact"


def test_exact_match_quarter_three_maps_to_july():
    curve = {datetime(2026, 7, 1): 0.115}
    rate, conf = rate_at_cod(curve, {15: 2026, 587: 3})
    assert rate == 0.115
    assert conf == "exact"


def test_extrapolated_forward_when_curve_starts_after_cod():
    curve = {datetime(2027, 1, 1): 0.13}
    rate, conf = rate_at_cod(curve, {15: 2026})
    assert rate == 0.13
    assert conf == "extrapolated_forward"


def test_clamped_end_when_cod_past_curve():
    curve = {datetime(2025, 1, 1): 0.10}
    rate, conf = rate_at_cod(curve, {15: 2030})
    assert rate == 0.10
    assert conf == "clamped_end"


def test_empty_curve_returns_none():
    rate, conf = rate_at_cod({}, {15: 2026})
    assert rate is None
    assert conf is None


def test_no_dateable_keys_returns_none():
    # Dict has values but no datetime keys — return None gracefully.
    rate, conf = rate_at_cod({"not a date": 0.1}, {15: 2026})
    assert rate is None
    assert conf is None


def test_no_cod_year_uses_earliest_curve_date():
    curve = {datetime(2026, 1, 1): 0.12, datetime(2027, 1, 1): 0.13}
    rate, conf = rate_at_cod(curve, {})
    assert rate == 0.12
    assert conf == "extrapolated_forward"


@pytest.mark.parametrize("q_str,expected_month", [
    ("Q1", 1), ("Q2", 4), ("Q3", 7), ("Q4", 10),
    ("Q3 2026", 7), ("Q4 2027", 10),
])
def test_quarter_string_parses_correctly(q_str, expected_month):
    curve = {datetime(2026, expected_month, 1): 0.20}
    rate, conf = rate_at_cod(curve, {15: 2026, 587: q_str})
    assert rate == 0.20
    assert conf == "exact"


def test_quarter_int_form_parses_correctly():
    curve = {datetime(2026, 7, 1): 0.18}
    # Quarter as bare int 3
    rate, conf = rate_at_cod(curve, {15: 2026, 587: 3})
    assert rate == 0.18
    assert conf == "exact"


def test_consumers_use_same_module():
    """Both walk_builder and mockup_view re-export the same callable —
    pin equality so a future copy-paste regression fails fast."""
    from lib.walk_builder import _rate_at_cod as wb_fn
    from lib.mockup_view import _rate_at_cod as mv_fn
    assert wb_fn is rate_at_cod
    assert mv_fn is rate_at_cod
