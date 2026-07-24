"""Command-line entry point: ``python -m police_thief``.

Argument parser construction lives in ``cli_parser.py`` (split out to keep
each file under the project's 150-line-per-file limit); this file owns the
three subcommand handlers and the top-level error-handling wrapper.
"""

from __future__ import annotations

import argparse
import sys

from police_thief.cli_parser import build_parser


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
                show_gui=args.gui,
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


def _run_audit(args: argparse.Namespace) -> int:
    from police_thief.config import ConfigError, load_game_config
    from police_thief.infra.league_audit import audit_league_series

    try:
        game_config = load_game_config(args.config_dir / "game.json")
    except ConfigError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    report = audit_league_series(args.logs_dir, args.group_id, game_config.network_and_league)
    for line in report.summary_lines():
        print(line)
    return 0 if report.passes else 2


def main(argv: list[str] | None = None) -> None:
    parser = build_parser(_run_peer, _run_replay, _run_audit)
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
