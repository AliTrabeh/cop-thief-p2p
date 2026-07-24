"""Bonus: tabular Q-learning strategy (BONUS-001, docs/requirements_analysis.md
§14). Explicitly optional per the spec, which frames reinforcement learning
as one tool among several a team *may* use, never a requirement (§4); the
shipped default remains the deterministic heuristic in
``strategy/heuristic.py``, and this module is never loaded unless a peer's
``config/<role>/game.toml`` explicitly points ``[strategy]`` at one of the
classes below.

**Honest scope and limitation.** ``BrainBase.decide()`` is called once per
own turn and has no callback for the eventual game outcome (capture/
survival/technical-loss) -- a pluggable strategy simply never learns whether
it won. So rather than pretending to learn from a reward this hook cannot
receive, these brains use a standard pursuit/evasion *reward-shaping*
signal instead (the mechanics live in ``qlearning_core.py``, split out to
keep each file under 150 lines): on every turn after the first, they compare
the change in Manhattan distance to the believed opponent cell that resulted
from their *previous* turn's action, and use that delta as an immediate
reward for a one-step tabular Q-learning update (Watkins' Q-learning,
discrete state/action space). This lets the policy improve *within* a single
long game and *across* games when a Q-table is persisted via
``q_table_path`` -- but it is not equivalent to learning from the true
terminal win/loss signal, and that trade-off is deliberate, not an oversight
(see ``docs/STATUS.md``).

Only the movement decision is learned. Barrier placement (police-only) reuses
the same simple "corner if adjacent" rule as the default heuristic brain
(``strategy/heuristic.py::HeuristicPoliceBrain._decide_move``) rather than
being part of the learned policy, keeping the state/action space small
enough for a tabular method to be sensible on a 7x7-and-up board.
"""

from __future__ import annotations

from police_thief.domain.models import Direction
from police_thief.domain.scent import most_likely_position
from police_thief.strategy.base import Action, BarrierAction, BeliefView, PoliceBrain, ThiefBrain
from police_thief.strategy.qlearning_core import QLearningMixin


class QLearningThiefBrain(QLearningMixin, ThiefBrain):
    """Evade via a learned policy: maximize Manhattan distance from the
    believed cop location (the same strategic goal as
    ``HeuristicThiefBrain``, but the direction choice is Q-learned instead
    of always greedy).
    """

    def _pick_move(self, view: BeliefView) -> Direction:
        target = most_likely_position(view.belief)
        return self.pick_via_q(view, target, maximize=True)


class QLearningPoliceBrain(QLearningMixin, PoliceBrain):
    """Pursue via a learned policy: minimize Manhattan distance to the
    believed thief location; barrier placement reuses the default brain's
    simple cornering rule rather than being part of the learned policy
    (see module docstring)."""

    def _pick_move(self, view: BeliefView) -> Direction:
        target = most_likely_position(view.belief)
        return self.pick_via_q(view, target, maximize=False)

    def _decide_move(self, view: BeliefView) -> Action | None:
        if not view.can_place_barrier:
            return None
        target = most_likely_position(view.belief)
        if view.own_position.manhattan_distance(target) <= 1 and target != view.own_position:
            return BarrierAction(coord=target)
        return None
