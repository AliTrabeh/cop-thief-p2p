"""Unit tests for strategy/llm_bluff.py — FR-061..064, BONUS-002.

Ollama's HTTP API is faked via an injected httpx.Client-like stub; no real
Ollama install or network access is used, matching this project's pattern
for infra/tunnel.py and infra/gmail_report.py.
"""

from __future__ import annotations

import httpx
import pytest

from police_thief.domain.models import Role
from police_thief.strategy.llm_bluff import (
    BanterContext,
    OllamaBanterProvider,
    TemplateBanterProvider,
    build_banter_provider,
)


def test_template_provider_returns_role_appropriate_text() -> None:
    provider = TemplateBanterProvider()
    police_line = provider.generate(BanterContext(role=Role.POLICE, turn_number=0))
    thief_line = provider.generate(BanterContext(role=Role.THIEF, turn_number=0))
    assert police_line != thief_line
    assert police_line and thief_line


def test_template_provider_is_deterministic_for_the_same_turn() -> None:
    provider = TemplateBanterProvider()
    context = BanterContext(role=Role.POLICE, turn_number=3)
    assert provider.generate(context) == provider.generate(context)


def test_template_provider_respects_hint_max_words() -> None:
    provider = TemplateBanterProvider(hint_max_words=2)
    text = provider.generate(BanterContext(role=Role.POLICE, turn_number=0))
    assert len(text.split()) <= 2


def test_template_provider_never_raises_across_many_turns() -> None:
    provider = TemplateBanterProvider()
    for turn in range(50):
        for role in (Role.POLICE, Role.THIEF):
            text = provider.generate(BanterContext(role=role, turn_number=turn))
            assert isinstance(text, str) and text


class _FakeOllamaTransport(httpx.BaseTransport):
    def __init__(self, response_text: str | None, *, status_code: int = 200) -> None:
        self._response_text = response_text
        self._status_code = status_code

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        if self._response_text is None:
            raise httpx.ConnectError("connection refused", request=request)
        return httpx.Response(
            self._status_code, json={"response": self._response_text}, request=request
        )


def test_ollama_provider_returns_the_models_response() -> None:
    client = httpx.Client(transport=_FakeOllamaTransport("On my way to catch you."))
    provider = OllamaBanterProvider(model="llama3.2", client=client)
    text = provider.generate(BanterContext(role=Role.POLICE, turn_number=0))
    assert text == "On my way to catch you."


def test_ollama_provider_truncates_to_hint_max_words() -> None:
    client = httpx.Client(transport=_FakeOllamaTransport("one two three four five six seven"))
    provider = OllamaBanterProvider(model="llama3.2", hint_max_words=3, client=client)
    text = provider.generate(BanterContext(role=Role.POLICE, turn_number=0))
    assert text == "one two three"


def test_ollama_provider_falls_back_to_template_on_connection_error() -> None:
    client = httpx.Client(transport=_FakeOllamaTransport(None))
    provider = OllamaBanterProvider(model="llama3.2", client=client)
    text = provider.generate(BanterContext(role=Role.THIEF, turn_number=0))
    assert text  # got the template fallback, not an exception


def test_ollama_provider_falls_back_to_template_on_http_error_status() -> None:
    client = httpx.Client(transport=_FakeOllamaTransport("ignored", status_code=500))
    provider = OllamaBanterProvider(model="llama3.2", client=client)
    text = provider.generate(BanterContext(role=Role.THIEF, turn_number=0))
    assert text


def test_ollama_provider_falls_back_to_template_on_empty_response() -> None:
    client = httpx.Client(transport=_FakeOllamaTransport(""))
    provider = OllamaBanterProvider(model="llama3.2", client=client)
    text = provider.generate(BanterContext(role=Role.THIEF, turn_number=0))
    assert text  # non-empty fallback line, not a blank string


def test_build_banter_provider_template() -> None:
    provider = build_banter_provider(
        "template", model="template", hint_max_words=15, step_deadline_seconds=30.0
    )
    assert isinstance(provider, TemplateBanterProvider)


def test_build_banter_provider_ollama() -> None:
    provider = build_banter_provider(
        "ollama", model="llama3.2", hint_max_words=15, step_deadline_seconds=30.0
    )
    assert isinstance(provider, OllamaBanterProvider)


def test_build_banter_provider_rejects_claude_api_without_silently_falling_back() -> None:
    with pytest.raises(NotImplementedError, match="A-005"):
        build_banter_provider(
            "claude_api", model="claude-sonnet-5", hint_max_words=15, step_deadline_seconds=30.0
        )


def test_build_banter_provider_rejects_claude_cli() -> None:
    with pytest.raises(NotImplementedError):
        build_banter_provider(
            "claude_cli", model="claude-sonnet-5", hint_max_words=15, step_deadline_seconds=30.0
        )


def test_build_banter_provider_rejects_unknown_provider() -> None:
    with pytest.raises(ValueError, match="unknown"):
        build_banter_provider(
            "not-a-real-provider", model="x", hint_max_words=15, step_deadline_seconds=30.0
        )
