"""Preview API for prototype generator.

Exposes /api/preview which accepts boards and state definitions and returns
a preview payload powered by the IUE (Interaction Understanding Engine).
"""
from typing import Any, Dict, List

from fastapi import APIRouter
from pydantic import BaseModel

from src.prototype_generator import build_preview_payload
from src.prototype_traversal import traverse_flows, generate_ai_handoff, enhanced_diagnostics
from src.iue import InteractionUnderstandingEngine
from src.llm.router import LLMProviderRouter

llm_router = LLMProviderRouter()
iue_engine = InteractionUnderstandingEngine()

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
    # Convert pydantic models to plain dicts
    boards = [b.dict() for b in req.boards]

    # Run IUE pipeline for structured flow suggestions with confidence & reasoning
    iue_flows = iue_engine.analyze_to_dicts(boards)

    # Build legacy payload (transformed samples, matrix, etc.)
    payload = build_preview_payload(boards, req.state_definitions, req.preview_options)

    # Enhance: replace heuristic flows with IUE-structured flows
    # Backward-compatible keys (from, to, reason) + IUE enrichment (confidence, role, status)
    payload["flows"] = iue_flows
    payload["iue_version"] = "1.0.0"
    return payload


@router.post("/traverse", response_model=Dict[str, Any])
async def traverse(req: TraversalRequest) -> Dict[str, Any]:
    boards = [b.dict() for b in req.boards]
    result = traverse_flows(req.flows, boards)
    return result


@router.post("/diagnostics", response_model=Dict[str, Any])
async def diagnostics(req: TraversalRequest) -> Dict[str, Any]:
    """Combined traversal + enhanced diagnostics endpoint."""
    boards = [b.dict() for b in req.boards]
    trav = traverse_flows(req.flows, boards)
    # build a quick matrix sample from boards for viewport-sensitive checks
    matrix = { '1440': boards[0] } if boards else {}
    enhanced = enhanced_diagnostics(boards, matrix)
    return { 'traversal': trav, 'enhanced': enhanced }


@router.post("/suggest_flows", response_model=Dict[str, Any])
async def suggest_flows(req: PreviewRequest) -> Dict[str, Any]:
    """Suggest flows using IUE (primary) with LLM enhancement when available."""
    boards = [b.dict() for b in req.boards]

    # Primary: IUE pipeline (always available, no API key required)
    iue_suggestions = iue_engine.analyze_to_dicts(boards)

    # Secondary: attempt LLM enhancement for higher-quality suggestions
    try:
        prompt = (
            "Suggest navigation links between these screens: "
            + str([b.get("title") for b in boards])
            + ". Reply JSON list of {'from','to','reason','params'}"
        )
        result = llm_router.chat(
            [
                {"role": "system", "content": "You are a helpful flow suggester."},
                {"role": "user", "content": prompt},
            ],
            max_tokens=1024,
        )
        content = llm_router.extract_content(result)
        import json

        llm_suggestions = json.loads(content) if content.strip().startswith("[") else []
        if llm_suggestions and len(llm_suggestions) > 0:
            return {
                "suggestions": llm_suggestions,
                "iue_fallback": iue_suggestions,
                "source": "llm",
            }
    except Exception:
        pass

    return {"suggestions": iue_suggestions, "source": "iue"}


@router.post("/handoff", response_model=Dict[str, Any])
async def handoff(req: HandoffRequest) -> Dict[str, Any]:
    boards = [b.dict() for b in req.boards]
    package = generate_ai_handoff(boards, req.flows)
    return package


@router.post('/handoff/generate_files', response_model=Dict[str, Any])
async def handoff_generate_files(req: HandoffRequest) -> Dict[str, Any]:
    """Return the handoff package and a suggested file payload; the server does not auto-write files in this PoC.

    The caller can use the returned 'files' list to create files in the repo.
    """
    boards = [b.dict() for b in req.boards]
    package = generate_ai_handoff(boards, req.flows)
    # craft file stubs
    files = []
    for cr in package.get('cursorrules', []):
        comp = cr['component_id']
        filename = f"deliverables/{comp}_component.md"
        content = f"# Component: {comp}\n\nIntent: {cr.get('intent')}\n\nPrompt:\n\n{package.get('prompts',[[]])[0]}\n"
        files.append({'path': filename, 'content': content})
    return {'package': package, 'files': files}
