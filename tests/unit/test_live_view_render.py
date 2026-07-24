"""Unit tests for gui/live_view.py's pure rendering logic — FR-070.

No display needed: ``LiveView`` itself (the real Tkinter window) is not
exercised here, only the render-model functions it's built on.
"""

from __future__ import annotations

from police_thief.domain.models import Coordinate
from police_thief.gui.live_view import (
    belief_to_color,
    render_grid,
    turn_banner_color,
    turn_banner_text,
)


def test_belief_to_color_is_white_with_no_information():
    assert belief_to_color(0.0, 0.0) == "#ffffff"


def test_belief_to_color_is_pure_red_at_peak_probability():
    assert belief_to_color(0.5, 0.5) == "#ff0000"


def test_belief_to_color_intensity_between_extremes():
    color = belief_to_color(0.25, 0.5)
    assert color.startswith("#ff")
    assert color not in ("#ffffff", "#ff0000")


def test_turn_banner_text_reflects_whose_turn_it_is():
    assert turn_banner_text(True) == "YOUR TURN"
    assert turn_banner_text(False) == "LOCKED"


def test_turn_banner_color_differs_by_turn_state():
    assert turn_banner_color(True) != turn_banner_color(False)


def test_render_grid_labels_only_own_position():
    own = Coordinate(row=1, col=1)
    belief = {Coordinate(row=2, col=2): 0.5}
    cells = render_grid(grid_size=3, own_position=own, belief=belief, own_label="C")
    labeled = [c for c in cells if c.label]
    assert len(labeled) == 1
    assert labeled[0].coord == own
    assert labeled[0].label == "C"


def test_render_grid_covers_every_cell_exactly_once():
    cells = render_grid(
        grid_size=4, own_position=Coordinate(row=0, col=0), belief={}, own_label="C"
    )
    coords = {c.coord for c in cells}
    assert len(cells) == 16
    assert len(coords) == 16


def test_render_grid_highest_belief_cell_gets_the_reddest_color():
    hot = Coordinate(row=2, col=2)
    belief = {hot: 0.9, Coordinate(row=0, col=0): 0.1}
    cells = render_grid(
        grid_size=3, own_position=Coordinate(row=1, col=1), belief=belief, own_label="C"
    )
    by_coord = {c.coord: c.color for c in cells}
    assert by_coord[hot] == "#ff0000"
