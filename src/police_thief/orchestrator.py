"""Single Gateway per peer (FR-052, architecture.md §3): owns the state
machine, board, opponent-belief scent, and strategy. This is the only
component that talks to the strategy module, mutates the board, and
produces/consumes protocol messages — the networking layer (Part 8) stays
rule-free, and the domain layer stays I/O-free.

Per-turn state-machine mapping and turn order: see docs/assumptions.md A-017.
"""

from __future__ import annotations

import contextlib
import json
from dataclasses import dataclass, field

from police_thief.domain.board import BoardState, IllegalActionError, Outcome
from police_thief.domain.crypto import commit as crypto_commit
from police_thief.domain.crypto import hash_state
from police_thief.domain.models import Coordinate, Direction, GameConfig, Role
from police_thief.domain.scent import ScentField
from police_thief.domain.state_machine import GamePhase, GamePhaseMachine, IllegalTransitionError
from police_thief.infra.protocol import MessageType, ProtocolMessage, ProtocolResponse, RejectReason
from police_thief.strategy.base import Action, BrainBase, MoveAction, build_belief_view


def _action_to_move_str(action: Action) -> str:
    if isinstance(action, MoveAction):
        return f"MOVE:{action.direction.value}"
    return f"BARRIER:{action.coord.row}:{action.coord.col}"


def _direction_from_move_str(move_str: str) -> Direction:
    return Direction(move_str.removeprefix("MOVE:"))


def _barrier_coord_from_move_str(move_str: str) -> Coordinate:
    _, row_str, col_str = move_str.split(":")
    return Coordinate(row=int(row_str), col=int(col_str))


def _opponent_of(role: Role) -> Role:
    return Role.THIEF if role is Role.POLICE else Role.POLICE


def _canonical_board_snapshot(board: BoardState) -> str:
    """A stable textual snapshot used as the crypto commitment's ``State``
    component, preventing a move from being replayed against a stale turn.
    """
    barrier_list = sorted((c.row, c.col) for c in board.barriers)
    return (
        f"cop={board.cop_position.row},{board.cop_position.col};"
        f"thief={board.thief_position.row},{board.thief_position.col};"
        f"barriers={barrier_list};moves={board.moves_made}"
    )


@dataclass
class LogEntry:
    """One committed-then-revealed action; ``nonce`` is filled in only at
    end-of-game (FINAL_REVEAL), matching the book's own timing (§5.3.2).
    """

    turn_number: int
    role: Role
    state_hash: str
    move: str
    intent: str
    h_commit: str
    nonce: str | None = None


@dataclass
class _PendingOwnTurn:
    action: Action
    entry: LogEntry


