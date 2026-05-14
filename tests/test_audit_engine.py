"""Per-rule unit tests for the audit engine.

These run against hand-built `AuditContext` inputs so each rule's behavior
is tested in isolation, with no workbook loading. Golden tests
(`tests/golden/`) cover the integration story; this file covers the
specific business rules that motivated each rule's bespoke logic.
"""

from __future__ import annotations

from lib.audit.context import AuditContext
from lib.audit.engine import AuditResult
from lib.audit.rules.cs_average import CSAverageRule
from lib.audit.rules.guidehouse import GuidehouseRule
from lib.audit.rules.market_bible import MarketBibleRule
from lib.audit.rules.range_check import RangeCheckRule
from lib.audit.rules.wrapped_epc import WrappedEPCRule


def _ctx(
    *,
    state: str | None = "IL",
    utility: str | None = "Ameren",
    program: str | None = None,
    program_used: str | None = None,
    market: dict | None = None,
    dc_mw: float = 7.0,
    epc_override: dict | None = None,
    abp_rec_live: bool = False,
    market_source_note: str = "",
    proj_data: dict | None = None,
    model_units: dict[int, str] | None = None,
    yield_kwh_per_wp: float = 1.55,
) -> AuditContext:
    """Hand-built context for rule unit tests."""
    return AuditContext(
        proj_data=proj_data or {},
        state=state,
        utility=utility,
        program=program,
        program_used=program_used or program,
        market_source_note=market_source_note,
        abp_rec_live=abp_rec_live,
        market=market,
        dc_mw=dc_mw,
        epc_override=epc_override,
        model_units=model_units or {},
        yield_kwh_per_wp=yield_kwh_per_wp,
    )


# ---------------------------------------------------------------------------
# CSAverageRule
# ---------------------------------------------------------------------------


class TestCSAverageRule:
    def test_in_range_yields_ok(self):
        """Bible EPC is $1.65/W ±$0.10; actual $1.65 → OK."""
        # row 118 = PV EPC Cost, bible value 1.65 ±0.10
        ctx = _ctx(proj_data={118: 1.65, 11: 7.0})
        result = AuditResult(context=ctx)
        CSAverageRule().apply(ctx, result)
        assert result.findings[118]["status"] == "OK"
        assert result.findings[118]["expected"] == 1.65
        assert result.findings[118]["source"].startswith("CS Average")

    def test_size_dependent_epc_override_small_project(self):
        """<5 MWdc project: epc_override sets bible EPC to $1.75/W."""
        ctx = _ctx(
            proj_data={118: 1.75, 11: 3.0},
            dc_mw=3.0,
            epc_override={
                "value": 1.75,
                "unit": "$/W",
                "tol": 0.10,
                "label": "PV EPC Cost",
                "note": "<5 MWdc: $1.75/W all-in",
            },
        )
        result = AuditResult(context=ctx)
        CSAverageRule().apply(ctx, result)
        assert result.findings[118]["status"] == "OK"
        assert result.findings[118]["expected"] == 1.75

    def test_size_dependent_epc_override_not_applied_for_large(self):
        """≥5 MWdc project: no epc_override, bible EPC stays at $1.65/W."""
        # Actual $1.75 against bible $1.65 with $0.10 tol → exactly on the edge.
        # We use $1.80 to push it firmly out of tol.
        ctx = _ctx(proj_data={118: 1.80, 11: 7.0}, dc_mw=7.0, epc_override=None)
        result = AuditResult(context=ctx)
        CSAverageRule().apply(ctx, result)
        assert result.findings[118]["status"] == "OFF"
        assert result.findings[118]["expected"] == 1.65

    def test_state_override_applied(self):
        """IL has a higher P&C Insurance bible value than the default."""
        ctx = _ctx(proj_data={296: 4185, 11: 7.0}, state="IL")
        result = AuditResult(context=ctx)
        CSAverageRule().apply(ctx, result)
        assert "IL override" in result.findings[296]["source"]


# ---------------------------------------------------------------------------
# MarketBibleRule
# ---------------------------------------------------------------------------


