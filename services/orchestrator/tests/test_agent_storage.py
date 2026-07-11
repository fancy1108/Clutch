"""Tests for agent_storage.save_agents validation (#54)."""

from __future__ import annotations

import pytest

from src.agent_storage import (
    AgentValidationError,
    BUILTIN_AGENT_ID,
    list_agents,
    save_agents,
)


def _minimal_user_agent(**overrides):
    base = {
        "id": "user-agent-1",
        "name": "Test Agent",
        "description": "",
        "markdownDoc": "",
        "avatar": "",
        "deliverables": [],
        "mcpTools": [],
        "mcpServerIds": [],
        "skills": [],
        "agentType": "claude-cli",
    }
    base.update(overrides)
    return base


def test_save_agents_accepts_known_agent_type() -> None:
    save_agents([_minimal_user_agent(agentType="zcode-cli")])
    agents = list_agents()
    saved = [a for a in agents if a.get("id") == "user-agent-1"]
    assert len(saved) == 1
    assert saved[0]["agentType"] == "zcode-cli"


def test_save_agents_accepts_legacy_alias() -> None:
    save_agents([_minimal_user_agent(agentType="ZCode CLI")])
    agents = list_agents()
    saved = [a for a in agents if a.get("id") == "user-agent-1"]
    assert saved[0]["agentType"] == "zcode-cli"


def test_save_agents_accepts_empty_agent_type_defaulting_to_clutch() -> None:
    # An agent record without an agentType field is legal — migrate_agent_record
    # will fall it back to 'clutch'.
    save_agents([_minimal_user_agent(agentType="")])
    agents = list_agents()
    saved = [a for a in agents if a.get("id") == "user-agent-1"]
    assert saved[0]["agentType"] == "clutch"


def test_save_agents_rejects_unknown_agent_type() -> None:
    """Prior behavior (#54): typo like 'zcod' silently became 'clutch' via
    migrate_agent_record, so the persisted agent quietly routed to the
    built-in engine instead of the CLI the user intended. Now we refuse the
    write.

    Note we use 'zcod' rather than 'zcode' — the latter is a documented legacy
    alias that maps to 'zcode-cli' and is intentionally accepted.
    """
    with pytest.raises(AgentValidationError, match="invalid agentType"):
        save_agents([_minimal_user_agent(agentType="zcod")])


def test_save_agents_rejects_typo_with_id_in_message() -> None:
    with pytest.raises(AgentValidationError, match="'user-agent-1'"):
        save_agents([_minimal_user_agent(id="user-agent-1", agentType="totally-fake-cli")])


def test_save_agents_ignores_builtin_agent_type_validation() -> None:
    """The Clutch built-in agent always has agentType='clutch' enforced by
    _effective_builtin(); user attempts to submit a mismatched value should
    not error out (the value is overridden anyway)."""
    builtin_override = {"id": BUILTIN_AGENT_ID, "name": "Clutch Agent", "agentType": "made-up"}
    # Should not raise — builtin is filtered out of user validation.
    save_agents([builtin_override])
    agents = list_agents()
    saved = [a for a in agents if a.get("id") == BUILTIN_AGENT_ID]
    assert saved[0]["agentType"] == "clutch"


def test_save_agents_rejects_first_bad_agent_in_batch() -> None:
    """Validation happens before any write; a bad agent in the batch should
    not leave the storage in a partially-updated state."""
    with pytest.raises(AgentValidationError):
        save_agents([
            _minimal_user_agent(id="good-1", agentType="claude-cli"),
            _minimal_user_agent(id="bad-1", agentType="not-a-cli"),
        ])
    # Neither should have been written.
    agents = list_agents()
    assert not any(a.get("id") in {"good-1", "bad-1"} for a in agents)
