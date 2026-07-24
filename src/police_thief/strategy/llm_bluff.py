"""Bonus: free-text banter/trash-talk generation (FR-061..064, BONUS-002,
docs/assumptions.md A-005).

Per the spec's own recommendation, an LLM -- if configured at all -- is
used only to generate flavor text shown alongside a move, **never** to
decide the move itself; the move is always pure Python
(``strategy/heuristic.py`` or the optional ``strategy/qlearning.py``).
Banter is not part of the commit-reveal protocol (``domain/crypto.py``)
and never affects the committed hash or game outcome -- a failed,
slow, or nonsensical banter call can never cost a game (PRD-0334).

Two providers are implemented, both zero marginal cost:

- ``TemplateBanterProvider`` (``[trash_talk].provider = "template"``, the
  default): canned phrases, fully offline, instant.
- ``OllamaBanterProvider`` (``"ollama"``): a locally self-hosted model via
  Ollama's HTTP API (http://localhost:11434 by default) -- no per-token
  billing, fully offline once the model is pulled.

``"claude_api"``/``"claude_cli"`` are deliberately **not** implemented here.
Enabling a real hosted-LLM API for cosmetic banter is a cost decision for a
human to make explicitly, not something this project defaults to or
silently falls back to -- requesting either raises :class:`NotImplementedError`
immediately rather than pretending to work.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

import httpx

from police_thief.domain.models import Role

_POLICE_LINES = [
    "Closing in. Nowhere left to run.",
    "I can smell your trail from here.",
    "The net is tightening.",
    "Every move you make leads me closer.",
    "This ends soon, and not in your favor.",
]
_THIEF_LINES = [
    "You'll have to do better than that, officer.",
    "Catch me if you can.",
    "Still just chasing shadows.",
    "I was here. Now I'm not.",
    "Slow and steady loses this race.",
]


@dataclass(frozen=True)
class BanterContext:
    """Everything a provider is allowed to use to generate flavor text --
    deliberately as small as the strategy layer's own ``BeliefView``
    (never the opponent's true position, never the unrevealed move)."""

    role: Role
    turn_number: int


class BanterProvider(ABC):
    """A provider must never raise -- callers treat any exception as a bug
    in the provider, not a normal degrade-to-silence path; implementations
    are responsible for catching their own transport/timeout errors and
    falling back internally (see :class:`OllamaBanterProvider`)."""

    @abstractmethod
    def generate(self, context: BanterContext) -> str: ...


def _truncate_to_word_limit(text: str, max_words: int) -> str:
    words = text.split()
    if len(words) <= max_words:
        return text
    return " ".join(words[:max_words])


class TemplateBanterProvider(BanterProvider):
    """Zero-cost, fully offline, deterministic: a canned line chosen by
    turn parity (no external call, no nondeterminism -- reproducible for
    tests without a fake clock or fake RNG)."""

    def __init__(self, *, hint_max_words: int = 15) -> None:
        self._hint_max_words = hint_max_words

    def generate(self, context: BanterContext) -> str:
        lines = _POLICE_LINES if context.role is Role.POLICE else _THIEF_LINES
        line = lines[context.turn_number % len(lines)]
        return _truncate_to_word_limit(line, self._hint_max_words)


class OllamaBanterProvider(BanterProvider):
    """Local, self-hosted LLM via Ollama's HTTP API. Falls back to a
    template line on *any* error (Ollama not running, model not pulled,
    timeout, malformed response) -- banter must never crash or stall a
    turn (PRD-0334).
    """

    def __init__(
        self,
        *,
        model: str,
        base_url: str = "http://localhost:11434",
        hint_max_words: int = 15,
        timeout_seconds: float = 5.0,
        client: httpx.Client | None = None,
    ) -> None:
        self._model = model
        self._base_url = base_url.rstrip("/")
        self._hint_max_words = hint_max_words
        self._timeout_seconds = timeout_seconds
        self._client = client
        self._fallback = TemplateBanterProvider(hint_max_words=hint_max_words)

    def generate(self, context: BanterContext) -> str:
        prompt = (
            f"You are the {context.role.value} in a game of cops and robbers. "
            f"In {self._hint_max_words} words or fewer, say something in character. "
            "Never reveal your exact position or your next move."
        )
        owns_client = self._client is None
        client = self._client or httpx.Client(timeout=self._timeout_seconds)
        try:
            response = client.post(
                f"{self._base_url}/api/generate",
                json={"model": self._model, "prompt": prompt, "stream": False},
            )
            response.raise_for_status()
            data = response.json()
            text = str(data.get("response", "")).strip()
            if not text:
                return self._fallback.generate(context)
            return _truncate_to_word_limit(text, self._hint_max_words)
        except (httpx.HTTPError, ValueError, KeyError):
            return self._fallback.generate(context)
        finally:
            if owns_client:
                client.close()


def build_banter_provider(
    provider_name: str, *, model: str, hint_max_words: int, step_deadline_seconds: float
) -> BanterProvider:
    """Resolve ``[trash_talk].provider``/``[llm].model`` config into a
    concrete provider. Raises for anything not implemented rather than
    silently substituting a different provider (a misconfiguration should
    be visible at startup, not discovered as unexpectedly-missing banter).
    """
    if provider_name == "template":
        return TemplateBanterProvider(hint_max_words=hint_max_words)
    if provider_name == "ollama":
        return OllamaBanterProvider(
            model=model,
            hint_max_words=hint_max_words,
            timeout_seconds=step_deadline_seconds,
        )
    if provider_name in ("claude_api", "claude_cli"):
        raise NotImplementedError(
            f"trash_talk.provider={provider_name!r} is not implemented in this project "
            "(docs/assumptions.md A-005: no default spend on a paid LLM API for cosmetic "
            "banter); use 'template' or 'ollama', or implement your own BanterProvider."
        )
    raise ValueError(f"unknown trash_talk.provider: {provider_name!r}")


__all__ = [
    "BanterContext",
    "BanterProvider",
    "OllamaBanterProvider",
    "TemplateBanterProvider",
    "build_banter_provider",
]
