"""Deterministic domain models: coordinates, moves, and the shared game config.

The config models mirror ``config/game.json`` field-for-field (see docs/protocol.md
§5) so a parsed JSON file maps 1:1 onto ``GameConfig`` with no renamed fields
(NFR-005). Parsing the file itself (I/O) lives in ``police_thief.config``
(Part 3); this module only defines the shapes and their validation rules.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Role(StrEnum):
    """Which side of the game this peer is playing."""

    POLICE = "police"
    THIEF = "thief"


class Direction(StrEnum):
    """The fixed movement vocabulary (FR-014): 4 orthogonal directions + STAY.

    Diagonal movement does not exist as a value here at all (assumptions.md A-010)
    — it is not merely rejected at runtime, it cannot be constructed.
    """

    NORTH = "N"
    SOUTH = "S"
    EAST = "E"
    WEST = "W"
    STAY = "STAY"


_DELTAS: dict[Direction, tuple[int, int]] = {
    Direction.NORTH: (-1, 0),
    Direction.SOUTH: (1, 0),
    Direction.EAST: (0, 1),
    Direction.WEST: (0, -1),
    Direction.STAY: (0, 0),
}


class Coordinate(BaseModel):
    """A board cell. ``axis_origin_corner = "top-left"``, ``axis_start_index = 0``:
    row 0 is the top row, col 0 is the left column, NORTH decreases row.
    """

    model_config = ConfigDict(frozen=True)

    row: int
    col: int

    def translated(self, direction: Direction) -> Coordinate:
        dr, dc = _DELTAS[direction]
        return Coordinate(row=self.row + dr, col=self.col + dc)

    def manhattan_distance(self, other: Coordinate) -> int:
        return abs(self.row - other.row) + abs(self.col - other.col)


class BoardAndAgentsConfig(BaseModel):
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


class WorldConfig(BaseModel):
    map_area: str = ""
    hint_max_words: int = Field(ge=0, default=15)


class MovementAndBarriersConfig(BaseModel):
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


class ScoringConfig(BaseModel):
    capture_cop: int = 20
    capture_thief: int = 5
    survival_cop: int = 5
    survival_thief: int = 10
    tie_score: int = 2
    technical_loss: int = 0


class PheromoneConfig(BaseModel):
    pheromone_center_intensity: float = 0.9
    pheromone_decay: float = Field(ge=0.0, le=1.0, default=0.10)
    pheromone_grid_size: int = Field(ge=1, default=5)

    @model_validator(mode="after")
    def _check(self) -> PheromoneConfig:
        if self.pheromone_grid_size % 2 == 0:
            raise ValueError("pheromone_grid_size must be odd (centered on the emitting agent)")
        return self


class NetworkAndLeagueConfig(BaseModel):
    response_timeout_sec: int = 30
    watchdog_timeout_sec: int = 60
    num_games: int = 6
    diversity_reward: int = 10
    min_games_to_pass: int = 2
    max_games_per_team: int = 10
    token_budget_per_series: int = 200_000


class RateLimiterGatekeeperConfig(BaseModel):
    requests_per_minute: int = Field(ge=30, default=30)
    concurrent_requests: int = Field(ge=2, default=2)
    retry_backoff_sec: int = Field(ge=5, default=5)
    max_retries: int = Field(ge=3, default=3)
    queue_depth: int = Field(ge=100, default=100)


class GameConfig(BaseModel):
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
