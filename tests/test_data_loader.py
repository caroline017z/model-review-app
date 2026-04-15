"""Unit tests for the label-based row resolver."""
from data_loader import _labels_match, _normalize_label


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