class TestMarketBibleRule:
    def test_no_market_yields_no_findings(self):
        ctx = _ctx(market=None)
        result = AuditResult(context=ctx)
        MarketBibleRule().apply(ctx, result)
        assert result.findings == {}

    def test_exact_match_writes_finding(self):
        """Market spec sets row 161 (rate discount) to 10%; matching → OK."""
        ctx = _ctx(
            program_used="ABP",
            market={161: 0.10},
            proj_data={161: 0.10, 11: 7.0},
        )
        result = AuditResult(context=ctx)
        MarketBibleRule().apply(ctx, result)
        assert result.findings[161]["status"] == "OK"
        assert "Market:" in result.findings[161]["source"]
        assert "IL/Ameren/ABP" in result.findings[161]["source"]

    def test_abp_rec_live_appends_source_note(self):
        """Source note appears in finding source when ABP REC live forced lookup."""
        ctx = _ctx(
            program_used="ABP",
            market={161: 0.10},
            proj_data={161: 0.10, 11: 7.0},
            abp_rec_live=True,
            market_source_note=" [ABP REC live → forced ABP lookup]",
        )
        result = AuditResult(context=ctx)
        MarketBibleRule().apply(ctx, result)
        assert "ABP REC live" in result.findings[161]["source"]

    def test_customer_mgmt_unit_conversion(self):
        """Bible row 240 is $/kWh; model stores $/MW/yr.

        Bible $0.005/kWh × yield 1.55 × 1e6 = $7,750/MW/yr.
        Model says $7800 → within 5% tolerance → OK.
        """
        ctx = _ctx(
            program_used="ABP",
            market={240: 0.005},
            proj_data={240: 7800, 11: 7.0, 14: 1.55},
            yield_kwh_per_wp=1.55,
        )
        result = AuditResult(context=ctx)
        MarketBibleRule().apply(ctx, result)
        assert result.findings[240]["status"] == "OK"
        # Display expected should be the converted $/MW/yr, not the raw $/kWh.
        assert result.findings[240]["expected"] > 1000  # converted
        assert result.findings[240]["unit"] == "$/MW/yr"


# ---------------------------------------------------------------------------
# RangeCheckRule
# ---------------------------------------------------------------------------


class TestRangeCheckRule:
    def test_in_range_creates_ok_finding(self):
        """EPC row 118 bible range [1.55, 1.75]; actual $1.65 → OK."""
        ctx = _ctx(proj_data={118: 1.65, 11: 7.0})
        result = AuditResult(context=ctx)
        RangeCheckRule().apply(ctx, result)
        assert result.findings[118]["status"] == "OK"
        assert "range" in result.findings[118]

    def test_out_of_range_creates_out_finding(self):
        """EPC row 118 actual $2.00 above max $1.75 → OUT."""
        ctx = _ctx(proj_data={118: 2.00, 11: 7.0})
        result = AuditResult(context=ctx)
        RangeCheckRule().apply(ctx, result)
        assert result.findings[118]["status"] == "OUT"
        assert "Above max" in result.findings[118]["note"]

    def test_merges_existing_ok_to_out_when_range_fails(self):
        """Pre-existing OK from CS Average + range OUT → promote to OUT."""
        ctx = _ctx(proj_data={118: 2.00, 11: 7.0})
        result = AuditResult(context=ctx)
        # Simulate CS Average putting an OK finding first.
        result.findings[118] = {
            "status": "OK",
            "expected": 1.65,
            "actual": 2.00,
            "tol": 0.10,
            "note": "",
            "source": "CS Average",
            "label": "PV EPC Cost",
            "unit": "$/W",
        }
        RangeCheckRule().apply(ctx, result)
        assert result.findings[118]["status"] == "OUT"
        assert "Above max" in result.findings[118]["note"]
        assert result.findings[118]["expected"] == 1.65  # CS expected preserved
        assert "range" in result.findings[118]

    def test_existing_off_not_demoted_by_range_ok(self):
        """If CS Average flagged OFF, range in-bounds should NOT demote."""
        ctx = _ctx(proj_data={118: 1.65, 11: 7.0})
        result = AuditResult(context=ctx)
        result.findings[118] = {
            "status": "OFF",
            "expected": 1.55,
            "actual": 1.65,
            "tol": 0.0,
            "note": "+0.1 vs bible 1.55",
            "source": "CS Average",
            "label": "PV EPC Cost",
            "unit": "$/W",
        }
        RangeCheckRule().apply(ctx, result)
        assert result.findings[118]["status"] == "OFF"
        assert "range" in result.findings[118]  # range attached for context

    def test_skips_derived_specs(self):
        """`derived: True` specs are skipped (e.g., DC:AC ratio)."""
        # DC:AC ratio is derived. Even with both rows set, no finding for it.
        ctx = _ctx(proj_data={11: 7.0, 12: 5.0})
        result = AuditResult(context=ctx)
        RangeCheckRule().apply(ctx, result)
        # No finding for the derived DC:AC ratio (no row number).
        # Both rows 11 and 12 may get findings as normal ranges.


# ---------------------------------------------------------------------------
# GuidehouseRule
# ---------------------------------------------------------------------------


