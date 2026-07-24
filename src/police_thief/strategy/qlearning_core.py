"""Shared tabular Q-learning machinery for the bonus RL brains
(``strategy/qlearning.py``, BONUS-001) — split out to keep each file under
the project's 150-line-per-file limit. See that module's docstring for the
honest scope/limitation of the reward signal used here.
"""

from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any

from police_thief.domain.models import Coordinate, Direction
from police_thief.strategy.base import BeliefView

# (sign of dx to target, sign of dy to target, capped Manhattan distance, can place a barrier)
State = tuple[int, int, int, bool]

_DISTANCE_CAP = 3
_DEFAULT_EPSILON = 0.1
_DEFAULT_ALPHA = 0.3
_DEFAULT_GAMMA = 0.9


def _sign(n: int) -> int:
    return (n > 0) - (n < 0)


def state_for(view: BeliefView, target: Coordinate) -> State:
    dx = _sign(target.col - view.own_position.col)
    dy = _sign(target.row - view.own_position.row)
    dist = min(view.own_position.manhattan_distance(target), _DISTANCE_CAP)
    return (dx, dy, dist, view.can_place_barrier)


class QLearningMixin:
    """Shared tabular Q-learning machinery. Mixed into
    :class:`~police_thief.strategy.qlearning.QLearningPoliceBrain`/
    :class:`~police_thief.strategy.qlearning.QLearningThiefBrain` alongside
    the matching ``BrainBase`` role marker; never instantiated on its own.
    """

    def __init__(
        self,
        *,
        epsilon: float = _DEFAULT_EPSILON,
        alpha: float = _DEFAULT_ALPHA,
        gamma: float = _DEFAULT_GAMMA,
        seed: int | None = None,
        q_table_path: Path | None = None,
    ) -> None:
        self.epsilon = epsilon
        self.alpha = alpha
        self.gamma = gamma
        self.rng = random.Random(seed)
        self.q_table_path = q_table_path
        self._q: dict[State, dict[str, float]] = {}
        self._prev_state: State | None = None
        self._prev_action_key: str | None = None
        if q_table_path is not None and q_table_path.exists():
            self.load(q_table_path)

    def _q_values(self, state: State, action_keys: list[str]) -> dict[str, float]:
        table = self._q.setdefault(state, {})
        for key in action_keys:
            table.setdefault(key, 0.0)
        return table

    def _choose(self, state: State, action_keys: list[str]) -> str:
        table = self._q_values(state, action_keys)
        if self.rng.random() < self.epsilon:
            return self.rng.choice(action_keys)
        best_value = max(table[k] for k in action_keys)
        best_keys = [k for k in action_keys if table[k] == best_value]
        return self.rng.choice(best_keys)

    def _update_from_previous_step(self, new_state: State, maximize: bool) -> None:
        if self._prev_state is None or self._prev_action_key is None:
            return
        old_distance = self._prev_state[2]
        new_distance = new_state[2]
        delta = new_distance - old_distance  # positive => distance to target grew
        reward = float(delta) if maximize else float(-delta)
        prev_table = self._q_values(self._prev_state, [self._prev_action_key])
        best_next = max(self._q.get(new_state, {}).values(), default=0.0)
        old_value = prev_table[self._prev_action_key]
        prev_table[self._prev_action_key] = old_value + self.alpha * (
            reward + self.gamma * best_next - old_value
        )

    def pick_via_q(self, view: BeliefView, target: Coordinate, maximize: bool) -> Direction:
        if not view.legal_moves:
            return Direction.STAY
        state = state_for(view, target)
        self._update_from_previous_step(state, maximize)
        action_keys = [d.value for d in view.legal_moves]
        chosen_key = self._choose(state, action_keys)
        self._prev_state = state
        self._prev_action_key = chosen_key
        return Direction(chosen_key)

    def save(self, path: Path) -> None:
        """Persist the learned Q-table as JSON so it can seed a later game
        (never called automatically -- an advanced/optional workflow)."""
        serializable = {
            "|".join(str(part) for part in state): values for state, values in self._q.items()
        }
        path.write_text(json.dumps(serializable), encoding="utf-8")

    def load(self, path: Path) -> None:
        raw: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
        table: dict[State, dict[str, float]] = {}
        for key, values in raw.items():
            dx_str, dy_str, dist_str, barrier_str = key.split("|")
            state: State = (int(dx_str), int(dy_str), int(dist_str), barrier_str == "True")
            table[state] = {k: float(v) for k, v in values.items()}
        self._q = table
