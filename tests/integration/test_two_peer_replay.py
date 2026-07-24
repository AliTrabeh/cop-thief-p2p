"""Integration test — TEST-006 (replay/tamper-detection half, split out of
test_two_peer_game.py to keep each file under 150 lines): the full game log
produced by two real Orchestrators independently verifies, and a
hand-tampered copy of that same real log is correctly flagged.
"""

from __future__ import annotations

import asyncio

from _two_peer_helpers import run_full_game

from police_thief.gui.replay_viewer import replay


def test_full_game_log_is_verified_ok_after_the_mutual_audit():
    police, thief = asyncio.run(run_full_game())

    police_log = police.export_log()
    thief_log = thief.export_log()
    assert police_log == thief_log  # both sides independently agree on the full record
    assert replay(police_log) == "Verified OK"


def test_full_game_log_is_flagged_tampered_after_the_fact():
    police, _thief = asyncio.run(run_full_game())
    log = police.export_log()
    assert log, "expected at least one turn to have been played"
    log[0]["move"] = "MOVE:S" if log[0]["move"] != "MOVE:S" else "MOVE:N"
    assert replay(log) == "TAMPERED"
