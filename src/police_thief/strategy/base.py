"""Pluggable strategy interface (FR-060/FR-061, Appendix F Table 22).

A strategy only ever sees a :class:`BeliefView` — its own role, its own true
position, its own legal actions, and a normalized belief map over the
opponent's likely location. It never sees the opponent's true position
(the "local truth" boundary, FR-005, applies to strategies exactly as it
does to the GUI).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from police_thief.domain.board import BoardState
from police_thief.domain.models import Coordinate, Direction, Role
from police_thief.domain.scent import ScentField, belief_map


@dataclass(frozen=True)
class MoveAction:
    direction: Direction


@dataclass(frozen=True)
class BarrierAction:
    coord: Coordinate


Action = MoveAction | BarrierAction


@dataclass(frozen=True)
class BeliefView:
    """Everything a strategy is allowed to know when it decides."""

    role: Role
    own_position: Coordinate
    legal_moves: tuple[Direction, ...]
    can_place_barrier: bool
    barriers_remaining: int
    belief: dict[Coordinate, float]


def build_belief_view(board: BoardState, opponent_scent: ScentField, role: Role) -> BeliefView:
    """Assemble the local-truth-only view for ``role`` from the board and the
    scent field the opponent has left (never from the board's true opponent
    position, even though this function technically has access to it via
    ``board`` — callers in the Orchestrator must construct ``opponent_scent``
    from received hints only, not from ``board`` directly, to preserve FR-005
    once real networking replaces this in-process convenience path).
    """
    cfg = board.config
    b = belief_map(opponent_scent, cfg.board_and_agents.grid_size)
    return BeliefView(
        role=role,
        own_position=board.position_of(role),
        legal_moves=tuple(board.legal_moves(role)),
        can_place_barrier=(
            role is Role.POLICE and board.barriers_placed < cfg.movement_and_barriers.max_barriers
        ),
        barriers_remaining=cfg.movement_and_barriers.max_barriers - board.barriers_placed,
        belief=b,
    )


class BrainBase(ABC):
    """Base class for pluggable police/thief strategies (FR-060)."""

    @abstractmethod
    def _pick_move(self, view: BeliefView) -> Direction:
        """Choose a movement direction given the current belief view.

        Must return a direction present in ``view.legal_moves``; the caller
        (the Orchestrator, Part 9) is responsible for rejecting an illegal
        return value rather than silently correcting it.
        """

    def _decide_move(self, view: BeliefView) -> Action | None:
        """Optional richer decision hook (Appendix F Table 22): the cop may
        override this to choose barrier placement over movement. Returning
        ``None`` (the default) defers entirely to :meth:`_pick_move`.
        """
        return None

    def decide(self, view: BeliefView) -> Action:
        action = self._decide_move(view)
        if action is not None:
            return action
        return MoveAction(direction=self._pick_move(view))


class ThiefBrain(BrainBase):
    """Marker base class for thief strategies (no barrier-placement hook —
    only the cop can place barriers, FR-015)."""


class PoliceBrain(BrainBase):
    """Marker base class for police strategies."""
