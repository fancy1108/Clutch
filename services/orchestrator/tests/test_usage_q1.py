"""Q-USAGE-1 — provider usage preferred; word-count estimate is fallback."""

from __future__ import annotations

from src.chat_messages import (
    _token_patch_turn,
    pop_turn_usage,
    stash_turn_usage,
)
from src.state import initial_state


def test_token_patch_turn_uses_provider_usage() -> None:
    state = initial_state("run_usage_true")
    patch = _token_patch_turn(
        state,
        user_text="hello world",
        assistant_text="a much longer reply that would inflate word-count tokens",
        usage={"prompt_tokens": 12, "completion_tokens": 34, "total_tokens": 46},
        estimated=False,
    )
    assert patch["token_input"] == 12
    assert patch["token_output"] == 34
    assert patch["session_tokens"] == 46
    assert patch["usage_estimated"] is False


def test_token_patch_turn_falls_back_to_word_count() -> None:
    state = initial_state("run_usage_est")
    patch = _token_patch_turn(
        state,
        user_text="one two three",
        assistant_text="four five",
    )
    assert patch["token_input"] == 3
    assert patch["token_output"] == 2
    assert patch["session_tokens"] == 5
    assert patch["usage_estimated"] is True


def test_token_patch_turn_mixed_session_stays_estimated() -> None:
    state = initial_state("run_usage_mix")
    state.update(
        _token_patch_turn(
            state,
            user_text="hi",
            assistant_text="there",
            usage={"input_tokens": 10, "output_tokens": 20},
            estimated=False,
        )
    )
    patch = _token_patch_turn(
        state,
        user_text="again",
        assistant_text="later",
    )
    assert patch["token_input"] == 11
    assert patch["usage_estimated"] is True


def test_stash_and_pop_turn_usage() -> None:
    stash_turn_usage("run_stash", {"input_tokens": 1, "output_tokens": 2}, False)
    usage, estimated = pop_turn_usage("run_stash")
    assert usage == {"input_tokens": 1, "output_tokens": 2}
    assert estimated is False
    assert pop_turn_usage("run_stash") == (None, True)
