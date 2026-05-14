"""Benchmark override CRUD endpoints."""

from __future__ import annotations

import copy

from fastapi import APIRouter
from pydantic import BaseModel

from lib.benchmark_store import apply_overrides, delete_overrides, load_overrides, save_overrides
from lib.config import BIBLE_BENCHMARKS

router = APIRouter()


class BenchmarkOverride(BaseModel):
    key: str  # "Category|Label"
    min_val: float | None = None
    max_val: float | None = None


@router.get("")
def get_benchmarks():
    """Return current benchmarks with user overrides applied."""
    benchmarks = copy.deepcopy(BIBLE_BENCHMARKS)
    overrides = load_overrides()
    apply_overrides(benchmarks, overrides)
    return {
        "benchmarks": benchmarks,
        "overrides": overrides,
    }


@router.put("")
def set_benchmarks(overrides: list[BenchmarkOverride]):
    """Save benchmark overrides."""
    data = {}
    for o in overrides:
        entry = {}
        if o.min_val is not None:
            entry["min"] = o.min_val
        if o.max_val is not None:
            entry["max"] = o.max_val
        if entry:
            data[o.key] = entry
    save_overrides(data)
    return {"saved": len(data)}


@router.delete("")
def reset_benchmarks():
    """Reset all benchmark overrides to defaults."""
    delete_overrides()
    return {"reset": True}
