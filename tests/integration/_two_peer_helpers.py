"""Shared helpers for the two-peer integration tests (test_two_peer_game.py,
test_two_peer_replay.py) — not itself a test file (no ``test_`` prefix, so
pytest doesn't collect it), split out purely to keep each test file under
150 lines.
"""

from __future__ import annotations

from police_thief.domain.board import BoardState, Outcome
from police_thief.domain.game_config import (
    BoardAndAgentsConfig,
    GameConfig,
    MovementAndBarriersConfig,
)
from police_thief.domain.models import Role
from police_thief.infra.mcp_client import MCPPeerClient
from police_thief.infra.mcp_server import build_server
from police_thief.orchestrator import Orchestrator
from police_thief.strategy.heuristic import HeuristicPoliceBrain, HeuristicThiefBrain


def make_config(**overrides: object) -> GameConfig:
    """Standalone equivalent of tests/conftest.py's fixture factory --
    duplicated (not imported) since `tests/` isn't an importable package and
    cross-directory conftest imports don't work with pytest's default import
    mode.
    """
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


async def play_one_turn(mover: Orchestrator, mover_client: MCPPeerClient) -> None:
    commit_message = mover.produce_commit()
    ack = await mover_client.send(commit_message)
    assert ack.accepted, f"opponent rejected commit: {ack.reason}"

    reveal_message = mover.produce_reveal()
    reveal_response = await mover_client.send(reveal_message)
    mover.confirm_reveal_accepted(reveal_response)


async def run_full_game(max_iterations: int = 100) -> tuple[Orchestrator, Orchestrator]:
    config = make_config()
    police = Orchestrator(
        role=Role.POLICE,
        game_id="integration-test-game",
        config=config,
        board=BoardState.initial(config),
        brain=HeuristicPoliceBrain(),
    )
    thief = Orchestrator(
        role=Role.THIEF,
        game_id="integration-test-game",
        config=config,
        board=BoardState.initial(config),
        brain=HeuristicThiefBrain(),
    )

    police_server = build_server("police-peer", police.handle_message)
    thief_server = build_server("thief-peer", thief.handle_message)
    police_to_thief = MCPPeerClient(thief_server)
    thief_to_police = MCPPeerClient(police_server)

    # assumptions.md A-017: cop moves first, then strict alternation.
    movers = [(police, police_to_thief), (thief, thief_to_police)]
    for i in range(max_iterations):
        mover, client = movers[i % 2]
        if mover.is_over:
            break
        await play_one_turn(mover, client)
        if police.board.outcome is not Outcome.ONGOING:
            break

    # End-of-game mutual audit (FR-045, §5.4): both sides reveal every nonce.
    police_final = police.produce_final_reveal()
    thief_final = thief.produce_final_reveal()
    await police_to_thief.send(police_final)
    await thief_to_police.send(thief_final)
    return police, thief
