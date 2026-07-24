"""The Replay Viewer: loads a finished game log, recomputes every
commitment hash from the now-revealed nonces, and reports ``Verified OK`` or
``TAMPERED`` (FR-071/072, §7.4-7.5).

This is deliberately not a GUI-only feature: :func:`replay` is the same
verification engine the Orchestrator's own end-of-game mutual audit
(FR-045) would use, matching the book's principle that integrity checking
must never be "blind trust of a centrally-issued hash" (§7.4).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TypedDict

from police_thief.domain.crypto import verify


class LogEntryDict(TypedDict):
    turn_number: int
    role: str
    state_hash: str
    move: str
    intent: str
    h_commit: str
    nonce: str | None


class ReplayError(Exception):
    """Raised for a malformed log file — never a bare exception leaking up."""


def verify_step(entry: LogEntryDict) -> str:
    """Recompute the commitment from the visible log fields (§7.5's own
    ``verify_step`` reference code). A missing nonce (never revealed) is
    treated as unverifiable, i.e. ``TAMPERED`` — an incomplete audit trail
    is not evidence of integrity.
    """
    nonce = entry.get("nonce")
    if not nonce:
        return "TAMPERED"
    ok = verify(
        state=entry["state_hash"],
        move=entry["move"],
        intent=entry["intent"],
        nonce=nonce,
        h_commit=entry["h_commit"],
    )
    return "Verified OK" if ok else "TAMPERED"


def replay(log: list[LogEntryDict]) -> str:
    """Walk every recorded step; the whole match is void on the first
    tamper (§7.5's own ``replay`` reference code).
    """
    for entry in log:
        if verify_step(entry) == "TAMPERED":
            return "TAMPERED"
    return "Verified OK"


def load_log(path: Path) -> list[LogEntryDict]:
    if not path.exists():
        raise ReplayError(f"log file not found: {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ReplayError(f"log file is not valid JSON: {path}: {exc}") from exc
    if not isinstance(data, list):
        raise ReplayError(f"log file must contain a JSON array of turn entries: {path}")
    return data


def verify_log_file(path: Path) -> str:
    """CLI/GUI entry point: ``python -m police_thief replay --log <path>``."""
    return replay(load_log(path))
