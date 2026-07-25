"""File-writing functions for the four mandatory per-match JSON deliverables
(split out of ``reporting.py`` to keep each file under 150 lines and to keep
the dependency one-directional).

``write_declaration`` and ``write_post_game_deliverables`` are called
separately, at different points in the real peer lifecycle
(``peer_startup.py`` calls the former before the turn loop starts;
``peer_deliverables.py`` calls the latter after it ends) so the declaration
genuinely precedes the game, per book §5.5 and Appendix E item 24.
``write_match_deliverables`` is a convenience wrapper over both, for tests
and simple one-shot use.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from police_thief.config import PeerConfig
from police_thief.infra.reporting import build_config_snapshot, build_declaration, build_result
from police_thief.orchestrator import Orchestrator


def write_declaration(
    output_dir: Path,
    peer_config: PeerConfig,
    game_id: str,
    commit_hash: str,
    timestamp: str,
    *,
    hardware: dict[str, Any],
    games_played_so_far: int | None,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"declaration_{game_id}.json"
    declaration = build_declaration(
        peer_config,
        game_id,
        commit_hash,
        timestamp,
        hardware=hardware,
        games_played_so_far=games_played_so_far,
    )
    path.write_text(json.dumps(declaration, indent=2), encoding="utf-8")
    return path


def write_post_game_deliverables(
    *,
    output_dir: Path,
    orch: Orchestrator,
    game_id: str,
    sub_game_number: int,
    commit_hash: str,
) -> dict[str, Path]:
    """Write the three deliverables that necessarily need post-game data
    (config snapshot, log, result) and return their paths."""
    output_dir.mkdir(parents=True, exist_ok=True)
    tag = f"{game_id}_g{sub_game_number:02d}"

    paths = {
        "config": output_dir / f"config_{tag}.json",
        "log": output_dir / f"log_{tag}.json",
        "result": output_dir / f"result_{game_id}.json",
    }
    paths["config"].write_text(
        json.dumps(build_config_snapshot(orch.config, game_id, sub_game_number), indent=2),
        encoding="utf-8",
    )
    paths["log"].write_text(json.dumps(orch.export_log(), indent=2), encoding="utf-8")
    paths["result"].write_text(
        json.dumps(build_result(orch, game_id, commit_hash=commit_hash), indent=2),
        encoding="utf-8",
    )
    return paths


def write_match_deliverables(
    *,
    output_dir: Path,
    peer_config: PeerConfig,
    orch: Orchestrator,
    game_id: str,
    sub_game_number: int,
    commit_hash: str,
    timestamp: str,
    hardware: dict[str, Any] | None = None,
    games_played_so_far: int | None = None,
) -> dict[str, Path]:
    """Convenience: write all four deliverables at once (tests, simple
    one-shot use). The real ``peer_runtime.py`` flow instead calls
    :func:`write_declaration` before the game and
    :func:`write_post_game_deliverables` after it.
    """
    declaration_path = write_declaration(
        output_dir,
        peer_config,
        game_id,
        commit_hash,
        timestamp,
        hardware=hardware or {},
        games_played_so_far=games_played_so_far,
    )
    other_paths = write_post_game_deliverables(
        output_dir=output_dir,
        orch=orch,
        game_id=game_id,
        sub_game_number=sub_game_number,
        commit_hash=commit_hash,
    )
    return {"declaration": declaration_path, **other_paths}
