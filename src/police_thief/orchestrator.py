"""Single Gateway per peer (FR-052, architecture.md §3): owns the state
machine, board, opponent-belief scent, and strategy. This is the only
component that talks to the strategy module, mutates the board, and
produces/consumes protocol messages — the networking layer (Part 8) stays
rule-free, and the domain layer stays I/O-free.

Per-turn state-machine mapping and turn order: see docs/assumptions.md A-017.

Split across four files (each kept under the project's 150-line limit): this
file owns the ``Orchestrator`` dataclass, its fields, and failure bookkeeping;
``orchestrator_turn.py`` owns the own-turn commit/reveal flow;
``orchestrator_messages.py`` owns incoming-message handling; both are plain
functions re-exposed here as methods. ``orchestrator_types.py`` owns the small
shared value types and string-(de)serialization helpers all three use.
"""

from __future__ import annotations

import contextlib
from dataclasses import dataclass, field

from police_thief import orchestrator_messages as _messages
from police_thief import orchestrator_turn as _turn
from police_thief.domain.board import BoardState, Outcome
from police_thief.domain.game_config import GameConfig
from police_thief.domain.models import Role
from police_thief.domain.scent import ScentField
from police_thief.domain.state_machine import GamePhase, GamePhaseMachine, IllegalTransitionError
from police_thief.infra.protocol import ProtocolMessage, ProtocolResponse
from police_thief.orchestrator_types import LogEntry, PendingOwnTurn, TechnicalLossError
from police_thief.strategy.base import BrainBase

__all__ = ["LogEntry", "Orchestrator", "TechnicalLossError"]


@dataclass
class Orchestrator:
    """Owns one peer's side of a single game."""

    role: Role
    game_id: str
    config: GameConfig
    board: BoardState
    brain: BrainBase
    phase: GamePhaseMachine = field(default_factory=GamePhaseMachine)
    turn_number: int = 0
    own_log: list[LogEntry] = field(default_factory=list)
    opponent_log: list[LogEntry] = field(default_factory=list)
    technical_loss_reason: str | None = field(default=None, init=False)
    technical_loss_role: Role | None = field(default=None, init=False)
    opponent_scent: ScentField = field(init=False)
    _pending: PendingOwnTurn | None = field(default=None, init=False, repr=False)
    _pending_opponent_commit: str = field(default="", init=False, repr=False)

    def __post_init__(self) -> None:
        self.opponent_scent = ScentField(config=self.config)

    @property
    def is_over(self) -> bool:
        return self.board.outcome is not Outcome.ONGOING or self.technical_loss_reason is not None

    def _fail(self, reason: str, disqualified: Role | None = None) -> None:
        """Record a disqualifying violation. ``technical_loss_reason``/
        ``is_over`` are the authoritative "is this game over" signal — the
        phase machine only visits TECHNICAL_LOSS from an active-mover state
        (COMPUTING_MOVE/AWAITING_REVEAL/VERIFYING, matching Figure 11
        exactly); a violation detected while merely receiving the opponent's
        message (still WAITING_FOR_OPPONENT) still ends the game via
        ``technical_loss_reason``, without forcing an off-diagram transition
        (assumptions.md A-017). ``disqualified`` records which role's action
        caused the violation, used by reporting (FR-021/assumptions.md A-014).
        """
        self.technical_loss_reason = reason
        self.technical_loss_role = disqualified
        if self.phase.is_terminal:
            return
        with contextlib.suppress(IllegalTransitionError):
            self.phase.transition(GamePhase.TECHNICAL_LOSS)

    def reject_own_commit(self, response: ProtocolResponse) -> None:
        """Called by the peer runtime if the opponent's ACK to our own
        COMMIT is rejected (before we ever reach :meth:`produce_reveal`).
        """
        self._fail(f"opponent rejected our commit: {response.reason}", disqualified=self.role)
        self._pending = None

    def mark_opponent_unresponsive(self, waited_seconds: float) -> None:
        """Called by the peer runtime (Part 16) when the opponent hasn't
        moved within the local wait budget (Deadline Tracker, FR-053) — a
        connectivity failure, not a rules violation, so no side is recorded
        as the disqualified party.
        """
        self._fail(f"opponent unresponsive after {waited_seconds:.0f}s", disqualified=None)

    # -- own turn (orchestrator_turn.py) -------------------------------------

    def produce_commit(self) -> ProtocolMessage:
        """Decide an action via the strategy module and commit to it."""
        return _turn.produce_commit(self)

    def produce_reveal(self) -> ProtocolMessage:
        """COMMITTING -> AWAITING_REVEAL: reveal move+hint (nonce still hidden)."""
        return _turn.produce_reveal(self)

    def confirm_reveal_accepted(self, response: ProtocolResponse) -> None:
        """AWAITING_REVEAL -> VERIFYING -> WAITING_FOR_OPPONENT: apply our own
        action locally once the opponent confirms the reveal was legal.
        """
        _turn.confirm_reveal_accepted(self, response)

    # -- incoming messages from the opponent (orchestrator_messages.py) -----

    def handle_message(self, message: ProtocolMessage) -> ProtocolResponse:
        """Dispatch table used by the FastMCP server handler (Part 8)."""
        return _messages.handle_message(self, message)

    def produce_final_reveal(self) -> ProtocolMessage:
        """End-of-game: reveal every nonce this side ever committed (§5.3.2
        step 4), so the opponent (and the standalone Replay Viewer, Part 13)
        can independently recompute and verify every commitment hash.
        """
        return _messages.produce_final_reveal(self)

    def _receive_final_reveal(self, message: ProtocolMessage) -> ProtocolResponse:
        return _messages.receive_final_reveal(self, message)

    def export_log(self) -> list[dict[str, object]]:
        """Merge our own and the opponent's log entries, sorted by turn, in
        the shape the Replay Viewer (Part 13) expects.
        """
        return _messages.export_log(self)

    def _receive_commit(self, message: ProtocolMessage) -> ProtocolResponse:
        return _messages.receive_commit(self, message)

    def _receive_reveal(self, message: ProtocolMessage) -> ProtocolResponse:
        return _messages.receive_reveal(self, message)
