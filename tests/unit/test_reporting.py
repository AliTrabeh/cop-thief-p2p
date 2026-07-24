"""Unit tests for infra/reporting.py — FR-082, Appendix F Table 20."""

from __future__ import annotations

import json
from pathlib import Path

from police_thief.config import PeerConfig
from police_thief.domain.board import BoardState, Outcome
from police_thief.domain.models import Role
from police_thief.infra.reporting import build_result, write_match_deliverables
from police_thief.orchestrator import Orchestrator
from police_thief.strategy.heuristic import HeuristicPoliceBrain


def _peer_config() -> PeerConfig:
    return PeerConfig.model_validate(
        {
            "version": "1.0",
            "game": {"group_name": "My-Team", "group_id": "my-team", "members": ["id-1"]},
            "network": {"my_port": 8801, "opponent_url": "http://127.0.0.1:8802/mcp"},
            "email": {"recipient": "rmisegal+uoh26finalgame@gmail.com"},
        }
    )


def _orchestrator(game_config) -> Orchestrator:
    board = BoardState.initial(game_config)
    return Orchestrator(
        role=Role.POLICE,
        game_id="report-test",
        config=game_config,
        board=board,
        brain=HeuristicPoliceBrain(),
    )


def test_build_result_for_a_capture(game_config):
    orch = _orchestrator(game_config)
    orch.board.outcome = Outcome.CAPTURE
    result = build_result(orch, "report-test")
    assert result["outcome"] == "capture"
    assert result["cop_score"] == 20
    assert result["thief_score"] == 5
    assert result["technical_loss_reason"] is None


def test_build_result_for_a_technical_loss(game_config):
    orch = _orchestrator(game_config)
    orch._fail("opponent's revealed move was illegal", disqualified=Role.THIEF)
    result = build_result(orch, "report-test")
    assert result["outcome"] == "technical_loss"
    assert result["technical_loss_role"] == "thief"
    assert result["cop_score"] == game_config.scoring.survival_cop
    assert result["thief_score"] == 0


def test_write_match_deliverables_creates_all_four_files(tmp_path: Path, game_config):
    orch = _orchestrator(game_config)
    orch.board.outcome = Outcome.SURVIVAL
    paths = write_match_deliverables(
        output_dir=tmp_path,
        peer_config=_peer_config(),
        orch=orch,
        game_id="report-test",
        sub_game_number=1,
        commit_hash="abc123",
        timestamp="2026-07-24T00:00:00Z",
    )
    assert set(paths) == {"declaration", "config", "log", "result"}
    for path in paths.values():
        assert path.exists()
        json.loads(path.read_text(encoding="utf-8"))  # must be valid JSON

    declaration = json.loads(paths["declaration"].read_text(encoding="utf-8"))
    assert declaration["group_name"] == "My-Team"
    assert declaration["github_commit"] == "abc123"

    result = json.loads(paths["result"].read_text(encoding="utf-8"))
    assert result["outcome"] == "survival"
