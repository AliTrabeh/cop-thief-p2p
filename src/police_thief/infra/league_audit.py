"""FR-083: the mutual daily-log / games-played-count audit for a multi-game
league series (Appendix F Table 18: ``num_games``, ``min_games_to_pass``,
``max_games_per_team``).

Scoped honestly to what a single peer can verify from its own deliverables
directory: how many of *this team's own* games have actually been played
(one ``declaration_<game_id>.json`` + matching ``result_<game_id>.json``
pair per completed game, per FR-082), and whether that count falls inside
the league's configured range. A genuinely *mutual* cross-team audit
additionally requires comparing this report against the rival team's own
logs -- an out-of-band step, exactly like the tunnel-URL exchange in
``infra/tunnel.py`` (docs/assumptions.md A-018) -- since no component in
this P2P design has a central view of both sides' logs at once (FR-001).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from police_thief.domain.models import NetworkAndLeagueConfig


@dataclass(frozen=True)
class GameRecord:
    game_id: str
    sub_game_number: int
    outcome: str | None
    declaration_path: Path
    result_path: Path | None


@dataclass(frozen=True)
class AuditReport:
    group_id: str
    logs_dir: Path
    games: tuple[GameRecord, ...]
    min_games_to_pass: int
    max_games_per_team: int
    num_games: int
    issues: tuple[str, ...] = field(default_factory=tuple)

    @property
    def games_played(self) -> int:
        return len(self.games)

    @property
    def meets_minimum(self) -> bool:
        return self.games_played >= self.min_games_to_pass

    @property
    def within_maximum(self) -> bool:
        return self.games_played <= self.max_games_per_team

    @property
    def passes(self) -> bool:
        return self.meets_minimum and self.within_maximum and not self.issues

    def summary_lines(self) -> list[str]:
        lines = [
            f"League audit for group_id={self.group_id!r} in {self.logs_dir}",
            f"  games played:        {self.games_played}",
            f"  min_games_to_pass:   {self.min_games_to_pass} "
            f"({'OK' if self.meets_minimum else 'NOT MET'})",
            f"  max_games_per_team:  {self.max_games_per_team} "
            f"({'OK' if self.within_maximum else 'EXCEEDED'})",
            f"  series size (num_games): {self.num_games}",
        ]
        if self.issues:
            lines.append("  issues:")
            lines.extend(f"    - {issue}" for issue in self.issues)
        lines.append(f"  overall: {'PASS' if self.passes else 'FAIL'}")
        return lines


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))  # type: ignore[no-any-return]
    except (OSError, json.JSONDecodeError):
        return None


def audit_league_series(
    logs_dir: Path, group_id: str, league_config: NetworkAndLeagueConfig
) -> AuditReport:
    """Scan every ``declaration_*.json`` under ``logs_dir`` (recursively --
    the two-role output-dir layout, e.g. ``logs/<game-id>/<role>/``, is not
    assumed), keep the ones belonging to ``group_id``, and pair each with
    its ``result_<game_id>.json`` sibling.
    """
    games: list[GameRecord] = []
    issues: list[str] = []
    seen_game_ids: set[str] = set()

    for declaration_path in sorted(logs_dir.rglob("declaration_*.json")):
        data = _read_json(declaration_path)
        if data is None:
            issues.append(f"unreadable/malformed declaration file: {declaration_path}")
            continue
        if data.get("group_id") != group_id:
            continue
        game_id = data.get("game_id")
        if not isinstance(game_id, str):
            issues.append(f"declaration missing game_id: {declaration_path}")
            continue
        if game_id in seen_game_ids:
            issues.append(f"duplicate declaration for game_id={game_id!r} at {declaration_path}")
            continue
        seen_game_ids.add(game_id)

        result_path = declaration_path.parent / f"result_{game_id}.json"
        result_data = _read_json(result_path) if result_path.exists() else None
        if result_data is None:
            issues.append(f"no matching result_{game_id}.json next to {declaration_path}")

        games.append(
            GameRecord(
                game_id=game_id,
                sub_game_number=int(data.get("sub_game_number", 1)),
                outcome=result_data.get("outcome") if result_data else None,
                declaration_path=declaration_path,
                result_path=result_path if result_data is not None else None,
            )
        )

    return AuditReport(
        group_id=group_id,
        logs_dir=logs_dir,
        games=tuple(games),
        min_games_to_pass=league_config.min_games_to_pass,
        max_games_per_team=league_config.max_games_per_team,
        num_games=league_config.num_games,
        issues=tuple(issues),
    )


__all__ = ["AuditReport", "GameRecord", "audit_league_series"]
