"""Rate Curves COD-period lookup.

Single canonical implementation of "given a per-month rate dict and a
project's COD year/quarter, return the rate at COD with a confidence flag."
Previously duplicated between lib/walk_builder.py and lib/mockup_view.py
with identical semantics — extracted here so future tweaks land once.

Confidence values:
  exact                — exact (year, month-from-quarter) match
  extrapolated_forward — first curve date on or after COD quarter start
  clamped_end          — COD is past the curve's last date; returns last rate
  None                 — no rate available (empty curve or no dateable keys)
"""
from __future__ import annotations

from typing import Mapping

from lib.utils import safe_float


def rate_at_cod(
    rc_monthly: Mapping, data: Mapping,
) -> tuple[float | None, str | None]:
    """Pick the Rate Curves rate at the project's COD period.

    rc_monthly: {datetime: $/kWh} — one RC's monthly rates for one project.
    data: project data dict (ROW_COD_YEAR=15, ROW_COD_QUARTER=587).
    """
    if not rc_monthly:
        return None, None
    cod_year_raw = safe_float(data.get(15))
    items = sorted(
        ((d, v) for d, v in rc_monthly.items() if hasattr(d, "year")),
        key=lambda kv: (kv[0].year, kv[0].month),
    )
    if not items:
        return None, None
    if cod_year_raw is None:
        # No COD year on the project — best-effort, earliest curve date.
        return safe_float(items[0][1]), "extrapolated_forward"
    cod_year = int(cod_year_raw)
    q_month = _quarter_first_month(data.get(587))
    for d, v in items:
        if d.year == cod_year and d.month == q_month:
            return safe_float(v), "exact"
    for d, v in items:
        if (d.year, d.month) >= (cod_year, q_month):
            return safe_float(v), "extrapolated_forward"
    return safe_float(items[-1][1]), "clamped_end"


def _quarter_first_month(q_raw) -> int:
    """COD Quarter cell → first month of the quarter (1, 4, 7, or 10).

    Accepts int 1-4 or strings containing "Q1"/"Q2"/"Q3"/"Q4" (case-
    insensitive, e.g. "Q3 2026"). Defaults to January when nothing
    parseable is provided.
    """
    if q_raw is None:
        return 1
    q_num = safe_float(q_raw)
    if q_num is not None and 1 <= int(q_num) <= 4:
        return (int(q_num) - 1) * 3 + 1
    s = str(q_raw).upper()
    for q, m in (("Q1", 1), ("Q2", 4), ("Q3", 7), ("Q4", 10)):
        if q in s:
            return m
    return 1
