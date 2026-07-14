from typing import List, Dict, Any


def traverse_flows(flows: List[Dict[str, Any]], boards: List[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Lightweight traversal that simulates path coverage and finds dead-ends.

    Returns diagnostics: {dead_ends: [from->to], unreachable_targets: [...], coverage: {count}}.
    This is a heuristic PoC for the interactivity flow consistency review.
    """
    if boards is None:
        boards = []
    graph = {}
    targets = set()
    for f in flows:
        graph.setdefault(f['from'], []).append(f['to'])
        targets.add(f['to'])
    # find dead-ends: nodes that have outgoing links to targets that have no outgoing links
    dead_ends = []
    for src, tos in graph.items():
        for to in tos:
            if to not in graph:
                dead_ends.append({'from': src, 'to': to})
    # unreachable targets: boards that are not referenced by any flow 'to'
    board_ids = set(b['id'] for b in boards)
    referenced = set(f['to'] for f in flows)
    unreachable = list(board_ids - referenced)
    return {
        'dead_ends': dead_ends,
        'unreachable_targets': unreachable,
        'coverage': {'flows': len(flows), 'boards': len(board_ids)},
    }


def generate_ai_handoff(boards: List[Dict[str, Any]], flows: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Generate a minimal AI-Native Handoff package (JSON) as a PoC.

    Contains:
    - cursorrules: simplified rule list mapping component ids to token names
    - prompts: LLM-optimized instruction snippets for downstream codegen
    - token_map: component -> design token suggestions
    """
    cursorrules = []
    prompts = []
    token_map = {}
    for b in boards:
        cursorrules.append({'component_id': b['id'], 'intent': f"render_{b.get('title','screen').lower().replace(' ','_')}", 'files': []})
        prompts.append(f"Generate React component for screen '{b.get('title','screen')}'. Use Tailwind and export default component named {b['id'].capitalize()}Screen.")
        token_map[b['id']] = {'colors': {'primary': '#0366d6'}, 'spacing': 'base*1.2'}
    return {'cursorrules': cursorrules, 'prompts': prompts, 'token_map': token_map}
