"""Simple runner for prototype_generator unit checks without pytest dependency.

Exit code 0 on success, 1 on failure. Prints failures.
"""
import sys
from src.prototype_generator import extract_flows_from_boards, inject_ui_and_business_states


def fail(msg: str):
    print("FAIL:", msg)
    sys.exit(1)


def test_extract_flows_title_match():
    boards = [
        {'id': 'a', 'title': 'Dashboard', 'elements': [{'type': 'button', 'text': 'Go to Alert Configuration'}]},
        {'id': 'b', 'title': 'Alert Configuration', 'elements': []},
    ]
    flows = extract_flows_from_boards(boards)
    if not any(f['from'] == 'a' and f['to'] == 'b' for f in flows):
        fail('title match flow not found')


def test_extract_flows_keyword_overlap_and_params():
    boards = [
        {'id': 'a', 'title': 'Services', 'elements': [{'type': 'button', 'text': 'Show last 30 days for node: node-alpha'}]},
        {'id': 'b', 'title': 'Service Details', 'elements': []},
    ]
    flows = extract_flows_from_boards(boards)
    if not any(f['from'] == 'a' and f['to'] == 'b' and ('range' in f['params'] or 'node' in f['params']) for f in flows):
        fail('keyword overlap/params not inferred')


def test_inject_ui_and_business_states_variants():
    tree = {'id': 'a', 'elements': [{'type': 'button', 'text': 'View Logs'}]}
    states = {'Normal': {'overrides': {'color': 'green'}}, 'Critical': {'overrides': {'color': 'red'}}}
    transformed = inject_ui_and_business_states(tree, states)
    if '__injected_states' not in transformed:
        fail('__injected_states missing')
    if 'elements' not in transformed:
        fail('elements missing')
    el = transformed['elements'][0]
    if 'business' not in el.get('__variants', {}):
        fail('business variants missing')
    if 'Normal' not in el['__variants']['business'] or 'Critical' not in el['__variants']['business']:
        fail('expected business states not present')


if __name__ == '__main__':
    test_extract_flows_title_match()
    test_extract_flows_keyword_overlap_and_params()
    test_inject_ui_and_business_states_variants()
    print('All prototype_generator checks passed')
    sys.exit(0)
