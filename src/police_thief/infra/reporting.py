"""Builds the four mandatory per-match JSON deliverables (Appendix F Table 20,
FR-082): ``declaration_<game_id>.json``, ``config_<game_id>_g<NN>.json``,
``log_<game_id>_g<NN>.json``, ``result_<game_id>.json``. Pure data assembly —
no I/O beyond writing the files this module is explicitly asked to write.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from police_thief.config import PeerConfig
from police_thief.domain.board import Outcome
from police_thief.domain.models import GameConfig, Role
from police_thief.domain.scoring import score, technical_loss_score
from police_thief.orchestrator import Orchestrator


def build_declaration(
    peer_config: PeerConfig, game_id: str, commit_hash: str, timestamp: str
) -> dict[str, Any]:
    """Pre-game fixed match data (FR-087: commit hash updated every game)."""
    return {
        "game_id": game_id,
        "group_name": peer_config.game.group_name,
        "group_id": peer_config.game.group_id,
        "sub_game_number": peer_config.game.sub_game_number,
        "members": peer_config.game.members,
        "repos": peer_config.game.repos,
        "model": peer_config.llm.model,
        "github_commit": commit_hash,
        "timestamp": timestamp,
    }


def build_config_snapshot(
    game_config: GameConfig, game_id: str, sub_game_number: int
) -> dict[str, Any]:
    return {
        "game_id": game_id,
        "sub_game_number": sub_game_number,
        "config": json.loads(game_config.model_dump_json()),
    }


def build_result(orch: Orchestrator, game_id: str) -> dict[str, Any]:
    """The final outcome, from this peer's own point of view (FR-081: each
    side sends its own report independently; conflicting reports score 0
    to both, per the league's own cross-check, not something this module
    can detect locally).
    """
    if orch.technical_loss_reason is not None:
        cop_score, thief_score = technical_loss_score(
            orch.config, orch.technical_loss_role or orch.role
        )
        outcome_name = "technical_loss"
    else:
        cop_score, thief_score = score(orch.board)
        outcome_name = orch.board.outcome.value
    return {
        "game_id": game_id,
        "reported_by_role": orch.role.value,
        "outcome": outcome_name,
        "technical_loss_reason": orch.technical_loss_reason,
        "technical_loss_role": (
            orch.technical_loss_role.value if orch.technical_loss_role else None
        ),
        "cop_score": cop_score,
        "thief_score": thief_score,
        "moves_made": orch.board.moves_made,
        "cop_position": [orch.board.cop_position.row, orch.board.cop_position.col],
        "thief_position": [orch.board.thief_position.row, orch.board.thief_position.col],
    }


def write_match_deliverables(
    *,
    output_dir: Path,
    peer_config: PeerConfig,
    orch: Orchestrator,
    game_id: str,
    sub_game_number: int,
    commit_hash: str,
    timestamp: str,
) -> dict[str, Path]:
    """Write all four deliverables and return their paths."""
    output_dir.mkdir(parents=True, exist_ok=True)
    tag = f"{game_id}_g{sub_game_number:02d}"

    paths = {
        "declaration": output_dir / f"declaration_{game_id}.json",
        "config": output_dir / f"config_{tag}.json",
        "log": output_dir / f"log_{tag}.json",
        "result": output_dir / f"result_{game_id}.json",
    }
    paths["declaration"].write_text(
        json.dumps(build_declaration(peer_config, game_id, commit_hash, timestamp), indent=2),
        encoding="utf-8",
    )
    paths["config"].write_text(
        json.dumps(build_config_snapshot(orch.config, game_id, sub_game_number), indent=2),
        encoding="utf-8",
    )
    paths["log"].write_text(json.dumps(orch.export_log(), indent=2), encoding="utf-8")
    paths["result"].write_text(json.dumps(build_result(orch, game_id), indent=2), encoding="utf-8")
    return paths


__all__ = [
    "Outcome",
    "Role",
    "build_config_snapshot",
    "build_declaration",
    "build_result",
    "write_match_deliverables",
]
