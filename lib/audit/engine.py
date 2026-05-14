"""AuditEngine: runs an ordered list of AuditRule against one project.

Result shape preserves the legacy `audit_project` return contract:

    {
        "rows": {row: finding_dict, ...},   # CS_AVERAGE + MARKET + RANGE
        "state": str | None,
        "utility": str | None,
        "program": str | None,               # raw, as-read from proj_data
        "program_used": str | None,          # after ABP REC override
        "abp_rec_live": bool,
        "market_matched": bool,
        "guidehouse": list[dict],            # GuidehouseRule output
        "wrapped_epc": dict,                 # WrappedEPCRule output
        "summary": {OK/OFF/OUT/MISSING/REVIEW: int},
    }

Rules cooperate via the AuditResult mutable accumulator. Most rules
write into `result.findings`; Guidehouse and WrappedEPC write into
their dedicated side-output fields. RangeCheckRule deliberately
runs LAST among the findings-rules because it MERGES with prior
exact-match findings (OFF takes priority over OUT, etc.).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from lib.audit.context import AuditContext


@dataclass
class AuditResult:
    """Mutable accumulator passed to every rule; serialized at the end.

    The legacy `audit_project` return dict has a flat shape that mixes
    row-level findings with project-level metadata + side outputs.
    `AuditResult.to_dict()` reconstructs that exact shape.
    """

    context: AuditContext
    findings: dict[int, dict[str, Any]] = field(default_factory=dict)
    guidehouse: list[dict[str, Any]] = field(default_factory=list)
    wrapped_epc: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        ctx = self.context
        return {
            "rows": self.findings,
            "state": ctx.state,
            "utility": ctx.utility,
            "program": ctx.program,
            "program_used": ctx.program_used,
            "abp_rec_live": ctx.abp_rec_live,
            "market_matched": ctx.market is not None,
            "guidehouse": self.guidehouse,
            "wrapped_epc": self.wrapped_epc,
            "summary": _summarize(self.findings),
        }


class AuditRule(ABC):
    """Base class for audit rules.

    Each rule receives the per-project context + the accumulating
    `AuditResult` and mutates the result in place. Rules are pure with
    respect to `context` (read-only) but may write to `result`.

    Subclasses must set `name` (used for debugging + future telemetry)
    and implement `apply`.
    """

    name: str = "unnamed-rule"

    @abstractmethod
    def apply(self, ctx: AuditContext, result: AuditResult) -> None: ...


class AuditEngine:
    """Run an ordered list of rules and return a legacy-compatible dict."""

    def __init__(self, rules: list[AuditRule]):
        self.rules = list(rules)

    def run(self, proj_data: dict) -> dict[str, Any]:
        """Audit a single project. Mirrors `bible_audit.audit_project`."""
        ctx = AuditContext.from_proj_data(proj_data)
        result = AuditResult(context=ctx)
        for rule in self.rules:
            rule.apply(ctx, result)
        return result.to_dict()


def _summarize(findings: dict[int, dict[str, Any]]) -> dict[str, int]:
    """Count findings by status — matches legacy `_summarize`."""
    counts = {"OK": 0, "OFF": 0, "OUT": 0, "MISSING": 0, "REVIEW": 0}
    for f in findings.values():
        status = f.get("status", "")
        counts[status] = counts.get(status, 0) + 1
    return counts
