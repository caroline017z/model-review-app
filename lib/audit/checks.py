"""Low-level check primitives shared by rules.

These were inlined as private helpers in the legacy `bible_audit.py`.
Extracted so rule modules can call them without circular imports.

Both functions preserve the exact behavior of the legacy private helpers
(`_exact_check`, `_range_check`); see `tests/test_bible_audit.py` for
the contracts they have to satisfy.
"""

from __future__ import annotations

from typing import Any

from lib.bible_reference import SSFA, TBD
from lib.config import PCT_ROWS
from lib.utils import safe_float

# Tolerance defaults when CS_AVERAGE entry omits "tol"
DEFAULT_PCT_TOL = 0.0  # exact match for percentages
DEFAULT_MONEY_TOL = 0.0  # exact match for $ values
NUMERIC_EPSILON = 1e-9


def exact_check(
    actual: Any,
    expected: Any,
    tol: float,
    unit: str = "",
    row: int | None = None,
) -> tuple[str, str]:
    """Return (status, note) for a single exact-match comparison.

    When the field is a percentage (unit='%', or row is in PCT_ROWS) or
    when the two sides disagree by >100x in magnitude, normalize both to
    fractions (0.40) before diffing. This prevents false OFFs when a model
    stores ITC as 40 and the bible stores 0.40.

    For known PCT_ROWS, normalization is deterministic (always to fraction
    form) rather than relying on the magnitude heuristic, which has edge
    cases (e.g., 0.005 vs 0.5).
    """
    a = safe_float(actual)
    e = safe_float(expected)
    if a is None:
        return "MISSING", "Model cell blank"
    if e is None:
        # Expected is a string sentinel/lookup
        if expected in (SSFA, TBD) or isinstance(expected, str):
            return "REVIEW", f"Ref: {expected}"
        return "REVIEW", "Reference non-numeric"

    # Deterministic pct normalization for known percentage rows.
    is_known_pct = row is not None and row in PCT_ROWS
    is_pct_unit = str(unit or "").strip() == "%"
    is_cross_magnitude = (abs(a) >= 5 and abs(e) <= 1.0) or (abs(e) >= 5 and abs(a) <= 1.0)
    if is_known_pct or is_pct_unit or is_cross_magnitude:
        # For known percentage rows, normalize anything > 1 to fraction form.
        # Use > 1 (not > 1.5) for known PCT_ROWS to handle escalator values
        # like 1.5% correctly (should become 0.015, not stay at 1.5).
        threshold = 1.0 if is_known_pct else 1.5
        if abs(a) > threshold:
            a = a / 100.0
        if abs(e) > threshold:
            e = e / 100.0

    diff = abs(a - e)
    if diff <= (tol or 0) + NUMERIC_EPSILON:
        return "OK", ""
    sign = "+" if a > e else "−"
    return "OFF", f"{sign}{diff:.4g} vs bible {e:.4g}"


def range_check(actual: Any, spec: dict) -> tuple[str, str]:
    """Return (status, note) for a range check from BIBLE_BENCHMARKS."""
    val = safe_float(actual)
    if val is None:
        return "MISSING", "Model cell blank"
    lo, hi = spec["min"], spec["max"]
    if val < lo:
        return "OUT", f"Below min ({lo})"
    if val > hi:
        return "OUT", f"Above max ({hi})"
    return "OK", ""
