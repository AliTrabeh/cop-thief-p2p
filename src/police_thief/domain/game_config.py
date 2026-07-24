"""The shared game config shape (``config/game.json``, docs/protocol.md §5),
split out of ``domain/models.py`` to keep each file under 150 lines.
``domain/models.py`` keeps the core value types (``Role``/``Direction``/
``Coordinate``); this module mirrors the JSON file field-for-field so a
parsed file maps 1:1 onto :class:`GameConfig`, no renamed fields (NFR-005).
Parsing the file (I/O) lives in ``police_thief.config`` (Part 3).
"""

from __future__ import annotations

from pydantic import Field, model_validator

from police_thief.domain.models import Coordinate, Direction, Role, _StrictConfigModel
from police_thief.domain.rate_limiter_config import RateLimiterGatekeeperConfig


class BoardAndAgentsConfig(_StrictConfigModel):
    grid_size: int = Field(ge=7)
    num_agents: int = Field(default=2)
    thief_start: tuple[int, int]
    cop_start: tuple[int, int]
    axis_origin_corner: str = "top-left"
    axis_start_index: int = 0

    @model_validator(mode="after")
    def _check(self) -> BoardAndAgentsConfig:
        if self.num_agents != 2:
            raise ValueError("num_agents is Fixed at 2 (Appendix F Table 13 #2)")
        if self.axis_origin_corner != "top-left":
            raise ValueError("only the top-left origin convention is implemented")
        if self.axis_start_index != 0:
            raise ValueError("only a zero-based axis start index is implemented")
        for name, (r, c) in (("thief_start", self.thief_start), ("cop_start", self.cop_start)):
            if not (0 <= r < self.grid_size and 0 <= c < self.grid_size):
                raise ValueError(
                    f"{name} {(r, c)} is outside a {self.grid_size}x{self.grid_size} board"
                )
        if self.thief_start == self.cop_start:
            raise ValueError("thief_start and cop_start must not coincide")
        return self


class WorldConfig(_StrictConfigModel):
    map_area: str = ""
    hint_max_words: int = Field(ge=0, default=15)


class MovementAndBarriersConfig(_StrictConfigModel):
    move_set: list[Direction] = Field(
        default_factory=lambda: [
            Direction.NORTH,
            Direction.SOUTH,
            Direction.EAST,
            Direction.WEST,
            Direction.STAY,
        ]
    )
    max_barriers: int = Field(ge=14)
    max_moves: int = Field(ge=35)
    survival_threshold: int = Field(ge=35)

    @model_validator(mode="after")
    def _check(self) -> MovementAndBarriersConfig:
        if any(
            d not in self.move_set
            for d in (Direction.NORTH, Direction.SOUTH, Direction.EAST, Direction.WEST)
        ):
            raise ValueError("move_set must include all 4 orthogonal directions (E-13/E-14)")
        return self


class ScoringConfig(_StrictConfigModel):
    capture_cop: int = 20
    capture_thief: int = 5
    survival_cop: int = 5
    survival_thief: int = 10
    tie_score: int = 2
    technical_loss: int = 0


class PheromoneConfig(_StrictConfigModel):
    pheromone_center_intensity: float = 0.9
    pheromone_decay: float = Field(ge=0.0, le=1.0, default=0.10)
    pheromone_grid_size: int = Field(ge=1, default=5)

    @model_validator(mode="after")
    def _check(self) -> PheromoneConfig:
        if self.pheromone_grid_size % 2 == 0:
            raise ValueError("pheromone_grid_size must be odd (centered on the emitting agent)")
        return self


class NetworkAndLeagueConfig(_StrictConfigModel):
    response_timeout_sec: int = 30
    watchdog_timeout_sec: int = 60
    num_games: int = 6
    diversity_reward: int = 10
    min_games_to_pass: int = 2
    max_games_per_team: int = 10
    token_budget_per_series: int = 200_000


class GameConfig(_StrictConfigModel):
    """Mirrors ``config/game.json`` exactly (docs/protocol.md §5)."""

    schema_version: str
    agreed_between: list[str]
    board_and_agents: BoardAndAgentsConfig
    world: WorldConfig = Field(default_factory=WorldConfig)
    movement_and_barriers: MovementAndBarriersConfig
    scoring: ScoringConfig = Field(default_factory=ScoringConfig)
    pheromones: PheromoneConfig = Field(default_factory=PheromoneConfig)
    network_and_league: NetworkAndLeagueConfig = Field(default_factory=NetworkAndLeagueConfig)
    rate_limiter_gatekeeper: RateLimiterGatekeeperConfig = Field(
        default_factory=RateLimiterGatekeeperConfig
    )

    @model_validator(mode="after")
    def _check_barrier_headroom(self) -> GameConfig:
        # assumptions.md A-009: barriers must leave room for both agents + a path.
        size = self.board_and_agents.grid_size
        free_cells = size * size - 2
        if self.movement_and_barriers.max_barriers >= free_cells:
            raise ValueError(
                f"max_barriers ({self.movement_and_barriers.max_barriers}) leaves no free path "
                f"on a {size}x{size} board (assumptions.md A-009)"
            )
        return self

    def start_position(self, role: Role) -> Coordinate:
        r, c = (
            self.board_and_agents.cop_start
            if role is Role.POLICE
            else self.board_and_agents.thief_start
        )
        return Coordinate(row=r, col=c)
