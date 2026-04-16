"""Tests for benchmark_store.py — override persistence and application."""
import json
import copy
import pytest
from benchmark_store import load_overrides, save_overrides, delete_overrides, apply_overrides
from config import BIBLE_BENCHMARKS


class TestApplyOverrides:
    def test_valid_override_modifies_min_max(self):
        benchmarks = copy.deepcopy(BIBLE_BENCHMARKS)
        overrides = {"CapEx|EPC Cost ($/W)": {"min": 1.40, "max": 1.90}}
        apply_overrides(benchmarks, overrides)
        assert benchmarks["CapEx"]["EPC Cost ($/W)"]["min"] == 1.40
        assert benchmarks["CapEx"]["EPC Cost ($/W)"]["max"] == 1.90

    def test_malformed_key_skipped(self):
        benchmarks = copy.deepcopy(BIBLE_BENCHMARKS)
        original = copy.deepcopy(benchmarks)
        overrides = {"bad_key_no_pipe": {"min": 0, "max": 99}}
        apply_overrides(benchmarks, overrides)
        assert benchmarks == original

    def test_unknown_category_skipped(self):
        benchmarks = copy.deepcopy(BIBLE_BENCHMARKS)
        original = copy.deepcopy(benchmarks)
        overrides = {"FakeCategory|FakeLabel": {"min": 0, "max": 99}}
        apply_overrides(benchmarks, overrides)
        assert benchmarks == original

    def test_partial_override_only_min(self):
        benchmarks = copy.deepcopy(BIBLE_BENCHMARKS)
        old_max = benchmarks["CapEx"]["EPC Cost ($/W)"]["max"]
        overrides = {"CapEx|EPC Cost ($/W)": {"min": 1.30}}
        apply_overrides(benchmarks, overrides)
        assert benchmarks["CapEx"]["EPC Cost ($/W)"]["min"] == 1.30
        assert benchmarks["CapEx"]["EPC Cost ($/W)"]["max"] == old_max

    def test_empty_overrides_no_change(self):
        benchmarks = copy.deepcopy(BIBLE_BENCHMARKS)
        original = copy.deepcopy(benchmarks)
        apply_overrides(benchmarks, {})
        assert benchmarks == original


class TestLoadOverrides:
    def test_returns_empty_when_no_file(self, tmp_path, monkeypatch):
        monkeypatch.setattr("benchmark_store._OVERRIDES_PATH", tmp_path / "nonexistent.json")
        assert load_overrides() == {}

    def test_returns_empty_on_invalid_json(self, tmp_path, monkeypatch):
        bad_file = tmp_path / "bad.json"
        bad_file.write_text("not valid json{{{")
        monkeypatch.setattr("benchmark_store._OVERRIDES_PATH", bad_file)
        assert load_overrides() == {}

    def test_round_trip(self, tmp_path, monkeypatch):
        file = tmp_path / "overrides.json"
        monkeypatch.setattr("benchmark_store._OVERRIDES_PATH", file)
        data = {"CapEx|EPC Cost ($/W)": {"min": 1.40, "max": 1.90}}
        save_overrides(data)
        assert load_overrides() == data

    def test_delete_removes_file(self, tmp_path, monkeypatch):
        file = tmp_path / "overrides.json"
        file.write_text("{}")
        monkeypatch.setattr("benchmark_store._OVERRIDES_PATH", file)
        delete_overrides()
        assert not file.exists()
