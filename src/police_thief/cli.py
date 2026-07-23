"""Command-line entry point: ``python -m police_thief``.

Subcommands are defined here in full (this is the real, final CLI surface per
docs/implementation_plan.md Part 12); the ``peer`` and ``replay`` handlers are
wired up to real logic incrementally as later implementation parts land
(Parts 8-13). Each stub says exactly which part will fill it in and never
pretends to run a game it can't yet run.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def _build_parser() -> argparse.ArgumentParser:
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
    peer.set_defaults(handler=_run_peer)

    replay = subparsers.add_parser("replay", help="verify and replay a finished game log")
    replay.add_argument(
        "--log", type=Path, required=True, help="path to a log_<game_id>_g<NN>.json file"
    )
    replay.set_defaults(handler=_run_replay)

    return parser


def _run_peer(args: argparse.Namespace) -> int:
    raise NotImplementedError(
        "peer runtime lands in docs/implementation_plan.md Part 9 (Orchestrator) "
        "through Part 13 (GUI); not implemented yet."
    )


def _run_replay(args: argparse.Namespace) -> int:
    raise NotImplementedError(
        "replay viewer lands in docs/implementation_plan.md Part 13; not implemented yet."
    )


def main(argv: list[str] | None = None) -> None:
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        exit_code = args.handler(args)
    except NotImplementedError as exc:
        if args.debug:
            raise
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(1)
    except Exception as exc:  # noqa: BLE001 - top-level CLI boundary, intentional
        if args.debug:
            raise
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(1)
    else:
        sys.exit(exit_code or 0)


if __name__ == "__main__":
    main()
