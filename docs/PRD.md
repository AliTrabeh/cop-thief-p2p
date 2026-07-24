# Product Requirements Document — Police–Thief P2P

This is the granular product requirements document for the project: every individually testable
product behavior, decomposed to a level finer than the `FR-xxx`/`NFR-xxx` IDs in
`docs/requirements_traceability.md`. Where the traceability matrix says "FR-030: scent decays each
turn," this document breaks that into the individual decay-formula requirement, the re-emission
requirement, the clamping-at-zero requirement, the normalization requirement, etc. — each with its
own ID, so "done" is unambiguous at the smallest useful grain.

**How this file relates to the other planning docs:**
- `docs/STATUS.md` — phase-level status (18 phases, "what stage is the project at").
- `docs/requirements_traceability.md` — the lecturer spec's own FR/NFR/PROTO/TEST/DOC IDs, mapped
  to modules and tests (source-of-truth for grading compliance).
- **This file (`docs/PRD.md`)** — the product's own requirements, one level more granular,
  covering not just what the spec mandates but every user-facing and internal behavior the shipped
  product needs to have, including things the spec leaves implicit (error messages, config
  defaults, CLI help text, etc.).

**ID scheme**: `PRD-NNNN`, assigned sequentially, grouped into numbered sections by subsystem.
IDs are never reused or renumbered — a dropped requirement is marked `Cut`, not deleted, so IDs
stay stable across revisions.

**Priority** (MoSCoW): **Must** (grading-critical or core gameplay breaks without it) · **Should**
(expected, degrades quality if missing) · **Could** (nice-to-have, non-blocking) · **Bonus**
(explicitly optional per the spec).

**Status**: **Done** (implemented + tested) · **Partial** (implemented, gap noted inline) ·
**Planned** (designed, not built) · **Not Started** · **Deferred** (needs a decision, not code) ·
**Cut** (explicitly out of scope).

**Ref**: the corresponding `FR-xxx`/`NFR-xxx`/`PROTO-xxx`/`TEST-xxx`/`DOC-xxx`/`A-xxx`/`E-xx` ID in
the other docs, where one exists; `—` when the requirement is product-level detail the spec itself
doesn't enumerate.

---

## 1. Product Vision & Scope

| ID | Requirement | Priority | Status | Ref |
|---|---|---|---|---|
| PRD-0001 | The product is a fully decentralized, peer-to-peer implementation of Cops-and-Robbers, with no central server, judge, matchmaking service, or shared authoritative game state. | Must | Done | FR-001 |
| PRD-0002 | Each of the two roles (cop, thief) is played by an independently-run OS process, potentially on two different machines owned by two different students/teams. | Must | Done | FR-001 |
| PRD-0003 | The game is modeled formally as a 2-agent Dec-POMDP: `⟨n, S, {Aᵢ}, P, R, {Ωᵢ}, O, γ⟩`. | Must | Done | — |
| PRD-0004 | Neither agent ever has access to the true global board state `S`; each only ever sees its own position plus a locally-derived belief about the opponent. | Must | Done | FR-005 |
| PRD-0005 | The product must be runnable and demonstrably playable end-to-end by a third party (the lecturer) without needing this development environment. | Must | Done | DOC-001 |
| PRD-0006 | The product ships as a single installable Python package (`police_thief`) with a `python -m police_thief` CLI entry point. | Must | Done | FR-002 |
| PRD-0007 | The product must support both a fully local (localhost, two terminals) demo mode and a genuinely remote (tunnel, real opponent machine) mode. | Must | Done | FR-006 |
| PRD-0008 | The product's default configuration must exactly match every mandatory parameter table in the lecturer's spec (grid size, scoring, pheromone constants, network/league constants). | Must | Done | FR-084 |
| PRD-0009 | The product must allow a rival team's strategy code to be swapped in without touching networking, crypto, or board logic. | Should | Done | FR-060 |
| PRD-0010 | The product must not consume paid third-party API credits (LLM tokens, etc.) by default. | Must | Done | A-005 |
| PRD-0011 | The product must produce, at the end of every game, a fixed set of machine-readable deliverable files suitable for automated grading. | Must | Done | FR-082 |
| PRD-0012 | The product's source, docs, and test suite must together make the system's correctness independently verifiable by a reviewer who did not write it. | Must | Done | DOC-005 |

