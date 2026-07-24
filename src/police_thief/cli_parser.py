"""Argument parser construction for ``python -m police_thief``, split out of
``cli.py`` to keep each file under the project's 150-line-per-file limit.
The handler functions themselves (``_run_peer``/``_run_replay``/``_run_audit``)
stay in ``cli.py`` and are wired in via ``set_defaults(handler=...)``.
"""

from __future__ import annotations

import argparse
from collections.abc import Callable
from pathlib import Path

Handler = Callable[[argparse.Namespace], int]


def build_parser(
    run_peer: Handler, run_replay: Handler, run_audit: Handler
) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="police-thief",
        description="Distributed Cops-and-Robbers over a Peer-to-Peer Network.",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="show full tracebacks on error instead of a clean message",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    peer = subparsers.add_parser("peer", help="start this side of a game (police or thief)")
    peer.add_argument("--role", choices=["police", "thief"], required=True)
    peer.add_argument(
        "--config-dir",
        type=Path,
        default=Path("config"),
        help="directory containing game.json and <role>/game.toml (default: ./config)",
    )
    peer.add_argument(
        "--game-id", default="local-demo", help="identifier used in the four JSON deliverables"
    )
    peer.add_argument(
        "--output-dir",
        type=Path,
        default=Path("logs"),
        help="directory to write the four JSON deliverables into (default: ./logs)",
    )
    peer.add_argument(
        "--max-wait-seconds",
        type=float,
        default=180.0,
        help="give up on an unresponsive opponent after this many seconds",
    )
    peer.add_argument(
        "--gui",
        action="store_true",
        help="show the local-truth-only live belief heatmap (requires a display)",
    )
    peer.set_defaults(handler=run_peer)

    replay = subparsers.add_parser("replay", help="verify and replay a finished game log")
    replay.add_argument(
        "--log", type=Path, required=True, help="path to a log_<game_id>_g<NN>.json file"
    )
    replay.set_defaults(handler=run_replay)

    audit = subparsers.add_parser(
        "audit", help="FR-083: check this team's own games-played count against the league config"
    )
    audit.add_argument(
        "--logs-dir",
        type=Path,
        default=Path("logs"),
        help="directory to scan recursively for declaration_*.json files (default: ./logs)",
    )
    audit.add_argument("--group-id", required=True, help="this team's group_id, per game.toml")
    audit.add_argument(
        "--config-dir",
        type=Path,
        default=Path("config"),
        help="directory containing game.json (default: ./config)",
    )
    audit.set_defaults(handler=run_audit)

    return parser
