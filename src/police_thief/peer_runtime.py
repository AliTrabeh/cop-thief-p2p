"""Wires config loading, the Orchestrator, and the FastMCP transport into a
runnable peer process (``python -m police_thief peer --role ...``, Part 16).

Turn-taking between two genuinely independent processes: each side polls
its own (locally mirrored) ``board.moves_made`` to know whose turn it is
(assumptions.md A-017 — cop moves first, strict alternation, so
``moves_made % 2`` deterministically identifies the mover without any extra
signaling message). The idle side is otherwise just its FastMCP server,
passively handling the mover's COMMIT/REVEAL calls via
``Orchestrator.handle_message`` (Part 8/9).
"""

from __future__ import annotations

import asyncio
import contextlib
import socket
import time
from datetime import UTC, datetime
from pathlib import Path

from police_thief.config import ConfigError, PeerConfig, load_game_config, load_peer_config
from police_thief.domain.board import BoardState
from police_thief.domain.models import Role
from police_thief.infra.gatekeeper import Gatekeeper
from police_thief.infra.gmail_report import report_match_result
from police_thief.infra.mcp_client import MCPPeerClient, PeerUnreachableError
from police_thief.infra.mcp_server import build_server
from police_thief.infra.reporting import build_result, write_match_deliverables
from police_thief.infra.tunnel import TunnelError, start_tunnel
from police_thief.infra.vcs import current_commit_hash
from police_thief.logging_setup import get_logger
from police_thief.orchestrator import Orchestrator, TechnicalLossError
from police_thief.strategy.base import BrainBase, load_brain_class
from police_thief.strategy.heuristic import HeuristicPoliceBrain, HeuristicThiefBrain
from police_thief.strategy.llm_bluff import BanterContext, BanterProvider, build_banter_provider

logger = get_logger("peer_runtime")


class PeerRuntimeError(Exception):
    """Raised for any startup/config problem — never a bare traceback."""


def _check_port_available(host: str, port: int) -> None:
    """Proactively probe the port before handing it to uvicorn/FastMCP.

    Necessary because uvicorn's own bind-failure path calls ``sys.exit()``
    from inside the server task rather than raising a normal exception --
    asyncio special-cases ``SystemExit``/``KeyboardInterrupt`` raised inside
    a task by re-raising them immediately out of the event loop's own
    dispatch step, which bypasses the task's stored exception entirely and
    would otherwise crash ``run_peer`` with a confusing, unhandled
    ``SystemExit: 3`` instead of a clear :class:`PeerRuntimeError`
    (PRD-0582).
    """
    probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        probe.bind((host, port))
    except OSError as exc:
        raise PeerRuntimeError(
            f"cannot start the FastMCP server on port {port} "
            f"(is another process already using it?): {exc}"
        ) from exc
    finally:
        probe.close()


def _default_brain(role: Role) -> BrainBase:
    return HeuristicPoliceBrain() if role is Role.POLICE else HeuristicThiefBrain()


def _resolve_brain(role: Role, strategy_spec: str | None) -> BrainBase:
    if not strategy_spec:
        return _default_brain(role)
    return load_brain_class(strategy_spec)()


def _resolve_banter_provider(peer_config: PeerConfig, hint_max_words: int) -> BanterProvider | None:
    """Never lets a banter misconfiguration take down the whole peer: an
    unimplemented provider (e.g. ``claude_api``, A-005) disables banter for
    this game with a logged warning instead of crashing startup, since
    banter is purely cosmetic and never affects protocol/outcome (PRD-0334).
    """
    try:
        return build_banter_provider(
            peer_config.trash_talk.provider,
            model=peer_config.llm.model,
            hint_max_words=hint_max_words,
            step_deadline_seconds=float(peer_config.llm.step_deadline_seconds),
        )
    except (NotImplementedError, ValueError) as exc:
        logger.warning("banter disabled: %s", exc)
        return None


