"""Bible vintage CRUD: upload, list, get-active, set-active, delete."""

from __future__ import annotations

import io
import logging
from typing import Any

from fastapi import APIRouter, HTTPException, UploadFile
from pydantic import BaseModel

from apps.api.bible_store import bible_store
from lib.bible_loader import BibleParseError, load_bible_from_excel

logger = logging.getLogger(__name__)
router = APIRouter()


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------


class VintageSummary(BaseModel):
    vintage_id: str
    label: str
    source: str
    uploaded_at: str
    is_active: bool


class VintageDetail(VintageSummary):
    # `cs_average` and `market_bible` aren't returned in full here — they're
    # large dicts and the SPA fetches them via a dedicated detail endpoint
    # if/when needed. The summary is enough for the vintage selector.
    cs_average_row_count: int
    market_entries_count: int


class UploadResponse(BaseModel):
    vintage_id: str
    label: str
    source: str
    uploaded_at: str
    overlaid_row_count: int
    is_active: bool


class SetActiveRequest(BaseModel):
    vintage_id: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _detail(b: Any, is_active: bool) -> VintageDetail:
    return VintageDetail(
        vintage_id=b.vintage_id,
        label=b.label,
        source=b.source,
        uploaded_at=b.uploaded_at,
        is_active=is_active,
        cs_average_row_count=len(b.cs_average),
        market_entries_count=len(b.market_bible),
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/vintages", response_model=list[VintageSummary])
def list_vintages():
    """All known bible vintages, oldest → newest."""
    return [VintageSummary.model_validate(v) for v in bible_store.list_vintages()]


@router.get("/active", response_model=VintageDetail)
def get_active():
    """The currently active vintage."""
    b = bible_store.active()
    return _detail(b, is_active=True)


@router.get("/vintages/{vintage_id}", response_model=VintageDetail)
def get_vintage(vintage_id: str):
    """Look up a specific vintage by ID."""
    b = bible_store.get(vintage_id)
    if b is None:
        raise HTTPException(404, f"Vintage {vintage_id!r} not found")
    is_active = b.vintage_id == bible_store.active().vintage_id
    return _detail(b, is_active=is_active)


@router.post("/vintages", response_model=UploadResponse)
async def upload_vintage(
    file: UploadFile,
    label: str = "",
    set_active: bool = True,  # noqa: B008 — query default is fine for bool
):
    """Upload a Pricing Bible xlsx → parse → save as a new vintage.

    Form / query params:
      - `file`        (required) the .xlsx upload
      - `label`       (optional) display label; defaults to filename
      - `set_active`  (optional, default true) whether to make the new
                       vintage the active one for future audits

    Returns the parsed vintage metadata + how many CS rows were overlaid.
    """
    if not file.filename:
        raise HTTPException(400, "No filename provided")
    ext = file.filename.rsplit(".", 1)[-1].lower()
    if ext != "xlsx":
        raise HTTPException(400, f"Unsupported file type: .{ext}. Bible uploads must be .xlsx")

    content = await file.read()
    # 10 MB is generous for a Pricing Bible (real ones are ~200-500 KB).
    if len(content) > 10_000_000:
        raise HTTPException(413, "Bible file too large (max 10MB)")
    buf = io.BytesIO(content)

    try:
        bible = load_bible_from_excel(buf, label=label, filename=file.filename)
    except BibleParseError as e:
        raise HTTPException(400, str(e)) from e
    except Exception as e:  # defensive: openpyxl can raise an assortment
        logger.exception("Unexpected bible-parse error: %s", e)
        raise HTTPException(400, f"Failed to parse bible: {e}") from e

    bible_store.save(bible, set_active=set_active)

    # Re-fetch the persisted record to make absolutely sure we return
    # what the next audit will actually use.
    saved = bible_store.get(bible.vintage_id)
    assert saved is not None  # we just saved it
    return UploadResponse(
        vintage_id=saved.vintage_id,
        label=saved.label,
        source=saved.source,
        uploaded_at=saved.uploaded_at,
        overlaid_row_count=len(saved.cs_average),
        is_active=(saved.vintage_id == bible_store.active().vintage_id),
    )


@router.post("/active", response_model=VintageDetail)
def set_active(req: SetActiveRequest):
    """Switch which vintage future audits use."""
    if not bible_store.set_active(req.vintage_id):
        raise HTTPException(404, f"Vintage {req.vintage_id!r} not found")
    b = bible_store.active()
    return _detail(b, is_active=True)


@router.delete("/vintages/{vintage_id}")
def delete_vintage(vintage_id: str):
    """Remove a non-active vintage from the store."""
    if vintage_id == bible_store.active().vintage_id:
        raise HTTPException(
            409,
            "Cannot delete the active vintage. Switch active first, then delete.",
        )
    if not bible_store.delete(vintage_id):
        raise HTTPException(404, f"Vintage {vintage_id!r} not found")
    return {"deleted": True}
