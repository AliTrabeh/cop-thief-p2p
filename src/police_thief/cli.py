"""Command-line entry point: ``python -m police_thief``."""

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
    peer.set_defaults(handler=_run_peer)

    replay = subparsers.add_parser("replay", help="verify and replay a finished game log")
    replay.add_argument(
        "--log", type=Path, required=True, help="path to a log_<game_id>_g<NN>.json file"
    )
    replay.set_defaults(handler=_run_replay)

    return parser


def _run_peer(args: argparse.Namespace) -> int:
    import asyncio

    from police_thief.domain.models import Role
    from police_thief.logging_setup import configure_logging
    from police_thief.peer_runtime import PeerRuntimeError, run_peer

    configure_logging("DEBUG" if args.debug else "INFO")
    role = Role(args.role)
    print(f"Starting {role.value} peer (game_id={args.game_id!r}, config_dir={args.config_dir})...")
    try:
        orch = asyncio.run(
            run_peer(
                role,
                args.config_dir,
                args.game_id,
                output_dir=args.output_dir,
                max_wait_seconds=args.max_wait_seconds,
            )
        )
    except PeerRuntimeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if orch.technical_loss_reason is not None:
        print(f"Game over: TECHNICAL LOSS ({orch.technical_loss_reason})")
        return 2
    print(f"Game over: {orch.board.outcome.value} after {orch.board.moves_made} moves.")
    print(f"Final positions: cop={orch.board.cop_position}, thief={orch.board.thief_position}")
    return 0


def _run_replay(args: argparse.Namespace) -> int:
    from police_thief.gui.replay_viewer import ReplayError, verify_log_file

    try:
        verdict = verify_log_file(args.log)
    except ReplayError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(f"Replay of {args.log}: {verdict}")
    return 0 if verdict == "Verified OK" else 2


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
