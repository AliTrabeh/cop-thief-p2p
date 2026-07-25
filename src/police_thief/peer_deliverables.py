"""End-of-game deliverable writing + reporting, split out of ``peer_runtime.py``
to keep each file under the project's 150-line-per-file limit: the three
post-game JSON files (config snapshot, log, result — FR-082; the pre-game
declaration is written separately by ``peer_declaration.py``) plus the
Gatekeeper-guarded match-result email (FR-080/081), both one-shot steps run
once a game has finished.
"""

from __future__ import annotations

import time
from pathlib import Path

from police_thief.config import PeerConfig
from police_thief.infra.gatekeeper import Gatekeeper
from police_thief.infra.gmail_report import report_match_result
from police_thief.infra.reporting import build_result
from police_thief.infra.reporting_writers import write_post_game_deliverables
from police_thief.logging_setup import get_logger
from police_thief.orchestrator import Orchestrator

logger = get_logger("peer_runtime")


def write_deliverables(
    orch: Orchestrator, peer_config: PeerConfig, game_id: str, output_dir: Path, commit_hash: str
) -> None:
    paths = write_post_game_deliverables(
        output_dir=output_dir,
        orch=orch,
        game_id=game_id,
        sub_game_number=peer_config.game.sub_game_number,
        commit_hash=commit_hash,
    )
    logger.info("wrote match deliverables: %s", {k: str(v) for k, v in paths.items()})

    gatekeeper = Gatekeeper(orch.config.rate_limiter_gatekeeper, clock=time.monotonic)
    status = report_match_result(
        mode=peer_config.email.mode,
        recipient=peer_config.email.recipient,
        result_json=build_result(orch, game_id, commit_hash=commit_hash),
        gatekeeper=gatekeeper,
        output_dir=output_dir,
        game_id=game_id,
    )
    logger.info("email report: %s", status)
