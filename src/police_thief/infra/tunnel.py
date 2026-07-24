"""Tunnel lifecycle management (FR-006, §2.4.1): exposes this peer's local
FastMCP server on a public URL so a genuinely remote rival can connect
(NAT traversal) — not needed for the localhost-only demo.

Two providers:

- ``ngrok`` — fully automated: launches the ``ngrok`` binary as a
  subprocess and discovers the assigned public URL via ngrok's own local
  admin API (``http://127.0.0.1:4040/api/tunnels``), matching the pattern
  in the book's own P2P figure (each side "hides" behind a tunnel that
  hands out one public URL).
- ``manual`` — for tools this project doesn't drive directly (e.g.
  Localtonet, whose local introspection API isn't something this codebase
  can verify without guessing), the user starts the tunnel themselves and
  supplies the resulting public URL via config; this module just carries
  that URL through, it never fabricates an integration it can't confirm
  works.

``none`` (the default) skips tunneling entirely — used for the localhost
two-terminal demo.
"""

from __future__ import annotations

import asyncio
import shutil
import subprocess
import time
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum

import httpx


class TunnelProvider(StrEnum):
    NONE = "none"
    NGROK = "ngrok"
    MANUAL = "manual"


class TunnelError(Exception):
    """Raised when a tunnel can't be started or its public URL can't be
    discovered — never a bare, unexplained traceback."""


ProcessFactory = Callable[[list[str]], "subprocess.Popen[bytes]"]
WhichFn = Callable[[str], str | None]


@dataclass
class TunnelHandle:
    """A running (or manually-supplied) tunnel. Always call :meth:`stop` in
    a ``finally`` block — a leaked tunnel process keeps a public port open
    long after the game ends.
    """

    provider: TunnelProvider
    public_url: str
    _process: subprocess.Popen[bytes] | None = None

    def stop(self) -> None:
        if self._process is None:
            return
        if self._process.poll() is not None:
            return  # already exited
        self._process.terminate()
        try:
            self._process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            self._process.kill()


async def start_ngrok_tunnel(
    local_port: int,
    *,
    ngrok_binary: str = "ngrok",
    api_port: int = 4040,
    startup_timeout: float = 15.0,
    poll_interval: float = 0.5,
    which_fn: WhichFn = shutil.which,
    process_factory: ProcessFactory = subprocess.Popen,
    http_client: httpx.AsyncClient | None = None,
    clock: Callable[[], float] = time.monotonic,
) -> TunnelHandle:
    """Start ``ngrok http <local_port>`` and poll its local admin API until
    a public HTTPS tunnel appears (or ``startup_timeout`` elapses).

    Every external dependency (binary lookup, process creation, HTTP
    client) is injectable so this can be fully unit-tested without a real
    ``ngrok`` binary or network access.
    """
    if which_fn(ngrok_binary) is None:
        raise TunnelError(
            f"{ngrok_binary!r} not found on PATH. Install ngrok "
            "(https://ngrok.com/download) or set provider='manual' instead."
        )

    process = process_factory([ngrok_binary, "http", str(local_port), "--log=stdout"])

    owns_client = http_client is None
    client = http_client if http_client is not None else httpx.AsyncClient()
    try:
        deadline = clock() + startup_timeout
        last_exc: Exception | None = None
        while clock() < deadline:
            if process.poll() is not None:
                raise TunnelError(
                    f"ngrok exited early (code {process.returncode}) before exposing a tunnel"
                )
            try:
                response = await client.get(f"http://127.0.0.1:{api_port}/api/tunnels", timeout=2.0)
                response.raise_for_status()
                tunnels = response.json().get("tunnels", [])
                https_tunnels = [t for t in tunnels if t.get("proto") == "https"]
                if https_tunnels:
                    return TunnelHandle(
                        provider=TunnelProvider.NGROK,
                        public_url=https_tunnels[0]["public_url"],
                        _process=process,
                    )
            except (httpx.HTTPError, ValueError) as exc:
                last_exc = exc
            await asyncio.sleep(poll_interval)
    except BaseException:
        process.terminate()
        raise
    finally:
        if owns_client:
            await client.aclose()

    process.terminate()
    raise TunnelError(
        f"ngrok did not expose a public HTTPS tunnel within {startup_timeout}s"
    ) from last_exc


async def start_tunnel(
    provider: TunnelProvider | str,
    local_port: int,
    *,
    manual_public_url: str = "",
    **ngrok_kwargs: object,
) -> TunnelHandle | None:
    """Dispatch on ``provider``. Returns ``None`` for ``"none"`` (no tunnel
    needed — the localhost demo).
    """
    provider = TunnelProvider(provider)
    if provider is TunnelProvider.NONE:
        return None
    if provider is TunnelProvider.MANUAL:
        if not manual_public_url:
            raise TunnelError(
                "provider='manual' requires a non-empty manual_public_url "
                "(start your tunnel yourself -- e.g. Localtonet -- and paste its URL here)"
            )
        return TunnelHandle(provider=TunnelProvider.MANUAL, public_url=manual_public_url)
    return await start_ngrok_tunnel(local_port, **ngrok_kwargs)  # type: ignore[arg-type]
