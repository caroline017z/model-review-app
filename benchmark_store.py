"""
Persistent benchmark override storage.
Reads/writes user-adjusted benchmark ranges to a JSON sidecar file
so they survive across Streamlit reruns and sessions.
"""

import json
from pathlib import Path
from datetime import datetime, timezone

_OVERRIDES_PATH = Path(__file__).parent / "benchmark_overrides.json"
_OVERRIDES_AUDIT_PATH = Path(__file__).parent / "benchmark_overrides_audit.jsonl"


def load_overrides() -> dict:
    """Read overrides from the JSON file. Returns {} if file missing or invalid."""
    if _OVERRIDES_PATH.exists():
        try:
            with open(_OVERRIDES_PATH, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def save_overrides(overrides: dict, note: str = "", actor: str = "streamlit-user") -> None:
    """Write overrides dict to the JSON file and append an audit record."""
    with open(_OVERRIDES_PATH, "w") as f:
        json.dump(overrides, f, indent=2)
    record = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "actor": actor,
        "note": (note or "").strip(),
        "override_count": len(overrides),
    }
    with open(_OVERRIDES_AUDIT_PATH, "a") as f:
        f.write(json.dumps(record) + "\n")


def delete_overrides() -> None:
    """Remove the overrides file (reset to defaults)."""
    if _OVERRIDES_PATH.exists():
        _OVERRIDES_PATH.unlink()
    record = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "actor": "streamlit-user",
        "note": "Reset to default benchmarks",
        "override_count": 0,
    }
    with open(_OVERRIDES_AUDIT_PATH, "a") as f:
        f.write(json.dumps(record) + "\n")


def apply_overrides(benchmarks: dict, overrides: dict) -> None:
    """Merge user overrides into the benchmarks dict in-place.

    overrides keys are "Category|Label", values are {"min": ..., "max": ...}.
    """
    for key, vals in overrides.items():
        if "|" not in key:
            continue
        cat, label = key.split("|", 1)
        if cat in benchmarks and label in benchmarks[cat]:
            if "min" in vals:
                benchmarks[cat][label]["min"] = vals["min"]
            if "max" in vals:
                benchmarks[cat][label]["max"] = vals["max"]
