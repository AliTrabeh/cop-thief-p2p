"""Async peer wiring (config load, strategy/banter resolution, FastMCP server
+ tunnel + client + optional live view) split out of ``peer_runtime.py`` to
keep each file under the project's 150-line-per-file limit. Everything here
runs once, before the turn loop starts; ``run_peer`` calls :func:`start_peer`
and then drives the returned handles.

The *pre-game* Step-0 declaration (hardware spec, commit hash, games-played
count -- book §5.5, Appendix E items 24/37) is written here too, via
``peer_declaration.py`` (split out separately): before the game, not
bundled with the other three deliverables at the end.
"""

from __future__ import annotations

import asyncio
import contextlib
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from police_thief.config import ConfigError, PeerConfig, load_game_config, load_peer_config
from police_thief.domain.board import BoardState
from police_thief.domain.game_config import GameConfig
from police_thief.domain.models import Role
from police_thief.infra.mcp_client import MCPPeerClient
from police_thief.infra.mcp_server import MessageMailbox, build_server
from police_thief.infra.tunnel import TunnelError, TunnelHandle, start_tunnel
from police_thief.infra.vcs import current_commit_hash
from police_thief.logging_setup import get_logger
from police_thief.orchestrator import Orchestrator
from police_thief.peer_declaration import make_step0_payload, write_pre_game_declaration
from police_thief.peer_setup import PeerRuntimeError, check_port_available, resolve_banter_provider
from police_thief.peer_setup import resolve_brain as _resolve_brain
from police_thief.strategy.llm_bluff import BanterProvider

if TYPE_CHECKING:
    from police_thief.gui.live_view import LiveView

logger = get_logger("peer_runtime")


@dataclass
class PeerHandles:
    orch: Orchestrator
    peer_config: PeerConfig
    game_config: GameConfig
    banter_provider: BanterProvider | None
    server_task: asyncio.Task[None]
    tunnel: TunnelHandle | None
    client: MCPPeerClient
    mailbox: MessageMailbox
    view: LiveView | None
    commit_hash: str
    declaration: dict
    declaration_signature: str


async def start_peer(
    role: Role, config_dir: Path, game_id: str, *, show_gui: bool, output_dir: Path | None = None
) -> PeerHandles:
    try:
        game_config = load_game_config(config_dir / "game.json")
        peer_config = load_peer_config(config_dir / role.value / "game.toml")
    except ConfigError as exc:
        raise PeerRuntimeError(str(exc)) from exc

    commit_hash = current_commit_hash()
    declaration, declaration_signature = make_step0_payload(
        peer_config, game_id, commit_hash, game_config, output_dir=output_dir
    )

    strategy_spec = (
        peer_config.strategy.police_class
        if role is Role.POLICE
        else peer_config.strategy.thief_class
    )
    brain = _resolve_brain(role, strategy_spec)
    banter_provider = resolve_banter_provider(
        peer_config, hint_max_words=game_config.world.hint_max_words
    )

    orch = Orchestrator(
        role=role,
        game_id=game_id,
        config=game_config,
        board=BoardState.initial(game_config),
        brain=brain,
    )
    check_port_available("0.0.0.0", peer_config.network.my_port)
    mailbox = MessageMailbox()
    server = build_server(f"{role.value}-peer", orch.handle_message, mailbox)
    server_task = asyncio.create_task(
        server.run_http_async(host="0.0.0.0", port=peer_config.network.my_port, show_banner=False)
    )
    await asyncio.sleep(0.3)  # let the server bind before we start dialing out
    if server_task.done():
        # A bind failure (e.g. port already in use by another peer process on
        # the same machine, PRD-0582) raises inside the task rather than
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

    return PeerHandles(
        orch=orch,
        peer_config=peer_config,
        game_config=game_config,
        banter_provider=banter_provider,
        server_task=server_task,
        tunnel=tunnel,
        client=client,
        mailbox=mailbox,
        view=view,
        commit_hash=commit_hash,
        declaration=declaration,
        declaration_signature=declaration_signature,
    )
