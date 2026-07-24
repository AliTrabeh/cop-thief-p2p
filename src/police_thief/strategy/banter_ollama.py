"""The local/self-hosted Ollama banter provider, split out of ``llm_bluff.py``
to keep each file under the project's 150-line-per-file limit.
"""

from __future__ import annotations

import httpx

from police_thief.strategy.banter_base import BanterContext, BanterProvider, TemplateBanterProvider
from police_thief.strategy.banter_base import truncate_to_word_limit as _truncate


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
            return _truncate(text, self._hint_max_words)
        except (httpx.HTTPError, ValueError, KeyError):
            return self._fallback.generate(context)
        finally:
            if owns_client:
                client.close()
