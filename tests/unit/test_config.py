"""Unit tests for config.py — NFR-005/NFR-008, TEST-001."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from police_thief.config import (
    ConfigError,
    load_game_config,
    load_peer_config,
    shared_config_hash,
)

VALID_GAME_JSON: dict[str, object] = {
    "schema_version": "1.2",
    "agreed_between": ["group-a", "group-b"],
    "board_and_agents": {
        "grid_size": 7,
        "num_agents": 2,
        "thief_start": [3, 3],
        "cop_start": [0, 0],
        "axis_origin_corner": "top-left",
        "axis_start_index": 0,
    },
    "world": {"map_area": "New York", "hint_max_words": 15},
    "movement_and_barriers": {
        "move_set": ["N", "S", "E", "W", "STAY"],
        "max_barriers": 14,
        "max_moves": 35,
        "survival_threshold": 35,
    },
    "scoring": {
        "capture_cop": 20,
        "capture_thief": 5,
        "survival_cop": 5,
        "survival_thief": 10,
        "tie_score": 2,
        "technical_loss": 0,
    },
    "pheromones": {
        "pheromone_center_intensity": 0.9,
        "pheromone_decay": 0.10,
        "pheromone_grid_size": 5,
    },
    "network_and_league": {
        "response_timeout_sec": 30,
        "watchdog_timeout_sec": 60,
        "num_games": 6,
        "diversity_reward": 10,
        "min_games_to_pass": 2,
        "max_games_per_team": 10,
        "token_budget_per_series": 200000,
    },
    "rate_limiter_gatekeeper": {
        "requests_per_minute": 30,
        "concurrent_requests": 2,
        "retry_backoff_sec": 5,
        "max_retries": 3,
        "queue_depth": 100,
    },
}

VALID_PEER_TOML = """
version = "1.10"

[game]
group_name = "My-Team"
group_id = "my-team"
sub_game_number = 1
members = ["id-1001", "id-1002"]
repos = { cop = "https://github.com/you/repo", thief = "https://github.com/you/repo" }

[network]
my_port = 8802
opponent_url = "http://127.0.0.1:8801/mcp"
turn_timeout_seconds = 180

[llm]
model = "template"
step_deadline_seconds = 30

[email]
recipient = "rmisegal+uoh26finalgame@gmail.com"
mode = "draft"
"""


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


def test_load_peer_config_round_trips_the_books_own_example(tmp_path: Path):
    path = tmp_path / "game.toml"
    path.write_text(VALID_PEER_TOML, encoding="utf-8")
    cfg = load_peer_config(path)
    assert cfg.game.group_name == "My-Team"
    assert cfg.network.my_port == 8802
    assert cfg.llm.model == "template"
    assert cfg.email.mode == "draft"


def test_load_peer_config_missing_file_raises_config_error(tmp_path: Path):
    with pytest.raises(ConfigError, match="not found"):
        load_peer_config(tmp_path / "nope.toml")


def test_load_peer_config_invalid_toml_raises_config_error(tmp_path: Path):
    path = tmp_path / "game.toml"
    path.write_text("not = [valid toml", encoding="utf-8")
    with pytest.raises(ConfigError, match="not valid TOML"):
        load_peer_config(path)


def test_load_peer_config_missing_required_field_raises_config_error(tmp_path: Path):
    path = tmp_path / "game.toml"
    path.write_text(
        'version = "1.0"\n[network]\nmy_port = 1\nopponent_url = "x"\n', encoding="utf-8"
    )
    with pytest.raises(ConfigError, match="failed validation"):
        load_peer_config(path)