## 2. Game World & State Space

| ID | Requirement | Priority | Status | Ref |
|---|---|---|---|---|
| PRD-0013 | The board is a square grid of configurable size (`grid_size`), default 7×7. | Must | Done | FR-010 |
| PRD-0014 | Grid size must be adjustable upward via config without code changes. | Must | Done | FR-010 |
| PRD-0015 | The board's axis origin corner is configurable (`axis_origin_corner`, default `top-left`). | Must | Done | A-003 |
| PRD-0016 | The board's axis start index is configurable (`axis_start_index`, default `0`). | Must | Done | A-003 |
| PRD-0017 | Exactly two agents occupy the board at any time: one cop, one thief (`num_agents = 2`). | Must | Done | FR-011 |
| PRD-0018 | Each agent has a distinct, configurable starting coordinate (`cop_start`, `thief_start`). | Must | Done | FR-012 |
| PRD-0019 | Starting coordinates must be validated as in-bounds for the configured `grid_size` at config-load time, not discovered mid-game. | Must | Done | A-009 |
| PRD-0020 | Starting coordinates must be validated as distinct from each other (no same-cell start). | Must | Done | FR-012 |
| PRD-0021 | The board tracks placed barriers as a set of occupied, non-agent cells. | Must | Done | FR-013 |
| PRD-0022 | The board tracks a running move counter, incremented once per completed turn. | Must | Done | FR-014 |
| PRD-0023 | The board tracks a running barrier counter, incremented once per barrier placed, capped at `max_barriers`. | Must | Done | FR-014 |
| PRD-0024 | A `map_area` label (default `"New York"`) is attached to the world config purely for flavor/reporting, with no effect on game logic. | Could | Done | — |
| PRD-0025 | A `hint_max_words` config field bounds any free-text hint/banter length (default 15 words). | Should | Done | FR-064 |
| PRD-0026 | The board representation must be serializable to canonical JSON for hashing/logging purposes. | Must | Done | PROTO-002 |
| PRD-0027 | The board state (`BoardState`) is an immutable-by-convention value object; mutation happens only through explicit, legality-checked transition functions. | Should | Done | NFR-001 |
| PRD-0028 | Board module code (`domain/board.py`) must have zero I/O imports (no network, no file writes) — pure domain logic. | Must | Done | NFR-001 |
| PRD-0029 | The board must expose a query for "is cell `(x, y)` currently occupied by a barrier." | Must | Done | FR-013 |
| PRD-0030 | The board must expose a query for "is cell `(x, y)` currently occupied by the opposing agent." | Must | Done | FR-011 |
| PRD-0031 | The board must expose a query for "is coordinate `(x, y)` in-bounds for the current grid." | Must | Done | FR-010 |
| PRD-0032 | 100% branch coverage is targeted on `domain/board.py` given its role as the single source of truth for legality. | Should | Done | implementation_plan.md Part 2 |
| PRD-0033 | The board's coordinate type (`Coordinate`) is a typed, hashable dataclass — never a bare tuple passed around ambiguously. | Should | Done | — |
| PRD-0034 | Board edge cases (corner cells, edge cells) must be covered by explicit fixture tests, not just interior cells. | Should | Done | implementation_plan.md Part 2 |

## 3. Movement & Action Space

