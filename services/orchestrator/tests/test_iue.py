"""IUE (Interaction Understanding Engine) unit tests."""
from src.iue import InteractionUnderstandingEngine
from src.iue.models import ElementRole, FlowSuggestion, ApprovalStatus


# Test boards: simulating a simple two-screen app
_DASHBOARD = {
    "id": "dashboard",
    "title": "Dashboard",
    "elements": [
        {"type": "button", "text": "Go to Settings"},
        {"type": "button", "text": "Create New Project"},
        {"type": "a", "text": "View Details"},
        {"type": "button", "text": "Submit"},
        {"type": "button", "text": "Cancel"},
        {"type": "button", "text": "Next"},
        {"type": "button", "text": "Search"},
    ],
}
_SETTINGS = {
    "id": "settings",
    "title": "Settings",
    "elements": [
        {"type": "button", "text": "Save"},
        {"type": "button", "text": "Delete Account"},
        {"type": "button", "text": "Back"},
    ],
}
_PROJECTS = {
    "id": "projects",
    "title": "Projects",
    "elements": [
        {"type": "button", "text": "New Project"},
        {"type": "button", "text": "Edit"},
    ],
}

BOARDS = [_DASHBOARD, _SETTINGS, _PROJECTS]


def test_iue_engine_analyze_returns_suggestions():
    """Full pipeline should return non-empty FlowSuggestion list."""
    engine = InteractionUnderstandingEngine()
    suggestions = engine.analyze(BOARDS)
    assert isinstance(suggestions, list)
    assert len(suggestions) > 0
    assert all(isinstance(s, FlowSuggestion) for s in suggestions)
    # Every suggestion should have confidence and reasoning
    for s in suggestions:
        assert s.confidence > 0.0
        assert s.confidence <= 1.0
        assert len(s.reasoning) > 0
        assert s.status == ApprovalStatus.PENDING


def test_iue_analyze_to_dicts_backward_compatible():
    """analyze_to_dicts should return dicts with from/to/reason (backward compat)."""
    engine = InteractionUnderstandingEngine()
    flows = engine.analyze_to_dicts(BOARDS)
    assert len(flows) > 0
    for f in flows:
        assert "from" in f
        assert "to" in f
        assert "reason" in f
        assert "confidence" in f
        assert "source_element_role" in f
        assert "status" in f


def test_iue_stage2_intent_classification():
    """Stage 2 should classify buttons with correct ElementRole."""
    engine = InteractionUnderstandingEngine()
    # Run stage 1 + stage 2 manually via the default handlers
    from src.iue.engine import default_stage1_candidates, default_stage2_classify
    candidates = default_stage1_candidates(BOARDS)
    classified = default_stage2_classify(candidates)

    # "Submit" button → SUBMIT_BUTTON
    submit = [c for c in classified if c.text == "Submit"]
    assert len(submit) == 1
    assert submit[0].role == ElementRole.SUBMIT_BUTTON
    assert submit[0].role_confidence >= 0.9

    # "Cancel" button → CANCEL_BUTTON
    cancel = [c for c in classified if c.text == "Cancel"]
    assert len(cancel) == 1
    assert cancel[0].role == ElementRole.CANCEL_BUTTON

    # "Search" button → SEARCH_BUTTON
    search = [c for c in classified if c.text == "Search"]
    assert len(search) == 1
    assert search[0].role == ElementRole.SEARCH_BUTTON

    # "Next" button → PAGINATION_NEXT
    next_btn = [c for c in classified if c.text == "Next"]
    assert len(next_btn) == 1
    assert next_btn[0].role == ElementRole.PAGINATION_NEXT

    # "Go to Settings" button → falls to ACTION_BUTTON (settings ≠ edit keyword)
    settings_btn = [c for c in classified if c.text == "Go to Settings"]
    assert len(settings_btn) == 1
    assert settings_btn[0].role in (ElementRole.ACTION_BUTTON, ElementRole.NAV_LINK)


def test_iue_stage4_confidence_scoring():
    """Stage 4 should score matches by match method."""
    from src.iue.engine import default_stage4_score
    from src.iue.models import TargetMatch

    matches = [
        TargetMatch(source_board_id="a", target_board_id="b", match_method="button_text_exact"),
        TargetMatch(source_board_id="a", target_board_id="c", match_method="keyword_overlap", overlap_tokens=["dashboard", "home", "index"]),
        TargetMatch(source_board_id="a", target_board_id="d", match_method="action_heuristic"),
    ]
    scored = default_stage4_score(matches)
    assert scored[0].confidence >= 0.9  # exact match should be first & high
    assert scored[1].confidence >= 0.7  # keyword_overlap with >=3 tokens gets +0.15
    assert scored[2].confidence <= 0.5  # action_heuristic is lowest base
    # Should be sorted descending by confidence
    assert scored[0].confidence >= scored[1].confidence >= scored[2].confidence


def test_iue_empty_boards():
    """Empty boards should return empty suggestion list."""
    engine = InteractionUnderstandingEngine()
    assert engine.analyze([]) == []
    assert engine.analyze_to_dicts([]) == []


def test_iue_role_intent_login_to_dashboard():
    """Login page 'Sign In' button should infer flow to Dashboard via role_intent."""
    engine = InteractionUnderstandingEngine()
    boards = [
        {"id": "login", "title": "Login", "elements": [
            {"type": "button", "text": "Sign In"},
        ]},
        {"id": "dashboard", "title": "Dashboard", "elements": []},
    ]
    flows = engine.analyze_to_dicts(boards)
    login_flows = [f for f in flows if f["from"] == "login"]
    assert len(login_flows) >= 1  # Sign In should have at least one suggestion
    sign_in_flow = login_flows[0]
    assert sign_in_flow["to"] == "dashboard"
    assert sign_in_flow["source_element_role"] == "SubmitButton"
    assert 0.30 <= sign_in_flow["confidence"] <= 0.40  # role_intent base
    assert "提交" in sign_in_flow["reason"] or "登录" in sign_in_flow["reason"]
    assert "Dashboard" in sign_in_flow["reason"]
