"""WrappedEPCRule: surface the wrapped-EPC build for transparency.

Ports the legacy `audit_project` block at lines 268-282.

Side-output rule: writes `result.wrapped_epc` (a dict), not
`result.findings`. The UI shows the per-component breakdown
(EPC + LNTP + Safe Harbor + Contingency) alongside the row-118 finding.

The actual exact-match audit on the wrapped total happens via row 118
in CSAverageRule — this rule only surfaces the component breakdown.

Input shape (from `data_loader.load_pricing_model`):

    proj_data["_wrapped_epc_components"] = [
        {"row": int, "component": str, "value": float|None}, ...
    ]
    proj_data["_wrapped_epc_total"] = float | None
    proj_data["_raw_epc_118"]       = float | None  # value before override
"""

from __future__ import annotations

from lib.audit.context import AuditContext
from lib.audit.engine import AuditResult, AuditRule


class WrappedEPCRule(AuditRule):
    name = "wrapped-epc"

    def apply(self, ctx: AuditContext, result: AuditResult) -> None:
        result.wrapped_epc = {
            "components": ctx.proj_data.get("_wrapped_epc_components") or [],
            "total": ctx.proj_data.get("_wrapped_epc_total"),
            "raw_epc": ctx.proj_data.get("_raw_epc_118"),
        }
