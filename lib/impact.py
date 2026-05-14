"""Per-row $impact estimation for walk diffs.

Given a row number and (m1_value, m2_value, project_data), returns an
approximate dollar impact of the input delta on sponsor proceeds. Used by
walk_builder to surface magnitude alongside each variance row so reviewers
can prioritize which diffs matter.

Only rows with a known mapping produce a value — unknown rows return None,
which renders as blank in the walk export. Formulas mirror _build_sensitivity
in mockup_view.py and are calibrated against 38DN historical walks.

Sign convention: positive impact = delta favors SPONSOR (e.g., lower EPC,
higher incentive). Matches the walk's M1 - M2 delta direction: if M2 has
higher EPC than M1, the impact is negative (worse for sponsor).
"""

from __future__ import annotations

from typing import Any

from lib.financial_constants import (
    BIBLE_ELIG_FRAC,
    DEFAULT_YIELD_KWH_PER_WP,
    OPEX_NPV_FACTOR,
    OPEX_TERM_YEARS,
)
from lib.rows import (
    ROW_CLOSING,
    ROW_ELIG_COSTS,
    ROW_EPC_WRAPPED,
    ROW_ITC_PCT,
    ROW_IX,
    ROW_LNTP,
    ROW_PPA_RATE,
    ROW_UPFRONT,
)
from lib.utils import safe_float


def _delta(m1: Any, m2: Any) -> float | None:
    """Walk delta = M1 - M2 (base - case). Matches walk_builder convention."""
    f1 = safe_float(m1)
    f2 = safe_float(m2)
    if f1 is None or f2 is None:
        return None
    return f1 - f2


def _dc_w(data: dict) -> float | None:
    """Project DC size in watts — used to scale $/W inputs to absolute $."""
    mwdc = safe_float(data.get(11))
    return (mwdc * 1_000_000) if mwdc and mwdc > 0 else None


def _annual_mwh(data: dict) -> float | None:
    """Approx annual production in MWh for revenue-impact math."""
    mwdc = safe_float(data.get(11))
    yld = safe_float(data.get(14)) or DEFAULT_YIELD_KWH_PER_WP
    if mwdc and mwdc > 0 and yld > 0:
        return mwdc * yld * 1000
    return None


def _impact_per_w(m1: Any, m2: Any, data: dict) -> float | None:
    """$/W input (EPC, LNTP, Upfront Incentive, etc.) → absolute $ impact.

    Positive delta (M1 > M2) means M2 is a LOWER cost in a CapEx context
    → favors sponsor. Caller specifies sign by flipping m1/m2 if needed.
    """
    d = _delta(m1, m2)
    dc_w = _dc_w(data)
    if d is None or dc_w is None:
        return None
    return d * dc_w


def _impact_om_per_mw_yr(m1: Any, m2: Any, data: dict) -> float | None:
    """$/MW/yr opex input → 25yr NPV'd $ impact. Positive delta = lower opex
    in M2 = favors sponsor."""
    d = _delta(m1, m2)
    mwdc = safe_float(data.get(11))
    if d is None or mwdc is None:
        return None
    return d * mwdc * OPEX_TERM_YEARS * OPEX_NPV_FACTOR


def _impact_ppa_rate(m1: Any, m2: Any, data: dict) -> float | None:
    """$/kWh rate input → 25yr NPV'd revenue impact. Positive delta
    (M1 rate > M2 rate) means M2 has LESS revenue = unfavorable for sponsor,
    so we flip the sign at the call site (rates are in the ROWS_FAVORABLE
    dict marked accordingly)."""
    d = _delta(m1, m2)
    ann_mwh = _annual_mwh(data)
    if d is None or ann_mwh is None:
        return None
    # delta $/kWh × annual kWh × 25yr × NPV dampener
    return d * ann_mwh * 1000 * OPEX_TERM_YEARS * OPEX_NPV_FACTOR