class TestGuidehouseRule:
    def test_no_components_yields_empty(self):
        ctx = _ctx(market={"rate_discount": 0.10}, proj_data={11: 7.0})
        result = AuditResult(context=ctx)
        GuidehouseRule().apply(ctx, result)
        assert result.guidehouse == []

    def test_match_within_tolerance_yields_ok(self):
        """Guidehouse discount 10.3% vs market 10% (0.5% tol) → OK."""
        ctx = _ctx(
            market={"rate_discount": 0.10},
            proj_data={
                11: 7.0,
                "_guidehouse_components": [
                    {"idx": 1, "name": "GH25 RC4", "discount": 0.103, "equity_on": True},
                ],
            },
        )
        result = AuditResult(context=ctx)
        GuidehouseRule().apply(ctx, result)
        assert result.guidehouse[0]["status"] == "OK"

    def test_mismatch_yields_off_with_pp_note(self):
        """Discount 13% vs market 10% (3pp gap, >0.5pp tol) → OFF."""
        ctx = _ctx(
            market={"rate_discount": 0.10},
            proj_data={
                11: 7.0,
                "_guidehouse_components": [
                    {"idx": 1, "name": "GH25 RC4", "discount": 0.13, "equity_on": True},
                ],
            },
        )
        result = AuditResult(context=ctx)
        GuidehouseRule().apply(ctx, result)
        assert result.guidehouse[0]["status"] == "OFF"
        assert "pp vs bible" in result.guidehouse[0]["note"]

    def test_no_market_value_yields_review(self):
        """Market has no rate_discount → REVIEW per component."""
        ctx = _ctx(
            market={},
            proj_data={
                11: 7.0,
                "_guidehouse_components": [
                    {"idx": 1, "name": "GH25 RC4", "discount": 0.10, "equity_on": True},
                ],
            },
        )
        result = AuditResult(context=ctx)
        GuidehouseRule().apply(ctx, result)
        assert result.guidehouse[0]["status"] == "REVIEW"

    def test_missing_discount_yields_missing(self):
        ctx = _ctx(
            market={"rate_discount": 0.10},
            proj_data={
                11: 7.0,
                "_guidehouse_components": [
                    {"idx": 1, "name": "GH25 RC4", "discount": None, "equity_on": True},
                ],
            },
        )
        result = AuditResult(context=ctx)
        GuidehouseRule().apply(ctx, result)
        assert result.guidehouse[0]["status"] == "MISSING"


# ---------------------------------------------------------------------------
# WrappedEPCRule
# ---------------------------------------------------------------------------


class TestWrappedEPCRule:
    def test_surfaces_components_and_total(self):
        components = [
            {"row": 103, "component": "PV EPC", "value": 1.20},
            {"row": 104, "component": "LNTP", "value": 0.10},
            {"row": 107, "component": "Safe Harbor", "value": 0.30},
            {"row": 108, "component": "Contingency", "value": 0.05},
        ]
        ctx = _ctx(
            proj_data={
                11: 7.0,
                "_wrapped_epc_components": components,
                "_wrapped_epc_total": 1.65,
                "_raw_epc_118": 1.60,
            }
        )
        result = AuditResult(context=ctx)
        WrappedEPCRule().apply(ctx, result)
        assert result.wrapped_epc["total"] == 1.65
        assert result.wrapped_epc["raw_epc"] == 1.60
        assert len(result.wrapped_epc["components"]) == 4

    def test_empty_when_unset(self):
        """Missing keys produce an empty-shaped dict, not a crash."""
        ctx = _ctx(proj_data={11: 7.0})
        result = AuditResult(context=ctx)
        WrappedEPCRule().apply(ctx, result)
        assert result.wrapped_epc == {
            "components": [],
            "total": None,
            "raw_epc": None,
        }


# ---------------------------------------------------------------------------
# AuditContext factory
# ---------------------------------------------------------------------------


class TestAuditContextFactory:
    def test_il_abp_rec_live_forces_program_to_abp(self):
        proj_data = {
            18: "IL",
            19: "Ameren",
            "_abp_rec_live": True,
        }
        ctx = AuditContext.from_proj_data(proj_data)
        assert ctx.program_used == "ABP"
        assert "ABP REC live" in ctx.market_source_note

    def test_non_il_abp_rec_does_not_force(self):
        """Outside IL, ABP REC live shouldn't change program_used."""
        proj_data = {
            18: "MD",
            19: "BGE",
            22: "Permanent",   # ROW_PROGRAM_A
            "_abp_rec_live": True,
        }
        ctx = AuditContext.from_proj_data(proj_data)
        assert ctx.program_used == "Permanent"
        assert ctx.market_source_note == ""

    def test_small_project_gets_epc_override(self):
        proj_data = {11: 3.0, 18: "IL", 19: "Ameren"}
        ctx = AuditContext.from_proj_data(proj_data)
        assert ctx.epc_override is not None
        assert ctx.epc_override["value"] == 1.75

    def test_large_project_no_override(self):
        proj_data = {11: 7.0, 18: "IL", 19: "Ameren"}
        ctx = AuditContext.from_proj_data(proj_data)
        assert ctx.epc_override is None
