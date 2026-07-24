"""Live GUI: local-truth-only belief heatmap + turn banner (FR-070, §7.3).

Rendering *logic* (color mapping, banner text, per-cell render model) is a
pure function of this peer's own true position and its own belief map —
never the opponent's true position or the objective board (FR-005) — and is
fully unit-testable without a display. ``LiveView`` wires that logic to an
actual Tkinter window and can only be exercised manually (needs a display),
per docs/testing_strategy.md.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from police_thief.domain.models import Coordinate

if TYPE_CHECKING:
    import tkinter as tk


def belief_to_color(probability: float, max_probability: float) -> str:
    """Deeper red = higher believed probability (§7.3.1's own convention).
    White when there's no information at all.
    """
    intensity = 0.0 if max_probability <= 0 else min(1.0, probability / max_probability)
    green_blue = int(255 * (1 - intensity))
    return f"#ff{green_blue:02x}{green_blue:02x}"


def turn_banner_text(is_my_turn: bool) -> str:
    return "YOUR TURN" if is_my_turn else "LOCKED"


def turn_banner_color(is_my_turn: bool) -> str:
    return "#2ecc71" if is_my_turn else "#95a5a6"  # green vs. grey, §7.3.2 figure


@dataclass(frozen=True)
class CellRender:
    coord: Coordinate
    color: str
    label: str  # non-empty only at this peer's own true position


def render_grid(
    grid_size: int,
    own_position: Coordinate,
    belief: dict[Coordinate, float],
    own_label: str,
) -> list[CellRender]:
    """Compute the local-truth-only render model. Only ``own_position``
    (this peer's own true location) and ``belief`` (this peer's own
    posterior about the opponent) are ever consulted here — nothing else
    about the objective board can leak into this function (FR-005/FR-070).
    """
    max_p = max(belief.values(), default=0.0)
    cells = []
    for row in range(grid_size):
        for col in range(grid_size):
            coord = Coordinate(row=row, col=col)
            color = belief_to_color(belief.get(coord, 0.0), max_p)
            label = own_label if coord == own_position else ""
            cells.append(CellRender(coord=coord, color=color, label=label))
    return cells


class LiveView:
    """A minimal Tkinter window: a grid of colored cells (the belief
    heatmap) plus a turn banner. Requires a display; not exercised in CI.
    """

    def __init__(self, grid_size: int, own_label: str, cell_size: int = 60) -> None:
        import tkinter as tk

        self._grid_size = grid_size
        self._own_label = own_label
        self._cell_size = cell_size

        self.root: tk.Tk = tk.Tk()
        self.root.title(f"Police-Thief -- {own_label} (local truth only)")
        self.banner = tk.Label(
            self.root, text=turn_banner_text(False), font=("Segoe UI", 16, "bold")
        )
        self.banner.pack(fill="x")
        self.canvas = tk.Canvas(
            self.root, width=grid_size * cell_size, height=grid_size * cell_size
        )
        self.canvas.pack()

    def update(
        self, own_position: Coordinate, belief: dict[Coordinate, float], is_my_turn: bool
    ) -> None:
        self.banner.config(text=turn_banner_text(is_my_turn), bg=turn_banner_color(is_my_turn))
        self.canvas.delete("all")
        size = self._cell_size
        for cell in render_grid(self._grid_size, own_position, belief, self._own_label):
            x0, y0 = cell.coord.col * size, cell.coord.row * size
            self.canvas.create_rectangle(
                x0, y0, x0 + size, y0 + size, fill=cell.color, outline="#888"
            )
            if cell.label:
                self.canvas.create_text(
                    x0 + size / 2, y0 + size / 2, text=cell.label, font=("Segoe UI", 14, "bold")
                )

    def run(self) -> None:
        self.root.mainloop()
