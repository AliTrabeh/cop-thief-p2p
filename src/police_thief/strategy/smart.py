"""Smart strategy: BFS graph distance (respects barriers) + minimax alpha-beta
for the cop and flood-fill mobility scoring for the thief.

Algorithms:
  - BFS replaces Manhattan distance so placed barriers are properly accounted for
  - Cop: depth-3 minimax with alpha-beta against the MAP-estimate thief position
  - Cop barriers: choke-point scoring -- block the cell that most reduces the
    thief's flood-fill reachable area (sector isolation)
  - Thief: maximise expected BFS distance + flood-fill mobility bonus so it
    avoids getting cornered even when the immediate escape looks equivalent
"""
from __future__ import annotations

from collections import deque

from police_thief.domain.models import Coordinate, Direction
from police_thief.domain.scent import most_likely_position
from police_thief.strategy.base import Action, BarrierAction, BeliefView, PoliceBrain, ThiefBrain

_MOBILITY_WEIGHT = 0.3   # weight of flood-fill bonus vs raw distance
_MINIMAX_DEPTH = 3       # ply depth for alpha-beta (cop move, thief move, cop move)
_BARRIER_CONFIDENCE = 1.5  # belief[target] must exceed uniform * this to spend a barrier
_CHOKE_MIN_GAIN = 3      # min reachable-cell reduction required to place a choke barrier


def _adj(pos: Coordinate, n: int, walls: frozenset[Coordinate]):
    for dr, dc in ((-1, 0), (1, 0), (0, 1), (0, -1)):
        nb = Coordinate(row=pos.row + dr, col=pos.col + dc)
        if 0 <= nb.row < n and 0 <= nb.col < n and nb not in walls:
            yield nb


def _bfs(src: Coordinate, dst: Coordinate, n: int, walls: frozenset[Coordinate]) -> int:
    """Shortest path length in the grid respecting placed barriers; n*n if unreachable."""
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


def _flood(pos: Coordinate, n: int, walls: frozenset[Coordinate]) -> int:
    """Count cells reachable from pos via BFS flood fill."""
    seen, q = {pos}, deque([pos])
    while q:
        for nb in _adj(q.popleft(), n, walls):
            if nb not in seen:
                seen.add(nb)
                q.append(nb)
    return len(seen)


def _exp_bfs(belief: dict[Coordinate, float], from_pos: Coordinate, n: int, walls: frozenset[Coordinate]) -> float:
    return sum(p * _bfs(from_pos, c, n, walls) for c, p in belief.items())


class SmartThiefBrain(ThiefBrain):
    """Evade: maximise expected BFS distance from cop belief + flood-fill mobility bonus."""

    def _pick_move(self, view: BeliefView) -> Direction:
        if not view.legal_moves:
            return Direction.STAY
        n = view.grid_size or int(round(len(view.belief) ** 0.5))
        w = view.barriers

        def score(d: Direction) -> float:
            p = view.own_position.translated(d)
            return _exp_bfs(view.belief, p, n, w) + _MOBILITY_WEIGHT * _flood(p, n, w)

        return max(view.legal_moves, key=score)


def _mm(cop: Coordinate, thief: Coordinate, n: int, walls: frozenset,
        depth: int, cop_turn: bool, a: float, b: float) -> float:
    dist = _bfs(cop, thief, n, walls)
    if dist == 0 or depth == 0:
        return float(dist)
    if cop_turn:
        v = float("inf")
        for nb in list(_adj(cop, n, walls)) + [cop]:
            v = min(v, _mm(nb, thief, n, walls, depth - 1, False, a, b))
            b = min(b, v)
            if b <= a:
                break
        return v
    else:
        v = float("-inf")
        for nb in list(_adj(thief, n, walls)) + [thief]:
            v = max(v, _mm(cop, nb, n, walls, depth - 1, True, a, b))
            a = max(a, v)
            if b <= a:
                break
        return v


class SmartPoliceBrain(PoliceBrain):
    """Pursue: minimax alpha-beta movement + choke-point barrier sector isolation."""

    def _pick_move(self, view: BeliefView) -> Direction:
        if not view.legal_moves:
            return Direction.STAY
        n = view.grid_size or int(round(len(view.belief) ** 0.5))
        w = view.barriers
        thief = most_likely_position(view.belief)
        best_d, best_v = view.legal_moves[0], float("inf")
        for d in view.legal_moves:
            v = _mm(view.own_position.translated(d), thief, n, w,
                    _MINIMAX_DEPTH - 1, False, float("-inf"), float("inf"))
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
            return None  # belief too diffuse to spend a scarce barrier
        cop = view.own_position
        base_reach = _flood(target, n, w)
        best_c, best_g = None, _CHOKE_MIN_GAIN - 1
        for dr, dc in ((-1, 0), (1, 0), (0, 1), (0, -1), (0, 0)):
            c = Coordinate(row=cop.row + dr, col=cop.col + dc)
            if not (0 <= c.row < n and 0 <= c.col < n) or c in w or c == cop:
                continue
            if c == target:
                return BarrierAction(coord=c)  # barrier on thief = immediate capture
            gain = base_reach - _flood(target, n, w | {c})
            if gain > best_g:
                best_g, best_c = gain, c
        return BarrierAction(coord=best_c) if best_c else None
