"""Prototype generator helpers for Clutch.

Contains initial interfaces for:
- extract_flows_from_boards(boards): analyze imported static boards and suggest navigation links
- inject_ui_and_business_states(tree, state_definitions): produce a preview-ready component tree with pseudoclass and business-state injections

This file contains enhanced heuristics for quick validation in tests. Not production-ready.
"""
from typing import List, Dict, Any
import re


def _extract_simple_params_from_text(text: str) -> Dict[str, Any]:
    """Try to find simple key=value or keyword patterns to form query params.

    Examples matched: "range=last30d", "last 30 days", "node: xyz", "node=xyz"
    Returns a dict of inferred params.
    """
    params: Dict[str, Any] = {}
    # key=value patterns
    for m in re.finditer(r"(\w+)=([\w\-_%]+)", text):
        params[m.group(1)] = m.group(2)
    # key: value patterns
    for m in re.finditer(r"(\w+):\s*([\w\-_%]+)", text):
        params[m.group(1)] = m.group(2)
    # date range like 'last 30 days' or 'last30d'
    m = re.search(r"last\s*(\d+)[\s-]*(day|days|d)", text, re.I)
    if m:
        params['range'] = f"last{m.group(1)}d"
    # node or service id heuristics
    m = re.search(r"node[_\- ]?(id)?[:= ]?([\w\-]+)", text, re.I)
    if m:
        params['node'] = m.group(2)
    return params


def _normalize_words(s: str) -> List[str]:
    words = re.findall(r"[a-zA-Z0-9]+", (s or "").lower())
    # naive singularization: include singular form for trailing 's' to improve overlap matching
    augmented: List[str] = []
    for w in words:
        augmented.append(w)
        if w.endswith('s') and len(w) > 3:
            augmented.append(w[:-1])
    return augmented


