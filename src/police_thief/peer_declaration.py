"""Pre-game Step-0 declaration writing, split out of ``peer_startup.py`` to
keep each file under the project's 150-line-per-file limit. See that
module's docstring for why the declaration is written before the game
rather than bundled with the other three deliverables at the end (book
§5.5 "Step-0 and Computational Fairness", Appendix E item 24).
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from police_thief.config import PeerConfig
from police_thief.domain.game_config import GameConfig
from police_thief.infra.hardware_declaration import collect_hardware_spec
from police_thief.infra.league_audit import audit_league_series
from police_thief.infra.reporting_writers import write_declaration
from police_thief.logging_setup import get_logger

logger = get_logger("peer_runtime")


def games_played_so_far(output_dir: Path, group_id: str, game_config: GameConfig) -> int | None:
    """Best-effort count of this team's own games already on disk (Appendix
    E item 37: declare accurately at the start of every game). Assumes the
    documented ``logs/<game_id>/<role>/`` layout (``output_dir.parent.parent``
    is the logs root); gracefully returns ``None`` if that assumption
    doesn't hold or the scan fails for any reason -- this must never block
    a peer from starting.
    """
    try:
        logs_root = output_dir.parent.parent
        return audit_league_series(logs_root, group_id, game_config.network_and_league).games_played
    except Exception:  # noqa: BLE001 - a best-effort declaration field, never fatal
        return None


def write_pre_game_declaration(
    output_dir: Path,
    peer_config: PeerConfig,
    game_id: str,
    commit_hash: str,
    game_config: GameConfig,
) -> None:
    write_declaration(
        output_dir,
        peer_config,
        game_id,
        commit_hash,
        datetime.now(UTC).isoformat(),
        hardware=collect_hardware_spec(),
        games_played_so_far=games_played_so_far(output_dir, peer_config.game.group_id, game_config),
    )
    logger.info("wrote pre-game declaration to %s", output_dir / f"declaration_{game_id}.json")
