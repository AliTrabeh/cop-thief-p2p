"""Scent/pheromone trail and belief-map engine (FR-030..032, §4.3-4.4, §6.4).

Only three values are mandatory here (Appendix F Table 16): deposit intensity
at the emitting cell (0.9), decay rate per turn (0.10), and the emission
field size (5x5). The book's own figures illustrate a *qualitative* radial
falloff ("intensity decreases the further from the center, per a radial
distribution") but never pins down an exact per-cell formula for the
in-between cells — per the book's own foreword convention, only Appendix F
binds numeric values, so the specific falloff curve below is a documented
implementation choice (assumptions.md A-015), not a transcription of one
worked figure's exact numbers.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from police_thief.domain.models import Coordinate, GameConfig


@dataclass
class ScentField:
    """Sparse scent-intensity map over board cells: ``Coordinate -> tau``."""

    config: GameConfig
    intensities: dict[Coordinate, float] = field(default_factory=dict)

    def intensity_at(self, coord: Coordinate) -> float:
        return self.intensities.get(coord, 0.0)

    def decay(self) -> None:
        """``tau_ij(t+1) = max(0, (1-rho)*tau_ij(t))`` for every existing cell,
        with entries that decay to (approximately) zero dropped to keep the
        map sparse rather than accumulating float noise forever.
        """
        rho = self.config.pheromones.pheromone_decay
        updated: dict[Coordinate, float] = {}
        for coord, tau in self.intensities.items():
            new_tau = max(0.0, (1 - rho) * tau)
            if new_tau > 1e-9:
                updated[coord] = new_tau
        self.intensities = updated

    def deposit(self, center: Coordinate) -> None:
        """Add a fresh emission field around ``center`` on top of whatever is
        already there (call *after* :meth:`decay` in the same turn, matching
        the book's single-formula per-turn update, §4.3).

        Falloff: peak at the center, linear in Euclidean distance to 0 at the
        field's outer radius (assumptions.md A-015) — clamped to the board
        and to the configured ``pheromone_grid_size`` window.
        """
        peak = self.config.pheromones.pheromone_center_intensity
        size = self.config.pheromones.pheromone_grid_size
        radius = size // 2
        grid_size = self.config.board_and_agents.grid_size

        for dr in range(-radius, radius + 1):
            for dc in range(-radius, radius + 1):
                r, c = center.row + dr, center.col + dc
                if not (0 <= r < grid_size and 0 <= c < grid_size):
                    continue
                dist = math.hypot(dr, dc)
                delta = peak * max(0.0, 1 - dist / (radius + 1))
                coord = Coordinate(row=r, col=c)
                self.intensities[coord] = max(0.0, self.intensities.get(coord, 0.0) + delta)

    def update_turn(self, center: Coordinate) -> None:
        """One full per-turn update: decay existing scent, then deposit fresh
        emission around ``center`` (the depositing agent's current cell).
        """
        self.decay()
        self.deposit(center)


def belief_map(scent: ScentField, grid_size: int) -> dict[Coordinate, float]:
    """Normalize scent intensities across the whole board into ``b(s)``, a
    probability distribution over "where the opponent probably is" (FR-032).

    Cells with no recorded scent get a small uniform floor rather than an
    exact zero, so ``argmax`` never degenerates before any scent exists and
    the distribution always sums to 1 (a valid posterior, however weak).
    """
    floor = 1e-6
    raw: dict[Coordinate, float] = {}
    for row in range(grid_size):
        for col in range(grid_size):
            coord = Coordinate(row=row, col=col)
            raw[coord] = scent.intensity_at(coord) + floor
    total = sum(raw.values())
    return {coord: value / total for coord, value in raw.items()}


def most_likely_position(belief: dict[Coordinate, float]) -> Coordinate:
    """``argmax_s b(s)`` (§6.4) — the heuristic's best single guess."""
    return max(belief, key=lambda coord: belief[coord])
