"""38DN Pricing Model — Bible Audit Engine.

Public surface:

    from lib.audit import AuditEngine, AuditContext, default_rules
    result = AuditEngine(default_rules()).run(proj_data)

The legacy `lib.bible_audit.audit_project(proj_data) -> dict` entry point
continues to work and now wraps this engine — same JSON shape, same
business rules. See engine.py for the result-dict adapter.

Module map
- context.py        — AuditContext factory (derived per-project state)
- engine.py         — AuditRule ABC + AuditEngine + AuditResult
- rules/            — five canonical rules (one per file for testability)
    cs_average      — CS_AVERAGE exact-match + size-dependent EPC override
    market_bible    — MARKET_BIBLE exact-match + ABP REC live override
                      + customer-mgmt $/kWh ↔ $/MW/yr conversion
    range_check     — BIBLE_BENCHMARKS range check + OFF/OUT merge promotion
    guidehouse      — Guidehouse rate-component audit (side output)
    wrapped_epc     — Wrapped EPC surfacing (side output)
"""

from lib.audit.context import AuditContext
from lib.audit.engine import AuditEngine, AuditResult, AuditRule
from lib.audit.rules import default_rules

__all__ = [
    "AuditContext",
    "AuditEngine",
    "AuditResult",
    "AuditRule",
    "default_rules",
]
