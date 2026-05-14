"""Snapshot generator + diff helper for golden-fixture regression tests.

The premise
-----------
Phase 3 of the upgrade plan refactors `lib/bible_audit.audit_project` from
an inline 5-stage if-chain into a rule-engine pattern. The refactor must
preserve every bespoke business rule (ABP REC live override, size-dependent
EPC, customer-mgmt $/kWh ↔ $/MW/yr conversion, OFF-vs-OUT merge promotion,
Guidehouse audit, Wrapped EPC). Same for Phase 4 (Bible loader) — it
replaces Python literals with a runtime-loaded record, and the resulting
audit output must be identical.

The safety net: lock the CURRENT audit + load + payload output as JSON
snapshots committed to the repo. Any drift in a future refactor fails CI
until explicitly accepted with `--update-snapshots`.

What gets snapshotted per fixture
---------------------------------
1. `load_pricing_model(file) → projects` — the parsed workbook
2. `audit_projects(projects) → {col: finding_dict}` — per-project audit
3. `build_payload(projects, ...) → (projects_list, portfolio)` — full review

All three captured as canonicalized JSON: floats rounded to 6 decimals,
ordered keys, sentinel filtering. See `_canonicalize` below.
"""

from __future__ import annotations

import dataclasses
import datetime as dt
import json
import math
from pathlib import Path
from typing import Any

# Where the fixtures and snapshots live (relative to repo root)
FIXTURE_DIR = Path("tests/golden/fixtures")
SNAPSHOT_DIR = Path("tests/golden/snapshots")

# Float precision for snapshot equality. Six decimals is tight enough to
# catch real changes, loose enough to absorb 64-bit float jitter across
# OS / openpyxl versions.
FLOAT_PRECISION = 6


def _canonicalize(obj: Any) -> Any:
    """Recursively normalize a value tree for stable JSON serialization.

    - Floats rounded to FLOAT_PRECISION; NaN/Inf normalized to None.
    - Datetime objects → ISO strings.
    - Tuples → lists.
    - Sets → sorted lists.
    - Bytes → base64-decoded would lose info; raise instead — no audit
      output should carry raw bytes.
    - Dataclasses → dict via asdict.
    """
    if obj is None:
        return None
    if isinstance(obj, bool):
        return obj
    if isinstance(obj, (int, str)):
        return obj
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return round(obj, FLOAT_PRECISION)
    if isinstance(obj, (dt.datetime, dt.date)):
        return obj.isoformat()
    if isinstance(obj, dict):
        # Stringify all keys — JSON requires it, and it lets json.dumps(sort_keys=True)
        # work on dicts with mixed int + str keys (Python row → label dicts).
        # Int keys are formatted with leading zeros so they sort numerically when
        # reloaded as strings: "0007" < "0010" < "0118".
        out: dict[str, Any] = {}
        for k, v in obj.items():
            if isinstance(k, int):
                key = f"{k:04d}"
            elif isinstance(k, str):
                key = k
            else:
                key = str(k)
            out[key] = _canonicalize(v)
        return out
    if isinstance(obj, (list, tuple)):
        return [_canonicalize(x) for x in obj]
    if isinstance(obj, set):
        return sorted([_canonicalize(x) for x in obj], key=lambda x: json.dumps(x, default=str))
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        return _canonicalize(dataclasses.asdict(obj))
    if isinstance(obj, bytes):
        raise TypeError(f"Refusing to serialize bytes in snapshot ({len(obj)} bytes)")
    # Anything else — coerce to str so the snapshot still records SOMETHING.
    return f"<unserializable:{type(obj).__name__}>"


def fixture_paths() -> list[Path]:
    """List the .xlsm fixtures present in tests/golden/fixtures/."""
    return sorted(FIXTURE_DIR.glob("fixture_*.xlsm"))


def snapshot_path(fixture: Path, kind: str) -> Path:
    """Stable snapshot file path: tests/golden/snapshots/<stem>.<kind>.json"""
    return SNAPSHOT_DIR / f"{fixture.stem}.{kind}.json"


def _filter_projects_view(projects: dict) -> dict:
    """Strip ephemeral metadata from the parsed projects dict before snapshot.

    `load_pricing_model` returns rich per-project dicts. A few keys are
    machine-state / openpyxl objects that don't belong in a stable snapshot:
    raw openpyxl Cell refs, MergedCell intervals, etc. Strip them.

    The 'data' sub-dict (row → value) is kept verbatim — that IS the audit
    surface and must round-trip 1:1.
    """
    out = {}
    for col, proj in projects.items():
        if not isinstance(proj, dict):
            out[col] = proj
            continue
        filtered = {}
        for k, v in proj.items():
            # Drop fields that aren't deterministic / aren't load-bearing.
            if k in {"_raw_cell_refs", "_openpyxl_internals"}:
                continue
            filtered[k] = v
        out[col] = filtered
    return out


