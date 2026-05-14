"""RangeCheckRule: BIBLE_BENCHMARKS [min, max] checks with merge semantics.

Ports the legacy `audit_project` block at lines 213-236.

Must run AFTER CSAverageRule and MarketBibleRule because it MERGES with
findings those rules wrote. Merge precedence:

- existing OK + range OUT  → promote to OUT (keep CS/Market `expected`,
                              append range note, attach `range` field)
- existing MISSING/REVIEW + range != OK → promote to range status
- otherwise                → keep existing status, only attach `range`

If no exact-match finding exists at the row, a fresh range-only finding
is written.

Derived ("derived: True") benchmarks are skipped — they're handled by
downstream code outside the audit engine (currently `mockup_view`).
"""

from __future__ import annotations

from lib.audit.checks import range_check
from lib.audit.context import AuditContext
from lib.audit.engine import AuditResult, AuditRule


class RangeCheckRule(AuditRule):
    name = "range-check"

    def apply(self, ctx: AuditContext, result: AuditResult) -> None:
        for category, checks in ctx.bible.bible_benchmarks.items():
            for label, spec in checks.items():
                if spec.get("derived"):
                    continue  # derived checks handled separately if needed
                row_val = spec["row"]
                assert isinstance(row_val, int)
                row = row_val
                status, note = range_check(ctx.proj_data.get(row), spec)
                existing = result.findings.get(row)
                if existing:
                    # Merge: prefer OFF over OUT; promote MISSING to OUT if
                    # range fails.
                    if existing["status"] == "OK" and status == "OUT":
                        existing["status"] = "OUT"
                        prev_note = existing.get("note") or ""
                        existing["note"] = (prev_note + "; " if prev_note else "") + note
                        existing["range"] = (spec["min"], spec["max"])
                    elif existing["status"] in ("MISSING", "REVIEW") and status != "OK":
                        existing["status"] = status
                        existing["note"] = note
                        existing["range"] = (spec["min"], spec["max"])
                    else:
                        existing["range"] = (spec["min"], spec["max"])
                else:
                    result.findings[row] = {
                        "status": status,
                        "expected": None,
                        "actual": ctx.proj_data.get(row),
                        "tol": None,
                        "note": note,
                        "source": f"Range: {category}",
                        "label": label,
                        "unit": spec.get("unit") or ctx.unit_for(row),
                        "range": (spec["min"], spec["max"]),
                    }
