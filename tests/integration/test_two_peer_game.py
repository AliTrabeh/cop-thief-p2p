"""Integration test — TEST-006: two independent Orchestrator instances (each
with its own BoardState mirror, exactly as two separate OS processes would
have) play a complete game to a definitive winner, communicating only
through the real FastMCP transport built in Part 8 (in-process, but a
genuine protocol round trip). Neither side ever reads the other's `board`
object directly — everything flows through `produce_commit`/`produce_reveal`/
`handle_message`, matching the true P2P, no-shared-memory architecture
(FR-001, FR-002).
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
from police_thief.domain.scoring import score
from police_thief.infra.mcp_client import MCPPeerClient
from police_thief.infra.mcp_server import build_server
from police_thief.orchestrator import Orchestrator
from police_thief.strategy.heuristic import HeuristicPoliceBrain, HeuristicThiefBrain


def _make_config(**overrides: object) -> GameConfig:
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
        await _play_one_turn(mover, client)
        if police.board.outcome is not Outcome.ONGOING:
            break
    return police, thief


def test_full_local_game_reaches_a_definitive_outcome():
    police, thief = asyncio.run(_run_full_game())

    assert police.board.outcome is not Outcome.ONGOING

    # Both sides' independent board mirrors must agree on the outcome and
    # final positions -- proof the message exchange kept them in sync
    # without ever sharing memory.
    assert police.board.outcome == thief.board.outcome
    assert police.board.cop_position == thief.board.cop_position
    assert police.board.thief_position == thief.board.thief_position
    assert police.board.moves_made == thief.board.moves_made

    cop_score, thief_score = score(police.board)
    assert isinstance(cop_score, int)
    assert isinstance(thief_score, int)


def test_capture_is_detected_symmetrically_by_both_sides():
    # A short-fused config where the cop starts adjacent to the thief makes
    # an early capture overwhelmingly likely without depending on exact
    # heuristic tie-breaking.
    config = _make_config(
        board_and_agents=_make_config().board_and_agents.model_copy(
            update={"thief_start": (0, 1), "cop_start": (0, 0)}
        )
    )
    police = Orchestrator(
        role=Role.POLICE,
        game_id="capture-test",
        config=config,
        board=BoardState.initial(config),
        brain=HeuristicPoliceBrain(),
    )
    thief = Orchestrator(
        role=Role.THIEF,
        game_id="capture-test",
        config=config,
        board=BoardState.initial(config),
        brain=HeuristicThiefBrain(),
    )
    # Give the cop a belief hint pointing at the thief's real cell -- with
    # zero information at all, a uniform belief map's argmax degenerately
    # ties on the cop's own start cell (assumptions.md-adjacent quirk also
    # seen in test_orchestrator.py), same as any real game's true turn 0
    # would before the thief's first REVEAL arrives.
    police.opponent_scent.deposit(police.board.thief_position)

    # Only police -> thief traffic happens in this single-turn test, so only
    # the thief's server side is needed.
    thief_server = build_server("thief-peer-2", thief.handle_message)
    police_to_thief = MCPPeerClient(thief_server)

    async def one_cop_turn() -> None:
        await _play_one_turn(police, police_to_thief)

    asyncio.run(one_cop_turn())
    assert police.board.outcome is Outcome.CAPTURE
    assert thief.board.outcome is Outcome.CAPTURE
