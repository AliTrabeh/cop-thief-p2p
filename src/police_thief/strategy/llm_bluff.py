"""Bonus: free-text banter/trash-talk generation (FR-061..064, BONUS-002,
docs/assumptions.md A-005).

Per the spec's own recommendation, an LLM -- if configured at all -- is
used only to generate flavor text shown alongside a move, **never** to
decide the move itself; the move is always pure Python
(``strategy/heuristic.py`` or the optional ``strategy/qlearning.py``).
Banter is not part of the commit-reveal protocol (``domain/crypto.py``)
and never affects the committed hash or game outcome -- a failed,
slow, or nonsensical banter call can never cost a game (PRD-0334).

Two providers are implemented, both zero marginal cost (split across sibling
files to keep each under the project's 150-line-per-file limit):

- ``TemplateBanterProvider`` (``banter_base.py``, ``[trash_talk].provider =
  "template"``, the default): canned phrases, fully offline, instant.
- ``OllamaBanterProvider`` (``banter_ollama.py``, ``"ollama"``): a locally
  self-hosted model via Ollama's HTTP API (http://localhost:11434 by
  default) -- no per-token billing, fully offline once the model is pulled.

``"claude_api"``/``"claude_cli"`` are deliberately **not** implemented here.
Enabling a real hosted-LLM API for cosmetic banter is a cost decision for a
human to make explicitly, not something this project defaults to or
silently falls back to -- requesting either raises :class:`NotImplementedError`
immediately rather than pretending to work.
"""

from __future__ import annotations

from police_thief.strategy.banter_base import BanterContext, BanterProvider, TemplateBanterProvider
from police_thief.strategy.banter_ollama import OllamaBanterProvider


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
