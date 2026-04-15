"""Unit tests for the fuzzy market lookup."""
from bible_reference import lookup_market, MARKET_BIBLE


class TestLookupMarket:
    def test_exact_key_hit(self):
        result = lookup_market("NY", "National Grid", "VDER (CS)")
        assert result is not None
        assert "rec_rate" in result

    def test_md_de_normalization(self):
        # MD and DE both resolve to the MD/DE key used in MARKET_BIBLE
        md = lookup_market("MD", "BGE", "MD PILOT")
        de = lookup_market("DE", "Delmarva", "MD PILOT")
        assert md is not None
        assert de is not None

    def test_case_insensitive_state(self):
        assert lookup_market("ny", "National Grid", "VDER (CS)") is not None

    def test_no_match_returns_none(self):
        # State that doesn't appear in MARKET_BIBLE
        result = lookup_market("WA", "Some Util", "Some Prog")
        assert result is None

    def test_empty_state_returns_none(self):
        assert lookup_market("", "x", "y") is None

    def test_utility_containment_match(self):
        # Fuzzy utility match: "Ameren Illinois" should still hit "Ameren"
        keys = [k for k in MARKET_BIBLE if k[0] == "IL"]
        if keys:
            _, util, prog = keys[0]
            result = lookup_market("IL", f"{util} Illinois", prog)
            # Fuzzy matcher permits containment either way
            assert result is not None
