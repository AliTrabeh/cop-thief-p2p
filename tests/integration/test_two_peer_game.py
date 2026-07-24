"""Integration test — TEST-006: two independent Orchestrator instances (each
with its own BoardState mirror, exactly as two separate OS processes would
have) play a complete game to a definitive winner, communicating only
through the real FastMCP transport built in Part 8 (in-process, but a
genuine protocol round trip). Neither side ever reads the other's `board`
object directly — everything flows through `produce_commit`/`produce_reveal`/
`handle_message`, matching the true P2P, no-shared-memory architecture
(FR-001, FR-002).

Replay/tamper-detection tests live in the sibling file
test_two_peer_replay.py (split out to keep each file under 150 lines);
shared setup helpers live in the non-test module _two_peer_helpers.py.
"""

from __future__ import annotations

import asyncio

from _two_peer_helpers import make_config, play_one_turn, run_full_game

from police_thief.domain.board import BoardState, Outcome
from police_thief.domain.game_config import GameConfig
from police_thief.domain.models import Role
from police_thief.domain.scoring import score
from police_thief.infra.mcp_client import MCPPeerClient
from police_thief.infra.mcp_server import build_server
from police_thief.orchestrator import Orchestrator
from police_thief.strategy.heuristic import HeuristicPoliceBrain, HeuristicThiefBrain


def test_full_local_game_reaches_a_definitive_outcome():
    police, thief = asyncio.run(run_full_game())

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
    base = make_config()
    config: GameConfig = make_config(
        board_and_agents=base.board_and_agents.model_copy(
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
        await play_one_turn(police, police_to_thief)

    asyncio.run(one_cop_turn())
    assert police.board.outcome is Outcome.CAPTURE
    assert thief.board.outcome is Outcome.CAPTURE
