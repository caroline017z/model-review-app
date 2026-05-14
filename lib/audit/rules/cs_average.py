"""CSAverageRule: cross-market exact-match against the CS_AVERAGE bible.

Ports the legacy `audit_project` block at lines 159-183 byte-for-byte.

Two pieces of bespoke logic live here:
1. **Size-dependent EPC override** — for projects under 5 MWdc, replace
   the default row-118 spec ($1.65/W) with the small-project spec
   ($1.75/W, $0.10 tol). The override is built once in `AuditContext`
   and just applied here.
2. **Per-state CS_AVERAGE overrides** — `CS_STATE_OVERRIDES` may
   substitute a different (value, tol) per state for a row (e.g., IL
   has a higher P&C insurance premium for hail risk).
"""

from __future__ import annotations

from typing import cast

from lib.audit.checks import DEFAULT_MONEY_TOL, exact_check
from lib.audit.context import AuditContext
from lib.audit.engine import AuditResult, AuditRule
from lib.bible_reference import CS_AVERAGE


class CSAverageRule(AuditRule):
    name = "cs-average"

    def apply(self, ctx: AuditContext, result: AuditResult) -> None:
        for row, spec in CS_AVERAGE.items():
            # Size-dependent EPC override for small projects (<5 MWdc)
            if row == 118 and ctx.epc_override:
                spec = ctx.epc_override
            expected = spec["value"]
            tol = cast(float, spec.get("tol", DEFAULT_MONEY_TOL))
            # State override?
            override = ctx.state_override_for(row)
            if override:
                expected = override["value"]
                tol = cast(float, override.get("tol", tol))

            unit = cast(str, spec.get("unit") or ctx.unit_for(row))
            status, note = exact_check(ctx.proj_data.get(row), expected, tol, unit, row=row)
            result.findings[row] = {
                "status": status,
                "expected": expected,
                "actual": ctx.proj_data.get(row),
                "tol": tol,
                "note": note,
                "source": "CS Average" + (f" [{ctx.state} override]" if override else ""),
                "label": spec.get("label", ""),
                "unit": unit,
            }
