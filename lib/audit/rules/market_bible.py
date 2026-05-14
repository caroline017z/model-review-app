"""MarketBibleRule: (state, utility, program)-keyed exact-match audit.

Ports the legacy `audit_project` block at lines 185-207.

Bespoke logic preserved:

1. **ABP REC live override** — when the data_loader sets
   `proj_data["_abp_rec_live"] = True` (an ABP REC rate component is
   toggled on for equity), the lookup forces `program_used = "ABP"`
   regardless of the project's text program field. This recovers the
   correct IL Ameren / IL ComEd market entry when models label the
   program "Community" or leave it blank. The override is applied in
   `AuditContext.from_proj_data`; this rule just reads `ctx.market`
   and the `ctx.market_source_note` suffix.

2. **Customer-mgmt unit conversion** — bible row 240 stores customer-mgmt
   cost in $/kWh but most models store it as $/MW/yr. Detected by
   magnitude (model > 100, bible < 1) and converted:
       $/kWh × yield (kWh/Wdc) × 1e6 = $/MW/yr
   with a 5% tolerance for rounding. Applied per-row inside this rule.
"""

from __future__ import annotations

from lib.audit.checks import exact_check
from lib.audit.context import AuditContext
from lib.audit.engine import AuditResult, AuditRule
from lib.utils import safe_float


class MarketBibleRule(AuditRule):
    name = "market-bible"

    def apply(self, ctx: AuditContext, result: AuditResult) -> None:
        if not ctx.market:
            return

        _yield = ctx.yield_kwh_per_wp

        for k, expected in ctx.market.items():
            if not isinstance(k, int):
                continue
            tol = 0.0
            mkt_unit = ctx.unit_for(k)
            actual = ctx.proj_data.get(k)

            # Unit conversion: bible stores customer mgmt/acq in $/kWh but
            # models often store these as $/MW/yr. Detect by magnitude:
            # if bible value < 0.1 and model value > 100, convert bible to
            # $/MW/yr.
            exp_for_check = expected
            if k == 240 and _yield > 0:
                a_float = safe_float(actual)
                e_float = safe_float(expected)
                if a_float is not None and e_float is not None and a_float > 100 and e_float < 1:
                    # Convert bible $/kWh to $/MW/yr:
                    # $/kWh × yield(kWh/Wdc) × 1,000,000(W/MW) = $/MW/yr
                    exp_for_check = e_float * _yield * 1_000_000
                    tol = exp_for_check * 0.05  # 5% tolerance for rounding
                    mkt_unit = "$/MW/yr"

            status, note = exact_check(actual, exp_for_check, tol, mkt_unit, row=k)
            # Store converted expected for display clarity
            if exp_for_check != expected:
                expected = exp_for_check
            result.findings[k] = {
                "status": status,
                "expected": expected,
                "actual": ctx.proj_data.get(k),
                "tol": tol,
                "note": note,
                "source": f"Market: {ctx.state}/{ctx.utility}/{ctx.program_used}"
                + ctx.market_source_note,
                "label": "",
                "unit": mkt_unit,
            }
