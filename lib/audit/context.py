"""AuditContext: per-project state derived once, passed to every rule.

Why this exists
---------------
The legacy `audit_project` function inlined four pieces of derived state
(market lookup, ABP REC live override, size-dependent EPC override, unit
fallback map). Pulling them out keeps each rule focused on its own logic
and makes it possible to unit-test rules with a hand-built context.

Phase 4 update: the bible itself is now an injected dependency, not a
module-level import. `AuditContext.from_proj_data(proj_data, bible)`
takes the bible to use for market lookup + state overrides + size
override; rules read fields off `ctx.bible` for everything else.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from lib.audit.bible import Bible, _normalize_state
from lib.config import INPUT_ROW_UNITS
from lib.rows import ROW_PROGRAM_A, ROW_PROGRAM_B, ROW_STATE, ROW_UTILITY
from lib.utils import safe_float


@dataclass
class AuditContext:
    """Everything a rule needs that's NOT the bible source data itself.

    Built once via `AuditContext.from_proj_data(proj_data, bible)`. Rules
    read fields off this object rather than re-deriving them.
    """

    proj_data: dict[Any, Any]
    bible: Bible
    state: str | None
    utility: Any
    program: Any
    program_used: Any
    market_source_note: str
    abp_rec_live: bool
    market: dict | None
    dc_mw: float
    epc_override: dict | None
    model_units: dict[int, str]
    yield_kwh_per_wp: float

    def unit_for(self, row: int, fallback: str = "") -> str:
        """Best available unit string for a canonical row.

        Prefer the model's own unit annotation (if data_loader extracted
        one), fall back to the hardcoded INPUT_ROW_UNITS table.
        """
        return self.model_units.get(row) or INPUT_ROW_UNITS.get(row, fallback)

    def state_override_for(self, row: int) -> dict | None:
        """The (per-state) CS_AVERAGE override entry for a row, if any."""
        return self.bible.state_override_for(self.state, row)

    @classmethod
    def from_proj_data(cls, proj_data: dict, bible: Bible) -> AuditContext:
        """Build an AuditContext from the raw project data dict + a bible.

        Order of derivations matches the legacy `audit_project` body
        exactly so behavior is preserved.
        """
        state = _normalize_state(proj_data.get(ROW_STATE))
        utility = proj_data.get(ROW_UTILITY)
        # Program lives in different rows depending on model — try a couple
        program = proj_data.get(ROW_PROGRAM_A) or proj_data.get(ROW_PROGRAM_B)

        # Size-dependent EPC bible value: >5 MWdc = $1.65/W (default in
        # CS_AVERAGE); <5 MWdc = $1.75/W via this override.
        dc_mw = safe_float(proj_data.get(11)) or 0  # ROW_DC_MW = 11
        epc_override: dict | None = None
        if dc_mw > 0 and dc_mw < 5:
            epc_override = {
                "value": 1.75,
                "unit": "$/W",
                "tol": 0.10,
                "label": "PV EPC Cost",
                "note": "<5 MWdc: $1.75/W all-in",
            }

        # ABP REC LIVE OVERRIDE
        # If an "ABP REC" rate component is toggled on for the equity
        # model, treat the project as ABP regardless of how the program
        # field is labeled. data_loader sets _abp_rec_live by scanning
        # rate-component names for "ABP REC" and checking the equity toggle.
        abp_rec_live = bool(proj_data.get("_abp_rec_live"))
        program_used = program
        market_source_note = ""
        if abp_rec_live and state == "IL":
            program_used = "ABP"
            market_source_note = " [ABP REC live → forced ABP lookup]"

        market = bible.lookup_market(state, utility, program_used)
        if market is None and abp_rec_live:
            # Final fallback: try plain "ABP" string
            market = bible.lookup_market(state, utility, "ABP")
            if market is not None and not market_source_note:
                market_source_note = " [ABP REC live → forced ABP lookup]"

        model_units = proj_data.get("_units_by_row") or {}
        yield_val = safe_float(proj_data.get(14)) or 0

        return cls(
            proj_data=proj_data,
            bible=bible,
            state=state,
            utility=utility,
            program=program,
            program_used=program_used,
            market_source_note=market_source_note,
            abp_rec_live=abp_rec_live,
            market=market,
            dc_mw=dc_mw,
            epc_override=epc_override,
            model_units=model_units,
            yield_kwh_per_wp=yield_val,
        )
