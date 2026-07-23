"""Final score computation from a finished board (FR-020/FR-021)."""

from __future__ import annotations

from police_thief.domain.board import BoardState, Outcome
from police_thief.domain.models import GameConfig, Role


def score(board: BoardState) -> tuple[int, int]:
    """Return ``(cop_score, thief_score)`` for a finished board.

    Raises :class:`ValueError` if the game has not ended yet — scoring an
    in-progress game is a caller bug, not a legitimate 0-0 result.
    """
    cfg: GameConfig = board.config
    s = cfg.scoring
    if board.outcome is Outcome.ONGOING:
        raise ValueError("cannot score a game that has not ended")
    if board.outcome in (Outcome.CAPTURE, Outcome.THIEF_STRANDED):
        return s.capture_cop, s.capture_thief
    if board.outcome is Outcome.SURVIVAL:
        return s.survival_cop, s.survival_thief
    raise AssertionError(f"unhandled outcome: {board.outcome}")


def technical_loss_score(cfg: GameConfig, disqualified: Role) -> tuple[int, int]:
    """Score for a technical disqualification (FR-021, FR-043).

    The book only specifies that the disqualified side scores
    ``technical_loss`` (0); it does not specify the non-disqualified side's
    score. Per assumptions.md A-014, the non-disqualified side is credited
    its survival score (rewarding fair play rather than leaving both sides at
    0, which would be indistinguishable from a double-DQ).
    """
    tl = cfg.scoring.technical_loss
    if disqualified is Role.POLICE:
        return tl, cfg.scoring.survival_thief
    return cfg.scoring.survival_cop, tl
