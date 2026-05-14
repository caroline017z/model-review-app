"""Canonical rule set for the bible audit.

`default_rules()` returns the rules in the exact order the legacy
`audit_project` function ran them. Changing the order is a behavior
change — golden tests will catch it.
"""

from lib.audit.engine import AuditRule
from lib.audit.rules.cs_average import CSAverageRule
from lib.audit.rules.guidehouse import GuidehouseRule
from lib.audit.rules.market_bible import MarketBibleRule
from lib.audit.rules.range_check import RangeCheckRule
from lib.audit.rules.wrapped_epc import WrappedEPCRule


def default_rules() -> list[AuditRule]:
    """The canonical 5-rule pipeline.

    Order matters
    -------------
    1. CSAverageRule    — populates `findings` with cross-market exact matches
    2. MarketBibleRule  — populates per-market exact matches (may clobber CS)
    3. RangeCheckRule   — MERGES with existing CS/Market findings
    4. GuidehouseRule   — writes `result.guidehouse` (side output)
    5. WrappedEPCRule   — writes `result.wrapped_epc` (side output)
    """
    return [
        CSAverageRule(),
        MarketBibleRule(),
        RangeCheckRule(),
        GuidehouseRule(),
        WrappedEPCRule(),
    ]


__all__ = [
    "CSAverageRule",
    "GuidehouseRule",
    "MarketBibleRule",
    "RangeCheckRule",
    "WrappedEPCRule",
    "default_rules",
]
