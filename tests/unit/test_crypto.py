"""Unit tests for domain/crypto.py — TEST-003, FR-040..045."""

from __future__ import annotations

import json

from police_thief.domain.crypto import commit, generate_nonce, hash_state, verify


def test_commit_then_verify_round_trip():
    h_commit, nonce = commit(state="s0", move="N", intent="truth")
    assert verify(state="s0", move="N", intent="truth", nonce=nonce, h_commit=h_commit)


def test_verify_fails_on_tampered_move():
    h_commit, nonce = commit(state="s0", move="N", intent="truth")
    assert not verify(state="s0", move="S", intent="truth", nonce=nonce, h_commit=h_commit)


def test_verify_fails_on_tampered_state():
    h_commit, nonce = commit(state="s0", move="N", intent="truth")
    assert not verify(state="s1", move="N", intent="truth", nonce=nonce, h_commit=h_commit)


def test_verify_fails_on_tampered_intent():
    h_commit, nonce = commit(state="s0", move="N", intent="truth")
    assert not verify(state="s0", move="N", intent="lie", nonce=nonce, h_commit=h_commit)


def test_verify_fails_on_tampered_nonce():
    h_commit, _nonce = commit(state="s0", move="N", intent="truth")
    forged_nonce = generate_nonce()
    assert not verify(state="s0", move="N", intent="truth", nonce=forged_nonce, h_commit=h_commit)


def test_nonce_is_fresh_every_commit():
    _, nonce1 = commit(state="s0", move="N", intent="truth")
    _, nonce2 = commit(state="s0", move="N", intent="truth")
    assert nonce1 != nonce2


def test_nonce_uniqueness_statistical_smoke_test():
    nonces = {generate_nonce() for _ in range(1000)}
    assert len(nonces) == 1000


def test_hash_state_matches_manual_sha256():
    import hashlib

    canonical = json.dumps({"a": 1}, sort_keys=True, separators=(",", ":"))
    expected = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    assert hash_state(canonical) == expected


def test_commit_is_order_independent_key_construction():
    # Both peers must hash byte-identical input regardless of how the caller
    # happened to build up the same logical values (docs/protocol.md §2).
    h1, n1 = commit(state="board-abc", move="STAY", intent="truth")
    payload_manual = json.dumps(
        {"state": "board-abc", "move": "STAY", "intent": "truth", "nonce": n1},
        sort_keys=True,
        separators=(",", ":"),
    )
    import hashlib

    assert h1 == hashlib.sha256(payload_manual.encode("utf-8")).hexdigest()
