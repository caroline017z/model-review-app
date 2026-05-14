"""Tests for rows.py — row constant integrity."""

import lib.rows as rows
from lib.config import INPUT_ROW_LABELS, OUTPUT_ROWS


class TestRowConstantsNoDuplicates:
    # Known intentional aliases (same row, different semantic name)
    _KNOWN_ALIASES = {
        31: {"ROW_APPRAISAL_IRR", "ROW_FMV_IRR"},  # FMV_IRR kept for backward compat
    }

    def test_no_duplicate_values(self):
        """No two ROW_* constants should share the same integer (except known aliases)."""
        seen = {}
        for name in dir(rows):
            if not name.startswith("ROW_"):
                continue
            val = getattr(rows, name)
            if not isinstance(val, int):
                continue
            if val in seen:
                # Check if this is a known alias pair
                alias_set = self._KNOWN_ALIASES.get(val, set())
                assert name in alias_set and seen[val] in alias_set, (
                    f"Duplicate row value {val}: {name} collides with {seen[val]}"
                )
            else:
                seen[val] = name


class TestRowConstantsInConfig:
    def test_row_constants_registered(self):
        """Every ROW_* constant should appear in INPUT_ROW_LABELS or OUTPUT_ROWS."""
        all_known = set(INPUT_ROW_LABELS.keys()) | set(OUTPUT_ROWS.keys())
        for name in dir(rows):
            if not name.startswith("ROW_"):
                continue
            val = getattr(rows, name)
            if not isinstance(val, int):
                continue
            assert val in all_known, (
                f"rows.{name} = {val} not found in INPUT_ROW_LABELS or OUTPUT_ROWS"
            )
