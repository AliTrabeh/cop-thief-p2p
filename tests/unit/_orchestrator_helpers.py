"""Shared helpers for the orchestrator unit tests (test_orchestrator.py,
test_orchestrator_messages.py) — not itself a test file (no ``test_``
prefix, so pytest doesn't collect it), split out purely to keep each test
file under 150 lines.
"""

from __future__ import annotations

from police_thief.domain.board import BoardState
from police_thief.domain.models import Role
from police_thief.orchestrator import Orchestrator
from police_thief.strategy.base import BeliefView, BrainBase
from police_thief.strategy.heuristic import HeuristicPoliceBrain, HeuristicThiefBrain


class CrashingBrain(BrainBase):
    """A pluggable strategy (FR-060) that's simply buggy -- must never take
    down the whole peer process (PRD-0286/PRD-0573)."""

    def _pick_move(self, view: BeliefView):  # noqa: ANN001, ANN201 - test double
        raise RuntimeError("boom")


def make_orchestrator(game_config, role: Role) -> Orchestrator:
    board = BoardState.initial(game_config)
    brain = HeuristicPoliceBrain() if role is Role.POLICE else HeuristicThiefBrain()
    return Orchestrator(
        role=role, game_id="test-game", config=game_config, board=board, brain=brain
    )
