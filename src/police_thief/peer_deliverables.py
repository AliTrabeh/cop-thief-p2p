"""End-of-game deliverable writing + reporting, split out of ``peer_runtime.py``
to keep each file under the project's 150-line-per-file limit: the four
mandatory JSON files (FR-082) plus the Gatekeeper-guarded match-result email
(FR-080/081), both one-shot steps run once a game has finished.
"""

from __future__ import annotations

import time
from datetime import UTC, datetime
from pathlib import Path

from police_thief.config import PeerConfig
from police_thief.infra.gatekeeper import Gatekeeper
from police_thief.infra.gmail_report import report_match_result
from police_thief.infra.reporting import build_result, write_match_deliverables
from police_thief.infra.vcs import current_commit_hash
from police_thief.logging_setup import get_logger
from police_thief.orchestrator import Orchestrator

logger = get_logger("peer_runtime")


def write_deliverables(
    orch: Orchestrator, peer_config: PeerConfig, game_id: str, output_dir: Path
) -> None:
    timestamp = datetime.now(UTC).isoformat()
    paths = write_match_deliverables(
        output_dir=output_dir,
        peer_config=peer_config,
        orch=orch,
        game_id=game_id,
        sub_game_number=peer_config.game.sub_game_number,
        commit_hash=current_commit_hash(),  # FR-087: real HEAD hash, "unknown" if not a checkout
        timestamp=timestamp,
    )
    logger.info("wrote match deliverables: %s", {k: str(v) for k, v in paths.items()})

    gatekeeper = Gatekeeper(orch.config.rate_limiter_gatekeeper, clock=time.monotonic)
    status = report_match_result(
        mode=peer_config.email.mode,
        recipient=peer_config.email.recipient,
        result_json=build_result(orch, game_id),
        gatekeeper=gatekeeper,
        output_dir=output_dir,
        game_id=game_id,
    )
    logger.info("email report: %s", status)
