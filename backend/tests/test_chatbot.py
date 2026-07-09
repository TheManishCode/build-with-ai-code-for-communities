"""Chatbot orchestration tests. Live LLM calls aren't exercised here (see the module's
own docstring on provider order) -- these confirm the graceful-degradation contract:
handle_turn never raises, and falls back to a plain apology when no provider is
available, the same "verify before shipping, degrade rather than crash" posture as
app.services.explain.
"""

from unittest.mock import patch

from app.core.config import settings
from app.services.chatbot import FALLBACK_REPLY, handle_turn


def test_handle_turn_falls_back_when_no_provider_configured(db):
    with patch.object(settings, "anthropic_api_key", None), patch.object(settings, "nvidia_nim_api_key", None):
        result = handle_turn(db, [{"role": "user", "content": "What's happening in Chikkur?"}])
    assert result.reply == FALLBACK_REPLY
    assert result.sources == []


def test_claude_turn_degrades_to_none_on_api_error_rather_than_raising(db):
    """_try_claude_turn's own try/except is what handle_turn relies on to never raise --
    exercised here with a real (invalid) key against the live Anthropic API, same
    "verified against the live API, not just mocked" posture as test_explain.py."""
    with patch.object(settings, "anthropic_api_key", "sk-ant-invalid-test-key"):
        from app.services.chatbot import _try_claude_turn

        result = _try_claude_turn(db, [{"role": "user", "content": "hello"}])
    assert result is None
