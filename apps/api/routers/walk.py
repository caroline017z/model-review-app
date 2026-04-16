"""Walk comparison endpoint — compare two models, return .xlsx."""
from __future__ import annotations

import json
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from apps.api.store import model_store
from lib.walk_builder import build_walk_xlsx

router = APIRouter()


class WalkRequest(BaseModel):
    m1_id: str
    m2_id: str
    m1_label: str = "Model 1"
    m2_label: str = "Model 2"


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
        )
    except Exception as e:
        raise HTTPException(500, f"Walk generation error: {e}")

    filename = f"Build_Walk_{req.m1_label}_vs_{req.m2_label}.xlsx".replace(" ", "_")
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-Walk-Summary": json.dumps(summary),
        },
    )
