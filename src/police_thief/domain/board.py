"""Board state, movement legality, barrier placement, capture and win detection.

Pure domain logic — no networking, no I/O, no randomness (NFR-001). Every rule
here traces to a requirement ID in docs/requirements_analysis.md; see the
docstring on each method.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from police_thief.domain.models import Coordinate, Direction, GameConfig, Role


class IllegalActionError(Exception):
    """Raised when a move or barrier placement violates the game's rules.

    This is a normal, expected outcome for an out-of-turn or out-of-bounds
    request — callers (the Orchestrator, Part 9) catch it and turn it into a
    protocol-level rejection; it is not a bug when raised.
    """


class Outcome(StrEnum):
    """Terminal reasons a game can end (FR-018, FR-020/021)."""

    ONGOING = "ongoing"
    CAPTURE = "capture"  # cop reached/cornered the thief (FR-018 a/b)
    THIEF_STRANDED = "thief_stranded"  # thief has no legal move (E-47, assumptions A-013)
    SURVIVAL = "survival"  # thief survived to the move/survival cap (FR-017)


@dataclass
class BoardState:
    """Mutable board state for one game. Construct via :meth:`initial`."""

    config: GameConfig
    cop_position: Coordinate
    thief_position: Coordinate
    barriers: set[Coordinate] = field(default_factory=set)
    barriers_placed: int = 0
    moves_made: int = 0
    thief_moves_survived: int = 0
    outcome: Outcome = Outcome.ONGOING

    @classmethod
    def initial(cls, config: GameConfig) -> BoardState:
        return cls(
            config=config,
            cop_position=config.start_position(Role.POLICE),
            thief_position=config.start_position(Role.THIEF),
        )

    # -- read-only queries -------------------------------------------------

    def position_of(self, role: Role) -> Coordinate:
        return self.cop_position if role is Role.POLICE else self.thief_position

    def in_bounds(self, coord: Coordinate) -> bool:
        n = self.config.board_and_agents.grid_size
        return 0 <= coord.row < n and 0 <= coord.col < n

    def is_legal_move(self, role: Role, direction: Direction) -> bool:
        """FR-014/FR-015: 4-directional + STAY, in bounds, not into a barrier."""
        if direction not in self.config.movement_and_barriers.move_set:
            return False
        if direction is Direction.STAY:
            return True
        target = self.position_of(role).translated(direction)
        return self.in_bounds(target) and target not in self.barriers

    def legal_moves(self, role: Role) -> list[Direction]:
        return [
            d for d in self.config.movement_and_barriers.move_set if self.is_legal_move(role, d)
        ]

    def can_place_barrier(self, coord: Coordinate) -> bool:
        """§3.4: a barrier lands on the cop's own cell or an orthogonal neighbor
        (Manhattan distance <= 1), consuming the cop's move for that turn.
        """
        if self.barriers_placed >= self.config.movement_and_barriers.max_barriers:
            return False
        if not self.in_bounds(coord):
            return False
        if coord in self.barriers:
            return False
        return self.cop_position.manhattan_distance(coord) <= 1

    # -- mutations -----------------------------------------------------------

    def apply_move(self, role: Role, direction: Direction) -> None:
        """Move ``role`` one step. Raises :class:`IllegalActionError` if illegal.

        Capture-by-arrival (FR-018 a) is detected here: if the cop's move lands
        on the thief's current cell, ``outcome`` becomes ``CAPTURE``.
        """
        if self.outcome is not Outcome.ONGOING:
            raise IllegalActionError("game is already over")
        if not self.is_legal_move(role, direction):
            raise IllegalActionError(
                f"{role.value} cannot move {direction.value} from the current state"
            )

        new_pos = self.position_of(role).translated(direction)
        if role is Role.POLICE:
            self.cop_position = new_pos
        else:
            self.thief_position = new_pos
            self.thief_moves_survived += 1
        self.moves_made += 1

        if self.cop_position == self.thief_position:
            self.outcome = Outcome.CAPTURE
        elif (
            role is Role.THIEF
            and self.thief_moves_survived >= self.config.movement_and_barriers.survival_threshold
        ) or self.moves_made >= self.config.movement_and_barriers.max_moves:
            self.outcome = Outcome.SURVIVAL
        elif role is Role.THIEF and not self.legal_moves(Role.THIEF):
            # assumptions.md A-013: a thief with literally no legal move (STAY
            # excluded from move_set in a non-default config) is stranded.
            self.outcome = Outcome.THIEF_STRANDED

    def place_barrier(self, coord: Coordinate) -> None:
        """FR-015/016: consumes the cop's turn instead of a move.

        Capture-by-cornering (FR-018 b, E-46) is detected here: a barrier
        placed on the thief's current cell is an immediate capture.
        """
        if self.outcome is not Outcome.ONGOING:
            raise IllegalActionError("game is already over")
        if not self.can_place_barrier(coord):
            raise IllegalActionError(f"barrier cannot be placed at {coord!r}")

        self.barriers.add(coord)
        self.barriers_placed += 1
        self.moves_made += 1
        if coord == self.thief_position:
            self.outcome = Outcome.CAPTURE
        elif self.moves_made >= self.config.movement_and_barriers.max_moves:
            self.outcome = Outcome.SURVIVAL
