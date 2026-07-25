"""Focused unit test for a peer_runtime.py error path that doesn't need a
real two-process game (see tests/e2e/ for the full real-process scenario):
a port collision must fail fast with a clear, actionable error rather than
hanging or surfacing a confusing downstream connection failure (PRD-0582).
"""

from __future__ import annotations

import asyncio
import json
import socket
from pathlib import Path

import pytest

from police_thief.domain.models import Role
from police_thief.peer_runtime import PeerRuntimeError, run_peer

_GAME_JSON: dict[str, object] = {
    "schema_version": "1.2",
    "agreed_between": ["group-a", "group-b"],
    "board_and_agents": {
        "grid_size": 7,
        "num_agents": 2,
        "thief_start": [3, 3],
        "cop_start": [0, 0],
        "axis_origin_corner": "top-left",
        "axis_start_index": 0,
    },
    "movement_and_barriers": {
        "move_set": ["N", "S", "E", "W", "STAY"],
        "max_barriers": 14,
        "max_moves": 35,
        "survival_threshold": 35,
    },
}

_PEER_TOML_TEMPLATE = """
version = "1.10"
[game]
group_name = "Test-Team"
group_id = "testteam"
[network]
my_port = {port}
opponent_url = "http://127.0.0.1:1/mcp"
[email]
recipient = "nobody@example.com"
mode = "draft"
"""


def _write_config(config_dir: Path, port: int) -> None:
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "game.json").write_text(json.dumps(_GAME_JSON), encoding="utf-8")
    role_dir = config_dir / "police"
    role_dir.mkdir(parents=True, exist_ok=True)
    (role_dir / "game.toml").write_text(_PEER_TOML_TEMPLATE.format(port=port), encoding="utf-8")


def test_run_peer_raises_clear_error_on_port_already_in_use(tmp_path: Path) -> None:
    blocker = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    blocker.bind(("0.0.0.0", 0))
    blocker.listen(1)
    port = blocker.getsockname()[1]
    try:
        config_dir = tmp_path / "config"
        _write_config(config_dir, port)
        with pytest.raises(PeerRuntimeError, match="already using it"):
            asyncio.run(
                run_peer(Role.POLICE, config_dir, "port-collision-test", max_wait_seconds=2)
            )
    finally:
        blocker.close()
