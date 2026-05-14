"""Review endpoint — audit + build full payload for selected projects."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from apps.api.bible_store import bible_store
from apps.api.store import model_store
from lib.data_loader import get_projects
from lib.mockup_view import build_payload, filter_projects, list_candidate_projects

router = APIRouter()


class ReviewRequest(BaseModel):
    model_id: str
    project_ids: list[str] | None = None
    model_label: str = "Model"
    reviewer: str = "Caroline Z."
    # Optional override. When None, the active vintage's label is used so
    # the UI always reflects what the audit actually ran against.
    bible_label: str | None = None


@router.post("")
def run_review(req: ReviewRequest):
    """Run audit for selected projects and return the full review payload."""
    entry = model_store.get(req.model_id)
    if not entry:
        raise HTTPException(404, "Model not found or expired")

    projects = get_projects(entry["result"]) or {}

    # Filter to selected project IDs, or use all candidates
    if req.project_ids:
        review_projects = filter_projects(projects, set(req.project_ids))
    else:
        candidates = list_candidate_projects(projects)
        suggested_ids = {c["id"] for c in candidates if c.get("suggested")}
        review_projects = filter_projects(projects, suggested_ids)

    # Run the audit against the currently active Bible vintage so uploaded
    # bibles take effect immediately. Label defaults to that vintage's label.
    active_bible = bible_store.active()
    bible_label = req.bible_label or active_bible.label

    try:
        projects_list, portfolio = build_payload(
            review_projects,
            model_label=req.model_label,
            reviewer=req.reviewer,
            bible_label=bible_label,
            bible=active_bible,
        )
    except Exception as e:
        raise HTTPException(500, f"Audit pipeline error: {e}") from e

    return {
        "projects": projects_list,
        "portfolio": portfolio,
    }
