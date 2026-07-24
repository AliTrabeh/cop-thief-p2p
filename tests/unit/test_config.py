"""Unit tests for config.py — NFR-005/NFR-008, TEST-001 (shared
config/game.json half; peer game.toml tests live in the sibling file
test_peer_config.py, split out to keep each file under 150 lines).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from _config_fixtures import VALID_GAME_JSON

from police_thief.config import ConfigError, load_game_config, shared_config_hash


def test_load_game_config_round_trips_the_books_own_example(tmp_path: Path):
    path = tmp_path / "game.json"
    path.write_text(json.dumps(VALID_GAME_JSON), encoding="utf-8")
    cfg = load_game_config(path)
    assert cfg.board_and_agents.grid_size == 7
    assert cfg.scoring.capture_cop == 20
    assert cfg.network_and_league.num_games == 6


def test_load_game_config_missing_file_raises_config_error(tmp_path: Path):
    with pytest.raises(ConfigError, match="not found"):
        load_game_config(tmp_path / "nope.json")


def test_load_game_config_invalid_json_raises_config_error(tmp_path: Path):
    path = tmp_path / "game.json"
    path.write_text("{not valid json", encoding="utf-8")
    with pytest.raises(ConfigError, match="not valid JSON"):
        load_game_config(path)


def test_load_game_config_schema_violation_raises_config_error(tmp_path: Path):
    bad = dict(VALID_GAME_JSON)
    bad["board_and_agents"] = {**VALID_GAME_JSON["board_and_agents"], "grid_size": 3}  # type: ignore[dict-item]
    path = tmp_path / "game.json"
    path.write_text(json.dumps(bad), encoding="utf-8")
    with pytest.raises(ConfigError, match="failed validation"):
        load_game_config(path)


def test_load_game_config_rejects_unknown_top_level_field(tmp_path: Path):
    bad = {**VALID_GAME_JSON, "totally_made_up_field": 1}
    path = tmp_path / "game.json"
    path.write_text(json.dumps(bad), encoding="utf-8")
    with pytest.raises(ConfigError, match="failed validation"):
        load_game_config(path)


def test_load_game_config_rejects_unknown_nested_field(tmp_path: Path):
    bad = json.loads(json.dumps(VALID_GAME_JSON))
    bad["scoring"]["captur_cop"] = 20  # a plausible typo of "capture_cop"
    path = tmp_path / "game.json"
    path.write_text(json.dumps(bad), encoding="utf-8")
    with pytest.raises(ConfigError, match="failed validation"):
        load_game_config(path)


def test_shared_config_hash_is_identical_for_byte_identical_files(tmp_path: Path):
    path_a = tmp_path / "a" / "game.json"
    path_b = tmp_path / "b" / "game.json"
    path_a.parent.mkdir()
    path_b.parent.mkdir()
    path_a.write_text(json.dumps(VALID_GAME_JSON), encoding="utf-8")
    path_b.write_text(
        json.dumps(VALID_GAME_JSON, indent=2), encoding="utf-8"
    )  # different whitespace
    assert shared_config_hash(path_a) == shared_config_hash(path_b)


def test_shared_config_hash_differs_for_a_tampered_field(tmp_path: Path):
    path_a = tmp_path / "a.json"
    path_b = tmp_path / "b.json"
    path_a.write_text(json.dumps(VALID_GAME_JSON), encoding="utf-8")
    tampered = json.loads(json.dumps(VALID_GAME_JSON))
    tampered["scoring"]["capture_cop"] = 999
    path_b.write_text(json.dumps(tampered), encoding="utf-8")
    assert shared_config_hash(path_a) != shared_config_hash(path_b)
