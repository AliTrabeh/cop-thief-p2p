"""The banter-provider interface and the zero-cost default implementation,
split out of ``llm_bluff.py`` to keep each file under the project's
150-line-per-file limit. See that module's docstring for the full picture
(why banter exists, why it can never affect protocol/outcome, and which
providers are/aren't implemented).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

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
    falling back internally (see ``banter_ollama.py::OllamaBanterProvider``).
    """

    @abstractmethod
    def generate(self, context: BanterContext) -> str: ...


def truncate_to_word_limit(text: str, max_words: int) -> str:
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
        return truncate_to_word_limit(line, self._hint_max_words)
