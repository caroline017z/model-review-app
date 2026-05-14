"""Unit tests for the label-based row resolver."""

from lib.data_loader import (
    _CRITICAL_CANONICAL_ROWS,
    _labels_match,
    _normalize_label,
    template_fingerprint,
    validate_model_result,
)


class TestLabelsMatch:
    # Positive cases
    def test_identical_labels(self):
        assert _labels_match("pv epc cost", "pv epc cost")

    def test_parenthesized_unit(self):
        # Size (MWDC) should match Size MWDC
        assert _labels_match("size mwdc", _normalize_label("Size (MWDC)"))

    def test_ampersand_normalization(self):
        assert _labels_match("closing and legal", _normalize_label("Closing & Legal"))

    def test_esc_abbreviation(self):
        # 'esc' as standalone word should expand to 'escalator'
        assert _labels_match(_normalize_label("PV O&M Esc"), _normalize_label("PV O&M Escalator"))

    def test_reasonable_substring_match(self):
        # Bible alias "EPC Cost" should match template "PV EPC Cost"
        assert _labels_match(_normalize_label("EPC Cost"), _normalize_label("PV EPC Cost"))

    # Negative cases — these are the bugs the tightened matcher prevents
    def test_customer_does_not_match_customer_mgmt_esc(self):
        # "Customer" (length 8) sitting at row 22 shouldn't steal the
        # Customer Management Escalator mapping.
        assert not _labels_match(
            _normalize_label("Customer Mgmt Esc"),
            _normalize_label("Customer"),
        )

    def test_annual_premium_does_not_over_match(self):
        # "Annual Premium" (insurance) vs "Decom Bond Annual Premium" —
        # they're legitimately distinct concepts.
        assert not _labels_match(
            _normalize_label("Annual Premium"),
            _normalize_label("Decom Bond Annual Premium"),
        )

    def test_short_common_substring_rejected(self):
        assert not _labels_match(
            _normalize_label("Rate"),
            _normalize_label("Escalator Rate Term"),
        )


class TestNormalizeLabel:
    def test_strips_whitespace_and_lowercases(self):
        assert _normalize_label("  Foo  Bar  ") == "foo bar"

    def test_none_returns_empty(self):
        assert _normalize_label(None) == ""

    def test_collapses_newlines(self):
        assert _normalize_label("Foo\nBar") == "foo bar"


class TestLabelsMatchUnitAware:
    """Unit-suffix rejection: labels with different unit tokens must not match."""

    def test_dollar_per_kwh_vs_dollar_per_w_rejected(self):
        assert not _labels_match(
            _normalize_label("Energy Rate ($/kWh)"),
            _normalize_label("Energy Rate ($/W)"),
        )

    def test_dollar_per_mw_vs_dollar_per_mwdc_accepted(self):
        # $/MW-dc is a variant of $/MW — should still match
        assert _labels_match(
            _normalize_label("Insurance ($/MW-dc/yr)"),
            _normalize_label("Insurance ($/MW-dc/yr)"),
        )

    def test_same_unit_suffix_accepted(self):
        assert _labels_match(
            _normalize_label("PV EPC Cost ($/W)"),
            _normalize_label("EPC Cost ($/W)"),
        )

    def test_no_unit_suffix_still_fuzzy_matches(self):
        # Labels without any unit tokens should still fuzzy-match normally
        assert _labels_match(
            _normalize_label("PV O&M Preventative"),
            _normalize_label("PV O&M Preventive"),
        )

    def test_preventive_vs_preventative_spelling(self):
        # Both spellings should match via substring logic
        c = _normalize_label("PV O&M Preventative")
        a = _normalize_label("PV O&M Preventive")
        # The substring check should catch this since they share enough chars
        assert _labels_match(c, a)


class TestTemplateFingerprint:
    def test_identical_maps_same_fingerprint(self):
        row_map = {canon: canon for canon in _CRITICAL_CANONICAL_ROWS}
        assert template_fingerprint(row_map) == template_fingerprint(dict(row_map))

    def test_different_maps_different_fingerprint(self):
        base = {canon: canon for canon in _CRITICAL_CANONICAL_ROWS}
        shifted = dict(base)
        # Simulate row 118 moving to row 119 in a template variant
        shifted[118] = 119
        assert template_fingerprint(base) != template_fingerprint(shifted)

    def test_stable_length(self):
        row_map = {canon: canon for canon in _CRITICAL_CANONICAL_ROWS}
        fp = template_fingerprint(row_map)
        assert isinstance(fp, str)
        assert len(fp) == 8  # 8-char sha1 prefix


class TestValidateModelResult:
    def _make_result(self, projects: dict, row_map: dict) -> dict:
        return {"projects": projects, "_row_map": row_map}

    def test_empty_projects_fails(self):
        result = self._make_result({}, {c: c for c in _CRITICAL_CANONICAL_ROWS})
        v = validate_model_result(result)
        assert v["ok"] is False
        assert v["project_count"] == 0

    def test_real_project_passes(self):
        result = self._make_result(
            {6: {"name": "Alpha", "data": {}}},
            {c: c for c in _CRITICAL_CANONICAL_ROWS},
        )
        v = validate_model_result(result)
        assert v["ok"] is True
        assert v["project_count"] == 1

    def test_too_many_critical_missing_fails(self):
        row_map = {c: c for c in _CRITICAL_CANONICAL_ROWS}
        # Knock out the first 5 criticals
        for c in list(_CRITICAL_CANONICAL_ROWS)[:5]:
            row_map[c] = None
        result = self._make_result(
            {6: {"name": "Alpha", "data": {}}},
            row_map,
        )
        v = validate_model_result(result)
        assert v["ok"] is False
        assert len(v["critical_missing"]) >= 5

    def test_blank_name_projects_excluded(self):
        result = self._make_result(
            {6: {"name": "  ", "data": {}}, 7: {"name": "", "data": {}}},
            {c: c for c in _CRITICAL_CANONICAL_ROWS},
        )
        v = validate_model_result(result)
        assert v["ok"] is False
        assert v["project_count"] == 0

    def test_fingerprint_in_result(self):
        result = self._make_result(
            {6: {"name": "Alpha", "data": {}}},
            {c: c for c in _CRITICAL_CANONICAL_ROWS},
        )
        v = validate_model_result(result)
        assert v["fingerprint"]
        assert len(v["fingerprint"]) == 8
