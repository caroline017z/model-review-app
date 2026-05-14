"""Regression: constants exported from lib.financial_constants must be the
SAME object referenced by both consumers (lib.impact and lib.mockup_view).

This test would have caught the Tranche 2 drift where impact.py shipped
1.35 for DEFAULT_YIELD_KWH_PER_WP while mockup_view.py used 1.55.
"""

import pytest

from lib import financial_constants, impact, mockup_view


@pytest.mark.parametrize(
    "name",
    [
        "DEFAULT_YIELD_KWH_PER_WP",
        "OPEX_NPV_FACTOR",
        "OPEX_TERM_YEARS",
        "BIBLE_ELIG_FRAC",
    ],
)
def test_constants_resolve_to_same_value_in_consumers(name):
    canonical = getattr(financial_constants, name)
    assert getattr(impact, name) == canonical, (
        f"lib.impact.{name} drifted from lib.financial_constants.{name}"
    )
    assert getattr(mockup_view, name) == canonical, (
        f"lib.mockup_view.{name} drifted from lib.financial_constants.{name}"
    )


def test_canonical_values_match_38dn_standards():
    """Spot-check the canonical values against 38DN historical calibration."""
    assert financial_constants.OPEX_TERM_YEARS == 25
    assert financial_constants.OPEX_NPV_FACTOR == 0.55
    assert financial_constants.DEFAULT_YIELD_KWH_PER_WP == 1.55
    assert financial_constants.BIBLE_ELIG_FRAC == 0.97
