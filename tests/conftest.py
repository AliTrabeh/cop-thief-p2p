"""Shared fixtures for unit tests: a minimal, valid GameConfig matching the
book's own worked example (docs/protocol.md §5), reused across test modules
so every test starts from the same known-good baseline.
"""

from __future__ import annotations

from collections.abc import Callable

import pytest

from police_thief.domain.models import (
    BoardAndAgentsConfig,
    GameConfig,
    MovementAndBarriersConfig,
)


def make_config(**overrides: object) -> GameConfig:
    base: dict[str, object] = {
        "schema_version": "1.2",
        "agreed_between": ["group-a", "group-b"],
        "board_and_agents": BoardAndAgentsConfig(
            grid_size=7,
            thief_start=(3, 3),
            cop_start=(0, 0),
        ),
        "movement_and_barriers": MovementAndBarriersConfig(
            max_barriers=14,
            max_moves=35,
            survival_threshold=35,
        ),
    }
    base.update(overrides)
    return GameConfig(**base)  # type: ignore[arg-type]


@pytest.fixture
def game_config() -> GameConfig:
    return make_config()


@pytest.fixture
def config_factory() -> Callable[..., GameConfig]:
    """Exposes ``make_config`` to test modules without a relative import
    (tests/ is not a package — pytest's rootdir-relative conftest discovery
    handles fixture sharing instead)."""
    return make_config
