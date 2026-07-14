"""Preview API for prototype generator (minimal stub).

Exposes /api/preview which accepts boards and state definitions and returns
a preview payload produced by services/orchestrator/src/prototype_generator.py
"""
from typing import Any, Dict, List

from fastapi import APIRouter
from pydantic import BaseModel

from src.prototype_generator import build_preview_payload

router = APIRouter(prefix="/api/preview", tags=["preview"])


class Board(BaseModel):
    id: str
    title: str | None = None
    elements: List[Dict[str, Any]] = []


class PreviewRequest(BaseModel):
    boards: List[Board]
    state_definitions: Dict[str, Dict[str, Any]] = {}


@router.post("/", response_model=Dict[str, Any])
async def preview(req: PreviewRequest) -> Dict[str, Any]:
    # Convert pydantic models to plain dicts for the prototype generator
    boards = [b.dict() for b in req.boards]
    payload = build_preview_payload(boards, req.state_definitions)
    return payload
