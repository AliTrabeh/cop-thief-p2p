"""Structured logging setup (NFR-004): configurable verbosity, and a
best-effort redaction filter so secrets/pre-reveal nonces never end up in
log output even if a caller accidentally logs a raw payload.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Iterable

_DEFAULT_REDACT_PATTERNS: tuple[str, ...] = (
    r"credentials\.json",
    r"token\.json",
    r'"nonce"\s*:\s*"[0-9a-f]+"',
)


class RedactionFilter(logging.Filter):
    """Replaces any pattern match in a log record's message with ``***``."""

    def __init__(self, patterns: Iterable[str] = _DEFAULT_REDACT_PATTERNS) -> None:
        super().__init__()
        self._patterns = [re.compile(p, re.IGNORECASE) for p in patterns]

    def filter(self, record: logging.LogRecord) -> bool:
        message = record.getMessage()
        for pattern in self._patterns:
            message = pattern.sub("***REDACTED***", message)
        record.msg = message
        record.args = ()
        return True


def configure_logging(level: str = "INFO") -> None:
    """Call once at process startup (CLI entry point)."""
    root = logging.getLogger("police_thief")
    root.setLevel(level.upper())
    if root.handlers:
        return  # already configured (e.g. re-entered in tests)
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    handler.addFilter(RedactionFilter())
    root.addHandler(handler)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(f"police_thief.{name}")
