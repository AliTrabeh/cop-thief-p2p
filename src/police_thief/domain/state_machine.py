"""Game phase state machine (FR-052, docs/protocol.md §4).

``WAITING_FOR_OPPONENT -> COMPUTING_MOVE -> COMMITTING -> AWAITING_REVEAL ->
VERIFYING -> WAITING_FOR_OPPONENT``, with ``TECHNICAL_LOSS`` reachable from
``COMPUTING_MOVE``, ``AWAITING_REVEAL``, and ``VERIFYING`` on any rule
violation. ``TECHNICAL_LOSS`` is terminal (no outgoing transitions) — any
attempted transition out of it is rejected, matching the book's Deadlock-
prevention rule (§8.3): a locked-out state must never advance without
explicit, auditable cause.
"""

from __future__ import annotations

from enum import StrEnum


class GamePhase(StrEnum):
    WAITING_FOR_OPPONENT = "WAITING_FOR_OPPONENT"
    COMPUTING_MOVE = "COMPUTING_MOVE"
    COMMITTING = "COMMITTING"
    AWAITING_REVEAL = "AWAITING_REVEAL"
    VERIFYING = "VERIFYING"
    TECHNICAL_LOSS = "TECHNICAL_LOSS"


class IllegalTransitionError(Exception):
    """Raised when a requested phase transition isn't in the transition table.

    Per §8.3's Deadlock box: a rejected transition must leave the machine
    exactly where it was, never nudge it into some adjacent state "to keep
    things moving." Silence here is deliberate, not a missing feature.
    """


_TRANSITIONS: dict[GamePhase, frozenset[GamePhase]] = {
    GamePhase.WAITING_FOR_OPPONENT: frozenset({GamePhase.COMPUTING_MOVE}),
    GamePhase.COMPUTING_MOVE: frozenset({GamePhase.COMMITTING, GamePhase.TECHNICAL_LOSS}),
    GamePhase.COMMITTING: frozenset({GamePhase.AWAITING_REVEAL}),
    GamePhase.AWAITING_REVEAL: frozenset({GamePhase.VERIFYING, GamePhase.TECHNICAL_LOSS}),
    GamePhase.VERIFYING: frozenset({GamePhase.WAITING_FOR_OPPONENT, GamePhase.TECHNICAL_LOSS}),
    GamePhase.TECHNICAL_LOSS: frozenset(),  # terminal
}


class GamePhaseMachine:
    """Tracks the current phase of one game and enforces legal transitions."""

    def __init__(self) -> None:
        self._state: GamePhase = GamePhase.WAITING_FOR_OPPONENT

    @property
    def state(self) -> GamePhase:
        return self._state

    @property
    def is_terminal(self) -> bool:
        return not _TRANSITIONS[self._state]

    def transition(self, target: GamePhase) -> GamePhase:
        """Move to ``target`` if legal, else raise :class:`IllegalTransitionError`."""
        if target not in _TRANSITIONS[self._state]:
            raise IllegalTransitionError(f"illegal transition: {self._state} -> {target}")
        self._state = target
        return self._state
