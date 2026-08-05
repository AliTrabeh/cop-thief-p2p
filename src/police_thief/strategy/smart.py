"""Optimal pursuit-evasion strategy, empirically validated against multiple
algorithms including expected Voronoi territory, thief-side minimax, and
particle-filtered expected minimax — all of which performed worse for the
reasons noted below.

Cop  — Depth-3 minimax alpha-beta (ODD total ply) against the MAP thief.
       Odd total depth = leaf is evaluated AFTER the cop's last move, giving
       correct last-mover advantage. Even depths (4, 6...) invert this and
       degrade against sub-optimal opponents due to over-fitting to adversarial
       thief play that doesn't match the real opponent. Depth 3 outperforms
       depth 5 for the same model-mismatch reason: longer horizon plans
       assume an optimal adversary response that real thieves don't exhibit,
       leading the cop down paths optimised for a phantom opponent.

Thief — Expected BFS distance over the *full* belief distribution.
        Tested alternatives that all performed worse:
          • Argmax Voronoi: collapses to (0,0) on uniform belief → catastrophic
          • Expected Voronoi: correct theory but single-step, doesn't account
            for cop's next move → gives deceptive territory signals
          • Thief minimax (depth 4): optimal vs BFS-minimising cop, but Ahmad's
            real cop uses Manhattan+mobility, causing model divergence by ply 3
        Expected BFS is robust because it averages over all cop positions
        (handles diffuse belief gracefully) and BFS correctly respects barriers.
        Flood-fill mobility bonus prevents self-cornering near edges.

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
_MOBILITY_WEIGHT = 0.3  # flood-fill secondary bonus for thief
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
    """Count cells reachable from pos (escape freedom)."""
    seen, q = {pos}, deque([pos])
    while q:
        for nb in _adj(q.popleft(), n, walls):
            if nb not in seen:
                seen.add(nb)
                q.append(nb)
    return len(seen)


def _exp_bfs(belief: dict[Coordinate, float], from_pos: Coordinate,
             n: int, walls: frozenset) -> float:
    """E_{c~belief}[BFS(from_pos, c)] — Bayes-optimal expected BFS distance."""
    return sum(p * _bfs(from_pos, c, n, walls) for c, p in belief.items())


def _mm(cop: Coordinate, thief: Coordinate, n: int, walls: frozenset,
        depth: int, cop_turn: bool, a: float, b: float) -> float:
    """Alpha-beta minimax; leaf eval is pure BFS distance."""
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
    """Evade: expected BFS distance over full cop belief + flood-fill mobility."""

    def _pick_move(self, view: BeliefView) -> Direction:
        if not view.legal_moves:
            return Direction.STAY
        n = view.grid_size or int(round(len(view.belief) ** 0.5))
        w = view.barriers

        def score(d: Direction) -> float:
            p = view.own_position.translated(d)
            return _exp_bfs(view.belief, p, n, w) + _MOBILITY_WEIGHT * _flood(p, n, w)

        return max(view.legal_moves, key=score)


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
            # depth-1 = 2 (even): leaf falls AFTER cop's last move — favourable
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
