"""Walk comparison endpoint — compare two models, return .xlsx."""
from __future__ import annotations

import json
import re

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from apps.api.store import model_store
from lib.walk_builder import build_walk_xlsx

router = APIRouter()


def _safe_filename_part(s: str) -> str:
    """Strip filename-illegal chars and collapse whitespace.

    Labels can carry `:` (macro-runner labels) or other reserved chars; the
    download dialog will reject or mangle the name otherwise.
    """
    s = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "", s or "")
    return re.sub(r"\s+", "_", s).strip("_") or "model"


class WalkRequest(BaseModel):
    m1_id: str
    m2_id: str
    m1_label: str = "Model 1"
    m2_label: str = "Model 2"
    project_numbers: list[int] | None = None
    project_names: list[str] | None = None


@router.post("")
def generate_walk(req: WalkRequest):
    """Compare two models and return a formatted Walk Summary .xlsx."""
    m1 = model_store.get(req.m1_id)
    m2 = model_store.get(req.m2_id)
    if not m1:
        raise HTTPException(404, f"Model 1 ({req.m1_id}) not found or expired")
    if not m2:
        raise HTTPException(404, f"Model 2 ({req.m2_id}) not found or expired")

    try:
        buf, summary = build_walk_xlsx(
            m1["result"], m2["result"],
            req.m1_label, req.m2_label,
            include_proj_numbers=set(req.project_numbers) if req.project_numbers else None,
            include_proj_names=set(req.project_names) if req.project_names else None,
        )
    except Exception as e:
        raise HTTPException(500, f"Walk generation error: {e}")

    # Template drift warning: if the two models have different fingerprints,
    # at least one critical row is at a different position in one vs the
    # other. The walk's row-by-row diff is still meaningful but may
    # misattribute some rows. Surface in the summary header.
    fp1 = m1["result"].get("fingerprint")
    fp2 = m2["result"].get("fingerprint")
    if fp1 and fp2 and fp1 != fp2:
        summary["template_drift"] = {
            "m1_fingerprint": fp1,
            "m2_fingerprint": fp2,
            "warning": (
                "Template fingerprints differ — at least one critical row "
                "resolved to a different position in M1 vs M2. Walk results "
                "may compare mismatched rows. Inspect the Project Inputs "
                "sheets side-by-side before trusting per-row diffs."
            ),
        }

    # Log diagnostic info for debugging empty walks
    if summary.get("n_matched", 0) == 0:
        from lib.data_loader import get_projects
        from lib.rows import ROW_PROJECT_NUMBER
        from lib.utils import safe_float
        m1p = get_projects(m1["result"]) or {}
        m2p = get_projects(m2["result"]) or {}
        m1_pnums = [safe_float(p.get("data", {}).get(ROW_PROJECT_NUMBER)) for p in m1p.values() if isinstance(p, dict)]
        m2_pnums = [safe_float(p.get("data", {}).get(ROW_PROJECT_NUMBER)) for p in m2p.values() if isinstance(p, dict)]
        import logging
        logging.warning(
            "Walk matched 0 projects. M1 has %d projects (proj#: %s), M2 has %d (proj#: %s)",
            len(m1p), m1_pnums[:5], len(m2p), m2_pnums[:5],
        )

    filename = f"Build_Walk_{_safe_filename_part(req.m1_label)}_vs_{_safe_filename_part(req.m2_label)}.xlsx"
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-Walk-Summary": json.dumps(summary),
        },
    )
