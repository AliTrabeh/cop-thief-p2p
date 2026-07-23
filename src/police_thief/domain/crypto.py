"""Commit-Reveal cryptographic anti-cheat protocol over SHA-256 (FR-040..045).

``H_commit = SHA256(State ‖ Move ‖ Intent ‖ Nonce)`` using canonical JSON so
both peers hash byte-identical input regardless of local dict/JSON-library
ordering (docs/protocol.md §2-3). No networking here — this module only
computes and checks hashes; the Orchestrator (Part 9) is responsible for
actually sending commit/reveal messages over FastMCP.
"""

from __future__ import annotations

import hashlib
import json
import secrets
from typing import Final

_NONCE_BYTES: Final = 16


def generate_nonce() -> str:
    """A fresh cryptographically-secure nonce (FR-041). Never use ``random``."""
    return secrets.token_hex(_NONCE_BYTES)


def _canonical_payload(state: str, move: str, intent: str, nonce: str) -> bytes:
    """Canonical JSON serialization (docs/protocol.md §2): sorted keys, fixed
    separators, so both peers produce byte-identical input to SHA-256.
    """
    obj = {"state": state, "move": move, "intent": intent, "nonce": nonce}
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")


def commit(state: str, move: str, intent: str) -> tuple[str, str]:
    """Produce ``(h_commit, nonce)`` for a move about to be committed.

    The caller sends only ``h_commit`` at commit time (FR-040/FR-042 step 1)
    and keeps ``nonce`` secret until the Reveal step.
    """
    nonce = generate_nonce()
    payload = _canonical_payload(state, move, intent, nonce)
    h_commit = hashlib.sha256(payload).hexdigest()
    return h_commit, nonce


def verify(state: str, move: str, intent: str, nonce: str, h_commit: str) -> bool:
    """Recompute the commitment hash from revealed data and compare.

    Uses :func:`secrets.compare_digest` (constant-time) rather than ``==``
    (FR-043). Any mismatch means the revealed data does not match what was
    committed — a hard technical disqualification, never a soft warning.
    """
    payload = _canonical_payload(state, move, intent, nonce)
    recomputed = hashlib.sha256(payload).hexdigest()
    return secrets.compare_digest(recomputed, h_commit)


def hash_state(canonical_state_json: str) -> str:
    """Hash a canonical-JSON board-state snapshot, used as the ``State``
    component of a commitment so a move can't be replayed against a
    different turn's state (docs/protocol.md §3).
    """
    return hashlib.sha256(canonical_state_json.encode("utf-8")).hexdigest()
