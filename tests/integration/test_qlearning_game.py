"""Integration test for the bonus Q-learning brains (BONUS-001): proves
they plug into a real two-orchestrator game exactly like the default
heuristic brains do in test_two_peer_game.py (same real FastMCP transport,
same commit-reveal-audit cycle), not just in isolated unit tests of
individual decisions.
"""

from __future__ import annotations

import asyncio

from police_thief.domain.board import BoardState, Outcome
from police_thief.domain.models import (
    BoardAndAgentsConfig,
    GameConfig,
    MovementAndBarriersConfig,
    Role,
)
from police_thief.gui.replay_viewer import replay
from police_thief.infra.mcp_client import MCPPeerClient
from police_thief.infra.mcp_server import build_server
from police_thief.orchestrator import Orchestrator
from police_thief.strategy.qlearning import QLearningPoliceBrain, QLearningThiefBrain


def _make_config(**overrides: object) -> GameConfig:
    base: dict[str, object] = {
        "schema_version": "1.2",
        "agreed_between": ["group-a", "group-b"],
        "board_and_agents": BoardAndAgentsConfig(grid_size=7, thief_start=(3, 3), cop_start=(0, 0)),
        "movement_and_barriers": MovementAndBarriersConfig(
            max_barriers=14, max_moves=35, survival_threshold=35
        ),
    }
    base.update(overrides)
    return GameConfig(**base)  # type: ignore[arg-type]


async def _play_one_turn(mover: Orchestrator, mover_client: MCPPeerClient) -> None:
    commit_message = mover.produce_commit()
    ack = await mover_client.send(commit_message)
    assert ack.accepted, f"opponent rejected commit: {ack.reason}"
    reveal_message = mover.produce_reveal()
    reveal_response = await mover_client.send(reveal_message)
    mover.confirm_reveal_accepted(reveal_response)


async def _run_full_game(max_iterations: int = 100) -> tuple[Orchestrator, Orchestrator]:
    config = _make_config()
    police = Orchestrator(
        role=Role.POLICE,
        game_id="qlearning-integration-test",
        config=config,
        board=BoardState.initial(config),
        brain=QLearningPoliceBrain(seed=42),
    )
    thief = Orchestrator(
        role=Role.THIEF,
        game_id="qlearning-integration-test",
        config=config,
        board=BoardState.initial(config),
        brain=QLearningThiefBrain(seed=42),
    )

    police_server = build_server("qlearning-police-peer", police.handle_message)
    thief_server = build_server("qlearning-thief-peer", thief.handle_message)
    police_to_thief = MCPPeerClient(thief_server)
    thief_to_police = MCPPeerClient(police_server)

    movers = [(police, police_to_thief), (thief, thief_to_police)]
    for i in range(max_iterations):
        mover, client = movers[i % 2]
        if mover.is_over:
            break
        await _play_one_turn(mover, client)
        if police.board.outcome is not Outcome.ONGOING:
            break

    police_final = police.produce_final_reveal()
    thief_final = thief.produce_final_reveal()
    await police_to_thief.send(police_final)
    await thief_to_police.send(thief_final)
    return police, thief


def test_qlearning_brains_play_a_full_game_to_a_definitive_outcome() -> None:
    police, thief = asyncio.run(_run_full_game())

    assert police.board.outcome is not Outcome.ONGOING
    assert police.board.outcome == thief.board.outcome
    assert police.board.cop_position == thief.board.cop_position
    assert police.board.thief_position == thief.board.thief_position
    assert police.technical_loss_reason is None
    assert thief.technical_loss_reason is None


def test_qlearning_game_log_is_verified_ok() -> None:
    police, thief = asyncio.run(_run_full_game())
    police_log = police.export_log()
    assert police_log == thief.export_log()
    assert replay(police_log) == "Verified OK"
