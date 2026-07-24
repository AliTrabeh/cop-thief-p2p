"""Unit tests for gui/replay_viewer.py — FR-071/072."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from police_thief.domain.crypto import commit
from police_thief.gui.replay_viewer import (
    ReplayError,
    load_log,
    replay,
    verify_log_file,
    verify_step,
)


def _make_entry(state="s0", move="MOVE:N", intent="truth", turn=0, role="police"):
    h_commit, nonce = commit(state=state, move=move, intent=intent)
    return {
        "turn_number": turn,
        "role": role,
        "state_hash": state,
        "move": move,
        "intent": intent,
        "h_commit": h_commit,
        "nonce": nonce,
    }


def test_verify_step_on_clean_entry_is_verified_ok():
    entry = _make_entry()
    assert verify_step(entry) == "Verified OK"


def test_verify_step_on_tampered_move_is_tampered():
    entry = _make_entry()
    entry["move"] = "MOVE:S"  # tampered after the commitment was made
    assert verify_step(entry) == "TAMPERED"


def test_verify_step_with_missing_nonce_is_tampered():
    entry = _make_entry()
    entry["nonce"] = None
    assert verify_step(entry) == "TAMPERED"


def test_replay_is_verified_ok_for_a_clean_log():
    log = [_make_entry(turn=0), _make_entry(turn=1, move="MOVE:E")]
    assert replay(log) == "Verified OK"


def test_replay_stops_at_first_tamper():
    clean = _make_entry(turn=0)
    tampered = _make_entry(turn=1)
    tampered["state_hash"] = "forged-state"
    log = [clean, tampered, _make_entry(turn=2)]
    assert replay(log) == "TAMPERED"


def test_load_log_missing_file_raises_replay_error(tmp_path: Path):
    with pytest.raises(ReplayError, match="not found"):
        load_log(tmp_path / "nope.json")


def test_load_log_invalid_json_raises_replay_error(tmp_path: Path):
    path = tmp_path / "log.json"
    path.write_text("{not valid json", encoding="utf-8")
    with pytest.raises(ReplayError, match="not valid JSON"):
        load_log(path)


def test_load_log_rejects_non_array_content(tmp_path: Path):
    path = tmp_path / "log.json"
    path.write_text(json.dumps({"not": "an array"}), encoding="utf-8")
    with pytest.raises(ReplayError, match="JSON array"):
        load_log(path)


def test_verify_log_file_round_trips_a_clean_log(tmp_path: Path):
    path = tmp_path / "log.json"
    log = [_make_entry(turn=0), _make_entry(turn=1, move="MOVE:S")]
    path.write_text(json.dumps(log), encoding="utf-8")
    assert verify_log_file(path) == "Verified OK"


def test_verify_log_file_detects_a_tampered_log(tmp_path: Path):
    path = tmp_path / "log.json"
    entry = _make_entry()
    entry["intent"] = "lie"  # tampered after the commitment was made
    path.write_text(json.dumps([entry]), encoding="utf-8")
    assert verify_log_file(path) == "TAMPERED"
