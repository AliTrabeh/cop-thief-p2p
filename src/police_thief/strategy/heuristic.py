"""Default deterministic heuristic strategy (§6.3.1, §6.4): expected-Manhattan-distance
pursuit/evasion under the *full* belief distribution, not a single point guess — pursue for
the cop, evade for the thief. Runs when a peer's config leaves ``[strategy]`` empty
(FR-060/FR-061, Appendix F Table 22).

**Why expected distance, not "chase argmax".** Committing to a single most-likely cell is
brittle whenever belief is diffuse or multi-modal — most sharply at the very start of a game,
before any scent exists, where a plain argmax degenerates into an arbitrary tie-break on the
agent's own start cell. Minimizing (cop) or maximizing (thief) the *expectation* of Manhattan
distance over the whole belief distribution is the Bayes-optimal single-step choice for that
objective, and it degrades gracefully as belief sharpens over the game: with zero information
it correctly reduces to "move toward/away from the board's own center of mass" instead of a
meaningless tie-break, and it converges to the old argmax-chasing behavior once belief is
sharply peaked around the true position.

The thief additionally applies a light mobility tie-break: evasion that only maximizes this
turn's distance is easy for a pursuing cop to corner near a wall using barriers, so nearly-tied
candidate moves prefer staying closer to the board's interior (more future escape directions).
"""

from __future__ import annotations

from police_thief.domain.models import Coordinate, Direction
from police_thief.domain.scent import most_likely_position
from police_thief.strategy.base import Action, BarrierAction, BeliefView, PoliceBrain, ThiefBrain

_MOBILITY_WEIGHT = 0.01  # small enough to only break near-ties, never override a real distance gain
_BARRIER_CONFIDENCE_FACTOR = 1.5  # belief must exceed this multiple of a uniform guess to spend one


def _expected_distance(belief: dict[Coordinate, float], from_pos: Coordinate) -> float:
    """``E_{c~belief}[manhattan_distance(from_pos, c)]`` — the Bayes-optimal distance
    estimate under uncertainty, used in place of distance-to-a-single-point-guess."""
    return sum(p * from_pos.manhattan_distance(c) for c, p in belief.items())


def _grid_size(belief: dict[Coordinate, float]) -> int:
    # belief_map() (domain/scent.py) always covers every cell of the square board exactly
    # once, so its cardinality alone recovers the board's side length.
    return int(round(len(belief) ** 0.5))


def _edge_distance(pos: Coordinate, grid_size: int) -> int:
    """Distance to the nearest board edge — a cheap proxy for future mobility (corners and
    edges have fewer escape directions than interior cells)."""
    return min(pos.row, pos.col, grid_size - 1 - pos.row, grid_size - 1 - pos.col)


class HeuristicThiefBrain(ThiefBrain):
    """Evade: move to maximize the expected Manhattan distance from the cop's belief
    distribution, lightly biased toward the board's interior."""

    def _pick_move(self, view: BeliefView) -> Direction:
        if not view.legal_moves:
            return Direction.STAY
        grid_size = _grid_size(view.belief)

        def score(direction: Direction) -> float:
            new_pos = view.own_position.translated(direction)
            return _expected_distance(view.belief, new_pos) + _MOBILITY_WEIGHT * _edge_distance(
                new_pos, grid_size
            )

        return max(view.legal_moves, key=score)


class HeuristicPoliceBrain(PoliceBrain):
    """Pursue: move to minimize the expected Manhattan distance to the thief's belief
    distribution; corner with a barrier only once belief is genuinely concentrated there,
    never on a near-uniform guess (assumptions.md A-016).
    """

    def _pick_move(self, view: BeliefView) -> Direction:
        if not view.legal_moves:
            return Direction.STAY

        def score(direction: Direction) -> float:
            new_pos = view.own_position.translated(direction)
            return _expected_distance(view.belief, new_pos)

        return min(view.legal_moves, key=score)

    def _decide_move(self, view: BeliefView) -> Action | None:
        if not view.can_place_barrier:
            return None
        target = most_likely_position(view.belief)
        if view.own_position.manhattan_distance(target) > 1 or target == view.own_position:
            return None
        uniform_share = 1.0 / len(view.belief)
        if view.belief[target] <= uniform_share * _BARRIER_CONFIDENCE_FACTOR:
            return None  # too uncertain to spend a scarce barrier on a guess
        return BarrierAction(coord=target)
