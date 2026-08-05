"""FastMCP client wrapper: calls the opponent's ``submit_message`` tool with
a bounded timeout + retry policy (the Deadline Tracker, FR-053).

Accepts either a real opponent URL (``"http://host:port/mcp"``, for actual
cross-process play, FR-050) or a :class:`fastmcp.FastMCP` server instance
directly (in-process transport, used by tests — docs/testing_strategy.md
requires at least one test on the real local communication layer, and
FastMCP's in-memory transport exercises the real protocol stack without a
socket, which is both real and CI-safe).

Windows note: ``verify=False`` is passed to the FastMCP ``Client`` for URL
transports.  All peer connections use plain ``http://`` (never ``https://``),
so no certificate verification is needed.  This also prevents httpx from
calling ``ssl.create_default_context()`` at connection time, which on certain
Windows builds triggers the ``OPENSSL_Uplink / no OPENSSL_Applink`` crash
caused by the ``cryptography`` package's bundled OpenSSL DLL being initialised
before Python's own ``_ssl.pyd`` can install the applink table.
"""

from __future__ import annotations

import asyncio
import contextlib
from typing import Any
from urllib.parse import urlparse

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
        # verify=False: peer connections are plain http://, no TLS needed;
        # also prevents the Windows OPENSSL_Uplink crash (see module docstring).
        _verify: bool | None = False if isinstance(self._transport, str) else None
        for attempt in range(self._max_retries + 1):
            try:
                async with Client(self._transport, timeout=self._timeout, verify=_verify) as client:
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
        """Poll the opponent until it answers or ``max_wait_seconds`` elapses.

        For URL transports, uses a raw TCP connect so no SSL/TLS stack is
        loaded (avoids the Windows OpenSSL DLL ordering issue on first use).
        For in-process FastMCP transports (tests), falls back to a real ping.
        """
        waited = 0.0
        while waited < max_wait_seconds:
            with contextlib.suppress(Exception):
                if isinstance(self._transport, str):
                    parsed = urlparse(self._transport)
                    host = parsed.hostname or "127.0.0.1"
                    port = parsed.port or 80
                    _, writer = await asyncio.wait_for(
                        asyncio.open_connection(host, port), timeout=0.5
                    )
                    writer.close()
                    await writer.wait_closed()
                    return True
                else:
                    async with Client(self._transport, timeout=self._timeout) as client:
                        if await client.ping():
                            return True
            await asyncio.sleep(poll_interval)
            waited += poll_interval
        return False
