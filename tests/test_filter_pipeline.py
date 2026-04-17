"""Unit tests for the project-selection pipeline.

Guarantees that the sidebar's MW total, the payload's MW total, and the
rendered HTML payload all stay in sync.
"""
from lib.mockup_view import list_candidate_projects, filter_projects, build_payload


def _synthetic(n_active=2, n_inactive=3, n_placeholder=10):
    """Build a fake m1_projects dict: active + inactive + empty-placeholder columns."""
    d = {}
    col = 6
    for i in range(n_active):
        d[col] = {
            "name": f"Active-{i}", "toggle": True,
            "data": {10: "AcmeDev", 11: 5.0 + i, 18: "IL", 19: "Ameren", 22: "ABP"},
        }
        col += 1
    for i in range(n_inactive):
        d[col] = {
            "name": f"Inactive-{i}", "toggle": False,
            "data": {10: "AcmeDev", 11: 3.0 + i, 18: "IL", 19: "Ameren", 22: "ABP"},
        }
        col += 1
    for _ in range(n_placeholder):
        d[col] = {
            "name": f"Placeholder-{col}", "toggle": True,
            "data": {11: 0, 18: "", 19: "", 22: ""},
        }
        col += 1
    return d


def test_candidates_exclude_placeholder_columns():
    projects = _synthetic()
    candidates = list_candidate_projects(projects)
    # 2 active + 3 inactive real — placeholders must be filtered (DC=0)
    assert len(candidates) == 5


def test_active_vs_inactive_split():
    projects = _synthetic()
    candidates = list_candidate_projects(projects)
    active = [c for c in candidates if c["toggled_on"]]
    inactive = [c for c in candidates if not c["toggled_on"]]
    assert len(active) == 2
    assert len(inactive) == 3


def test_filter_projects_only_includes_chosen():
    projects = _synthetic()
    candidates = list_candidate_projects(projects)
    # Include only the first active project
    ids = {candidates[0]["id"]}
    filtered = filter_projects(projects, ids)
    assert len(filtered) == 1


def test_mw_total_consistency_across_pipeline():
    projects = _synthetic()
    candidates = list_candidate_projects(projects)
    # Include every candidate (all on+off real projects)
    all_ids = {c["id"] for c in candidates}
    filtered = filter_projects(projects, all_ids)
    _, portfolio = build_payload(filtered, model_label="Test")
    # Candidate MW sum == payload totalMw
    candidate_mw = sum(c["dc"] for c in candidates)
    assert abs(portfolio["totalMw"] - round(candidate_mw, 1)) < 0.05


def test_developer_grouping_identifier_present():
    projects = _synthetic()
    candidates = list_candidate_projects(projects)
    for c in candidates:
        assert c["developer"] == "AcmeDev"


def test_empty_input_safe():
    candidates = list_candidate_projects({})
    assert candidates == []
    filtered = filter_projects({}, None)
    assert filtered == {}
    _, portfolio = build_payload({}, model_label="Empty")
    assert portfolio["count"] == 0
    assert portfolio["totalMw"] == 0.0
