"""Preview API for prototype generator (minimal stub).

Exposes /api/preview which accepts boards and state definitions and returns
a preview payload produced by services/orchestrator/src/prototype_generator.py
"""
from typing import Any, Dict, List

from fastapi import APIRouter
from pydantic import BaseModel

from src.prototype_generator import build_preview_payload
from src.prototype_traversal import traverse_flows, generate_ai_handoff

router = APIRouter(prefix="/api/preview", tags=["preview"])


class Board(BaseModel):
    id: str
    title: str | None = None
    elements: List[Dict[str, Any]] = []


class PreviewRequest(BaseModel):
    boards: List[Board]
    state_definitions: Dict[str, Dict[str, Any]] = {}
    preview_options: Dict[str, Any] | None = None


class TraversalRequest(BaseModel):
    flows: List[Dict[str, Any]]
    boards: List[Board] = []


class HandoffRequest(BaseModel):
    boards: List[Board]
    flows: List[Dict[str, Any]] = []


@router.post("/", response_model=Dict[str, Any])
async def preview(req: PreviewRequest) -> Dict[str, Any]:
    # Convert pydantic models to plain dicts for the prototype generator
    boards = [b.dict() for b in req.boards]
    payload = build_preview_payload(boards, req.state_definitions, req.preview_options)
    return payload


@router.post("/traverse", response_model=Dict[str, Any])
async def traverse(req: TraversalRequest) -> Dict[str, Any]:
    boards = [b.dict() for b in req.boards]
    result = traverse_flows(req.flows, boards)
    return result


@router.post("/handoff", response_model=Dict[str, Any])
async def handoff(req: HandoffRequest) -> Dict[str, Any]:
    boards = [b.dict() for b in req.boards]
    package = generate_ai_handoff(boards, req.flows)
    return package
