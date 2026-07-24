"""Tunnel value types, split out of ``tunnel.py`` to keep each file under
the project's 150-line-per-file limit: the provider enum, the error type,
and the running-tunnel handle.
"""

from __future__ import annotations

import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum


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
