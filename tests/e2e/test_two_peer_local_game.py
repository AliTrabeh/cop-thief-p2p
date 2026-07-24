"""End-to-end test — TEST-007: spawns two real OS subprocesses
(``python -m police_thief peer --role police/thief``) against the project's
real ``config/`` files, on localhost, and verifies they complete a full game,
agree on the outcome, produce all four JSON deliverables, and that the
Replay Viewer confirms ``Verified OK`` on the resulting log.

This is slower than the in-process integration tests (real process
start-up, real HTTP sockets) and is the same scenario demonstrated live via
``scripts/run_demo.ps1``.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = PROJECT_ROOT / "config"


@pytest.mark.e2e
def test_two_real_peer_processes_complete_a_game(tmp_path: Path):
    if not (CONFIG_DIR / "game.json").exists():
        pytest.skip("config/game.json not present in this checkout")

    game_id = "e2e-pytest"
    police_out = tmp_path / "police"
    thief_out = tmp_path / "thief"

    def _spawn(role: str, output_dir: Path, log_file) -> subprocess.Popen[bytes]:
        return subprocess.Popen(  # noqa: S603 - fixed, non-shell argv, no user input
            [
                sys.executable,
                "-m",
                "police_thief",
                "peer",
                "--role",
                role,
                "--config-dir",
                str(CONFIG_DIR),
                "--game-id",
                game_id,
                "--output-dir",
                str(output_dir),
                "--max-wait-seconds",
                "30",
            ],
            cwd=PROJECT_ROOT,
            stdout=log_file,
            stderr=subprocess.STDOUT,
        )

    # Redirect each subprocess's output to its own file rather than a PIPE:
    # with two concurrent children, sequentially calling .communicate() on
    # one blocks its reader while the other's own PIPE buffer can fill up
    # and make it block on write() -- a classic cross-process deadlock this
    # harness hit in development. Files sidestep it entirely.
    police_log_path = tmp_path / "police_stdout.log"
    thief_log_path = tmp_path / "thief_stdout.log"
    with police_log_path.open("wb") as police_log, thief_log_path.open("wb") as thief_log:
        police_proc = _spawn("police", police_out, police_log)
        thief_proc = _spawn("thief", thief_out, thief_log)
        try:
            # Real HTTP transport opens a fresh MCP client session per
            # message (init/notify/SSE/close) rather than reusing a
            # connection, unlike the fast in-process integration tests --
            # each turn can take several seconds under load, so this needs
            # real headroom, not the in-process tests' sub-second budget.
            police_proc.wait(timeout=240)
            thief_proc.wait(timeout=240)
        finally:
            for proc in (police_proc, thief_proc):
                if proc.poll() is None:
                    proc.kill()

    police_stdout = police_log_path.read_text(encoding="utf-8", errors="replace")
    thief_stdout = thief_log_path.read_text(encoding="utf-8", errors="replace")
    assert police_proc.returncode in (0, 2), f"police stdout:\n{police_stdout}"
    assert thief_proc.returncode in (0, 2), f"thief stdout:\n{thief_stdout}"

    police_result = json.loads((police_out / f"result_{game_id}.json").read_text(encoding="utf-8"))
    thief_result = json.loads((thief_out / f"result_{game_id}.json").read_text(encoding="utf-8"))
    assert police_result["outcome"] == thief_result["outcome"]
    assert police_result["moves_made"] == thief_result["moves_made"]

    for output_dir in (police_out, thief_out):
        for name in ("declaration", "config", "log", "result"):
            matches = list(output_dir.glob(f"{name}_{game_id}*.json"))
            assert matches, f"missing {name} deliverable in {output_dir}"

    replay_proc = subprocess.run(  # noqa: S603
        [
            sys.executable,
            "-m",
            "police_thief",
            "replay",
            "--log",
            str(next((police_out).glob(f"log_{game_id}*.json"))),
        ],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert "Verified OK" in replay_proc.stdout, replay_proc.stdout
    assert replay_proc.returncode == 0
