from src.prototype_generator import extract_flows_from_boards, inject_ui_and_business_states


def test_extract_flows_title_match():
    boards = [
        {'id': 'a', 'title': 'Dashboard', 'elements': [{'type': 'button', 'text': 'Go to Alert Configuration'}]},
        {'id': 'b', 'title': 'Alert Configuration', 'elements': []},
    ]
    flows = extract_flows_from_boards(boards)
    assert any(f['from'] == 'a' and f['to'] == 'b' for f in flows)


def test_extract_flows_keyword_overlap_and_params():
    boards = [
        {'id': 'a', 'title': 'Services', 'elements': [{'type': 'button', 'text': 'Show last 30 days for node: node-alpha'}]},
        {'id': 'b', 'title': 'Service Details', 'elements': []},
    ]
    flows = extract_flows_from_boards(boards)
    # should infer a param 'range' and 'node' and create a suggestion
    assert any(f['from'] == 'a' and f['to'] == 'b' and ('range' in f['params'] or 'node' in f['params']) for f in flows)


def test_inject_ui_and_business_states_variants():
    tree = {'id': 'a', 'elements': [{'type': 'button', 'text': 'View Logs'}]}
    states = {'Normal': {'overrides': {'color': 'green'}}, 'Critical': {'overrides': {'color': 'red'}}}
    transformed = inject_ui_and_business_states(tree, states)
    assert '__injected_states' in transformed
    assert 'elements' in transformed
    el = transformed['elements'][0]
    assert ' __variants' not in el  # ensure we didn't add a stray key
    assert ' __injected_states' not in el
    assert ' __variants' not in el
    # correct variant keys
    assert 'business' in el['__variants']
    assert 'Normal' in el['__variants']['business']
    assert 'Critical' in el['__variants']['business']
