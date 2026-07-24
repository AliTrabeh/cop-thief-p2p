"""Peer startup helpers split out of ``peer_runtime.py`` to keep each file
under the project's 150-line-per-file limit: the port-availability probe,
strategy-class resolution (default heuristic vs. a configured pluggable
brain), and banter-provider resolution. All are pure setup steps run once
before ``run_peer``'s turn loop starts.
"""

from __future__ import annotations

import socket

from police_thief.config import PeerConfig
from police_thief.domain.models import Role
from police_thief.logging_setup import get_logger
from police_thief.strategy.base import BrainBase, load_brain_class
from police_thief.strategy.heuristic import HeuristicPoliceBrain, HeuristicThiefBrain
from police_thief.strategy.llm_bluff import BanterProvider, build_banter_provider

logger = get_logger("peer_runtime")


class PeerRuntimeError(Exception):
    """Raised for any startup/config problem — never a bare traceback."""


def check_port_available(host: str, port: int) -> None:
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


def resolve_brain(role: Role, strategy_spec: str | None) -> BrainBase:
    if not strategy_spec:
        return _default_brain(role)
    return load_brain_class(strategy_spec)()


def resolve_banter_provider(peer_config: PeerConfig, hint_max_words: int) -> BanterProvider | None:
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
