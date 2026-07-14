"""Prototype generator stubs for Clutch.

Contains initial interfaces for:
- extract_flows_from_boards(boards): analyze imported static boards and suggest navigation links
- inject_ui_and_business_states(tree, state_definitions): produce a preview-ready component tree with pseudoclass and business-state injections

This is a minimal, non-production scaffold intended to be extended.
"""
from typing import List, Dict, Any


def extract_flows_from_boards(boards: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Analyze a list of board representations and return suggested navigation links.

    Each board is expected to be a dict with at least 'id', 'title', and 'elements' (list of UI elements with text/type).
    Returns a list of link suggestions: {from: board_id, to: board_id, reason: str, params: {}}.
    """
    suggestions = []
    # TODO: Implement LLM-backed extraction; for now, use simple heuristic matching.
    for src in boards:
        for tgt in boards:
            if src['id'] == tgt['id']:
                continue
            # heuristic: button text in src matches title or keywords in tgt
            src_texts = " ".join(e.get('text','') for e in src.get('elements', []))
            if tgt.get('title') and tgt['title'].lower() in src_texts.lower():
                suggestions.append({
                    'from': src['id'],
                    'to': tgt['id'],
                    'reason': f"Title match: {tgt.get('title')}",
                    'params': {}
                })
    return suggestions


def inject_ui_and_business_states(component_tree: Dict[str, Any], state_definitions: Dict[str, Any]) -> Dict[str, Any]:
    """Given a component tree and state definitions, return a transformed tree ready for preview.

    - component_tree: nested dict representing pages/components
    - state_definitions: mapping like {'Normal': {...}, 'Critical': {...}}

    The function should inject hover/focus/active pseudo-class markers and add business-state variants.
    """
    transformed = dict(component_tree)  # shallow copy for scaffold
    # TODO: walk tree and inject classes / state variants. This is a placeholder implementation.
    transformed['__injected_states'] = list(state_definitions.keys())
    return transformed


# Lightweight helper to build a sample flow preview payload
def build_preview_payload(boards: List[Dict[str, Any]], state_definitions: Dict[str, Any]) -> Dict[str, Any]:
    flows = extract_flows_from_boards(boards)
    # pick first board as sample component tree placeholder
    sample_tree = boards[0] if boards else {'id': 'empty', 'elements': []}
    transformed = inject_ui_and_business_states(sample_tree, state_definitions)
    return {
        'flows': flows,
        'transformed_sample': transformed,
    }
