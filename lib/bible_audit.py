"""38DN Pricing Model Review — Bible Audit (public API).

This module is the stable public entry point for auditing a project
against the Q1 '26 Pricing Bible. The actual rule logic lives under
`lib/audit/` as named rule classes — see `lib.audit.__init__` for the
module map.

Why the split
-------------
Phase 3 of the upgrade plan replaced a 285-line inline if-chain
(`audit_project`) with an explicit `AuditEngine` + 5 named rules. The
public API (function names, return shape, status semantics) is
preserved. Golden snapshots gate the equivalence.

What stays here
---------------
- `audit_project(proj_data)` — single-project audit (delegates to engine)
- `audit_projects(projects)` — fan-out across a projects dict
- `verdict_from_summary(summary)` — CLEAN / REVIEW / REWORK classifier
- `status_class(audit_result, row)` — CSS class lookup helper
- `status_tooltip(audit_result, row)` — tooltip-string helper
- `STATUS_CSS` — status → CSS class mapping

Per-rule logic lives in `lib/audit/rules/*.py` and is documented there.
"""

from __future__ import annotations

from typing import Any

from lib.audit import AuditEngine, default_rules
from lib.audit.checks import exact_check as _exact_check  # noqa: F401 — kept for tests/back-compat
from lib.audit.checks import range_check as _range_check  # noqa: F401 — kept for tests/back-compat

# Default engine reused across audit_project calls. Rules are stateless,
# so a module-level singleton is safe and avoids per-call allocation.
_engine = AuditEngine(default_rules())


def audit_project(proj_data: dict) -> dict[str, Any]:
    """Audit one project against the bible.

    Args
    ----
    proj_data: dict
        `{row_number: cell_value}` — typically `projects[col]["data"]`.
        May include side metadata at string keys (`_units_by_row`,
        `_guidehouse_components`, `_abp_rec_live`, …) as written by
        `lib.data_loader`.

    Returns
    -------
    dict with the legacy shape: `rows`, `state`, `utility`, `program`,
    `program_used`, `abp_rec_live`, `market_matched`, `guidehouse`,
    `wrapped_epc`, `summary`.
    """
    return _engine.run(proj_data)


def audit_projects(projects: dict) -> dict[Any, dict[str, Any]]:
    """Audit a dict of projects. Returns `{col: audit_result}`."""
    results = {}
    for col, proj in projects.items():
        data = proj["data"] if isinstance(proj, dict) and "data" in proj else proj
        results[col] = audit_project(data)
    return results


def verdict_from_summary(summary: dict) -> str:
    """Classify an audit summary as CLEAN / REVIEW / REWORK REQUIRED.

    Rules (match review-panel behavior exactly):
      - 0 failures of any kind         → CLEAN
      - 2+ OFF, or 1+ OFF with 2+ OUT  → REWORK REQUIRED
      - otherwise (some issues)        → REVIEW
    """
    off = summary.get("OFF", 0)
    out = summary.get("OUT", 0)
    missing = summary.get("MISSING", 0)
    if off == 0 and out == 0 and missing == 0:
        return "CLEAN"
    if off >= 2 or (off >= 1 and out >= 2):
        return "REWORK REQUIRED"
    return "REVIEW"


# ---------------------------------------------------------------------------
# Inline-highlight helpers (consumed by app.py / comparison rendering)
# ---------------------------------------------------------------------------

# CSS class per status — applied to comparison-table <td>
STATUS_CSS = {
    "OK": "",
    "OFF": "audit-off",  # red — exact mismatch
    "OUT": "audit-out",  # yellow — out of range
    "MISSING": "audit-missing",  # grey — blank
    "REVIEW": "audit-review",  # blue — manual review (S-SFA / TBD)
}


def status_class(audit_result: dict | None, row: int) -> str:
    """Return the CSS class for a model row's audit status, or '' if no finding."""
    if not audit_result:
        return ""
    f = audit_result.get("rows", {}).get(row)
    if not f:
        return ""
    return STATUS_CSS.get(f["status"], "")


def status_tooltip(audit_result: dict | None, row: int) -> str:
    """Build a hover-tooltip string for a row's audit finding."""
    if not audit_result:
        return ""
    f = audit_result.get("rows", {}).get(row)
    if not f:
        return ""
    parts = [f"Status: {f['status']}"]
    if f.get("expected") is not None:
        parts.append(f"Ref: {f['expected']} {f.get('unit', '')}".strip())
    if f.get("range"):
        lo, hi = f["range"]
        parts.append(f"Range: {lo}–{hi}")
    if f.get("note"):
        parts.append(f["note"])
    if f.get("source"):
        parts.append(f"({f['source']})")
    return " | ".join(parts)
