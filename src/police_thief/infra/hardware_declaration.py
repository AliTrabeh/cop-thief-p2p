"""Best-effort hardware/environment declaration (book §5.5 "Step-0 and
Computational Fairness", Appendix E item 24): each side must declare its
own hardware spec before a game starts, so a computational-fairness bonus
can be judged fairly between competitors on different machines. Every
field degrades to ``None``/"unknown" rather than raising -- a peer must
never fail to start a game because hardware introspection didn't work on
some platform.
"""

from __future__ import annotations

import os
import platform
from typing import Any


def _total_ram_mb() -> int | None:
    system = platform.system()
    try:
        if system == "Windows":
            import ctypes

            class _MemoryStatusEx(ctypes.Structure):
                _fields_ = (
                    ("dwLength", ctypes.c_ulong),
                    ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong),
                    ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong),
                    ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong),
                    ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
                )

            stat = _MemoryStatusEx()
            stat.dwLength = ctypes.sizeof(_MemoryStatusEx)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat))
            return int(stat.ullTotalPhys // (1024 * 1024))
        if system == "Linux":
            with open("/proc/meminfo", encoding="utf-8") as handle:
                for line in handle:
                    if line.startswith("MemTotal:"):
                        return int(line.split()[1]) // 1024
    except Exception:  # noqa: BLE001 - hardware introspection must never crash a peer
        return None
    return None


def collect_hardware_spec() -> dict[str, Any]:
    """OS, CPU core count, RAM (best-effort). GPU/VRAM is reported as "not
    applicable" -- this project performs no GPU compute (heuristic and
    tabular Q-learning brains are pure CPU, LLM banter calls a remote/local
    API rather than running a model in-process).
    """
    return {
        "os": f"{platform.system()} {platform.release()}".strip(),
        "cpu_cores": os.cpu_count(),
        "ram_mb": _total_ram_mb(),
        "gpu": "not applicable (no GPU compute used)",
    }
