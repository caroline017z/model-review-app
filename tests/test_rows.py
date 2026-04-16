"""Tests for rows.py — row constant integrity."""
import rows
from config import INPUT_ROW_LABELS, OUTPUT_ROWS


class TestRowConstantsNoDuplicates:
    def test_no_duplicate_values(self):
        """No two ROW_* constants in rows.py should share the same integer."""
        seen = {}
        for name in dir(rows):
            if not name.startswith("ROW_"):
                continue
            val = getattr(rows, name)
            if not isinstance(val, int):
                continue
            assert val not in seen, (
                f"Duplicate row value {val}: {name} collides with {seen[val]}"
            )
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
