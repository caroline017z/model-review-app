"""Model upload, list, and delete endpoints."""
from __future__ import annotations

import io
import logging
from fastapi import APIRouter, HTTPException, UploadFile
from pydantic import BaseModel

from apps.api.store import model_store
from lib.data_loader import load_pricing_model, get_projects, validate_model_result
from lib.mockup_view import list_candidate_projects

logger = logging.getLogger(__name__)
router = APIRouter()


class CandidateProject(BaseModel):
    id: str
    name: str
    dc: float
    developer: str
    state: str
    utility: str
    program: str
    toggled_on: bool
    suggested: bool
    proj_number: int | None = None
    col_letter: str = ""
    dev_sibling: bool = False


class UploadResponse(BaseModel):
    model_id: str
    filename: str
    project_count: int
    projects: list[CandidateProject]
    fingerprint: str
    critical_missing: list[int]


class ModelInfo(BaseModel):
    model_id: str
    filename: str
    project_count: int


@router.post("/upload", response_model=UploadResponse)
async def upload_model(file: UploadFile):
    """Upload a .xlsm/.xlsx pricing model, parse it, return model ID + projects."""
    if not file.filename:
        raise HTTPException(400, "No filename provided")
    ext = file.filename.rsplit(".", 1)[-1].lower()
    if ext not in ("xlsm", "xlsx"):
        raise HTTPException(400, f"Unsupported file type: .{ext}. Use .xlsm or .xlsx")

    content = await file.read()
    if len(content) > 50_000_000:
        raise HTTPException(413, "File too large (max 50MB)")
    buf = io.BytesIO(content)

    try:
        result = load_pricing_model(buf)
    except KeyError as e:
        # e.g. missing "Project Inputs" sheet — user-friendly 400
        raise HTTPException(400, str(e))
    except Exception as e:
        logger.exception("Failed to parse model: %s", e)
        raise HTTPException(400, f"Failed to parse model: {e}")

    # Structural validation: reject workbooks with zero real projects or
    # too many critical rows unresolved (usually signals wrong template).
    validation = validate_model_result(result)
    if not validation["ok"]:
        reasons = []
        if validation["project_count"] == 0:
            reasons.append("no real projects found in Project Inputs sheet")
        if len(validation["critical_missing"]) > 3:
            reasons.append(
                f"{len(validation['critical_missing'])} critical row mappings "
                f"unresolved (rows {validation['critical_missing']}) — this "
                f"usually means the workbook uses a different template"
            )
        raise HTTPException(400, "Model validation failed: " + "; ".join(reasons))

    model_id = model_store.put(result, file.filename)
    projects = get_projects(result) or {}
    candidates = list_candidate_projects(projects)

    return UploadResponse(
        model_id=model_id,
        filename=file.filename,
        project_count=len(candidates),
        projects=[CandidateProject(**{k: c.get(k) for k in CandidateProject.model_fields}) for c in candidates],
        fingerprint=validation["fingerprint"],
        critical_missing=validation["critical_missing"],
    )


@router.get("/{model_id}", response_model=ModelInfo)
def get_model(model_id: str):
    """Get model metadata."""
    entry = model_store.get(model_id)
    if not entry:
        raise HTTPException(404, "Model not found or expired")
    projects = get_projects(entry["result"]) or {}
    return ModelInfo(
        model_id=model_id,
        filename=entry["filename"],
        project_count=len(projects),
    )


@router.delete("/{model_id}")
def delete_model(model_id: str):
    """Remove a model from the store."""
    if not model_store.delete(model_id):
        raise HTTPException(404, "Model not found")
    return {"deleted": True}