def _impact_itc_pct(m1: Any, m2: Any, data: dict) -> float | None:
    """ITC % delta → $ impact via eligible costs × EPC × DC.
    Higher ITC in M2 = MORE tax credit = favorable for sponsor.
    """
    d = _delta(m1, m2)
    dc_w = _dc_w(data)
    epc = safe_float(data.get(ROW_EPC_WRAPPED))
    elig = safe_float(data.get(ROW_ELIG_COSTS)) or BIBLE_ELIG_FRAC
    if d is None or dc_w is None or epc is None:
        return None
    return d * elig * epc * dc_w


# Registry of per-row impact formulas.
# (m1_val, m2_val, project_data_dict) → float or None.
# "favor" field: True if a higher M1 value favors sponsor (e.g., a higher
# incentive in M1 means M2 took it away → negative impact on M2 side).
# CapEx rows invert: higher EPC in M1 means M2 is cheaper → M1 loses out.
_IMPACT_FORMULAS: dict[int, dict] = {
    ROW_EPC_WRAPPED: {"fn": _impact_per_w, "favor_m1_high": False},  # higher cost = worse
    ROW_LNTP: {"fn": _impact_per_w, "favor_m1_high": False},
    ROW_IX: {"fn": _impact_per_w, "favor_m1_high": False},
    ROW_CLOSING: {"fn": _impact_per_w, "favor_m1_high": False},
    ROW_UPFRONT: {"fn": _impact_per_w, "favor_m1_high": True},  # more incentive = better
    ROW_PPA_RATE: {"fn": _impact_ppa_rate, "favor_m1_high": True},  # higher rate = more revenue
    ROW_ITC_PCT: {"fn": _impact_itc_pct, "favor_m1_high": True},
    # OpEx family
    225: {"fn": _impact_om_per_mw_yr, "favor_m1_high": False},  # PV O&M Prev
    226: {"fn": _impact_om_per_mw_yr, "favor_m1_high": False},  # PV O&M Corr
    228: {"fn": _impact_om_per_mw_yr, "favor_m1_high": False},  # ESS O&M
    230: {"fn": _impact_om_per_mw_yr, "favor_m1_high": False},  # AM Fee
    240: {"fn": _impact_om_per_mw_yr, "favor_m1_high": False},  # Cust Mgmt
    296: {"fn": _impact_om_per_mw_yr, "favor_m1_high": False},  # P&C Insurance
    298: {"fn": _impact_om_per_mw_yr, "favor_m1_high": False},  # Catastrophic
    302: {"fn": _impact_om_per_mw_yr, "favor_m1_high": False},  # Internal AM
}


def per_project_impact(
    row: int,
    m1_val: Any,
    m2_val: Any,
    project_data: dict,
) -> float | None:
    """Dollar impact of M1→M2 delta on sponsor proceeds for ONE project.

    Positive = M1 better for sponsor than M2; negative = M2 better.
    Returns None for rows without a known formula.
    """
    spec = _IMPACT_FORMULAS.get(row)
    if spec is None:
        return None
    raw = spec["fn"](m1_val, m2_val, project_data)
    if raw is None:
        return None
    # Flip sign so positive always means "M1 better for sponsor".
    # _delta is M1 - M2; if a higher value favors sponsor, M1 > M2 → positive
    # already means M1 better. If lower favors sponsor (costs), M1 - M2 > 0
    # means M1 is more expensive → M1 WORSE, so flip.
    return raw if spec["favor_m1_high"] else -raw


def portfolio_impact(
    row: int,
    per_project_values: dict,
    m1_data_by_pnum: dict,
) -> float | None:
    """Sum per-project impacts across the matched portfolio.

    per_project_values: {proj_number: (m1_val, m2_val)}
    m1_data_by_pnum: {proj_number: m1_project["data"]} — provides per-project
        MWdc (row 11), yield (row 14), EPC (row 118), eligible costs (row 602)
        needed by the formulas.
    Returns None when the row has no formula OR no per-project impact
    could be computed (e.g., all projects missing required fields).
    """
    if row not in _IMPACT_FORMULAS:
        return None
    total = 0.0
    any_valid = False
    for pnum, (m1v, m2v) in per_project_values.items():
        data = m1_data_by_pnum.get(pnum)
        if data is None:
            continue
        imp = per_project_impact(row, m1v, m2v, data)
        if imp is not None:
            total += imp
            any_valid = True
    return total if any_valid else None
