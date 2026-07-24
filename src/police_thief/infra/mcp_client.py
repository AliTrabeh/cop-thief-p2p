"""FastMCP client wrapper: calls the opponent's ``submit_message`` tool with
a bounded timeout + retry policy (the Deadline Tracker, FR-053).

Accepts either a real opponent URL (``"http://host:port/mcp"``, for actual
cross-process play, FR-050) or a :class:`fastmcp.FastMCP` server instance
directly (in-process transport, used by tests — docs/testing_strategy.md
requires at least one test on the real local communication layer, and
FastMCP's in-memory transport exercises the real protocol stack without a
socket, which is both real and CI-safe).
"""

from __future__ import annotations

import asyncio
import contextlib
from typing import Any

from fastmcp import Client, FastMCP

from police_thief.infra.protocol import ProtocolMessage, ProtocolResponse

Transport = str | FastMCP


class PeerUnreachableError(Exception):
    """Raised once the retry budget is exhausted (FR-053: never wait forever
    on an unresponsive peer)."""


class MCPPeerClient:
    def __init__(
        self,
        transport: Transport,
        timeout_seconds: float = 30.0,
        max_retries: int = 3,
        retry_backoff_seconds: float = 5.0,
    ) -> None:
        self._transport = transport
        self._timeout = timeout_seconds
        self._max_retries = max_retries
        self._retry_backoff = retry_backoff_seconds

    async def send(self, message: ProtocolMessage) -> ProtocolResponse:
        """Send ``message`` to the opponent; retries on transport failure,
        raises :class:`PeerUnreachableError` once retries are exhausted.
        A well-formed protocol-level rejection (e.g. ``STALE_TURN``) is
        *not* a transport failure and is returned normally, not retried.
        """
        last_exc: Exception | None = None
        for attempt in range(self._max_retries + 1):
            try:
                async with Client(self._transport, timeout=self._timeout) as client:
                    result = await client.call_tool(
                        "submit_message", {"message": message.model_dump(mode="json")}
                    )
                    data: Any = result.data
                    return ProtocolResponse.model_validate(data)
            except Exception as exc:  # noqa: BLE001 - transport errors of many distinct shapes
                last_exc = exc
                if attempt < self._max_retries:
                    await asyncio.sleep(self._retry_backoff)
        raise PeerUnreachableError(
            f"opponent unreachable after {self._max_retries} retries"
        ) from last_exc

    async def wait_until_reachable(
        self, max_wait_seconds: float = 60.0, poll_interval: float = 1.0
    ) -> bool:
        """Poll the opponent with a lightweight ``ping`` (no game semantics)
        until it answers or ``max_wait_seconds`` elapses.

        Two independently-started peer processes (Part 16's two-terminal
        demo) don't launch at exactly the same instant; without this
        handshake, the first mover's in-game retry budget (a handful of
        attempts meant for *mid-game* hiccups) can exhaust itself waiting
        for the opponent's server to even finish binding its port.
        """
        waited = 0.0
        while waited < max_wait_seconds:
            with contextlib.suppress(Exception):  # not up yet; keep polling
                async with Client(self._transport, timeout=self._timeout) as client:
                    if await client.ping():
                        return True
            await asyncio.sleep(poll_interval)
            waited += poll_interval
        return False
