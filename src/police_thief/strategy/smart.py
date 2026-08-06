"""Optimal pursuit-evasion strategy, empirically validated.

Cop  — Depth-3 minimax alpha-beta (ODD total ply) against the MAP thief.
       Odd total depth = leaf evaluated AFTER cop's last move (correct last-
       mover advantage).  MAP (argmax belief) is the right target: the belief
       tracker concentrates probability near the thief's real position within
       a few turns, so argmax is nearly always the true position.  Expected
       minimax over K positions dilutes pursuit when belief is spread and was
       empirically worse.

Thief — BFS-optimal cop model + adjacency mobility bonus.
        _thief_mm models the cop as a BFS minimiser (cop picks the neighbour
        with shortest BFS path to the thief).  BFS == Manhattan on an open
        grid, so behaviour is identical to the Manhattan model with no
        barriers; the BFS model generalises correctly once barriers are
        placed, making the thief robust to any opponent cop strategy.
        Mobility bonus: len(adj(new_thief)) — the LOCAL adjacency count (2 at
        corners, 3 at edges, 4 at interior). Flood fill counts all reachable
        cells, which is always n² on an open grid (constant, useless). The
        adjacency count is the right measure: it distinguishes corners from
        edges and penalises positions where the cop can immediately restrict
        the thief's escape options.

Barriers — Greedy max-reachability-reduction: block the cop-adjacent cell
           that most shrinks the thief's BFS flood-fill area (sector isolation
           / choke-point strategy).
"""
from __future__ import annotations

from collections import deque

from police_thief.domain.models import Coordinate, Direction
from police_thief.domain.scent import most_likely_position
from police_thief.strategy.base import Action, BarrierAction, BeliefView, PoliceBrain, ThiefBrain

_POLICE_DEPTH = 3       # ODD total ply: leaf falls after cop's last move
_THIEF_DEPTH = 4        # cop-thief-cop-thief look-ahead (2 thief decisions)
_MOBILITY_WEIGHT = 0.5  # adj-count bonus in leaf eval: corner=2, edge=3, interior=4
_BARRIER_CONFIDENCE = 1.5
_CHOKE_MIN_GAIN = 2


def _adj(pos: Coordinate, n: int, walls: frozenset) -> list[Coordinate]:
    result = []
    for dr, dc in ((-1, 0), (1, 0), (0, 1), (0, -1)):
        nb = Coordinate(row=pos.row + dr, col=pos.col + dc)
        if 0 <= nb.row < n and 0 <= nb.col < n and nb not in walls:
            result.append(nb)
    return result


def _bfs(src: Coordinate, dst: Coordinate, n: int, walls: frozenset) -> int:
    """Shortest path respecting barriers; n*n if unreachable."""
    if src == dst:
        return 0
    seen, q = {src}, deque([(src, 0)])
    while q:
        p, d = q.popleft()
        for nb in _adj(p, n, walls):
            if nb == dst:
                return d + 1
            if nb not in seen:
                seen.add(nb)
                q.append((nb, d + 1))
    return n * n


def _flood(pos: Coordinate, n: int, walls: frozenset) -> int:
    """Count cells reachable from pos (useful when barriers partition the grid)."""
    seen, q = {pos}, deque([pos])
    while q:
        for nb in _adj(q.popleft(), n, walls):
            if nb not in seen:
                seen.add(nb)
                q.append(nb)
    return len(seen)


def _bfs_all(src: Coordinate, n: int, walls: frozenset) -> dict[Coordinate, int]:
    """Single-source BFS: distances from src to all reachable cells in O(n²)."""
    dist: dict[Coordinate, int] = {src: 0}
    q: deque[Coordinate] = deque([src])
    while q:
        p = q.popleft()
        for nb in _adj(p, n, walls):
            if nb not in dist:
                dist[nb] = dist[p] + 1
                q.append(nb)
    return dist


def _manhattan(a: Coordinate, b: Coordinate) -> int:
    return abs(a.row - b.row) + abs(a.col - b.col)