def extract_flows_from_boards(boards: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Analyze a list of board representations and return suggested navigation links.

    Each board is expected to be a dict with at least 'id', 'title', and 'elements' (list of UI elements with text/type).
    Returns a list of link suggestions: {from: board_id, to: board_id, reason: str, params: {}}.
    """
    suggestions: List[Dict[str, Any]] = []
    # lightweight heuristics to approximate LLM suggestions for MVP tests
    for src in boards:
        # include the board title as part of the source text to improve matching
        src_texts = " ".join(([src.get('title','')] + [e.get('text', '') for e in src.get('elements', [])]))
        src_words = set(_normalize_words(src_texts))
        # scan for param-like tokens in source texts
        inferred_params = _extract_simple_params_from_text(src_texts)
        for tgt in boards:
            if src['id'] == tgt['id']:
                continue
            tgt_title = tgt.get('title') or ""
            tgt_words = set(_normalize_words(tgt_title))
            # 1) exact title substring match
            if tgt_title and tgt_title.lower() in src_texts.lower():
                suggestions.append({'from': src['id'], 'to': tgt['id'], 'reason': f"Title match: {tgt_title}", 'params': inferred_params})
                continue
            # 2) word overlap between src element texts and target title
            common = src_words & tgt_words
            if common:
                suggestions.append({'from': src['id'], 'to': tgt['id'], 'reason': f"Keyword overlap: {sorted(common)[:5]}", 'params': inferred_params})
                continue
            # 3) button/action heuristic: look for verbs in src that imply create/edit/view
            action_verbs = {'create', 'new', 'add', 'edit', 'view', 'open', 'details', 'configure', 'manage'}
            if any(v in src_words for v in action_verbs) and any(w in tgt_words for w in {'create', 'configure', 'settings', 'new', 'edit'}):
                suggestions.append({'from': src['id'], 'to': tgt['id'], 'reason': 'Action→Page heuristic', 'params': inferred_params})
                continue
    return suggestions


def inject_ui_and_business_states(component_tree: Dict[str, Any], state_definitions: Dict[str, Any]) -> Dict[str, Any]:
    """Given a component tree and state definitions, return a transformed tree ready for preview.

    - component_tree: nested dict representing pages/components
    - state_definitions: mapping like {'Normal': {...}, 'Critical': {...}}

    The function should inject hover/focus/active pseudo-class markers and add business-state variants.
    For MVP we annotate component nodes with a '__variants' key listing injected classes / markers.
    """
    transformed = dict(component_tree)  # shallow copy for scaffold
    # naive walk: if elements exist, tag them with injected pseudo markers
    elements = transformed.get('elements', [])
    new_elements = []
    for el in elements:
        el_copy = dict(el)
        # inject pseudo-class markers as metadata
        el_copy.setdefault('__variants', {})
        el_copy['__variants'].setdefault('ui', [])
        el_copy['__variants']['ui'].extend(['hover:scale-95', 'focus:ring-2', 'active:opacity-90'])
        # add business state mapping hints
        el_copy['__variants'].setdefault('business', {})
        for state_name, spec in state_definitions.items():
            # record that this element has a variant for that business state
            el_copy['__variants']['business'][state_name] = spec.get('overrides', {}) if isinstance(spec, dict) else {}
        new_elements.append(el_copy)
    transformed['elements'] = new_elements
    transformed['__injected_states'] = list(state_definitions.keys())
    return transformed


# Lightweight helper to build a sample flow preview payload
def _apply_extreme_mode(component: Dict[str, Any]) -> Dict[str, Any]:
    """Return a copy of component with extreme data injected for stress testing.

    Replaces short texts with very long strings and small numbers with huge values to simulate overflow.
    This is intentionally simple for PoC.
    """
    comp = dict(component)
    elements = comp.get('elements', [])
    new_elements = []
    for el in elements:
        copy = dict(el)
        text = str(copy.get('text', ''))
        # replace with long token
        if text:
            copy['text'] = text + ' ' + ('_LONGTEXT_' * 20)
        # numeric extreme
        if copy.get('type') in ('number', 'metric') or re.search(r"\d", str(copy.get('text',''))):
            copy['text'] = '9999999999.99'
        new_elements.append(copy)
    comp['elements'] = new_elements
    return comp


def build_preview_payload(boards: List[Dict[str, Any]], state_definitions: Dict[str, Any], preview_options: Dict[str, Any] = None) -> Dict[str, Any]:
    """Build preview payload.

    preview_options (optional): {
      'extreme': bool,
      'viewports': ['2560','1440','390']
    }

    Returns flows and transformed samples. If viewports provided, returns 'matrix' mapping viewport->sample.
    """
    flows = extract_flows_from_boards(boards)
    preview_options = preview_options or {}
    extreme = bool(preview_options.get('extreme'))
    viewports = preview_options.get('viewports') or []

    # base sample (use first board as placeholder)
    sample_tree = boards[0] if boards else {'id': 'empty', 'elements': []}

    # transformed sample for default viewport
    transformed = inject_ui_and_business_states(sample_tree, state_definitions)

    result: Dict[str, Any] = {'flows': flows, 'transformed_sample': transformed}

    # matrix mode: produce per-viewport transformed samples (conceptual; real responsive rendering is frontend)
    if viewports:
        matrix: Dict[str, Dict[str, Any]] = {}
        for vp in viewports:
            # apply extreme modifications first if requested
            comp = sample_tree
            if extreme:
                comp = _apply_extreme_mode(sample_tree)
            # annotate with viewport hint so frontend can simulate css constraints
            comp_v = dict(comp)
            comp_v['__viewport'] = vp
            matrix[vp] = inject_ui_and_business_states(comp_v, state_definitions)
        result['matrix'] = matrix

    # also return an 'extreme_sample' for quick inspection
    if extreme:
        extreme_sample = inject_ui_and_business_states(_apply_extreme_mode(sample_tree), state_definitions)
        result['extreme_sample'] = extreme_sample

    return result