| ID | Requirement | Priority | Status | Ref |
|---|---|---|---|---|
| PRD-0035 | Both agents share the same action space: four cardinal moves (N/S/E/W) plus STAY. | Must | Done | FR-014 |
| PRD-0036 | Diagonal movement is not merely rejected — it has no representable value in the action type at all (`Direction` enum has 4 members + STAY). | Must | Done | A-010 |
| PRD-0037 | A move that would leave the grid boundary is illegal and rejected before it can be applied to board state. | Must | Done | FR-015 |
| PRD-0038 | A move onto a barrier cell is illegal and rejected. | Must | Done | FR-015 |
| PRD-0039 | A move onto the opponent's current cell is legal and constitutes a capture (cop moving onto thief), not an error. | Must | Done | FR-020 |
| PRD-0040 | The STAY action is always legal regardless of board state (never blocked). | Must | Done | FR-014 |
| PRD-0041 | Move legality checking is a pure function of `(BoardState, Direction) → bool`, independent of whose turn it is. | Should | Done | FR-015 |
| PRD-0042 | The cop, additionally, has a barrier-placement action available instead of a move on any given turn. | Must | Done | FR-016 |
| PRD-0043 | The thief never has a barrier-placement action. | Must | Done | FR-016 |
| PRD-0044 | An illegal move revealed at the protocol layer (not just rejected locally) ends the game as a technical loss for the offending side. | Must | Done | FR-016 |
| PRD-0045 | The move/action type is part of the canonical JSON committed and hashed — it cannot be altered after commit without detection. | Must | Done | FR-040 |
| PRD-0046 | Action legality must be re-checked independently by both peers on reveal (never trust the mover's own claim of legality). | Must | Done | FR-044, E-22 |
| PRD-0047 | A property-based/fuzz test asserts the default brain always returns a legal move for any legal random board state. | Should | Done | implementation_plan.md Part 7 |
| PRD-0048 | Move direction names in logs/JSON are the exact strings `N`, `S`, `E`, `W`, `STAY` (matching the spec's `move_set` field) — no alternate encodings. | Must | Done | PROTO-002 |
| PRD-0049 | The action space is identical in size and shape for both roles except for the barrier-placement addition — no role gets an extra movement option. | Must | Done | FR-014 |
| PRD-0050 | Applying a legal move updates exactly one agent's position; the other agent's position is untouched. | Must | Done | FR-014 |
| PRD-0051 | STAY does not reset or otherwise affect the pheromone deposit at the agent's current cell (a stationary agent still deposits scent). | Should | Done | FR-030 |
| PRD-0052 | Move history is append-only in the game log — no move can be retroactively edited once revealed. | Must | Done | FR-045 |

## 4. Barrier Mechanics

| ID | Requirement | Priority | Status | Ref |
|---|---|---|---|---|
| PRD-0053 | Barriers may only be placed by the cop, on an adjacent empty cell. | Must | Done | FR-016 |
| PRD-0054 | Total barriers placed across a game is capped at `max_barriers` (default 14), enforced by the board, not just by convention. | Must | Done | FR-017 |
| PRD-0055 | Attempting to place a barrier beyond the cap is illegal and rejected the same way an out-of-bounds move is. | Must | Done | FR-017 |
| PRD-0056 | A barrier cannot be placed on a cell already occupied by a barrier. | Must | Done | FR-013 |
| PRD-0057 | A barrier cannot be placed on a cell currently occupied by either agent. | Must | Done | FR-013 |
| PRD-0058 | Every barrier placement is revealed to the opponent via the same commit-reveal cycle as a move — never placed silently or out-of-band. | Must | Done | FR-016 |
| PRD-0059 | A cop "cornering" the thief (thief has no legal moves remaining due to barriers/board edge) is a distinct, detectable end-of-game condition. | Should | Done | README §4 |
| PRD-0060 | The default heuristic cop brain prefers a cornering barrier placement over a move when the believed thief cell is adjacent. | Could | Done | README §4 |
| PRD-0061 | Barrier state is part of the board snapshot used for legality checks on every subsequent turn (barriers persist for the whole game, never expire). | Must | Done | FR-013 |
| PRD-0062 | The barrier counter is exposed in the live GUI / logs so a human observer can see remaining barrier budget. | Should | Partial | FR-070 |
| PRD-0063 | Barrier legality has its own dedicated unit tests distinct from movement legality tests. | Must | Done | tests/unit/test_board.py |
| PRD-0064 | A barrier placement action is structurally distinguishable from a move action in the wire protocol (not overloaded onto the same field ambiguously). | Must | Done | PROTO-002 |
| PRD-0065 | Placing the game's final available barrier does not itself end the game — only capture/survival/technical-loss conditions do. | Must | Done | FR-016 |
| PRD-0066 | Barrier cells are rendered visually distinct from empty/occupied cells in the live GUI heatmap. | Should | Partial | FR-070 |
| PRD-0067 | The barrier cap is one of the values validated at config-load time to be a small non-negative integer consistent with `grid_size` (can't exceed total cell count). | Should | Done | A-009 |

## 5. Capture & Win Conditions

| ID | Requirement | Priority | Status | Ref |
|---|---|---|---|---|
| PRD-0068 | Capture occurs when the cop's revealed move results in occupying the thief's current cell. | Must | Done | FR-020 |
| PRD-0069 | Capture is derived automatically from real board state on both sides independently — never self-reported by either player. | Must | Done | FR-044, E-22 |
| PRD-0070 | Both peers' independently-computed capture determination must agree exactly (same outcome, same move count) — asserted by integration/e2e tests. | Must | Done | FR-044 |
| PRD-0071 | Survival is declared once `max_moves` is reached without capture (default 35). | Must | Done | FR-021 |
| PRD-0072 | `survival_threshold` (default 35) and `max_moves` (default 35) are both config-driven, not hardcoded. | Must | Done | FR-021 |
| PRD-0073 | A technical loss is declared against a side that reveals an illegal move, fails a commit/reveal hash check, or times out past its deadline. | Must | Done | FR-043, FR-053 |
| PRD-0074 | Exactly one of {capture, survival, tie, technical-loss} is the terminal outcome of any completed game — no game ends in an undefined state. | Must | Done | FR-021 |
| PRD-0075 | A tie outcome is representable and scored distinctly from survival (per the scoring table's `tie_score`). | Must | Done | FR-020 |
| PRD-0076 | Outcome determination does not depend on message arrival order beyond what the state machine already enforces (no race condition where either side could "win" depending on network timing). | Must | Done | FR-052 |
| PRD-0077 | The `max_moves` hard cap guarantees every game terminates in bounded time regardless of strategy behavior (no infinite-game risk). | Must | Done | final_audit.md §11 |
| PRD-0078 | Outcome, final positions, and move count are all included in the final JSON `result` deliverable. | Must | Done | FR-082 |
| PRD-0079 | A "cornering" capture (thief has zero legal moves due to barriers) is distinguished in the result payload from a direct move-onto-thief capture, if the two are logically distinct in the implementation. | Could | Partial | README §4 |
| PRD-0080 | Every possible terminal state has at least one dedicated test asserting it is reachable and correctly scored. | Must | Done | tests/unit/test_scoring.py, tests/unit/test_orchestrator.py |
| PRD-0081 | `TECHNICAL_LOSS` is a terminal state in the state machine with zero outgoing transitions (cannot un-happen). | Must | Done | FR-052, TEST-004 |
| PRD-0082 | Both sides converge on the same declared outcome even in the two-real-OS-process e2e test (not just in-process simulation). | Must | Done | TEST-007 |

## 6. Scoring & Rewards

| ID | Requirement | Priority | Status | Ref |
|---|---|---|---|---|
| PRD-0083 | Scoring constants exactly match the spec's mandatory table: `capture_cop=20`, `capture_thief=5`, `survival_cop=5`, `survival_thief=10`, `tie_score=2`, `technical_loss=0`. | Must | Done | A-001 |
| PRD-0084 | Scoring is asymmetric by design (cop and thief are scored on different scales reflecting the Dec-POMDP reward `R`) — not a bug, an intentional per-role reward split. | Must | Done | A-001 |
| PRD-0085 | The scoring function is pure: `(Outcome, Role) → int`, with no side effects and no hidden state. | Must | Done | domain/scoring.py |
| PRD-0086 | Scoring is computed identically and independently by both peers; no peer trusts the other's self-reported score. | Must | Done | FR-021 |
| PRD-0087 | A technical loss always scores `0` for the offending side regardless of how much of the game had already been "won" positionally. | Must | Done | A-001 |
| PRD-0088 | `diversity_reward` (default 10) exists in config for the multi-game league mode, rewarding playing a wider variety of rivals. | Should | Partial | FR-084 |
| PRD-0089 | Scoring constants are loaded from `config/game.json → scoring`, never hardcoded duplicated literals inside the scoring function. | Must | Done | domain/scoring.py |
| PRD-0090 | A dedicated unit test asserts the scoring table round-trips through config load exactly matching the book's own example numbers. | Must | Done | tests/unit/test_config.py |
| PRD-0091 | Scoring is unit-tested for every one of the four outcome × two role combinations (8 cases) plus the tie case. | Must | Done | tests/unit/test_scoring.py |
| PRD-0092 | The scoring module has no I/O imports (pure domain package boundary). | Must | Done | NFR-001 |
| PRD-0093 | League-level score aggregation across multiple games (summing per-game scores for a series) is at minimum representable in the data model, even if the audit/reporting side is not fully wired. | Should | Planned | FR-083 |
| PRD-0094 | `min_games_to_pass` (default 2) and `max_games_per_team` (default 10) are validated as sane relative to each other at config load (`min <= max`). | Should | Done | A-002 |
| PRD-0095 | `num_games` (default 6, per-series) is a fixed constant per the spec's Table 18 and is asserted against in a config round-trip test. | Must | Done | FR-084 |
| PRD-0096 | `token_budget_per_series` (default 200000) exists in config to cap LLM usage across an entire league series, not just per game. | Should | Done | A-005 |
| PRD-0097 | Two internal contradictions found in the lecturer's own spec around scoring numbers are explicitly documented with the resolution chosen, not silently picked. | Must | Done | assumptions.md (games-per-rival / capture-scoring) |
| PRD-0098 | Score values are always non-negative integers in the current model (no negative-score / penalty mechanic exists). | Must | Done | domain/scoring.py |
| PRD-0099 | The result JSON deliverable includes both the raw outcome label and the numeric score derived from it, so a grader doesn't have to recompute the mapping. | Must | Done | FR-082 |
| PRD-0100 | Scoring changes (e.g. a future rebalance) are a one-file config edit (`config/game.json`), never require touching `domain/scoring.py` logic. | Should | Done | domain/scoring.py |

## 7. Scent / Pheromone Observation Model

| ID | Requirement | Priority | Status | Ref |
|---|---|---|---|---|
| PRD-0101 | Each agent deposits a pheromone/scent value at its current cell every turn (`pheromone_center_intensity`, default 0.9). | Must | Done | FR-030 |
| PRD-0102 | Scent decays every turn at a configurable rate (`pheromone_decay`, default 0.10). | Must | Done | FR-030 |
| PRD-0103 | The decay curve matches the book's own numerical figure for a single deposit's falloff. | Must | Done | TEST-002 |
| PRD-0104 | Re-emission (the depositing agent remaining in scent range across multiple turns) converges toward the book's documented "~half-peak-at-turn-8" behavior. | Must | Done | TEST-002 |
| PRD-0105 | Scent values are clamped at a minimum of zero (never go negative through repeated decay). | Must | Done | TEST-002 |
| PRD-0106 | The scent field has a bounded spatial extent (`pheromone_grid_size`, default 5) around each deposit — not global-board diffusion. | Must | Done | FR-030 |
| PRD-0107 | Each agent's scent field is private to that agent's own trail — an agent never directly senses the opponent's true position through this channel. | Must | Done | FR-005 |
| PRD-0108 | Scent decay/emission parameters (`PheromoneConfig`) are fixed at config-parse time; no in-game code path mutates them mid-game. | Must | Done | FR-031 |
| PRD-0109 | The scent module has zero I/O imports — pure deterministic math over a grid. | Must | Done | NFR-001 |
| PRD-0110 | Scent field updates are a pure function of `(previous field, current agent position) → new field`, replayable deterministically from a log. | Must | Done | FR-045 |
| PRD-0111 | Overlapping scent deposits (agent revisiting a cell before full decay) accumulate rather than reset to the peak value. | Should | Done | tests/unit/test_scent.py |
| PRD-0112 | The scent grid is independent of (does not need to equal) the game board's `grid_size` — it's a local window, not the whole board. | Should | Done | FR-030 |
| PRD-0113 | A dedicated test validates the scent field never exceeds the theoretical peak intensity (`pheromone_center_intensity`) at any cell. | Should | Done | tests/unit/test_scent.py |
| PRD-0114 | Scent state for a given agent is included in that agent's own log records (for replay), but never leaked into the opponent's log or messages. | Must | Done | FR-005 |
| PRD-0115 | The decay formula is documented in `docs/protocol.md`/`architecture.md` with the exact equation used, not just described in prose. | Should | Done | architecture.md |
| PRD-0116 | Config validation rejects a `pheromone_decay` outside the sane `[0, 1]` range at load time. | Should | Done | tests/unit/test_config.py |
| PRD-0117 | Config validation rejects a negative or zero `pheromone_grid_size`. | Should | Done | tests/unit/test_config.py |
| PRD-0118 | The scent engine's numeric behavior at the grid boundary (deposit near an edge) doesn't crash or silently truncate incorrectly — validated by an edge-case test. | Should | Done | tests/unit/test_scent.py |
| PRD-0119 | Scent intensity-to-color mapping for the GUI heatmap is a separate, independently testable pure function from the scent math itself. | Should | Done | gui/live_view.py::belief_to_color |
| PRD-0120 | The scent/belief subsystem's test suite runs with 100% (or near-100%) branch coverage given its role as the core observability mechanic of the whole game. | Should | Done | README §7 |
| PRD-0121 | Scent decay is applied exactly once per completed turn — never double-applied or skipped due to an off-by-one in the turn loop. | Must | Done | orchestrator.py |
| PRD-0122 | The re-emission/decay formulas are validated against multiple different `pheromone_decay` values, not just the default, to catch parametrization bugs. | Could | Done | tests/unit/test_scent.py |

## 8. Belief State & Partial Observability

| ID | Requirement | Priority | Status | Ref |
|---|---|---|---|---|
| PRD-0123 | Each agent's belief `b(s) = P(opponent at s | scent received)` is a normalized probability distribution over board cells. | Must | Done | FR-032 |
| PRD-0124 | The belief map is derived solely from the agent's own received scent field — never from a peek at true board state. | Must | Done | FR-005 |
| PRD-0125 | `most_likely_position` (belief-map argmax) is exposed as a first-class query for strategy code to consume. | Must | Done | FR-032 |
| PRD-0126 | The default heuristic brains consume the belief map, never the true `BoardState` opponent position, when deciding a move. | Must | Done | FR-005, FR-060 |
| PRD-0127 | A dedicated test asserts the thief brain never sees the cop's true position directly (and vice versa) — enforced structurally via `BeliefView`, not just by convention. | Must | Done | tests/unit/test_strategy.py |
| PRD-0128 | `build_belief_view` produces a value object (`BeliefView`) that strategy code receives instead of the raw board, making the observability boundary a type-level guarantee. | Must | Done | strategy/base.py |
| PRD-0129 | Belief-map normalization is validated by a test that sums the distribution and asserts it equals 1.0 (within floating-point tolerance) whenever any scent exists. | Must | Done | tests/unit/test_scent.py |
| PRD-0130 | The belief map correctly degrades to a uniform (or all-zero, per documented convention) distribution when no scent has been received yet (start of game). | Should | Done | tests/unit/test_scent.py |
| PRD-0131 | The live GUI's heatmap renders each side's own belief map only — a "local-truth-only" view, matching the Dec-POMDP model, not an all-knowing debug view. | Must | Done | FR-005, FR-070 |
| PRD-0132 | Belief computation is deterministic given the same scent field input (no hidden randomness), so replay can reproduce it exactly. | Must | Done | FR-045 |
| PRD-0133 | The gap between "true opponent position" and "believed opponent position" is a documented, intentional core mechanic of the game, not an implementation shortcut. | Must | Done | README §1 |
| PRD-0134 | Belief-map computation has no I/O imports (pure domain logic layered on top of the scent field). | Must | Done | NFR-001 |
| PRD-0135 | An agent's belief about the opponent updates every turn regardless of whether the opponent's last move is currently visible or fully occluded by decay. | Must | Done | domain/scent.py |
| PRD-0136 | Multiple simultaneous local maxima in the belief map (ambiguous scent trail) are handled deterministically by the argmax tie-break rule (documented, not arbitrary). | Should | Done | domain/scent.py |
| PRD-0137 | The belief model's partial-observability guarantee holds even in the two-real-process e2e test, not just the in-process unit tests. | Must | Done | tests/e2e/test_two_peer_local_game.py |

## 9. Cryptographic Commit-Reveal Protocol

| ID | Requirement | Priority | Status | Ref |
|---|---|---|---|---|
| PRD-0138 | Every move is committed (hashed) before it is revealed in plaintext. | Must | Done | FR-040 |
| PRD-0139 | The commit hash formula is `SHA256(State ‖ Move ‖ Intent ‖ Nonce)`, matching the book's own reference implementation almost verbatim. | Must | Done | FR-040 |
| PRD-0140 | Canonical JSON serialization (`sort_keys=True`) is used for the hashed payload so both peers hash byte-identical input regardless of dict key insertion order. | Must | Done | PROTO-002 |
| PRD-0141 | The nonce is generated with `secrets.token_hex(16)` — a cryptographically secure random source, not `random`. | Must | Done | FR-041 |
| PRD-0142 | The nonce for a given move stays secret until the reveal phase for that move. | Must | Done | FR-040 |
| PRD-0143 | Hash comparison during verification uses `secrets.compare_digest`, not `==`, to avoid a timing side-channel. | Must | Done | TEST-003 |
| PRD-0144 | `commit()`/`verify()` round-trip correctly: a genuine commit always verifies true against its own reveal. | Must | Done | TEST-003 |
| PRD-0145 | A tampered move value, tampered state value, or tampered nonce each independently causes verification to fail. | Must | Done | TEST-003 |
| PRD-0146 | Canonical JSON serialization is proven stable across different key insertion orders in a dedicated test. | Must | Done | TEST-003 |
| PRD-0147 | Nonce uniqueness across many generated nonces is checked by a statistical smoke test (no observed collisions in a large sample). | Should | Done | TEST-003 |
| PRD-0148 | At game end, both peers reveal every nonce used throughout the game (`produce_final_reveal`/`_receive_final_reveal`). | Must | Done | FR-045 |
| PRD-0149 | Each peer independently replays its full committed log through `verify_step`/`replay` after the final reveal, producing either `Verified OK` or `TAMPERED`. | Must | Done | FR-045, FR-071 |
| PRD-0150 | Verification never blindly trusts a centrally-issued hash — each peer performs the check itself against its own recorded commits. | Must | Done | FR-045 |
| PRD-0151 | A hand-tampered log fixture is correctly flagged `TAMPERED` by the Replay Viewer (negative-path test, not just the happy path). | Must | Done | tests/unit/test_replay_viewer.py |
| PRD-0152 | A clean, untampered log is correctly flagged `Verified OK`. | Must | Done | tests/unit/test_replay_viewer.py |
| PRD-0153 | The 4-phase commit-reveal sequence (commit → ack → reveal → confirm) is documented as a sequence diagram in `docs/protocol.md`. | Should | Done | protocol.md §3 |
| PRD-0154 | A commit/reveal hash mismatch at the protocol layer triggers a technical-loss outcome for the offending side, not a silent skip. | Must | Done | FR-043 |
| PRD-0155 | The crypto module (`domain/crypto.py`) has zero I/O imports — pure hashing/serialization logic. | Must | Done | NFR-001 |
| PRD-0156 | A grep-based lint check (or equivalent) exists to catch any future accidental use of `==` instead of `secrets.compare_digest` for hash comparison. | Should | Done | implementation_plan.md Part 4 |
| PRD-0157 | The commit payload includes the *state* the move was made against, not just the move itself, closing the "replay an old committed move against a new state" attack. | Must | Done | FR-040 |
| PRD-0158 | Every committed field (state, move, intent, nonce) is independently tamper-tested, not just the aggregate hash. | Must | Done | TEST-003 |
| PRD-0159 | The reveal message and the original commit message are cryptographically linked (the reveal must re-derive the exact same hash the commit announced). | Must | Done | FR-042 |
| PRD-0160 | `docs/protocol.md` documents the exact byte-level canonical JSON rules (key order, separators, encoding) so a third party could reimplement a compatible verifier from the doc alone. | Should | Done | protocol.md §3 |
| PRD-0161 | The "Intent" field in the commit hash captures the semantic action (move vs. barrier) distinctly from the raw direction/coordinate payload. | Must | Done | FR-040 |
| PRD-0162 | Nonces are never logged or transmitted before their corresponding reveal phase (checked by the logging redaction filter). | Must | Done | NFR-004 |

---

*Continued in the next sections (10–37) covering networking, protocol, reliability, strategy,
config, CLI, GUI, reporting, testing, non-functional requirements, and submission packaging.*
