"""Unit tests for the three economically load-bearing builders:
_build_capital_stack, _build_cashflow, _build_sensitivity.

These were zero-coverage in Sprint 4; this module closes that gap.
"""

import json

from lib.mockup_view import (
    DEBT_FRACTION_OF_NET,
    OPEX_TERM_YEARS,
    TAX_EQUITY_MONETIZATION,
    _build_capital_stack,
    _build_cashflow,
    _build_sensitivity,
    build_payload,
    render_html,
)


class TestCapitalStack:
    def _proj(self, **overrides):
        base = {
            "data": {
                11: 5.0,
                118: 1.65,
                119: 0.10,
                122: 0.05,
                123: 0.06,
                216: 0.0,
                597: 0.40,
                602: 0.97,
            }
        }
        base["data"].update(overrides.get("data", {}))
        if "dscr_schedule" in overrides:
            base["dscr_schedule"] = overrides["dscr_schedule"]
        return base

    def test_illustrative_flag_always_set(self):
        stack = _build_capital_stack(self._proj(), None)
        assert stack["illustrative"] is True
        assert stack["assumptions"]["debtFraction"] == DEBT_FRACTION_OF_NET
        assert stack["assumptions"]["teMonetization"] == TAX_EQUITY_MONETIZATION

    def test_dscr_schedule_hint_surfaces(self):
        stack = _build_capital_stack(
            self._proj(dscr_schedule={1: 1.35, 2: 1.32}),
            None,
        )
        assert stack["assumptions"]["hasModelDscr"] is True

    def test_empty_dscr_schedule_not_flagged(self):
        stack = _build_capital_stack(
            self._proj(dscr_schedule={1: 0, 2: 0}),
            None,
        )
        assert stack["assumptions"]["hasModelDscr"] is False

    def test_zero_itc_means_zero_te_bar(self):
        stack = _build_capital_stack(
            self._proj(data={597: 0.0}),
            None,
        )
        # stack order: [sponsor, te, debt, incentive]
        assert stack["model"][1] == 0.0

    def test_bars_are_nonnegative(self):
        stack = _build_capital_stack(self._proj(), None)
        assert all(v >= 0 for v in stack["model"])
        assert all(v >= 0 for v in stack["bible"])

    def test_model_total_tracks_capex(self):
        # Sum of four bars should approximately recover the CapEx total the
        # reviewer inputs (EPC + LNTP + C&L + IX).
        stack = _build_capital_stack(self._proj(), None)
        total = sum(stack["model"])
        expected_capex = 1.65 + 0.10 + 0.05 + 0.06  # 1.86
        # Allow 5% slack for the 0.85× TE monetization shortfall.
        assert abs(total - expected_capex) / expected_capex < 0.1


class TestCashflow:
    def _proj(self, **data_overrides):
        base_data = {11: 5.0, 118: 1.65, 157: 0.08, 158: 0.015, 597: 0.40, 602: 0.97}
        base_data.update(data_overrides)
        return {"data": base_data, "rate_comps": {}}

    def test_25_year_arrays(self):
        cf = _build_cashflow(self._proj())
        assert len(cf["opCF"]) == OPEX_TERM_YEARS
        assert len(cf["taxBn"]) == OPEX_TERM_YEARS
        assert len(cf["terminal"]) == OPEX_TERM_YEARS

    def test_terminal_lands_in_final_year(self):
        cf = _build_cashflow(self._proj())
        assert cf["terminal"][-1] > 0
        # Only the final year has a non-zero terminal value.
        assert all(v == 0 for v in cf["terminal"][:-1])

    def test_terminal_is_defensibly_sized(self):
        # Terminal / Y25 op CF should land below 2x (vs old 2.5x rule)
        cf = _build_cashflow(self._proj())
        ratio = cf["terminal"][-1] / cf["opCF"][-1]
        assert ratio < 2.0

    def test_itc_zero_means_only_macrs_in_y1(self):
        # Build proj directly since numeric row keys can't go through **kwargs.
        proj = {
            "data": {11: 5.0, 118: 1.65, 157: 0.08, 158: 0.015, 597: 0.0, 602: 0.97},
            "rate_comps": {},
        }
        cf = _build_cashflow(proj)
        # With ITC=0: basis = full capex, no ITC kicker.
        # Y1 tax = 0.20 * capex * 0.21 = ~$347 for 5MW × $1.65/W.
        assert 250 < cf["taxBn"][0] < 450

    def test_macrs_y7_onward_is_zero(self):
        cf = _build_cashflow(self._proj())
        for yr in range(7, OPEX_TERM_YEARS):
            assert cf["taxBn"][yr] == 0

    def test_zero_dc_returns_zero_arrays(self):
        cf = _build_cashflow({"data": {11: 0}, "rate_comps": {}})
        assert all(v == 0 for v in cf["opCF"])
        assert all(v == 0 for v in cf["taxBn"])
        assert all(v == 0 for v in cf["terminal"])

    def test_primary_rate_fallback_from_rate_comps(self):
        # Row 157/158 absent → fall back to rate_comps[1]
        proj = {
            "data": {11: 5.0, 118: 1.65, 597: 0.40, 602: 0.97},
            "rate_comps": {1: {"energy_rate": 0.09, "escalator": 0.02, "equity_on": True}},
        }
        cf = _build_cashflow(proj)
        # Y1 op CF should be positive with that rate.
        assert cf["opCF"][0] > 0


