"""Unit tests for infra/league_audit.py — FR-083 (multi-game league audit).

All fixtures are hand-written JSON files on a tmp_path; no real game needs
to have been played to exercise this module.
"""

from __future__ import annotations

import json
from pathlib import Path

from police_thief.domain.models import NetworkAndLeagueConfig
from police_thief.infra.league_audit import audit_league_series

LEAGUE_CONFIG = NetworkAndLeagueConfig(min_games_to_pass=2, max_games_per_team=10, num_games=6)


def _write_game(
    dir_: Path,
    game_id: str,
    group_id: str,
    *,
    sub_game_number: int = 1,
    outcome: str = "capture",
    with_result: bool = True,
) -> None:
    dir_.mkdir(parents=True, exist_ok=True)
    (dir_ / f"declaration_{game_id}.json").write_text(
        json.dumps(
            {
                "game_id": game_id,
                "group_id": group_id,
                "sub_game_number": sub_game_number,
            }
        ),
        encoding="utf-8",
    )
    if with_result:
        (dir_ / f"result_{game_id}.json").write_text(
            json.dumps({"game_id": game_id, "outcome": outcome}), encoding="utf-8"
        )


def test_audit_counts_only_this_teams_games(tmp_path: Path) -> None:
    _write_game(tmp_path / "g1" / "police", "g1", "my-team")
    _write_game(tmp_path / "g2" / "police", "g2", "rival-team")
    report = audit_league_series(tmp_path, "my-team", LEAGUE_CONFIG)
    assert report.games_played == 1
    assert report.games[0].game_id == "g1"


def test_audit_scans_recursively_across_role_subdirectories(tmp_path: Path) -> None:
    _write_game(tmp_path / "g1" / "police", "g1", "my-team")
    _write_game(tmp_path / "g2" / "thief", "g2", "my-team")
    report = audit_league_series(tmp_path, "my-team", LEAGUE_CONFIG)
    assert report.games_played == 2


def test_audit_below_minimum_fails(tmp_path: Path) -> None:
    _write_game(tmp_path / "g1" / "police", "g1", "my-team")
    report = audit_league_series(tmp_path, "my-team", LEAGUE_CONFIG)
    assert not report.meets_minimum
    assert not report.passes


def test_audit_within_range_passes(tmp_path: Path) -> None:
    for i in range(2):
        _write_game(tmp_path / f"g{i}" / "police", f"g{i}", "my-team")
    report = audit_league_series(tmp_path, "my-team", LEAGUE_CONFIG)
    assert report.meets_minimum
    assert report.within_maximum
    assert report.passes


def test_audit_exceeding_maximum_fails(tmp_path: Path) -> None:
    cfg = NetworkAndLeagueConfig(min_games_to_pass=1, max_games_per_team=2, num_games=6)
    for i in range(3):
        _write_game(tmp_path / f"g{i}" / "police", f"g{i}", "my-team")
    report = audit_league_series(tmp_path, "my-team", cfg)
    assert report.games_played == 3
    assert not report.within_maximum
    assert not report.passes


def test_audit_flags_missing_result_file(tmp_path: Path) -> None:
    _write_game(tmp_path / "g1" / "police", "g1", "my-team", with_result=False)
    report = audit_league_series(tmp_path, "my-team", LEAGUE_CONFIG)
    assert any("no matching result_" in issue for issue in report.issues)
    assert not report.passes


def test_audit_flags_duplicate_declaration_for_same_game_id(tmp_path: Path) -> None:
    _write_game(tmp_path / "a" / "police", "g1", "my-team")
    _write_game(tmp_path / "b" / "police", "g1", "my-team")
    report = audit_league_series(tmp_path, "my-team", LEAGUE_CONFIG)
    assert report.games_played == 1
    assert any("duplicate declaration" in issue for issue in report.issues)


def test_audit_flags_malformed_declaration_file(tmp_path: Path) -> None:
    bad_dir = tmp_path / "g1" / "police"
    bad_dir.mkdir(parents=True)
    (bad_dir / "declaration_g1.json").write_text("{not valid json", encoding="utf-8")
    report = audit_league_series(tmp_path, "my-team", LEAGUE_CONFIG)
    assert report.games_played == 0
    assert any("unreadable/malformed" in issue for issue in report.issues)


def test_audit_empty_logs_dir_is_a_clean_zero_games_report(tmp_path: Path) -> None:
    report = audit_league_series(tmp_path, "my-team", LEAGUE_CONFIG)
    assert report.games_played == 0
    assert report.issues == ()
    assert not report.passes  # below min_games_to_pass, but no *issues* -- just zero games


def test_summary_lines_render_pass_and_fail_text(tmp_path: Path) -> None:
    for i in range(2):
        _write_game(tmp_path / f"g{i}" / "police", f"g{i}", "my-team")
    report = audit_league_series(tmp_path, "my-team", LEAGUE_CONFIG)
    text = "\n".join(report.summary_lines())
    assert "my-team" in text
    assert "PASS" in text
