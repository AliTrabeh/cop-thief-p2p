"""FastMCP client wrapper: calls the opponent's dedicated per-step tools
(spec Section 2.3.2, Figure 6) with a bounded timeout and retry policy.

Dedicated send methods (matching the spec's named-tool-per-operation design):
  send_step0          — pre-game Step-0 hardware/software declaration (§5.5)
  send_commit         — Step 1: send sealed commitment H_commit only (§5.3.1)
  send_ack            — Step 2: send acknowledgment to the active player (§5.3.2)
  send_reveal         — Step 3: reveal move + verbal hint, Nonce hidden (§5.3.2)
  send_final_audit    — Step 4: send all Nonces for end-of-game audit (§5.4)
  send_capture_claim  — send capture claim from cop side (§3.5)

Accepts either a real opponent URL ("http://host:port/mcp", for actual
cross-process play) or a FastMCP server instance directly (in-process
transport, used by tests — exercises the real protocol stack without a socket).

Windows note: ``verify=False`` is passed to the FastMCP Client for URL
transports. All peer connections use plain http:// (never https://), so no
certificate verification is needed. This also prevents httpx from calling
ssl.create_default_context() at connection time, which on certain Windows
builds triggers the OPENSSL_Uplink / no OPENSSL_Applink crash.
"""

from __future__ import annotations

import asyncio
import contextlib
from typing import Any
from urllib.parse import urlparse

from fastmcp import Client, FastMCP

Transport = str | FastMCP


class PeerUnreachableError(Exception):
    """Raised once the retry budget is exhausted (never wait forever on an
    unresponsive peer)."""


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

    async def _call(self, tool_name: str, arguments: dict) -> dict:
        """Shared call path: every send_* method routes through here so the
        retry / timeout / verify logic lives in one place.
        """
        last_exc: Exception | None = None
        _verify: bool | None = False if isinstance(self._transport, str) else None
        for attempt in range(self._max_retries + 1):
            try:
                async with Client(
                    self._transport, timeout=self._timeout, verify=_verify
                ) as client:
                    result = await client.call_tool(tool_name, arguments)
                    data: Any = result.data
                    return data if isinstance(data, dict) else {}
            except Exception as exc:  # noqa: BLE001 — transport errors of many shapes
                last_exc = exc
                if attempt < self._max_retries:
                    await asyncio.sleep(self._retry_backoff)
        raise PeerUnreachableError(
            f"opponent unreachable after {self._max_retries} retries"
        ) from last_exc

    async def send_step0(
        self, *, role: str, declaration: dict, signature: str
    ) -> dict:
        """Send pre-game Step-0 hardware/software declaration to opponent (§5.5)."""
        return await self._call(
            "receive_step0",
            {"role": role, "declaration": declaration, "signature": signature},
        )

    async def send_commit(self, *, role: str, step: int, h_commit: str) -> dict:
        """Send Step 1 sealed commitment to opponent's receive_commit tool (§5.3.1)."""
        return await self._call(
            "receive_commit", {"role": role, "step": step, "h_commit": h_commit}
        )

    async def send_ack(self, *, role: str, step: int) -> dict:
        """Send Step 2 acknowledgment to the active player's receive_ack tool (§5.3.2)."""
        return await self._call("receive_ack", {"role": role, "step": step})

    async def send_reveal(
        self, *, role: str, step: int, move: str, hint: str, intent: str
    ) -> dict:
        """Send Step 3 reveal (move + hint, Nonce hidden) to opponent (§5.3.2)."""
        return await self._call(
            "receive_reveal",
            {
                "role": role,
                "step": step,
                "move": move,
                "hint": hint,
                "intent": intent,
            },
        )

    async def send_final_audit(self, *, role: str, nonces: dict[str, str]) -> dict:
        """Send Step 4: all Nonces for end-of-game audit to opponent (§5.4)."""
        return await self._call(
            "receive_final_audit", {"role": role, "nonces": nonces}
        )

    async def send_capture_claim(self, *, role: str, claimed: bool) -> dict:
        """Send capture claim to the thief's receive_capture_claim tool (§3.5)."""
        return await self._call(
            "receive_capture_claim", {"role": role, "claimed": claimed}
        )

    async def wait_until_reachable(
        self, max_wait_seconds: float = 60.0, poll_interval: float = 1.0
    ) -> bool:
        """Poll the opponent until it answers or max_wait_seconds elapses.

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