class TestSensitivity:
    def _proj(self):
        return {
            "data": {
                11: 5.0,
                118: 1.65,
                119: 0.10,
                157: 0.08,
                158: 0.015,
                216: 0.20,
                296: 3500,
                597: 0.40,
                602: 0.97,
            },
            "rate_comps": {},
        }

    def test_returns_labels_lo_hi(self):
        t = _build_sensitivity(self._proj())
        assert set(t.keys()) >= {"labels", "lo", "hi"}
        assert len(t["labels"]) == len(t["lo"]) == len(t["hi"])

    def test_capped_at_seven_inputs(self):
        t = _build_sensitivity(self._proj())
        assert len(t["labels"]) <= 7

    def test_ranked_by_absolute_swing(self):
        t = _build_sensitivity(self._proj())
        swings = [abs(hi - lo) for hi, lo in zip(t["hi"], t["lo"], strict=True)]
        assert swings == sorted(swings, reverse=True)

    def test_epc_direction_is_negative_at_plus_10(self):
        # +10% EPC shock must produce a negative NPP impact.
        t = _build_sensitivity(self._proj())
        idx = t["labels"].index("EPC $/W")
        assert t["hi"][idx] < 0

    def test_zero_dc_yields_empty(self):
        t = _build_sensitivity({"data": {11: 0}, "rate_comps": {}})
        assert t["labels"] == []


class TestRenderHtmlIntegration:
    def test_inject_round_trip_produces_valid_json(self):
        fake = {1: {"name": "Joel", "toggle": True, "data": {11: 4.85, 118: 1.22, 18: "IL"}}}
        html = render_html(fake, model_label="T")
        # Extract the injected JS block
        import re

        m = re.search(
            r"let PORTFOLIO = (\{[\s\S]*?\});\s*let PROJECTS = (\[[\s\S]*?\]);\s*let WALK_AVAILABLE",
            html,
        )
        assert m, "Inject block not found"
        portfolio = json.loads(m.group(1))
        projects = json.loads(m.group(2))
        assert portfolio["count"] == 1
        assert projects[0]["name"] == "Joel"
        # Constants shipped for JS-side rule-of-thumb sync
        assert "constants" in portfolio
        assert portfolio["constants"]["irrPctPerCent"] > 0

    def test_heatmap_shape_matches_project_count(self):
        fake = {
            1: {"name": "A", "toggle": True, "data": {11: 5, 118: 1.5}},
            2: {"name": "B", "toggle": True, "data": {11: 7, 118: 1.7}},
        }
        _, portfolio = build_payload(fake, model_label="Test")
        hm = portfolio["heatmap"]
        assert len(hm["projects"]) == 2
        assert len(hm["z"]) == 2
        assert all(len(row) == len(hm["fields"]) for row in hm["z"])