class TechnicalLossError(Exception):
    """Raised for a disqualifying violation — ours or the opponent's (FR-021/FR-043)."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


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
    _pending: _PendingOwnTurn | None = field(default=None, init=False, repr=False)
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

    # -- own turn: WAITING_FOR_OPPONENT -> COMPUTING_MOVE -> COMMITTING ----

    def produce_commit(self) -> ProtocolMessage:
        """Decide an action via the strategy module and commit to it."""
        self.phase.transition(GamePhase.COMPUTING_MOVE)
        view = build_belief_view(self.board, self.opponent_scent, self.role)
        action = self.brain.decide(view)
        state_hash = hash_state(_canonical_board_snapshot(self.board))
        move_str = _action_to_move_str(action)
        h_commit, nonce = crypto_commit(state=state_hash, move=move_str, intent="truth")
        entry = LogEntry(
            turn_number=self.turn_number,
            role=self.role,
            state_hash=state_hash,
            move=move_str,
            intent="truth",
            h_commit=h_commit,
            nonce=nonce,
        )
        self._pending = _PendingOwnTurn(action=action, entry=entry)
        self.phase.transition(GamePhase.COMMITTING)
        return ProtocolMessage(
            message_type=MessageType.COMMIT,
            game_id=self.game_id,
            turn_number=self.turn_number,
            sender_role=self.role,
            payload={"h_commit": entry.h_commit},
        )

    def produce_reveal(self) -> ProtocolMessage:
        """COMMITTING -> AWAITING_REVEAL: reveal move+hint (nonce still hidden)."""
        if self._pending is None:
            raise TechnicalLossError("produce_reveal() called before produce_commit()")
        self.phase.transition(GamePhase.AWAITING_REVEAL)
        entry = self._pending.entry
        return ProtocolMessage(
            message_type=MessageType.REVEAL,
            game_id=self.game_id,
            turn_number=self.turn_number,
            sender_role=self.role,
            payload={"move": entry.move},
        )

    def confirm_reveal_accepted(self, response: ProtocolResponse) -> None:
        """AWAITING_REVEAL -> VERIFYING -> WAITING_FOR_OPPONENT: apply our own
        action locally once the opponent confirms the reveal was legal.
        """
        if self._pending is None:
            raise TechnicalLossError("confirm_reveal_accepted() with no pending turn")
        if not response.accepted:
            self._fail(f"opponent rejected our reveal: {response.reason}", disqualified=self.role)
            return
        self.phase.transition(GamePhase.VERIFYING)
        action = self._pending.action
        try:
            if isinstance(action, MoveAction):
                self.board.apply_move(self.role, action.direction)
            else:
                self.board.place_barrier(action.coord)
        except IllegalActionError as exc:
            self._fail(
                f"own action became illegal before it could be applied: {exc}",
                disqualified=self.role,
            )
            return
        self.own_log.append(self._pending.entry)
        self._pending = None
        self.turn_number += 1
        if not self.phase.is_terminal:
            self.phase.transition(GamePhase.WAITING_FOR_OPPONENT)

    # -- incoming messages from the opponent --------------------------------

    def handle_message(self, message: ProtocolMessage) -> ProtocolResponse:
        """Dispatch table used by the FastMCP server handler (Part 8)."""
        if message.message_type is MessageType.COMMIT:
            return self._receive_commit(message)
        if message.message_type is MessageType.REVEAL:
            return self._receive_reveal(message)
        if message.message_type is MessageType.FINAL_REVEAL:
            return self._receive_final_reveal(message)
        return ProtocolResponse(accepted=False, reason=RejectReason.MALFORMED)

    def produce_final_reveal(self) -> ProtocolMessage:
        """End-of-game: reveal every nonce this side ever committed (§5.3.2
        step 4), so the opponent (and the standalone Replay Viewer, Part 13)
        can independently recompute and verify every commitment hash.
        """
        payload = {
            str(entry.turn_number): json.dumps(
                {"state_hash": entry.state_hash, "nonce": entry.nonce}
            )
            for entry in self.own_log
        }
        return ProtocolMessage(
            message_type=MessageType.FINAL_REVEAL,
            game_id=self.game_id,
            turn_number=self.turn_number,
            sender_role=self.role,
            payload=payload,
        )

    def _receive_final_reveal(self, message: ProtocolMessage) -> ProtocolResponse:
        """Fill in the opponent's ``state_hash``/``nonce`` for every turn we
        already recorded, so :meth:`export_log` can produce a fully
        verifiable record (FR-045, §5.4 mutual audit).
        """
        for entry in self.opponent_log:
            key = str(entry.turn_number)
            if key not in message.payload:
                continue
            data = json.loads(message.payload[key])
            entry.state_hash = data["state_hash"]
            entry.nonce = data["nonce"]
        return ProtocolResponse(accepted=True)

    def export_log(self) -> list[dict[str, object]]:
        """Merge our own and the opponent's log entries, sorted by turn, in
        the shape the Replay Viewer (Part 13) expects.
        """
        combined = [*self.own_log, *self.opponent_log]
        combined.sort(key=lambda e: (e.turn_number, e.role.value))
        return [
            {
                "turn_number": e.turn_number,
                "role": e.role.value,
                "state_hash": e.state_hash,
                "move": e.move,
                "intent": e.intent,
                "h_commit": e.h_commit,
                "nonce": e.nonce,
            }
            for e in combined
        ]

    def _receive_commit(self, message: ProtocolMessage) -> ProtocolResponse:
        """Record the opponent's commitment hash for the end-of-game audit;
        no board mutation happens on a bare commit (docs/protocol.md §3).
        """
        self._pending_opponent_commit = message.payload.get("h_commit", "")
        return ProtocolResponse(accepted=True)

    def _receive_reveal(self, message: ProtocolMessage) -> ProtocolResponse:
        """Apply the opponent's revealed move to our mirror of their
        position, checking legality immediately. The cryptographic proof
        that this reveal matches the earlier commit is deferred to the
        end-of-game audit (§5.4) since the nonce isn't sent yet.
        """
        opponent_role = _opponent_of(self.role)
        move_str = message.payload.get("move", "")
        try:
            if move_str.startswith("MOVE:"):
                self.board.apply_move(opponent_role, _direction_from_move_str(move_str))
            elif move_str.startswith("BARRIER:"):
                self.board.place_barrier(_barrier_coord_from_move_str(move_str))
            else:
                return ProtocolResponse(accepted=False, reason=RejectReason.MALFORMED)
        except IllegalActionError:
            self._fail("opponent's revealed move was illegal", disqualified=opponent_role)
            return ProtocolResponse(accepted=False, reason=RejectReason.ILLEGAL_MOVE)

        self.opponent_log.append(
            LogEntry(
                turn_number=message.turn_number,
                role=opponent_role,
                state_hash="",  # unknown until FINAL_REVEAL
                move=move_str,
                intent="truth",
                h_commit=self._pending_opponent_commit,
            )
        )
        self.opponent_scent.deposit(self.board.position_of(opponent_role))
        return ProtocolResponse(accepted=True)
