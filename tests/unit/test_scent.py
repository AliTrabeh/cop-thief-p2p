"""Unit tests for domain/scent.py — TEST-002, FR-030..032."""

from __future__ import annotations

import math

from police_thief.domain.models import Coordinate
from police_thief.domain.scent import ScentField, belief_map, most_likely_position


def test_deposit_peaks_exactly_at_center(game_config):
    field = ScentField(config=game_config)
    center = Coordinate(row=3, col=3)
    field.deposit(center)
    assert field.intensity_at(center) == game_config.pheromones.pheromone_center_intensity


def test_deposit_falls_off_monotonically_with_distance(game_config):
    field = ScentField(config=game_config)
    center = Coordinate(row=3, col=3)
    field.deposit(center)
    near = field.intensity_at(Coordinate(row=3, col=4))  # distance 1
    far = field.intensity_at(Coordinate(row=3, col=5))  # distance 2
    corner = field.intensity_at(Coordinate(row=5, col=5))  # distance ~2.83
    assert near > far > corner >= 0.0


def test_deposit_is_zero_outside_the_field_radius(game_config):
    field = ScentField(config=game_config)
    center = Coordinate(row=3, col=3)
    field.deposit(center)
    # pheromone_grid_size=5 -> radius 2; a cell 3 away in both axes is outside.
    assert field.intensity_at(Coordinate(row=6, col=6)) == 0.0


def test_decay_matches_formula_exactly(game_config):
    field = ScentField(config=game_config)
    coord = Coordinate(row=0, col=0)
    field.intensities[coord] = 0.9
    rho = game_config.pheromones.pheromone_decay
    field.decay()
    assert math.isclose(field.intensity_at(coord), (1 - rho) * 0.9)


def test_single_deposit_then_decay_reaches_half_peak_around_turn_seven(game_config):
    # Mirrors the book's own Figure 5 ("single deposit, then decay" curve
    # crossing half-of-peak around turn 7-8 turns at rho=0.10).
    field = ScentField(config=game_config)
    center = Coordinate(row=3, col=3)
    field.deposit(center)
    peak = field.intensity_at(center)
    turn = 0
    while field.intensity_at(center) > peak / 2:
        field.decay()
        turn += 1
    assert 6 <= turn <= 8


def test_reemission_keeps_center_near_peak_while_agent_present(game_config):
    field = ScentField(config=game_config)
    center = Coordinate(row=3, col=3)
    for _ in range(10):
        field.update_turn(center)
    # steady-state center value should stabilize close to the peak, not decay away.
    assert field.intensity_at(center) > 0.85 * game_config.pheromones.pheromone_center_intensity


def test_decay_never_goes_negative(game_config):
    field = ScentField(config=game_config)
    field.intensities[Coordinate(row=0, col=0)] = 0.001
    for _ in range(50):
        field.decay()
    assert all(v >= 0.0 for v in field.intensities.values())


def test_belief_map_sums_to_one(game_config):
    field = ScentField(config=game_config)
    grid_size = game_config.board_and_agents.grid_size
    b = belief_map(field, grid_size)
    assert math.isclose(sum(b.values()), 1.0, rel_tol=1e-6)
    assert len(b) == grid_size * grid_size


def test_belief_map_argmax_tracks_the_scent_source(game_config):
    field = ScentField(config=game_config)
    grid_size = game_config.board_and_agents.grid_size
    source = Coordinate(row=3, col=3)
    field.deposit(source)
    b = belief_map(field, grid_size)
    assert most_likely_position(b) == source


def test_belief_map_is_uniform_when_no_scent_exists(game_config):
    field = ScentField(config=game_config)
    grid_size = game_config.board_and_agents.grid_size
    b = belief_map(field, grid_size)
    values = list(b.values())
    assert max(values) - min(values) < 1e-9
