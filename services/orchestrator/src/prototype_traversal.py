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


# Enhanced diagnostics: truncation / contrast / fix suggestions
def enhanced_diagnostics(boards: List[Dict[str, Any]], matrix: Dict[str, Dict[str, Any]] | None = None) -> Dict[str, Any]:
    """Run additional diagnostics beyond traversal to detect truncation risks and offer simple fixes.

    Returns a dict: {issues: [{board, vp, issue, suggestion}], summary: {...}}
    """
    issues = []
    # board-level checks
    for b in boards:
        for el in b.get('elements', []):
            text = str(el.get('text', '') or '')
            if len(text) > 120:
                issues.append({'board': b.get('id'), 'vp': None, 'issue': 'long_text', 'detail': text[:120] + '...', 'suggestion': 'Consider truncating or wrapping, apply .truncate or CSS max-width'})
    # matrix-level viewport checks (if provided)
    if matrix:
        for vp, sample in matrix.items():
            for el in sample.get('elements', []):
                text = str(el.get('text','') or '')
                if len(text) > 120:
                    issues.append({'board': sample.get('id','sample'), 'vp': vp, 'issue': 'long_text_viewport', 'detail': text[:120] + '...', 'suggestion': 'Add responsive truncation or reduce text in this viewport'})
                # numeric overflow heuristic
                if el.get('type') in ('metric', 'number') and re.search(r'\d{6,}', str(el.get('text',''))):
                    issues.append({'board': sample.get('id','sample'), 'vp': vp, 'issue': 'numeric_overflow', 'detail': str(el.get('text','')), 'suggestion': 'Format numbers (k/M) or limit precision'})
    summary = {'total_issues': len(issues)}
    return {'issues': issues, 'summary': summary}