def build_snapshots(fixture: Path) -> dict[str, Any]:
    """Run the full audit pipeline on a fixture; return three snapshot blobs.

    Returns: {"load": ..., "audit": ..., "payload": ...}
    """
    # Local imports so this module loads without lib/ on the path (e.g.
    # when invoked standalone for CLI inspection).
    from lib.bible_audit import audit_projects
    from lib.data_loader import get_projects, load_pricing_model
    from lib.mockup_view import build_payload, filter_projects, list_candidate_projects

    with open(fixture, "rb") as f:
        loaded = load_pricing_model(f)
    projects = get_projects(loaded) or {}

    audits = audit_projects(projects)

    candidates = list_candidate_projects(projects)
    suggested_ids = {c["id"] for c in candidates if c.get("suggested")}
    review_projects = filter_projects(projects, suggested_ids)
    projects_list, portfolio = build_payload(
        review_projects,
        model_label=fixture.stem,
        reviewer="Golden Test",
        bible_label="Q1 '26",
    )

    return {
        "load": {
            "fixture": fixture.name,
            "result_top_level_keys": sorted(loaded.keys()) if isinstance(loaded, dict) else [],
            "projects": _filter_projects_view(projects),
            "candidate_count": len(candidates),
            "suggested_count": len(suggested_ids),
        },
        "audit": {
            "fixture": fixture.name,
            "by_column": audits,
        },
        "payload": {
            "fixture": fixture.name,
            "projects": projects_list,
            "portfolio": portfolio,
        },
    }


def write_snapshot(fixture: Path, kind: str, payload: Any) -> Path:
    """Write a canonicalized JSON snapshot. Returns the path written."""
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    path = snapshot_path(fixture, kind)
    canonical = _canonicalize(payload)
    # indent=2 for readable diffs in PR reviews.
    text = json.dumps(canonical, indent=2, sort_keys=True)
    path.write_text(text, encoding="utf-8")
    return path


def read_snapshot(fixture: Path, kind: str) -> Any:
    """Read an existing snapshot, raising FileNotFoundError if absent."""
    path = snapshot_path(fixture, kind)
    if not path.exists():
        raise FileNotFoundError(
            f"Snapshot not found: {path}\n"
            f"Generate with: uv run python tests/golden/snapshotter.py --write"
        )
    return json.loads(path.read_text(encoding="utf-8"))


def diff_against_snapshot(fixture: Path, kind: str, current: Any) -> str | None:
    """Compare current value tree against on-disk snapshot.

    Returns None if equal, or a unified-diff-style string describing the
    difference for the test failure message.
    """
    expected = read_snapshot(fixture, kind)
    actual = json.loads(json.dumps(_canonicalize(current), sort_keys=True))
    if expected == actual:
        return None
    # Build a compact diff. For now: show the first ~50 changed paths.
    return _summarize_diff(expected, actual)


def _summarize_diff(expected: Any, actual: Any, path: str = "$", limit: int = 50) -> str:
    """Produce a human-readable diff focused on the first changes."""
    diffs: list[str] = []

    def walk(e, a, p):
        if len(diffs) >= limit:
            return
        if type(e) is not type(a):
            diffs.append(f"  {p}: type changed {type(e).__name__} -> {type(a).__name__}")
            return
        if isinstance(e, dict):
            ek = set(e.keys())
            ak = set(a.keys())
            for k in sorted(ek - ak):
                diffs.append(f"  {p}.{k}: removed")
            for k in sorted(ak - ek):
                diffs.append(f"  {p}.{k}: added (now {a[k]!r})")
            for k in sorted(ek & ak):
                walk(e[k], a[k], f"{p}.{k}")
        elif isinstance(e, list):
            if len(e) != len(a):
                diffs.append(f"  {p}: length {len(e)} -> {len(a)}")
            for i, (ex, ax) in enumerate(zip(e, a, strict=False)):
                walk(ex, ax, f"{p}[{i}]")
        else:
            if e != a:
                diffs.append(f"  {p}: {e!r} -> {a!r}")

    walk(expected, actual, path)
    if not diffs:
        return "(snapshots differ but no scalar deltas found)"
    head = "\n".join(diffs[:limit])
    if len(diffs) >= limit:
        head += f"\n  … (truncated; ≥{limit} differences total)"
    return head


def main(argv: list[str] | None = None) -> int:
    """CLI: generate or refresh snapshots for all fixtures.

    Usage:
        uv run python tests/golden/snapshotter.py            # diff mode
        uv run python tests/golden/snapshotter.py --write    # (re)generate
    """
    import argparse

    parser = argparse.ArgumentParser(description="Golden-fixture snapshot tool")
    parser.add_argument(
        "--write",
        action="store_true",
        help="Generate fresh snapshots (overwrites existing).",
    )
    args = parser.parse_args(argv)

    fixtures = fixture_paths()
    if not fixtures:
        print(f"No fixtures in {FIXTURE_DIR}", flush=True)
        return 1

    any_diff = False
    for fixture in fixtures:
        print(f"\n=== {fixture.name} ===")
        try:
            snaps = build_snapshots(fixture)
        except Exception as e:  # noqa: BLE001
            print(f"  FAIL to build snapshot: {e}")
            return 2

        for kind, payload in snaps.items():
            if args.write:
                p = write_snapshot(fixture, kind, payload)
                print(f"  wrote {p} ({p.stat().st_size / 1024:.1f} KB)")
            else:
                try:
                    diff = diff_against_snapshot(fixture, kind, payload)
                except FileNotFoundError as e:
                    print(f"  {kind}: MISSING — {e}")
                    any_diff = True
                    continue
                if diff is None:
                    print(f"  {kind}: ok")
                else:
                    print(f"  {kind}: DIFF\n{diff}")
                    any_diff = True

    if any_diff and not args.write:
        print(
            "\nSnapshots differ. Inspect the diff above and either fix the code or rerun with --write."
        )
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
