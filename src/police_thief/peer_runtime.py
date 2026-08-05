"""Wires config loading, the Orchestrator, and the FastMCP transport into a
runnable peer process (``python -m police_thief peer --role ...``).

Turn-taking: each side polls its own (locally mirrored) ``board.moves_made``
to know whose turn it is (cop moves first, strict alternation, so
``moves_made % 2`` deterministically identifies the mover without any extra
signaling message).

Per-turn protocol (spec Figure 6, §5.3):
  Active player:
    1. produce_commit() → send_commit() on opponent's receive_commit tool
    2. Await own server's mailbox.acks (opponent calls our receive_ack tool)
    3. produce_reveal() → send_reveal() on opponent's receive_reveal tool

  Passive player (while waiting for own turn):
    1. Drain mailbox.pending_acks — each entry means we received a commit and
       must call send_ack() back to the active player's receive_ack tool
    2. The reveal arrives via our server's receive_reveal tool (handled by
       orchestrator synchronously in the server tool handler)

Split: this file owns the turn loop and cleanup; ``peer_startup.py`` owns
async setup; ``peer_setup.py`` owns one-time sync startup helpers;
``peer_declaration.py`` owns the pre-game Step-0 declaration;
``peer_deliverables.py`` owns end-of-game JSON/email reporting.
"""

from __future__ import annotations

import asyncio
import contextlib
from pathlib import Path

from police_thief.domain.board import Outcome
from police_thief.domain.models import Role
from police_thief.infra.mcp_client import MCPPeerClient, PeerUnreachableError
from police_thief.infra.mcp_server import MessageMailbox
from police_thief.infra.protocol import ProtocolResponse
from police_thief.logging_setup import get_logger
from police_thief.orchestrator import Orchestrator, TechnicalLossError
from police_thief.peer_deliverables import write_deliverables
from police_thief.peer_setup import PeerRuntimeError
from police_thief.peer_startup import PeerHandles, start_peer
from police_thief.strategy.llm_bluff import BanterContext

__all__ = ["PeerRuntimeError", "run_peer"]

logger = get_logger("peer_runtime")


async def _play_own_turn(
    orch: Orchestrator,
    client: MCPPeerClient,
    mailbox: MessageMailbox,
    response_timeout: float,
    hint: str = "",
) -> None:
    """Execute one full commit → ack → reveal cycle as the active player."""
    commit_message = orch.produce_commit()

    # Step 1: send commit to opponent's receive_commit tool
    commit_resp = await client.send_commit(
        role=orch.role.value,
        step=commit_message.turn_number,
        h_commit=commit_message.payload["h_commit"],
    )
    if not commit_resp.get("accepted"):
        reason = commit_resp.get("reason") or commit_resp.get("error", "unknown")
        orch.reject_own_commit(ProtocolResponse(accepted=False, reason=reason))
        return

    # Step 2: wait for the passive player to call OUR receive_ack tool (spec §5.3.2)
    try:
        await asyncio.wait_for(mailbox.acks.get(), timeout=response_timeout)
    except asyncio.TimeoutError:
        orch.mark_opponent_unresponsive(response_timeout)
        return

    # Step 3: send reveal to opponent's receive_reveal tool
    reveal_message = orch.produce_reveal(hint=hint)
    reveal_resp = await client.send_reveal(
        role=orch.role.value,
        step=reveal_message.turn_number,
        move=reveal_message.payload["move"],
        hint=reveal_message.payload.get("hint", ""),
        intent=reveal_message.payload.get("intent", "truth"),
    )
    orch.confirm_reveal_accepted(ProtocolResponse.model_validate(reveal_resp))


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
    orch = handles.orch
    client = handles.client
    mailbox = handles.mailbox
    response_timeout = float(
        handles.game_config.network_and_league.response_timeout_sec
    )
    expected_mover_parity = 0 if role is Role.POLICE else 1
    waited = 0.0

    logger.info(
        "waiting for opponent at %s to come online...",
        handles.peer_config.network.opponent_url,
    )
    reachable = await client.wait_until_reachable(max_wait_seconds=max_wait_seconds)
    if not reachable:
        orch.mark_opponent_unresponsive(max_wait_seconds)
    else:
        # Step-0 exchange: send our hardware/software declaration before the first
        # turn so the opponent can verify fairness up front (spec §5.5).
        try:
            await client.send_step0(
                role=role.value,
                declaration=handles.declaration,
                signature=handles.declaration_signature,
            )
            logger.info("sent Step-0 declaration to opponent")
        except PeerUnreachableError:
            logger.warning("could not deliver Step-0 declaration to opponent")

    while not orch.is_over:
        my_turn = orch.board.moves_made % 2 == expected_mover_parity
        _refresh_gui(handles, role, my_turn)

        if my_turn:
            logger.info("turn %d: computing move", orch.turn_number)
            # Generate hint (bluff text) before the reveal so it can be included
            hint = ""
            if handles.banter_provider is not None:
                context = BanterContext(role=role, turn_number=orch.turn_number)
                hint = handles.banter_provider.generate(context)
                logger.info("hint for this turn: %s", hint)
            try:
                await _play_own_turn(orch, client, mailbox, response_timeout, hint)
            except TechnicalLossError as exc:
                logger.error("own turn ended in technical loss: %s", exc)
            waited = 0.0

        else:
            # Passive player: drain pending_acks and send our ACK back (spec §5.3.2 Step 2)
            if not mailbox.pending_acks.empty():
                pending = await mailbox.pending_acks.get()
                try:
                    await client.send_ack(role=role.value, step=pending["step"])
                    logger.debug("sent ACK for step %d", pending["step"])
                except PeerUnreachableError:
                    logger.warning("could not send ACK to opponent")
                waited = 0.0
            else:
                await asyncio.sleep(poll_interval)
                waited += poll_interval
                if waited > max_wait_seconds:
                    orch.mark_opponent_unresponsive(waited)
                    break

    _refresh_gui(handles, role, False)

    # Capture claim protocol (spec §3.5): cop sends the claim; thief awaits and acknowledges.
    if role is Role.POLICE and orch.board.outcome is Outcome.CAUGHT:
        try:
            await client.send_capture_claim(role=role.value, claimed=True)
            logger.info("sent capture claim to thief")
        except PeerUnreachableError:
            logger.warning("could not deliver capture claim to thief")
    elif role is Role.THIEF and orch.board.outcome is Outcome.CAUGHT:
        try:
            claim = await asyncio.wait_for(mailbox.capture_claims.get(), timeout=response_timeout)
            logger.info("received capture claim from cop: claimed=%s", claim.get("claimed"))
        except asyncio.TimeoutError:
            logger.warning("capture claim from cop did not arrive in time")

    # End-of-game Step 4: send all Nonces for mutual audit (spec §5.4)
    final_reveal_msg = orch.produce_final_reveal()
    try:
        await client.send_final_audit(
            role=final_reveal_msg.sender_role.value,
            nonces=final_reveal_msg.payload,
        )
    except PeerUnreachableError:
        logger.warning("could not deliver final audit; opponent may already be gone")
    else:
        # Give the opponent's server a brief window to send their FINAL_AUDIT back
        # so our server can record their nonces before we shut down.
        await asyncio.sleep(2.0)


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
    handles = await start_peer(role, config_dir, game_id, show_gui=show_gui, output_dir=output_dir)
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
        write_deliverables(
            handles.orch, handles.peer_config, game_id, output_dir, handles.commit_hash
        )

    return handles.orch
