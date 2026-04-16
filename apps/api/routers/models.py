"""Model upload, list, and delete endpoints."""
from __future__ import annotations

import io
import logging
from fastapi import APIRouter, HTTPException, UploadFile
from pydantic import BaseModel

from apps.api.store import model_store
from lib.data_loader import load_pricing_model, get_projects
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
    buf = io.BytesIO(content)

    try:
        result = load_pricing_model(buf)
    except KeyError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        logger.exception("Failed to parse model: %s", e)
        raise HTTPException(400, f"Failed to parse model: {e}")

    model_id = model_store.put(result, file.filename)
    projects = get_projects(result) or {}
    candidates = list_candidate_projects(projects)

    return UploadResponse(
        model_id=model_id,
        filename=file.filename,
        project_count=len(candidates),
        projects=[CandidateProject(**{k: c.get(k) for k in CandidateProject.model_fields}) for c in candidates],
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
