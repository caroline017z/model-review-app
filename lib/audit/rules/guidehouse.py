"""GuidehouseRule: rate-component-level audit of the Guidehouse discount.

Ports the legacy `audit_project` block at lines 239-265.

Side-output rule: writes `result.guidehouse` (a list of per-component
dicts), not `result.findings`. The UI surfaces these alongside the row
findings.

Input shape (from `data_loader._scan_rate_components`):

    proj_data["_guidehouse_components"] = [
        {"idx": int, "name": str, "discount": float|None, "equity_on": bool},
        ...
    ]

Comparison: actual Guidehouse discount vs the market-expected discount
(`market["rate_discount"]`), with 0.5% tolerance. When the market has
no expected value (no MARKET_BIBLE entry, or no `rate_discount` key),
status is "REVIEW".
"""

from __future__ import annotations

from lib.audit.context import AuditContext
from lib.audit.engine import AuditResult, AuditRule


class GuidehouseRule(AuditRule):
    name = "guidehouse"

    def apply(self, ctx: AuditContext, result: AuditResult) -> None:
        # data_loader scans rate-component names for "Guidehouse" / "GH" and
        # returns each match with its applied discount %. The bible expects
        # a specific Guidehouse-derived discount per market.
        guidehouse = ctx.proj_data.get("_guidehouse_components") or []
        expected_disc = (ctx.market or {}).get("rate_discount") if ctx.market else None

        for comp in guidehouse:
            actual = comp.get("discount")
            if actual is None:
                status, note = "MISSING", "Guidehouse discount not entered"
            elif expected_disc is None:
                status, note = "REVIEW", "No bible Guidehouse discount for this market"
            else:
                diff = abs(actual - expected_disc)
                if diff <= 0.005:  # 0.5% tolerance
                    status, note = "OK", ""
                else:
                    sign = "+" if actual > expected_disc else "−"
                    status = "OFF"
                    note = f"{sign}{diff * 100:.2f} pp vs bible {expected_disc * 100:.2f}%"
            result.guidehouse.append(
                {
                    "rate_idx": comp["idx"],
                    "name": comp["name"],
                    "actual": actual,
                    "expected": expected_disc,
                    "equity_on": comp["equity_on"],
                    "status": status,
                    "note": note,
                }
            )
