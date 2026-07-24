"""Shared fixture data for the config unit tests (test_config.py,
test_peer_config.py) — not itself a test file (no ``test_`` prefix, so
pytest doesn't collect it), split out purely to keep each test file under
150 lines.
"""

from __future__ import annotations

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
