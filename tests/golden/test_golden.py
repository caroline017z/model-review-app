"""Golden-fixture regression tests.

Locks the JSON output of `load_pricing_model`, `audit_projects`, and
`build_payload` against committed snapshots. Any drift fails CI until
explicitly accepted by regenerating snapshots:

    uv run python tests/golden/snapshotter.py --write

These snapshots are the safety net for Phase 3 (audit-engine refactor)
and Phase 4 (Bible loader replacement). Both phases must produce
identical JSON output before being merged — see docs/upgrade-plan.md.

Skipped automatically if the .xlsm fixtures aren't present locally
(Git LFS not pulled / first-time clone). Run `git lfs pull` to fetch them.
"""

from __future__ import annotations

import pytest

from tests.golden.snapshotter import (
    build_snapshots,
    diff_against_snapshot,
    fixture_paths,
    snapshot_path,
)

FIXTURES = fixture_paths()


def _has_lfs_content(fixture):
    """Detect Git LFS pointer files (200-byte stubs) vs real workbooks."""
    return fixture.stat().st_size > 100_000  # real fixtures are >10 MB


# Parametrize once across all fixtures so test IDs are predictable.
@pytest.fixture(scope="session", params=FIXTURES, ids=[f.stem for f in FIXTURES])
def fixture_snapshots(request):
    """Build the three-kind snapshot dict once per fixture per test session."""
    f = request.param
    if not _has_lfs_content(f):
        pytest.skip(f"LFS content not pulled for {f.name} (run `git lfs pull`)")
    return f, build_snapshots(f)


@pytest.mark.parametrize("kind", ["load", "audit", "payload"])
def test_snapshot_matches(fixture_snapshots, kind):
    """The on-disk snapshot must equal the freshly-computed output.

    Drift means either:
      (a) Intentional refactor — regenerate with `snapshotter.py --write`
          and review the diff in your PR.
      (b) Unintentional change — the snapshot caught a real regression;
          investigate before "fixing" the snapshot.
    """
    fixture, snaps = fixture_snapshots
    payload = snaps[kind]
    if not snapshot_path(fixture, kind).exists():
        pytest.fail(
            f"Snapshot missing for {fixture.name} / {kind}. "
            f"First-time setup: run `uv run python tests/golden/snapshotter.py --write`."
        )
    diff = diff_against_snapshot(fixture, kind, payload)
    if diff is not None:
        pytest.fail(
            f"\nGolden snapshot drift for {fixture.name} / {kind}.json\n"
            f"\nFirst differences:\n{diff}\n"
            f"\nIf the drift is intentional, regenerate snapshots:\n"
            f"    uv run python tests/golden/snapshotter.py --write\n"
            f"and review the diff in your PR description."
        )
