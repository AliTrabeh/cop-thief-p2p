"""Default deterministic heuristic strategy (§6.3.1, §6.4): Manhattan distance
to ``argmax_s b(s)`` — pursue for the cop, evade for the thief. Runs when a
peer's config leaves ``[strategy]`` empty (FR-060/FR-061, Appendix F Table 22).
"""

from __future__ import annotations

from police_thief.domain.models import Coordinate, Direction
from police_thief.domain.scent import most_likely_position
from police_thief.strategy.base import Action, BarrierAction, BeliefView, PoliceBrain, ThiefBrain


def _direction_toward_or_away(view: BeliefView, target: Coordinate, maximize: bool) -> Direction:
    if not view.legal_moves:
        # No legal move at all is only reachable in a non-default config
        # (assumptions.md A-013); nothing sensible to return but STAY.
        return Direction.STAY

    def score(direction: Direction) -> int:
        new_pos = view.own_position.translated(direction)
        return new_pos.manhattan_distance(target)

    return max(view.legal_moves, key=score) if maximize else min(view.legal_moves, key=score)


class HeuristicThiefBrain(ThiefBrain):
    """Evade: move to maximize Manhattan distance from the believed cop location."""

    def _pick_move(self, view: BeliefView) -> Direction:
        target = most_likely_position(view.belief)
        return _direction_toward_or_away(view, target, maximize=True)


class HeuristicPoliceBrain(PoliceBrain):
    """Pursue: move to minimize Manhattan distance to the believed thief
    location; if the thief's believed cell is within barrier range, corner it
    instead of moving (the cop-specific `_decide_move` hook, assumptions.md
    A-016).
    """

    def _pick_move(self, view: BeliefView) -> Direction:
        target = most_likely_position(view.belief)
        return _direction_toward_or_away(view, target, maximize=False)

    def _decide_move(self, view: BeliefView) -> Action | None:
        if not view.can_place_barrier:
            return None
        target = most_likely_position(view.belief)
        if view.own_position.manhattan_distance(target) <= 1 and target != view.own_position:
            return BarrierAction(coord=target)
        return None
