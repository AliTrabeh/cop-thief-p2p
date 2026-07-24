"""Wires config loading, the Orchestrator, and the FastMCP transport into a
runnable peer process (``python -m police_thief peer --role ...``, Part 16).

Turn-taking between two genuinely independent processes: each side polls
its own (locally mirrored) ``board.moves_made`` to know whose turn it is
(assumptions.md A-017 — cop moves first, strict alternation, so
``moves_made % 2`` deterministically identifies the mover without any extra
signaling message). The idle side is otherwise just its FastMCP server,
passively handling the mover's COMMIT/REVEAL calls via
``Orchestrator.handle_message`` (Part 8/9).

Split across four files (each kept under the project's 150-line limit): this
file owns just the turn loop and cleanup; ``peer_startup.py`` owns the async
setup wiring (config, server, tunnel, client, GUI); ``peer_setup.py`` owns
one-time sync startup helpers (port probe, strategy/banter resolution);
``peer_deliverables.py`` owns end-of-game JSON/email reporting.
"""

from __future__ import annotations

import asyncio
import contextlib
from pathlib import Path

from police_thief.domain.models import Role
from police_thief.infra.mcp_client import MCPPeerClient, PeerUnreachableError
from police_thief.logging_setup import get_logger
from police_thief.orchestrator import Orchestrator, TechnicalLossError
from police_thief.peer_deliverables import write_deliverables
from police_thief.peer_setup import PeerRuntimeError
from police_thief.peer_startup import PeerHandles, start_peer
from police_thief.strategy.llm_bluff import BanterContext

__all__ = ["PeerRuntimeError", "run_peer"]

logger = get_logger("peer_runtime")


async def _play_own_turn(orch: Orchestrator, client: MCPPeerClient) -> None:
    commit_message = orch.produce_commit()
    ack = await client.send(commit_message)
    if not ack.accepted:
        orch.reject_own_commit(ack)
        return
    reveal_message = orch.produce_reveal()
    reveal_response = await client.send(reveal_message)
    orch.confirm_reveal_accepted(reveal_response)


def _refresh_gui(handles: PeerHandles, role: Role, is_my_turn: bool) -> None:
    if handles.view is None:
        return
    from police_thief.domain.scent import belief_map

    grid_size = handles.game_config.board_and_agents.grid_size
    belief = belief_map(handles.orch.opponent_scent, grid_size)
    handles.view.update(handles.orch.board.position_of(role), belief, is_my_turn)
    handles.view.root.update()


async def _drive_turn_loop(
    handles: PeerHandles, role: Role, poll_interval: float, max_wait_seconds: float
) -> None:
    orch, client = handles.orch, handles.client
    expected_mover_parity = 0 if role is Role.POLICE else 1
    waited = 0.0
    logger.info(
        "waiting for opponent at %s to come online...", handles.peer_config.network.opponent_url
    )
    reachable = await client.wait_until_reachable(max_wait_seconds=max_wait_seconds)
    if not reachable:
        orch.mark_opponent_unresponsive(max_wait_seconds)
    while not orch.is_over:
        my_turn = orch.board.moves_made % 2 == expected_mover_parity
        _refresh_gui(handles, role, my_turn)
        if my_turn:
            logger.info("turn %d: computing move", orch.turn_number)
            try:
                await _play_own_turn(orch, client)
            except TechnicalLossError as exc:
                logger.error("own turn ended in technical loss: %s", exc)
            else:
                if handles.banter_provider is not None:
                    context = BanterContext(role=role, turn_number=orch.turn_number)
                    logger.info("banter: %s", handles.banter_provider.generate(context))
            waited = 0.0
        else:
            await asyncio.sleep(poll_interval)
            waited += poll_interval
            if waited > max_wait_seconds:
                orch.mark_opponent_unresponsive(waited)
                break

    _refresh_gui(handles, role, False)
    try:
        await client.send(orch.produce_final_reveal())
    except PeerUnreachableError:
        logger.warning("could not deliver final reveal; opponent may already be gone")


async def run_peer(
    role: Role,
    config_dir: Path,
    game_id: str,
    *,
    output_dir: Path | None = None,
    poll_interval: float = 0.5,
    max_wait_seconds: float = 180.0,
    show_gui: bool = False,
) -> Orchestrator:
    """Run one full game as ``role`` and return the finished Orchestrator."""
    handles = await start_peer(role, config_dir, game_id, show_gui=show_gui)
    try:
        await _drive_turn_loop(handles, role, poll_interval, max_wait_seconds)
    finally:
        handles.server_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await handles.server_task
        if handles.tunnel is not None:
            handles.tunnel.stop()
        if handles.view is not None:
            handles.view.root.destroy()

    if output_dir is not None:
        write_deliverables(handles.orch, handles.peer_config, game_id, output_dir)

    return handles.orch