async def _play_own_turn(orch: Orchestrator, client: MCPPeerClient) -> None:
    commit_message = orch.produce_commit()
    ack = await client.send(commit_message)
    if not ack.accepted:
        orch.reject_own_commit(ack)
        return
    reveal_message = orch.produce_reveal()
    reveal_response = await client.send(reveal_message)
    orch.confirm_reveal_accepted(reveal_response)


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
    try:
        game_config = load_game_config(config_dir / "game.json")
        peer_config = load_peer_config(config_dir / role.value / "game.toml")
    except ConfigError as exc:
        raise PeerRuntimeError(str(exc)) from exc

    strategy_spec = (
        peer_config.strategy.police_class
        if role is Role.POLICE
        else peer_config.strategy.thief_class
    )
    brain = _resolve_brain(role, strategy_spec)
    banter_provider = _resolve_banter_provider(
        peer_config, hint_max_words=game_config.world.hint_max_words
    )

    orch = Orchestrator(
        role=role,
        game_id=game_id,
        config=game_config,
        board=BoardState.initial(game_config),
        brain=brain,
    )
    _check_port_available("0.0.0.0", peer_config.network.my_port)
    server = build_server(f"{role.value}-peer", orch.handle_message)
    server_task = asyncio.create_task(
        server.run_http_async(host="0.0.0.0", port=peer_config.network.my_port, show_banner=False)
    )
    await asyncio.sleep(0.3)  # let the server bind before we start dialing out
    if server_task.done():
        # A bind failure (e.g. port already in use by another peer process
        # on the same machine, PRD-0582) raises inside the task rather than
        # here; surface it now with a clear, actionable message instead of
        # silently continuing to dial out against a server that never bound.
        bind_exc = server_task.exception()
        detail = (
            f": {bind_exc}" if bind_exc is not None else " (it exited immediately without raising)"
        )
        raise PeerRuntimeError(
            f"the FastMCP server failed to start on port {peer_config.network.my_port} "
            f"(is another process already using it?){detail}"
        ) from bind_exc

    tunnel = None
    try:
        tunnel = await start_tunnel(
            peer_config.tunnel.provider,
            peer_config.network.my_port,
            manual_public_url=peer_config.tunnel.manual_public_url,
        )
    except TunnelError as exc:
        server_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await server_task
        raise PeerRuntimeError(f"could not start tunnel: {exc}") from exc
    if tunnel is not None:
        logger.info("tunnel up: share this URL with your rival -> %s/mcp", tunnel.public_url)
        print(f"Public URL for your opponent to use as their opponent_url: {tunnel.public_url}/mcp")

    client = MCPPeerClient(
        peer_config.network.opponent_url,
        timeout_seconds=float(game_config.network_and_league.response_timeout_sec),
    )

    view = None
    if show_gui:
        from police_thief.gui.live_view import LiveView

        view = LiveView(
            grid_size=game_config.board_and_agents.grid_size, own_label=role.value[0].upper()
        )

    def _refresh_gui(is_my_turn: bool) -> None:
        if view is None:
            return
        from police_thief.domain.scent import belief_map

        belief = belief_map(orch.opponent_scent, game_config.board_and_agents.grid_size)
        view.update(orch.board.position_of(role), belief, is_my_turn)
        view.root.update()

    expected_mover_parity = 0 if role is Role.POLICE else 1
    waited = 0.0
    try:
        logger.info(
            "waiting for opponent at %s to come online...", peer_config.network.opponent_url
        )
        reachable = await client.wait_until_reachable(max_wait_seconds=max_wait_seconds)
        if not reachable:
            orch.mark_opponent_unresponsive(max_wait_seconds)
        while not orch.is_over:
            my_turn = orch.board.moves_made % 2 == expected_mover_parity
            _refresh_gui(my_turn)
            if my_turn:
                logger.info("turn %d: computing move", orch.turn_number)
                try:
                    await _play_own_turn(orch, client)
                except TechnicalLossError as exc:
                    logger.error("own turn ended in technical loss: %s", exc)
                else:
                    if banter_provider is not None:
                        context = BanterContext(role=role, turn_number=orch.turn_number)
                        logger.info("banter: %s", banter_provider.generate(context))
                waited = 0.0
            else:
                await asyncio.sleep(poll_interval)
                waited += poll_interval
                if waited > max_wait_seconds:
                    orch.mark_opponent_unresponsive(waited)
                    break

        _refresh_gui(False)
        try:
            await client.send(orch.produce_final_reveal())
        except PeerUnreachableError:
            logger.warning("could not deliver final reveal; opponent may already be gone")
    finally:
        server_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await server_task
        if tunnel is not None:
            tunnel.stop()
        if view is not None:
            view.root.destroy()

    if output_dir is not None:
        _write_deliverables(orch, peer_config, game_id, output_dir)

    return orch


def _write_deliverables(
    orch: Orchestrator, peer_config: PeerConfig, game_id: str, output_dir: Path
) -> None:
    timestamp = datetime.now(UTC).isoformat()
    paths = write_match_deliverables(
        output_dir=output_dir,
        peer_config=peer_config,
        orch=orch,
        game_id=game_id,
        sub_game_number=peer_config.game.sub_game_number,
        commit_hash=current_commit_hash(),  # FR-087: real HEAD hash, "unknown" if not a checkout
        timestamp=timestamp,
    )
    logger.info("wrote match deliverables: %s", {k: str(v) for k, v in paths.items()})

    gatekeeper = Gatekeeper(orch.config.rate_limiter_gatekeeper, clock=time.monotonic)
    status = report_match_result(
        mode=peer_config.email.mode,
        recipient=peer_config.email.recipient,
        result_json=build_result(orch, game_id),
        gatekeeper=gatekeeper,
        output_dir=output_dir,
        game_id=game_id,
    )
    logger.info("email report: %s", status)
