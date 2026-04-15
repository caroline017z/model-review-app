"""Unit tests for the Python→HTML translation layer."""
import json
import pytest
from mockup_view import (
    _as_fraction, _compute_impact, _roll_up, _safe_json,
    render_html, build_payload,
    BIBLE_EPC_PER_W, BIBLE_ELIG_FRAC,
)


class TestSafeJson:
    def test_closes_script_breakout(self):
        s = _safe_json({"x": "</script><img src=x>"})
        assert "</script>" not in s
        assert "<\\/script>" in s

    def test_escapes_html_comment_opener(self):
        s = _safe_json({"x": "<!-- evil"})
        assert "<!--" not in s

    def test_escapes_u2028_u2029(self):
        s = _safe_json({"x": "a\u2028b\u2029c"})
        assert "\u2028" not in s
        assert "\u2029" not in s
        assert "\\u2028" in s
        assert "\\u2029" in s

    def test_still_valid_json(self):
        s = _safe_json({"name": "Joel", "dc": 4.85})
        # After replacement, the string is still valid JSON
        assert json.loads(s) == {"name": "Joel", "dc": 4.85}


class TestAsFraction:
    def test_decimal_passthrough(self):
        assert _as_fraction(0.40) == 0.40

    def test_whole_percent_converted(self):
        assert _as_fraction(40) == 0.40

    def test_none_returns_none(self):
        assert _as_fraction(None) is None

    def test_threshold_boundary_stays_fraction(self):
        assert _as_fraction(1.0) == 1.0  # 100% still fractional


class TestComputeImpact:
    # 5 MW default project with bible-matching EPC / ITC / Eligible.
    _BASE = {11: 5.0, 118: 1.65, 597: 0.40, 602: 0.97}

    def _data(self, **overrides):
        d = dict(self._BASE)
        # Numeric row overrides — e.g. epc=1.22 → d[118] = 1.22
        aliases = {"epc": 118, "itc": 597, "elig": 602, "dc": 11}
        for k, v in overrides.items():
            if k in aliases:
                d[aliases[k]] = v
            else:
                d[k] = v
        return d

    def test_epc_dollar_per_w_delta(self):
        # $/W unit: higher EPC = negative impact on sponsor.
        info = {"unit": "$/W", "label": "PV EPC Cost",
                "expected": 1.65, "actual": 1.80}
        impact = _compute_impact(info, self._data())
        # delta = +0.15, impact = -0.15 × dc_w = -$750k
        assert impact == pytest.approx(-750_000)

    def test_upfront_incentive_positive(self):
        # Higher upfront = upside (flip sign).
        info = {"unit": "$/W", "label": "Upfront Incentive",
                "expected": 0.80, "actual": 1.00}
        impact = _compute_impact(info, self._data())
        # delta = +0.20, revenue impact = +0.20 × dc_w = +$1M
        assert impact == pytest.approx(1_000_000)

    def test_itc_impact_anchored_to_bible_epc(self):
        # ITC 0% vs 40% — should use BIBLE_EPC_PER_W, not the model's EPC.
        info = {"unit": "%", "label": "ITC Rate",
                "expected": 0.40, "actual": 0.0}
        impact = _compute_impact(info, self._data(epc=1.22))
        expected = (0.0 - 0.40) * BIBLE_ELIG_FRAC * BIBLE_EPC_PER_W * 5_000_000
        assert impact == pytest.approx(expected, rel=1e-6)

    def test_eligible_costs_impact_anchored_to_bible_epc(self):
        info = {"unit": "%", "label": "Eligible Costs %",
                "expected": 0.97, "actual": 0.90}
        impact = _compute_impact(info, self._data(epc=1.22, itc=0.40))
        expected = (0.90 - 0.97) * 0.40 * BIBLE_EPC_PER_W * 5_000_000
        assert impact == pytest.approx(expected, rel=1e-6)

    def test_missing_dc_returns_none(self):
        info = {"unit": "$/W", "label": "X", "expected": 1.65, "actual": 1.80}
        assert _compute_impact(info, {11: 0}) is None


class TestRollUp:
    def test_leverage_scale_clamped(self):
        rolled = _roll_up([{"impact": -100_000}], dc_mw=5.0, sponsor_fraction=0.10)
        # Very thin equity clamps to 2.0
        assert rolled["leverageScale"] == 2.0

    def test_calibration_point_scale_one(self):
        rolled = _roll_up([{"impact": -100_000}], dc_mw=5.0, sponsor_fraction=0.45)
        assert rolled["leverageScale"] == 1.0

    def test_no_findings_zero(self):
        rolled = _roll_up([], dc_mw=5.0)
        assert rolled["equityK"] == 0
        assert rolled["nppPerW"] == 0


class TestRenderHtml:
    def test_inject_marker_round_trip(self):
        fake = {
            1: {"name": "Joel", "toggle": True,
                "data": {11: 4.85, 118: 1.22, 18: "IL", 19: "Ameren"}},
        }
        html = render_html(fake, model_label="Test")
        # Marker replaced; payload landed
        assert "/* __INJECT_DATA_START__" in html
        assert "__INJECT_DATA_END__" in html
        assert '"Joel"' in html
        assert "PORTFOLIO" in html
        assert "PROJECTS" in html

    def test_empty_input_renders_gracefully(self):
        html = render_html({}, model_label="Empty")
        assert "let PROJECTS = []" in html
        assert "No projects loaded" in html  # template default