def _thief_mm(thief: Coordinate, cop: Coordinate, n: int, walls: frozenset,
              depth: int, thief_turn: bool) -> float:
    """Minimax from thief's perspective.  Cop is modelled as a BFS minimiser
    (picks the neighbour with shortest BFS path to the thief).  BFS == Manhattan
    on an open grid so behaviour matches any Manhattan cop; with barriers the BFS
    model correctly handles walls that Manhattan ignores, making the thief robust
    to any opponent cop strategy.  The thief maximises.
    Leaf: BFS distance + adjacency-count bonus so the search correctly
    penalises corner dead-ends (adj 2) vs open interior cells (adj 4).
    """
    dist = _bfs(cop, thief, n, walls)
    if dist == 0 or depth == 0:
        return float(dist) + _MOBILITY_WEIGHT * len(_adj(thief, n, walls))
    if thief_turn:
        best = float("-inf")
        for nb in _adj(thief, n, walls) + [thief]:
            v = _thief_mm(nb, cop, n, walls, depth - 1, False)
            if v > best:
                best = v
        return best
    else:
        cop_opts = _adj(cop, n, walls) + [cop]
        cop_next = min(cop_opts, key=lambda c: _bfs(c, thief, n, walls))
        return _thief_mm(thief, cop_next, n, walls, depth - 1, True)


def _mm(cop: Coordinate, thief: Coordinate, n: int, walls: frozenset,
        depth: int, cop_turn: bool, a: float, b: float) -> float:
    """Alpha-beta minimax for the cop; leaf eval is pure BFS distance."""
    dist = _bfs(cop, thief, n, walls)
    if dist == 0 or depth == 0:
        return float(dist)
    if cop_turn:
        v = float("inf")
        for nb in _adj(cop, n, walls) + [cop]:
            v = min(v, _mm(nb, thief, n, walls, depth - 1, False, a, b))
            b = min(b, v)
            if b <= a:
                break
        return v
    else:
        v = float("-inf")
        for nb in _adj(thief, n, walls) + [thief]:
            v = max(v, _mm(cop, nb, n, walls, depth - 1, True, a, b))
            a = max(a, v)
            if b <= a:
                break
        return v


class SmartThiefBrain(ThiefBrain):
    """Evade: MAP-cop minimax look-ahead + no-stay rule.

    Uses _thief_mm with depth=4 against the MAP (most-likely) cop position.
    MAP avoids scent-trail artifacts from belief spread that cause oscillation
    between corner and edge.  Depth-4 gives 2 thief decisions inside the
    tree so it can plan around corners.  Leaf eval adds adjacency-count bonus
    so the search correctly penalises corner dead-ends vs open cells.
    Never stays voluntarily: STAY is excluded unless all adj cells are blocked.
    """

    def _pick_move(self, view: BeliefView) -> Direction:
        if not view.legal_moves:
            return Direction.STAY
        n = view.grid_size or int(round(len(view.belief) ** 0.5))
        w = view.barriers
        cop_est = most_likely_position(view.belief)

        # Exclude STAY — it freezes the thief at its local BFS maximum
        moves = [d for d in view.legal_moves if d is not Direction.STAY]
        if not moves:
            moves = list(view.legal_moves)

        def score(d: Direction) -> float:
            new_pos = view.own_position.translated(d)
            # Cop moves first in response to our candidate move
            return _thief_mm(new_pos, cop_est, n, w, _THIEF_DEPTH, False)

        return max(moves, key=score)


class SmartPoliceBrain(PoliceBrain):
    """Pursue: depth-3 minimax vs MAP thief estimate + greedy choke-point barriers."""

    def _pick_move(self, view: BeliefView) -> Direction:
        if not view.legal_moves:
            return Direction.STAY
        n = view.grid_size or int(round(len(view.belief) ** 0.5))
        w = view.barriers
        thief = most_likely_position(view.belief)
        best_d, best_v = view.legal_moves[0], float("inf")
        for d in view.legal_moves:
            v = _mm(view.own_position.translated(d), thief, n, w,
                    _POLICE_DEPTH - 1, False, float("-inf"), float("inf"))
            if v < best_v:
                best_v, best_d = v, d
        return best_d

    def _decide_move(self, view: BeliefView) -> Action | None:
        if not view.can_place_barrier:
            return None
        n = view.grid_size or int(round(len(view.belief) ** 0.5))
        w = view.barriers
        target = most_likely_position(view.belief)
        if view.belief.get(target, 0) <= _BARRIER_CONFIDENCE / len(view.belief):
            return None
        cop = view.own_position
        base_reach = _flood(target, n, w)
        best_c, best_g = None, _CHOKE_MIN_GAIN - 1
        for dr, dc in ((-1, 0), (1, 0), (0, 1), (0, -1)):
            c = Coordinate(row=cop.row + dr, col=cop.col + dc)
            if not (0 <= c.row < n and 0 <= c.col < n) or c in w:
                continue
            if c == target:
                return BarrierAction(coord=c)
            gain = base_reach - _flood(target, n, w | {c})
            if gain > best_g:
                best_g, best_c = gain, c
        return BarrierAction(coord=best_c) if best_c else None
