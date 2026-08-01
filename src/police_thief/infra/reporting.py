"""Builds the four mandatory per-match JSON deliverables (Appendix F Table 20,
FR-082): ``declaration_<game_id>.json``, ``config_<game_id>_g<NN>.json``,
``log_<game_id>_g<NN>.json``, ``result_<game_id>.json``. Pure data assembly —
no I/O; the file-writing functions that use these builders live in the
sibling module ``reporting_writers.py`` (split out to keep each file under
150 lines, and to keep the dependency one-directional: writers depend on
builders, not the reverse).

The declaration is meant to be written *before* a game starts (book §5.5
"Step-0 and Computational Fairness", Appendix E item 24: hardware/commit-hash
fairness must be declared up front, not reconstructed after the fact) while
the other three necessarily need post-game data — see
``reporting_writers.py``'s docstring for how the real peer lifecycle splits
the two write calls.
"""

from __future__ import annotations

import json
from typing import Any

from police_thief.config import PeerConfig
from police_thief.domain.board import Outcome
from police_thief.domain.game_config import GameConfig
from police_thief.domain.models import Role
from police_thief.domain.scoring import score, technical_loss_score
from police_thief.orchestrator import Orchestrator
from police_thief.orchestrator_types import opponent_of


def build_declaration(
    peer_config: PeerConfig,
    game_id: str,
    commit_hash: str,
    timestamp: str,
    *,
    hardware: dict[str, Any],
    games_played_so_far: int | None,
) -> dict[str, Any]:
    """Pre-game fixed match data (FR-087: commit hash updated every game;
    book §5.5: hardware spec; Appendix E item 37: games-played-so-far).
    """
    return {
        "game_id": game_id,
        "group_name": peer_config.game.group_name,
        "group_id": peer_config.game.group_id,
        "opponent_group_id": peer_config.game.opponent_group_id or None,
        "sub_game_number": peer_config.game.sub_game_number,
        "members": peer_config.game.members,
        "repos": peer_config.game.repos,
        "model": peer_config.llm.model,
        "github_commit": commit_hash,
        "timestamp": timestamp,
        "hardware": hardware,
        "games_played_so_far": games_played_so_far,
    }


def build_config_snapshot(
    game_config: GameConfig, game_id: str, sub_game_number: int
) -> dict[str, Any]:
    return {
        "game_id": game_id,
        "sub_game_number": sub_game_number,
        "config": json.loads(game_config.model_dump_json()),
    }


def build_result(orch: Orchestrator, game_id: str, *, commit_hash: str) -> dict[str, Any]:
    """The final outcome, from this peer's own point of view (FR-081: each
    side sends its own report independently; conflicting reports score 0
    to both, per the league's own cross-check, not something this module
    can detect locally). Includes ``github_commit`` (book §5.5: the same
    field the completion email must carry, not just the pre-game
    declaration).
    """
    if orch.technical_loss_reason is not None:
        # technical_loss_role is None only for connectivity timeouts (no rules violation);
        # the unresponsive party is still the de facto disqualified side.
        disqualified = orch.technical_loss_role or opponent_of(orch.role)
        cop_score, thief_score = technical_loss_score(orch.config, disqualified)
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
        "github_commit": commit_hash,
    }


__all__ = [
    "Outcome",
    "Role",
    "build_config_snapshot",
    "build_declaration",
    "build_result",
]
