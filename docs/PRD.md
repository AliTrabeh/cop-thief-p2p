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

## 10. Anti-Cheat & Tamper Detection

| ID | Requirement | Priority | Status | Ref |
|---|---|---|---|---|
| PRD-0163 | A player cannot change a committed move after seeing the opponent's commit (the hash is announced before either side's move is known in plaintext). | Must | Done | FR-040 |
| PRD-0164 | A player cannot claim a false capture/survival outcome — outcomes are derived independently from real board state on each side. | Must | Done | FR-044, E-22 |
| PRD-0165 | A player cannot claim to have played a legal move that was actually illegal — the receiving side independently re-validates every revealed move. | Must | Done | FR-016, FR-044 |
| PRD-0166 | A player cannot retroactively alter game history — the log is append-only and every entry is covered by the eventual full-log replay verification. | Must | Done | FR-045 |
| PRD-0167 | A player cannot selectively skip revealing a committed move without triggering a technical loss (the state machine requires reveal to advance). | Must | Done | FR-052 |
| PRD-0168 | A player cannot forge the opponent's identity — messages are addressed to a specific configured `opponent_url`, and (where signature verification is wired) validated. | Must | Partial | FR-051 |
| PRD-0169 | Cheating detection never depends on trusting the accused party's own logs — verification always replays independently-held commit records. | Must | Done | FR-045 |
| PRD-0170 | Every anti-cheat guarantee claimed in the README is backed by at least one negative-path test (tampered input correctly rejected), not just a positive-path test. | Must | Done | tests/unit/test_crypto.py, tests/unit/test_replay_viewer.py |
| PRD-0171 | The commit-reveal protocol is documented as directly matching Appendix E's anti-cheat mandatory items, with an explicit E-## cross-reference for each. | Should | Done | requirements_analysis.md |
| PRD-0172 | Duplicate message replay (an old, already-processed message resent) is detected and rejected by the transport/sequencing layer. | Must | Done | PROTO-004 |
| PRD-0173 | Stale/out-of-sequence messages are rejected rather than silently reordered or accepted. | Must | Done | PROTO-004 |
| PRD-0174 | Malformed payloads (schema-invalid JSON) are rejected at the server boundary before reaching game logic. | Must | Done | FR-051 |
| PRD-0175 | Oversized payloads are rejected by a dedicated size guard, preventing a memory/DoS vector through the message channel. | Must | Done | NFR-006 |
| PRD-0176 | A signature-verification step exists in the message-handling pipeline design, even though full cryptographic signing of every message (beyond the commit hash itself) is only partially wired. | Should | Partial | FR-051 |
| PRD-0177 | The anti-cheat design assumes an adversarial opponent by default — every acceptance path has a corresponding rejection test for the adversarial case. | Must | Done | testing_strategy.md |

## 11. P2P Networking & FastMCP Transport

| ID | Requirement | Priority | Status | Ref |
|---|---|---|---|---|
| PRD-0178 | Peers communicate exclusively via the Model Context Protocol (MCP), using FastMCP as the concrete implementation. | Must | Done | FR-050 |
| PRD-0179 | Each peer process runs its own FastMCP tool server (`infra/mcp_server.py`), exposing its game-protocol tools to the opponent. | Must | Done | FR-050 |
| PRD-0180 | Each peer process also acts as an MCP client (`infra/mcp_client.py`) calling into the opponent's server — a genuinely symmetric P2P design, not client-server in disguise. | Must | Done | architecture.md §1/§9 |
| PRD-0181 | No component in the architecture plays the role of a central match server, judge, or lobby. | Must | Done | FR-001 |
| PRD-0182 | A real local FastMCP server+client round trip is tested over the real in-process transport (genuine protocol behavior, no sockets needed in CI). | Must | Done | TEST-005 |
| PRD-0183 | Network calls have a configurable timeout (`response_timeout_sec`, default 30s per game.json / `turn_timeout_seconds`, default 180s per peer config). | Must | Done | FR-053 |
| PRD-0184 | A timed-out call triggers a retry per the Deadline Tracker's configured retry policy before giving up. | Must | Done | FR-004, FR-053 |
| PRD-0185 | An unreachable peer, after exhausting retries, raises a clear, catchable error rather than hanging indefinitely. | Must | Done | TEST-005 |
| PRD-0186 | `wait_until_reachable` allows a peer to poll for its opponent coming online before starting the game loop, for orderly startup. | Should | Done | FR-004 |
| PRD-0187 | For genuinely remote play, a local tunneling tool (ngrok) can expose the local FastMCP server publicly. | Must | Done | FR-006 |
| PRD-0188 | ngrok tunnel lifecycle (start, discover assigned public URL via ngrok's local admin API, tear down on shutdown) is fully automated. | Must | Done | FR-006 |
| PRD-0189 | A `provider = "manual"` config mode supports any other tunneling tool (e.g. Localtonet) by letting the user paste in the public URL directly. | Must | Done | FR-006, A-018 |
| PRD-0190 | A `provider = "none"` config mode (the default) skips tunneling entirely for localhost-only play. | Must | Done | FR-006 |
| PRD-0191 | Starting a tunnel is understood/documented to expose only this peer's own port; the discovered public URL still must be exchanged with the rival out-of-band. | Must | Done | README §9 |
| PRD-0192 | The tunnel module's external dependencies (the ngrok binary, its local HTTP admin API) are fully fake-able/injectable for unit testing without a real ngrok install. | Must | Done | tests/unit/test_tunnel.py |
| PRD-0193 | 11+ dedicated unit tests cover tunnel start/stop/URL-discovery/failure paths. | Must | Done | tests/unit/test_tunnel.py |
| PRD-0194 | A real two-OS-process game (not simulated) completes successfully over real HTTP on localhost, with both processes launched independently. | Must | Done | TEST-007 |
| PRD-0195 | Per-message sessions (initialize → notify → SSE → close) are used rather than one long-lived connection, a documented simplicity-over-latency trade-off. | Should | Done | README §2 |
| PRD-0196 | The documented latency cost of per-message sessions (several seconds per turn in a real two-process game) is explicitly called out, not hidden. | Should | Done | README §2, progress.md |
| PRD-0197 | Each peer's `opponent_url` is independently configured per role (`config/<role>/game.toml → [network] → opponent_url`), never auto-discovered or centrally assigned. | Must | Done | config/police/game.toml |
| PRD-0198 | The network module has clean separation between transport concerns (`mcp_client.py`/`mcp_server.py`) and protocol/message-shape concerns (`infra/protocol.py`). | Should | Done | architecture.md §2 |
| PRD-0199 | The FastMCP server's tool surface is documented in `docs/protocol.md` with the exact tool names and argument schemas. | Should | Done | protocol.md §1 |
| PRD-0200 | Running against a real ngrok binary and a genuinely remote rival is explicitly flagged as not yet done, rather than falsely claimed as tested. | Must | Done | README §9 (Known Limitations) |
| PRD-0201 | The transport layer never silently swallows a network error — every failure path either retries per policy or surfaces as a technical-loss/watchdog event. | Must | Done | FR-053, FR-054 |
| PRD-0202 | Port numbers for both roles are independently configurable (`my_port`, default 8801/8802) to avoid collisions when running two peers on one machine. | Must | Done | config/police/game.toml |

## 12. Message Protocol Schema

| ID | Requirement | Priority | Status | Ref |
|---|---|---|---|---|
| PRD-0203 | Every protocol message carries an explicit `schema_version` field for forward/backward compatibility checks. | Must | Done | PROTO-001 |
| PRD-0204 | The shared config (`config/game.json`) is hash-checked between peers (`shared_config_hash`) so both sides provably agree on the same rule set before playing. | Must | Done | NFR-008 |
| PRD-0205 | A `ProtocolMessage`/`ProtocolResponse` pair of typed structures defines every wire message shape — no ad hoc untyped dicts crossing the network boundary. | Must | Done | infra/protocol.py |
| PRD-0206 | Message sequencing (turn/step numbers) is tracked and validated server-side to catch duplicate or skipped steps. | Must | Done | FR-051, PROTO-004 |
| PRD-0207 | The COMMIT message type carries only the hash, never the plaintext move, at the point it's sent. | Must | Done | protocol.md §3 |
| PRD-0208 | The REVEAL message type carries the plaintext move plus the nonce needed to re-derive the commit hash. | Must | Done | protocol.md §3 |
| PRD-0209 | The FINAL_REVEAL message type carries every nonce used across the whole game, for end-of-game full-log verification. | Must | Done | FR-045 |
| PRD-0210 | Every message type used in the protocol is enumerated and documented in `docs/protocol.md`, with no undocumented "secret" message types in the code. | Should | Done | protocol.md |
| PRD-0211 | A schema-invalid message (missing required field, wrong type) produces a clear rejection at the server, not an unhandled exception/stack trace to the caller. | Must | Done | FR-051 |
| PRD-0212 | Protocol message and response types are validated with Pydantic (or equivalent), not manual dict-key checking scattered through the code. | Should | Done | infra/protocol.py |
| PRD-0213 | The full 4-phase sequence (commit → ack → reveal → confirm) is enforced in order by the receiving side's state machine, not just assumed. | Must | Done | protocol.md §4 |
| PRD-0214 | Config schema version (`"1.2"` for `game.json`, `"1.10"` for peer `game.toml`) is explicit and checked, so a stale config format fails loudly rather than silently misbehaving. | Should | Done | config/game.json |
| PRD-0215 | The `group_name`/`group_id`/`members`/`repos` identity block in peer config is part of the documented schema, feeding the declaration JSON deliverable. | Must | Done | FR-088 |
| PRD-0216 | Protocol-level tests exercise the network transport's real request/response cycle end-to-end, not just schema unit tests in isolation. | Must | Done | TEST-005 |
| PRD-0217 | The protocol module (`infra/protocol.py`) is decoupled from FastMCP specifics, so the message shapes could in principle be reused over a different transport. | Could | Done | architecture.md §2 |
| PRD-0218 | Every mandatory parameter from Appendix F's parameter table is represented as a field somewhere in the `game.json` schema, cross-checked explicitly. | Must | Done | requirements_traceability.md "Coverage check" |
| PRD-0219 | Protocol version negotiation failure (mismatched `schema_version` between peers) is a defined, tested failure mode, not undefined behavior. | Should | Done | PROTO-001 |
| PRD-0220 | The message protocol never embeds secrets (API keys, tokens, credentials) in any message payload. | Must | Done | NFR-004 |

## 13. Game State Machine & Turn Sequencing

| ID | Requirement | Priority | Status | Ref |
|---|---|---|---|---|
| PRD-0221 | Game phases are modeled as an explicit `GamePhase` enum, not implicit state scattered across booleans/flags. | Must | Done | FR-052 |
| PRD-0222 | Every legal phase transition is enumerated in a transition table matching `docs/protocol.md` §4 exactly. | Must | Done | FR-052 |
| PRD-0223 | Any illegal transition attempt raises a dedicated `IllegalTransitionError`, never silently ignored or coerced. | Must | Done | TEST-004 |
| PRD-0224 | `TECHNICAL_LOSS` is terminal — no transition out of it exists in the table. | Must | Done | TEST-004 |
| PRD-0225 | Every legal transition in the table has a corresponding positive-path test asserting it succeeds. | Must | Done | TEST-004 |
| PRD-0226 | Every illegal transition has a corresponding negative-path test asserting it raises. | Must | Done | TEST-004 |
| PRD-0227 | The state machine is a standalone, dependency-free module (`domain/state_machine.py`) usable and testable without any networking code running. | Must | Done | NFR-001 |
| PRD-0228 | Turn order (cop/thief alternation, or whatever ordering the spec mandates) is enforced by the state machine, not left to strategy code discipline. | Must | Done | FR-052 |
| PRD-0229 | The Orchestrator wires the state machine as the authoritative gate for every phase change in an actual running game (not just a standalone testable component). | Must | Done | architecture.md §5 |
| PRD-0230 | The state machine has no notion of "trust the other peer" — each peer runs its own independent instance and only advances on messages that pass validation. | Must | Done | FR-052 |
| PRD-0231 | A frozen/stuck main loop (no phase progress) is detectable by the Watchdog as distinct from a legitimately slow-but-alive opponent. | Must | Done | FR-054 |
| PRD-0232 | State-machine phase names in logs match the documented enum values exactly (no drift between docs and code). | Should | Done | protocol.md §4 |
| PRD-0233 | Turn sequencing survives the real two-OS-process e2e scenario with both sides' state machines reaching the identical terminal phase. | Must | Done | TEST-007 |
| PRD-0234 | The state machine diagram in `docs/architecture.md`/`docs/protocol.md` is a Mermaid diagram, not just prose, per the documentation deliverable requirement. | Should | Done | DOC-002 |
| PRD-0235 | A "start of game" initial phase and a well-defined set of terminal phases are both explicitly modeled (no ambiguous "null" state). | Must | Done | domain/state_machine.py |
| PRD-0236 | Every turn's phase sequence is captured in the exported game log for later replay verification. | Must | Done | FR-045 |
| PRD-0237 | Concurrent/overlapping turns (both sides trying to act "at once") cannot occur — the state machine's phase gating serializes the interaction. | Must | Done | FR-052 |
| PRD-0238 | State machine transitions are cheap, synchronous, in-process calls — no network I/O inside the state machine itself. | Must | Done | NFR-001 |

## 14. Reliability: Deadline Tracker & Watchdog

| ID | Requirement | Priority | Status | Ref |
|---|---|---|---|---|
| PRD-0239 | A Deadline Tracker enforces a per-call response timeout against the opponent (`response_timeout_sec`). | Must | Done | FR-004, FR-053 |
| PRD-0240 | The Deadline Tracker retries a timed-out call according to a configured policy before declaring the opponent unreachable. | Must | Done | FR-053 |
| PRD-0241 | A Watchdog independently monitors the main game loop for the local process freezing/hanging (`watchdog_timeout_sec`, default 60s). | Must | Done | FR-054 |
| PRD-0242 | The Watchdog triggers a clean shutdown (not a crash/hang) when it detects a frozen main loop. | Must | Done | FR-054 |
| PRD-0243 | Deadline Tracker and Watchdog are tested independently of each other (separate simulated failure scenarios). | Must | Done | tests/unit/test_watchdog.py |
| PRD-0244 | A simulated unresponsive peer correctly triggers the deadline-tracker technical-loss path in an integration test. | Must | Done | implementation_plan.md Part 9 |
| PRD-0245 | A simulated frozen main loop correctly triggers watchdog-initiated shutdown in a test. | Must | Done | implementation_plan.md Part 9 |
| PRD-0246 | Both reliability mechanisms are wired into the Orchestrator's Single Gateway, not bolted on separately per call site. | Must | Done | architecture.md §6/§7 |
| PRD-0247 | Cleanup on any failure path (deadline exceeded, watchdog fired, normal completion) goes through the same `finally`-block teardown (server task cancellation, GUI teardown). | Must | Done | NFR-003 |
| PRD-0248 | The four JSON deliverables are still written correctly even when a game ends via technical loss/timeout, not just on a clean finish. | Must | Done | final_audit.md §14 |
| PRD-0249 | Watchdog and Deadline Tracker timeouts are both independently configurable via `config/game.json`, not hardcoded constants. | Must | Done | config/game.json |
| PRD-0250 | A documented, known cosmetic issue exists (cancelling the ASGI server task logs a noisy but harmless traceback) rather than being hidden or silently worked around with a broad exception swallow. | Could | Done | final_audit.md §14 |
| PRD-0251 | The failure-mode table in `docs/architecture.md` §7 enumerates every reliability scenario handled (timeout, freeze, malformed input, oversized payload, etc.). | Should | Done | architecture.md §7 |
| PRD-0252 | Retry backoff behavior (`retry_backoff_sec`, `max_retries`) is shared config between the Gatekeeper and the Deadline Tracker's retry policy, avoiding duplicated constants. | Should | Done | config/game.json |
| PRD-0253 | No reliability mechanism (Watchdog, Deadline Tracker) can itself cause a false technical-loss for a peer that is, in fact, behaving correctly but simply slow within tolerance. | Must | Done | tests/unit/test_watchdog.py |

## 15. Rate Limiting & Gatekeeper

| ID | Requirement | Priority | Status | Ref |
|---|---|---|---|---|
| PRD-0254 | A Token Bucket algorithm governs the rate of outgoing/incoming calls (`requests_per_minute`, default 30). | Must | Done | FR-055 |
| PRD-0255 | The Token Bucket's burst-then-refill curve numerically matches the book's own documented figure. | Must | Done | implementation_plan.md Part 10 |
| PRD-0256 | A Quota Manager enforces a daily/session budget and rejects calls once exhausted. | Must | Done | FR-055 |
| PRD-0257 | A DOS Detector locks/blocks on an anomalous burst pattern distinct from normal gameplay traffic. | Must | Done | FR-055 |
| PRD-0258 | Concurrent in-flight request count is capped (`concurrent_requests`, default 2). | Must | Done | config/game.json |
| PRD-0259 | A bounded retry-queue depth (`queue_depth`, default 100) prevents unbounded memory growth under sustained overload. | Must | Done | config/game.json |
| PRD-0260 | The Gatekeeper pipeline (Token Bucket → Quota Manager → DOS Detector) is composed as a single guarded entry point, not scattered ad hoc checks. | Must | Done | infra/gatekeeper.py |
| PRD-0261 | Gmail send calls are Gatekeeper-guarded exactly like game-protocol calls — no separate ungoverned path to send email. | Must | Done | FR-080 |
| PRD-0262 | An integration test with a fake clock proves the Quota Manager blocks a send once the configured budget is exhausted. | Must | Done | implementation_plan.md Part 11 |
| PRD-0263 | Oversized-payload rejection (NFR-006) is enforced at both the Gatekeeper and the MCP server boundary as defense in depth. | Should | Done | tests/network/test_mcp_transport.py |
| PRD-0264 | Rate-limiter constants (`requests_per_minute`, `concurrent_requests`, `retry_backoff_sec`, `max_retries`, `queue_depth`) all live in `config/game.json → rate_limiter_gatekeeper`, not hardcoded. | Must | Done | config/game.json |
| PRD-0265 | The Gatekeeper module has a fully independent, mockable-clock unit test suite (no real `time.sleep` waits needed to exercise the refill logic). | Should | Done | tests/unit/test_gatekeeper.py |
| PRD-0266 | Rejected calls due to rate limiting produce a distinct, identifiable error/response rather than looking like a generic failure. | Should | Done | infra/gatekeeper.py |
| PRD-0267 | The Gatekeeper is reusable across both the game-protocol channel and the Gmail-reporting channel via a shared interface. | Should | Done | infra/gatekeeper.py |
| PRD-0268 | Rate-limiting behavior is exercised (not bypassed) even in the real two-OS-process e2e test, proving it doesn't just work in mocked unit tests. | Should | Done | tests/e2e/test_two_peer_local_game.py |
| PRD-0269 | The DOS Detector's anomaly threshold is config-driven and documented, not a magic number buried in code. | Should | Done | infra/gatekeeper.py |
| PRD-0270 | Gatekeeper rejections never crash the process — they're a normal, handled control-flow branch. | Must | Done | infra/gatekeeper.py |
| PRD-0271 | The rate-limiting design explicitly protects against both an aggressive opponent and a misbehaving local retry loop (bidirectional protection, not just inbound). | Should | Done | architecture.md §7 |

## 16. Strategy / AI Brain Architecture

| ID | Requirement | Priority | Status | Ref |
|---|---|---|---|---|
| PRD-0272 | A `BrainBase` abstract base class defines the contract every strategy implementation must satisfy. | Must | Done | FR-060 |
| PRD-0273 | Role-specific subclasses (`ThiefBrain`, `PoliceBrain`) narrow the contract per role without duplicating shared logic. | Must | Done | FR-060 |
| PRD-0274 | Strategy code receives a `BeliefView` (partial-observability-respecting) input, never the raw true `BoardState`. | Must | Done | FR-005, FR-060 |
| PRD-0275 | The brain interface's "decide a move" method always returns a value from the legal action space for the current board state. | Must | Done | implementation_plan.md Part 7 |
| PRD-0276 | A property-based fuzz test generates many random legal board states and asserts the default brain's output is always legal. | Should | Done | implementation_plan.md Part 7 |
| PRD-0277 | Strategy modules have zero direct network/transport dependencies — the Orchestrator calls the brain, not the other way around. | Must | Done | architecture.md §6 |
| PRD-0278 | The default brain requires no machine-learning model, training data, or GPU — it must run instantly, deterministically, offline. | Must | Done | README §4 |
| PRD-0279 | No reinforcement learning is used by default, matching the spec's framing of RL as optional, not mandatory. | Must | Done | requirements_analysis.md §4 |
| PRD-0280 | Strategy decisions are logged (which move was chosen and, ideally, why) to aid debugging and replay analysis. | Should | Partial | domain logging |
| PRD-0281 | The strategy interface is stable enough that a rival team's brain can be swapped in without any change to `orchestrator.py`, `domain/`, or `infra/`. | Must | Done | README §4 |
| PRD-0282 | Barrier-placement decisions (cop-only) are part of the same brain interface as movement decisions, not a bolted-on separate mechanism. | Must | Done | strategy/heuristic.py |
| PRD-0283 | The strategy layer's only allowed inputs are the agent's own position, its belief map, and static config — never the opponent's private state. | Must | Done | FR-005 |
| PRD-0284 | Strategy module tests run entirely without a display, network, or GUI dependency. | Must | Done | NFR-001 |
| PRD-0285 | The brain interface exposes a hook for optional free-text "hint"/banter output, separate from and never influencing the move decision. | Should | Done | FR-064, README §4 |
| PRD-0286 | A malformed or crashing custom brain implementation fails loudly and safely (caught, logged, converted to a technical loss) rather than corrupting shared process state. | Should | Partial | strategy/base.py |
| PRD-0287 | Strategy classes are pure decision functions with no persistent mutable global state between calls (aside from documented, intentional per-game history if any). | Should | Done | strategy/heuristic.py |
| PRD-0288 | The strategy architecture is documented in `docs/protocol.md` §6 with the exact method signatures a custom brain must implement. | Should | Done | protocol.md §6 |
| PRD-0289 | Strategy selection (which brain class runs) is resolved once at peer startup, not re-resolved mid-game. | Must | Done | peer_runtime.py |

## 17. Default Heuristic Brain

| ID | Requirement | Priority | Status | Ref |
|---|---|---|---|---|
| PRD-0290 | The default cop brain moves to minimize Manhattan distance to `argmax_s b(s)` (the believed most-likely thief cell). | Must | Done | README §4 |
| PRD-0291 | The default cop brain places a cornering barrier instead of moving when the believed thief cell is adjacent. | Should | Done | README §4 |
| PRD-0292 | The default thief brain moves to maximize the same Manhattan distance (pure evasion heuristic). | Must | Done | README §4 |
| PRD-0293 | The default heuristic is fully deterministic — the same belief state always produces the same move (no randomness). | Must | Done | strategy/heuristic.py |
| PRD-0294 | The default heuristic never requires network access, model downloads, or external services to run. | Must | Done | README §4 |
| PRD-0295 | The default heuristic is the out-of-the-box behavior with zero configuration required (works immediately after `uv sync`). | Must | Done | README §6 |
| PRD-0296 | The default heuristic's tie-breaking rule (multiple equally-good moves) is deterministic and documented, not arbitrary dict-ordering-dependent behavior. | Should | Done | strategy/heuristic.py |
| PRD-0297 | The default heuristic correctly handles the case where the belief map is still uniform/empty (start of game, no scent yet) without crashing. | Must | Done | tests/unit/test_strategy.py |
| PRD-0298 | The default heuristic respects the barrier cap — it never attempts a barrier placement once `max_barriers` is reached. | Must | Done | tests/unit/test_strategy.py |
| PRD-0299 | The default heuristic is fast enough to decide a move well within the per-turn timeout, with large headroom. | Must | Done | README §6 |
| PRD-0300 | The default heuristic's behavior is covered by unit tests asserting both the "chase" (cop) and "evade" (thief) directionality against known belief-map fixtures. | Must | Done | tests/unit/test_strategy.py |
| PRD-0301 | The default heuristic serves as the reference implementation new custom brains are expected to at least match in legality/robustness, per `docs/protocol.md` §6. | Should | Done | protocol.md §6 |

## 18. Pluggable Strategy System

| ID | Requirement | Priority | Status | Ref |
|---|---|---|---|---|
| PRD-0302 | A rival team can point their peer config at their own strategy class via `[strategy] → police_class`/`thief_class` in `config/<role>/game.toml`. | Must | Done | FR-060 |
| PRD-0303 | The pluggable class reference uses the `package.module:Class` string format, resolved dynamically at startup. | Must | Done | strategy/base.py::load_brain_class |
| PRD-0304 | The loader validates that the resolved class is actually a subclass of `BrainBase` before accepting it. | Must | Done | strategy/base.py |
| PRD-0305 | The loader rejects a non-`BrainBase` class with a clear error message, not a cryptic `AttributeError` at first use. | Must | Done | tests/unit/test_strategy.py |
| PRD-0306 | The loader rejects a malformed `module:Class` string (wrong format, unimportable module, missing class) with a clear, actionable error. | Must | Done | strategy/base.py |
| PRD-0307 | If `[strategy]` is left unset (commented out, the shipped default), the peer falls back to the shipped heuristic brain with zero extra config. | Must | Done | config/police/game.toml |
| PRD-0308 | Swapping in a custom brain requires no changes to `orchestrator.py`, `infra/`, or `domain/` — verified by the architecture's module-boundary design. | Must | Done | README §4 |
| PRD-0309 | A custom brain can, in principle, be an RL-trained model, an LLM-backed decision-maker, or any other approach, as long as it satisfies the `BrainBase` contract. | Should | Done | README §4 |
| PRD-0310 | The pluggable-loader test suite covers both the happy path (valid custom class resolves and runs) and multiple failure paths. | Must | Done | tests/unit/test_strategy.py |
| PRD-0311 | Custom-brain loading happens once at peer startup, with a clear startup-time failure if the class can't be resolved (never a silent fallback to default that masks a config typo). | Must | Done | peer_runtime.py |
| PRD-0312 | The pluggable strategy mechanism is documented with a worked example (exact config syntax) in `docs/protocol.md` §6. | Should | Done | protocol.md §6 |
| PRD-0313 | Pluggability is exercised by at least one test that supplies a genuinely custom (non-default) `BrainBase` subclass and confirms it's actually invoked, not silently ignored. | Must | Done | tests/unit/test_strategy.py |

## 19. Bonus: Reinforcement-Learning Brain

| ID | Requirement | Priority | Status | Ref |
|---|---|---|---|---|
| PRD-0314 | An optional `strategy/qlearning.py` brain may implement tabular or function-approximation RL over the belief-map state space. | Bonus | Not Started | BONUS-001 |
| PRD-0315 | If built, the RL brain must satisfy the same `BrainBase` contract as the heuristic brain (drop-in replaceable). | Bonus | Not Started | BONUS-001 |
| PRD-0316 | If built, the RL brain's training process must be reproducible and documented (seed, hyperparameters, training script). | Bonus | Not Started | — |
| PRD-0317 | If built, a trained model artifact must be small enough to commit to the repo or trivially regeneratable, not a multi-GB blob. | Bonus | Not Started | — |
| PRD-0318 | If built, the RL brain must still only ever consume the same `BeliefView` input as the heuristic brain — no special-cased access to true board state. | Bonus | Not Started | FR-005 |
| PRD-0319 | If built, the RL brain's decision latency must stay well within the per-turn timeout even during a real two-process game. | Bonus | Not Started | — |
| PRD-0320 | If built, an RL-vs-heuristic benchmark (win rate over N games) should be documented to demonstrate the RL brain adds value. | Bonus | Not Started | — |
| PRD-0321 | The RL brain is explicitly optional per the spec — its absence must never block core submission requirements. | Must | Done | requirements_analysis.md §4 |
| PRD-0322 | If built, RL training/inference dependencies (e.g. `numpy`, a small RL library) must be added to `pyproject.toml` only under an optional extras group, not bloating the default install. | Bonus | Not Started | — |
| PRD-0323 | If not built, this is explicitly documented as "Not Started" (not silently omitted) in `docs/STATUS.md`, `docs/requirements_traceability.md`, and `README.md`'s Known Limitations. | Must | Done | STATUS.md |
| PRD-0324 | If built, unit tests for the RL brain follow the same offline/no-I/O-dependency pattern as the rest of `strategy/`. | Bonus | Not Started | — |
| PRD-0325 | The decision to build (or not build) the RL brain is a product/scope decision, not silently deferred without the user's awareness. | Must | Done | — |

## 20. Bonus: LLM Trash-Talk / Banter

| ID | Requirement | Priority | Status | Ref |
|---|---|---|---|---|
| PRD-0326 | An optional `strategy/llm_bluff.py` module may generate free-text banter/trash-talk shown alongside a move, never used to decide the move itself. | Bonus | Not Started | FR-061 |
| PRD-0327 | The `[llm]` config section (`model`, `step_deadline_seconds`) and `[trash_talk]` config section (`provider`) already exist and default to `template` (zero tokens, offline). | Must | Done | A-005 |
| PRD-0328 | If built, banter generation must respect `hint_max_words` so output can't balloon into an unbounded wall of text. | Bonus | Not Started | FR-064 |
| PRD-0329 | If built, banter generation must have a hard `step_deadline_seconds` timeout so a slow/unreachable LLM provider can never stall the game loop. | Bonus | Not Started | FR-062 |
| PRD-0330 | If built, at minimum a `template` provider (canned phrases, zero cost, offline) must remain the default so the product never requires paid API credits out of the box. | Must | Done | A-005 |
| PRD-0331 | If built, an `ollama` provider option supports a fully local/offline LLM with no per-token cost. | Bonus | Not Started | — |
| PRD-0332 | If built, a `claude_api`/`claude_cli` provider option is available but never enabled by default, per the user's standing instruction to avoid consuming Anthropic API credits unless explicitly required. | Bonus | Not Started | A-005 |
| PRD-0333 | If built, `token_budget_per_series` (already present in config, default 200000) caps total LLM spend across a league series regardless of provider. | Should | Partial | config/game.json |
| PRD-0334 | If built, banter failures (LLM provider error/timeout) degrade gracefully to no-banter, never to a crashed turn or technical loss. | Must | Not Started | — |
| PRD-0335 | If built, banter content must never leak information the emitting agent shouldn't reveal (true position, unrevealed move) — a content-safety boundary distinct from the game-legality boundary. | Must | Not Started | — |
| PRD-0336 | If not built, this is explicitly documented as "Not Started" everywhere it's tracked (STATUS.md, traceability matrix, README), matching the honesty standard applied to the RL brain. | Must | Done | STATUS.md |
| PRD-0337 | If built, unit tests mock the LLM provider entirely — no real API calls in the automated test suite. | Bonus | Not Started | testing_strategy.md |
| PRD-0338 | If built, the banter feature is fully optional at the config level (`provider` can be left at `template` with zero behavior change to core gameplay). | Must | Done (config exists) | A-005 |
| PRD-0339 | If built, banter output is included in the live GUI / logs distinctly from move data, clearly labeled as flavor text. | Bonus | Not Started | — |
| PRD-0340 | The decision to leave LLM banter unimplemented in the current submission is a deliberate, documented cost/scope trade-off, not an oversight. | Must | Done | README §9 |

## 21. Configuration Management

| ID | Requirement | Priority | Status | Ref |
|---|---|---|---|---|
| PRD-0341 | A shared, byte-identical `config/game.json` is loaded and validated by both peers (`load_game_config`). | Must | Done | NFR-005 |
| PRD-0342 | A private, per-role `config/<role>/game.toml` is loaded and validated separately per peer (`load_peer_config`). | Must | Done | NFR-005 |
| PRD-0343 | `shared_config_hash` lets both peers cryptographically confirm they're using the exact same shared ruleset before playing. | Must | Done | NFR-008 |
| PRD-0344 | Config loading fails with a clear, explicit error message on a missing required field — never leaks a raw `KeyError` to the end user. | Must | Done | implementation_plan.md Part 3 |
| PRD-0345 | Loading the book's own transcribed example JSON/TOML round-trips cleanly into typed `GameConfig`/`PeerConfig` objects. | Must | Done | tests/unit/test_config.py |
| PRD-0346 | A hash mismatch between two copies of `game.json` is detected, not silently ignored, before a game starts. | Must | Done | implementation_plan.md Part 3 |
| PRD-0347 | All config values use `pathlib.Path` where they represent filesystem locations, never raw string path concatenation. | Must | Done | NFR-002 |
| PRD-0348 | Config validation rejects a barrier count inconsistent with `grid_size` (can't exceed total board cells) at load time. | Should | Done | A-009 |
| PRD-0349 | Config validation rejects out-of-bounds `cop_start`/`thief_start` coordinates for the configured `grid_size` at load time. | Must | Done | A-009 |
| PRD-0350 | Config supports overriding `[network] → my_port` / `opponent_url` independently per role, enabling both localhost multi-port and remote-tunnel setups from the same schema. | Must | Done | config/police/game.toml |
| PRD-0351 | `[email] → recipient`/`mode` config controls the Gmail reporting destination and safety mode (`draft` vs `send`) per peer. | Must | Done | FR-080 |
| PRD-0352 | `[tunnel] → provider`/`manual_public_url` config controls tunneling behavior per peer without code changes. | Must | Done | FR-006 |
| PRD-0353 | `[strategy] → police_class`/`thief_class` (optional) lets a peer point at a custom brain without touching any other config section. | Must | Done | FR-060 |
| PRD-0354 | `[llm]`/`[trash_talk]` sections exist with safe, zero-cost defaults even though the feature they configure isn't fully implemented yet. | Should | Done | A-005 |
| PRD-0355 | Peer identity fields (`group_name`, `group_id`, `sub_game_number`, `members`, `repos`) are structured, typed config, not free-text notes. | Must | Done | FR-088 |
| PRD-0356 | Config schema versions (`game.json` "1.2", peer `game.toml` "1.10") are tracked so future format changes are detectable. | Should | Done | config/game.json |
| PRD-0357 | No secrets (API keys, OAuth tokens) are ever stored in `config/game.json` or `config/<role>/game.toml` — those live in gitignored files (`credentials.json`, `token.json`). | Must | Done | NFR-004, .gitignore |
| PRD-0358 | Config loading has zero network I/O — purely reads local files, so it can be unit tested without any server running. | Must | Done | NFR-001 |
| PRD-0359 | Default config values, where sensible, match the exact numbers in the lecturer's own mandatory-parameter tables (grid size, scoring, pheromone, network/league). | Must | Done | A-001, A-002, A-004 |
| PRD-0360 | A single documented example config (in the repo, `config/`) is real, runnable configuration — not just a schema reference buried in docs. | Must | Done | README §5 |
| PRD-0361 | Config module (`config.py`) is fully covered by unit tests including both valid and multiple distinct invalid fixtures. | Must | Done | tests/unit/test_config.py |
| PRD-0362 | Changing any single mandatory parameter (e.g. `grid_size`) requires editing exactly one file (`config/game.json`), never a code change. | Must | Done | config.py |

## 22. CLI & Usability

| ID | Requirement | Priority | Status | Ref |
|---|---|---|---|---|
| PRD-0363 | `python -m police_thief --help` prints usable top-level usage text. | Must | Done | FR-002 |
| PRD-0364 | `python -m police_thief peer --role police|thief` starts a peer process for the given role. | Must | Done | FR-002 |
| PRD-0365 | `python -m police_thief peer --gui` optionally launches the live belief-heatmap view alongside the peer process. | Should | Done | FR-070 |
| PRD-0366 | `python -m police_thief replay --log <path>` runs the Replay Viewer against a produced log file. | Must | Done | FR-071 |
| PRD-0367 | Every subcommand has its own `--help` text (`peer --help`, `replay --help`). | Should | Done | final_audit.md "Exact commands used" |
| PRD-0368 | Invalid CLI arguments produce a clean, human-readable error, never a raw Python stack trace, unless a `--debug` flag is passed. | Must | Done | implementation_plan.md Part 12 |
| PRD-0369 | A scripted local CLI run reliably produces all four JSON deliverables in `logs/<game-id>/`. | Must | Done | implementation_plan.md Part 12 |
| PRD-0370 | The CLI exits with a distinct, correct process exit code on success vs. failure, suitable for scripting/CI. | Should | Partial | cli.py |
| PRD-0371 | The CLI never requires interactive input mid-run (fully scriptable/non-interactive once launched with its arguments). | Must | Done | cli.py |
| PRD-0372 | PowerShell demo scripts (`run_police.ps1`, `run_thief.ps1`, `run_demo.ps1`, `run_tests.ps1`) wrap the CLI for one-command demo/test runs on Windows. | Must | Done | TEST-007 |
| PRD-0373 | `run_demo.ps1` runs both peers as background jobs, waits for completion, and automatically runs the Replay Viewer on the resulting log. | Should | Done | README §6 |
| PRD-0374 | `run_tests.ps1` supports a fast default mode (skips the ~1-minute real-subprocess e2e test) and a `-Full` mode that includes it. | Should | Done | README §6 |
| PRD-0375 | Every command documented in `README.md` §6 has actually been run and verified during development, not just written speculatively. | Must | Done | final_audit.md §15 |
| PRD-0376 | The CLI's role selection (`--role police|thief`) is validated against the two known roles only, rejecting typos with a clear message. | Must | Done | cli.py |
| PRD-0377 | The CLI is the single entry point for all documented user-facing operations — no separate undocumented scripts are required for the core demo. | Must | Done | README §6 |

## 23. Live GUI / Belief Heatmap

| ID | Requirement | Priority | Status | Ref |
|---|---|---|---|---|
| PRD-0378 | A Tkinter-based live view renders the local peer's own belief-map heatmap in real time as the game progresses. | Must | Done | FR-070 |
| PRD-0379 | The heatmap is strictly "local-truth-only" — it shows only what that peer's own agent could actually know, never the opponent's true position. | Must | Done | FR-005, FR-070 |
| PRD-0380 | `render_grid` and `belief_to_color` are pure, independently unit-testable rendering-logic functions, separated from the Tkinter main loop. | Must | Done | tests/unit/test_live_view_render.py |
| PRD-0381 | The rendering-logic tests run headless (no display needed) in CI. | Must | Done | tests/unit/test_live_view_render.py |
| PRD-0382 | A turn banner (`turn_banner_*`) shows the current turn number / phase / last outcome in the live view. | Should | Done | gui/live_view.py |
| PRD-0383 | The live view is opt-in via `--gui`, never forced on for headless/CI/automated runs. | Must | Done | FR-070 |
| PRD-0384 | The live GUI updates without blocking or stalling the underlying game loop / network I/O. | Must | Done | peer_runtime.py |
| PRD-0385 | The live GUI window is cleanly destroyed as part of the peer's `finally`-block teardown on any exit path. | Must | Done | NFR-003 |
| PRD-0386 | The color mapping from belief intensity to visual color is a documented, deterministic formula (not an arbitrary/undocumented gradient). | Should | Done | gui/live_view.py |
| PRD-0387 | The agent's own current position and any placed barriers are visually distinguishable from belief-intensity cells in the same view. | Should | Partial | gui/live_view.py |
| PRD-0388 | A real widget smoke test has been manually performed (needs a real display, so it's not part of automated CI, but has been verified at least once). | Should | Done | requirements_traceability.md FR-070 |
| PRD-0389 | The live-view heatmap screenshot required for the submission checklist (Appendix C Table 6) has not yet been captured as an artifact, though the functionality works. | Must | Planned | final_audit.md §20 |
| PRD-0390 | The GUI module has no impact on headless test-suite runtime (its logic-only parts are covered; the Tkinter loop itself is excluded from CI). | Should | Done | testing_strategy.md |
| PRD-0391 | The live view degrades gracefully (or is simply skipped) on a machine with no display available, when `--gui` isn't passed. | Must | Done | cli.py |
| PRD-0392 | Live-view rendering never crashes the peer process on an edge-case belief state (all-zero, single-peak, fully saturated). | Should | Done | tests/unit/test_live_view_render.py |

## 24. Replay Viewer & Verification

| ID | Requirement | Priority | Status | Ref |
|---|---|---|---|---|
| PRD-0393 | `gui/replay_viewer.py` loads a produced game log (`load_log`) and replays it move by move. | Must | Done | FR-071 |
| PRD-0394 | `verify_step` independently re-derives and checks the commit hash for each individual step in the log. | Must | Done | FR-045, FR-071 |
| PRD-0395 | `replay`/`verify_log_file` runs the full log through verification and produces a single terminal `Verified OK` or `TAMPERED` banner. | Must | Done | FR-071 |
| PRD-0396 | A hand-crafted tampered-log fixture is correctly and reliably flagged `TAMPERED`. | Must | Done | tests/unit/test_replay_viewer.py |
| PRD-0397 | A genuine, untampered log produced by a real game is correctly flagged `Verified OK`. | Must | Done | tests/unit/test_replay_viewer.py, integration test |
| PRD-0398 | The Replay Viewer is runnable as a documented CLI subcommand (`python -m police_thief replay --log <path>`), not just an internal function. | Must | Done | FR-071 |
| PRD-0399 | Replay verification requires no network access — it works entirely offline against a saved log file. | Must | Done | domain package boundary |
| PRD-0400 | Replay verification is deterministic — running it twice on the same log always produces the same verdict. | Must | Done | gui/replay_viewer.py |
| PRD-0401 | The Replay Viewer's `Verified OK` screenshot required for the submission checklist hasn't yet been captured as an artifact, though the underlying function is fully tested. | Must | Planned | final_audit.md §20 |
| PRD-0402 | The Replay Viewer is exercised (not just unit tested in isolation) by the full integration test that plays a real two-orchestrator game and then verifies its own output log. | Must | Done | tests/integration/test_two_peer_game.py |
| PRD-0403 | Replay verification checks every committed field independently (state, move, intent, nonce), matching the granularity of the crypto module's own tamper tests. | Must | Done | tests/unit/test_replay_viewer.py |
| PRD-0404 | The Replay Viewer can be run by a third party (e.g. the lecturer) against a log file they didn't produce themselves, using only the documented CLI command. | Must | Done | README §6 |
| PRD-0405 | A malformed/corrupted (not just tampered-but-well-formed) log file produces a clear error from the Replay Viewer, not a crash. | Should | Partial | gui/replay_viewer.py |
| PRD-0406 | The Replay Viewer's pass/fail verdict is unambiguous in its printed output (no case where the result is unclear to a human reader). | Must | Done | gui/replay_viewer.py |
| PRD-0407 | Replay Viewer logic has no GUI/display dependency of its own (distinct from the live GUI module), so it runs in any environment including CI. | Must | Done | tests/unit/test_replay_viewer.py |

## 25. Logging & Observability

| ID | Requirement | Priority | Status | Ref |
|---|---|---|---|---|
| PRD-0408 | Structured logging is configured centrally (`logging_setup.py::configure_logging`), not ad hoc `print()` calls scattered through the code. | Must | Done | NFR-004 |
| PRD-0409 | A `RedactionFilter` strips or masks secret-looking values (credentials, tokens, nonces-before-reveal) from all log output. | Must | Done | NFR-004 |
| PRD-0410 | A negative test asserts log output never contains the literal substrings `credentials`, `token`, or a not-yet-revealed nonce. | Must | Done | tests/unit/test_logging_setup.py |
| PRD-0411 | Log verbosity is controllable (at minimum via config/CLI flags), so a debug run can get more detail without code changes. | Should | Done | logging_setup.py |
| PRD-0412 | `get_logger` provides a consistent, named-logger pattern used uniformly across `domain/`, `infra/`, `strategy/`, and `gui/`. | Should | Done | logging_setup.py |
| PRD-0413 | Log records include enough context (game ID, role, turn number) to reconstruct a timeline after the fact without cross-referencing multiple files. | Should | Done | orchestrator.py |
| PRD-0414 | Logging never blocks or measurably slows the real-time game loop (no synchronous remote log shipping in the default config). | Must | Done | logging_setup.py |
| PRD-0415 | Logging failures (e.g. disk full) degrade gracefully and never crash the game itself. | Should | Not Verified | — |
| PRD-0416 | Log files are written under the gitignored `logs/` directory, never accidentally committed. | Must | Done | .gitignore |
| PRD-0417 | The redaction filter is itself unit-tested with deliberately planted secret-like strings to confirm it actually catches them (not just a theoretical guarantee). | Must | Done | tests/unit/test_logging_setup.py |
| PRD-0418 | Logging configuration is itself part of the standard config-loading path, not a separate manual setup step. | Should | Done | logging_setup.py |
| PRD-0419 | Every module that could reasonably need a log line (networking, crypto failures, state transitions, rate-limit rejections) actually has one at an appropriate level. | Should | Done | — |
| PRD-0420 | Log levels (DEBUG/INFO/WARNING/ERROR) are used meaningfully and consistently, not everything dumped at one level. | Should | Done | logging_setup.py |
| PRD-0421 | The one known noisy `ERROR`-level traceback (cancelled ASGI lifespan on shutdown) is documented as cosmetic/expected rather than left unexplained. | Could | Done | final_audit.md §14 |
| PRD-0422 | Logging setup has no external network dependency of its own (no shipping logs to a remote service by default). | Must | Done | logging_setup.py |

## 26. Reporting & Deliverables (JSON files)

| ID | Requirement | Priority | Status | Ref |
|---|---|---|---|---|
| PRD-0423 | Every completed game writes exactly four JSON deliverable files: `declaration_<game_id>.json`, `config_<tag>.json`, `log_<tag>.json`, `result_<game_id>.json`. | Must | Done | FR-082 |
| PRD-0424 | `build_declaration` produces the Step-0 hardware/identity declaration JSON per Appendix A. | Must | Done | FR-081, NFR-007 |
| PRD-0425 | `build_result` produces the final outcome/score/positions/move-count summary JSON. | Must | Done | FR-081, FR-082 |
| PRD-0426 | The config deliverable is a faithful copy/snapshot of the actual `game.json` used for that specific game (not a generic template). | Must | Done | FR-082 |
| PRD-0427 | The log deliverable contains the full committed/revealed move history sufficient for independent replay verification. | Must | Done | FR-045, FR-082 |
| PRD-0428 | All four deliverables are written to a per-game directory (`logs/<game-id>/<role>/`), never overwriting a previous game's files. | Must | Done | README §6 |
| PRD-0429 | Deliverable JSON schemas are stable and documented, so an automated grading script could parse them without ambiguity. | Must | Done | protocol.md §5 |
| PRD-0430 | The declaration JSON's `commit_hash` field currently holds the placeholder `"unknown"` because a running process can't know its own containing commit's hash; this is documented, not silently wrong. | Must | Partial | final_audit.md §20 |
| PRD-0431 | Every deliverable file is schema-tested (unit test asserts the produced dict has every mandatory key). | Must | Done | tests/unit/test_reporting.py |
| PRD-0432 | Deliverables are written correctly regardless of which terminal outcome the game reached (capture, survival, tie, technical loss). | Must | Done | final_audit.md §14 |
| PRD-0433 | Deliverable file names encode the game ID unambiguously, so multiple games' outputs never collide on disk. | Must | Done | infra/reporting.py |
| PRD-0434 | The reporting module has no direct network dependency of its own — it only writes local files (Gmail sending is a separate, distinct module). | Must | Done | architecture.md §1 |
| PRD-0435 | Reporting logic is fully covered by unit tests independent of any real game having been played (fixture-driven). | Must | Done | tests/unit/test_reporting.py |
| PRD-0436 | The four-deliverable requirement is called out explicitly as "mandatory" in the README and cross-linked to the exact spec appendix that requires it. | Must | Done | README §1 |
| PRD-0437 | Deliverable JSON is human-readable (indented, not minified) to ease manual inspection during grading. | Should | Done | infra/reporting.py |
| PRD-0438 | No deliverable file ever contains a secret (credentials, tokens, unrevealed nonces). | Must | Done | NFR-004 |
| PRD-0439 | Both peers independently produce their own copy of all four deliverables — a grader can cross-check the two sides agree. | Must | Done | README §6, TEST-007 |
| PRD-0440 | The reporting module's output has been manually inspected at least once against a real produced game, not just asserted by unit tests against synthetic fixtures. | Should | Done | final_audit.md §15 |

## 27. Gmail Integration

| ID | Requirement | Priority | Status | Ref |
|---|---|---|---|---|
| PRD-0441 | `infra/gmail_report.py` implements a send-only OAuth2 flow per Appendix A — never requests read/inbox-modify scopes. | Must | Done | FR-080 |
| PRD-0442 | `report_match_result` sends (or drafts) an end-of-game report email built from `infra/reporting.py::build_result`. | Must | Done | FR-081 |
| PRD-0443 | Every send attempt is Gatekeeper-guarded, so email sending can never bypass the rate-limiting/quota system. | Must | Done | FR-080 |
| PRD-0444 | A `mode = "draft"` config option (the safe development default) creates a Gmail draft instead of actually sending. | Must | Done | config/police/game.toml |
| PRD-0445 | A `mode = "send"` config option performs a real send, intended only for an actual league match. | Must | Done | config/police/game.toml |
| PRD-0446 | `credentials.json`/`token.json` OAuth material is never committed to the repo (gitignored explicitly). | Must | Done | .gitignore, NFR-004 |
| PRD-0447 | The send path is mocked in all automated CI tests — no real Gmail API call happens during `pytest`. | Must | Done | testing_strategy.md |
| PRD-0448 | An integration test with a fake clock confirms the Gatekeeper correctly blocks a Gmail send once quota is exhausted. | Must | Done | implementation_plan.md Part 11 |
| PRD-0449 | A real OAuth2 flow against a live Google account, and a real sent (non-draft) report email, have not yet been performed/confirmed in this project's development history. | Must | Planned | final_audit.md §20 |
| PRD-0450 | The recipient address for match reports is config-driven (`[email] → recipient`), not hardcoded. | Must | Done | config/police/game.toml |
| PRD-0451 | Gmail send failures (network error, auth error, quota exceeded) degrade gracefully — the game result is never lost even if the email fails. | Must | Done | infra/gmail_report.py |
| PRD-0452 | The Gmail module's report content matches the same schema as the local JSON `result` deliverable, so there's one source of truth for match-result content. | Should | Done | infra/reporting.py |
| PRD-0453 | OAuth token refresh is handled without requiring a fresh interactive login on every single run. | Should | Done | infra/gmail_report.py |
| PRD-0454 | The `googleapiclient`/`google.oauth2`/`google.auth` third-party dependencies are scoped with a documented mypy override (no upstream type stubs), not silently ignored project-wide. | Should | Done | pyproject.toml |
| PRD-0455 | The one untyped Google API call site has an inline, justified `# type: ignore` rather than a blanket module-level suppression. | Should | Done | infra/gmail_report.py |

## 28. League / Multi-Game Play

| ID | Requirement | Priority | Status | Ref |
|---|---|---|---|---|
| PRD-0456 | A league series is defined as `num_games` (default 6) games, per Table 18 of the spec. | Must | Done | FR-084 |
| PRD-0457 | `min_games_to_pass` (default 2) is the minimum number of completed games required for a team to count as having participated. | Must | Done | FR-084 |
| PRD-0458 | `max_games_per_team` (default 10) caps how many games a single team can play across the league. | Must | Done | FR-084 |
| PRD-0459 | `diversity_reward` (default 10) exists to reward playing a wider variety of rival teams rather than repeatedly farming one weak opponent. | Should | Partial | FR-084 |
| PRD-0460 | A mutual daily-log / games-played-count audit between rival teams is not yet wired — this only matters once actually running a real multi-game series. | Should | Planned | FR-083 |
| PRD-0461 | Each individual game within a series produces its own complete set of four JSON deliverables, independently of series-level aggregation. | Must | Done | FR-082 |
| PRD-0462 | League-level constants are all sourced from `config/game.json → network_and_league`, matching the spec's Table 18 numbers exactly. | Must | Done | A-002, A-004 |
| PRD-0463 | A round-trip config test confirms the loaded `NetworkAndLeagueConfig` matches the book's own example numbers exactly. | Must | Done | tests/unit/test_config.py |
| PRD-0464 | Playing multiple games in a series against the same opponent doesn't require restarting the whole peer process from scratch (or, if it does, that's documented as the current operating model). | Could | Partial | — |
| PRD-0465 | Aggregate series scoring (summing per-game scores across a 6-game series) is at least representable, even if the audit/reporting automation for it isn't fully built. | Should | Planned | FR-083 |
| PRD-0466 | Two internal contradictions in the lecturer's spec regarding "games per rival" counts are documented with the resolution chosen. | Must | Done | assumptions.md |
| PRD-0467 | `sub_game_number` in peer identity config lets a team distinguish which game-within-a-series a given run corresponds to. | Should | Done | config/police/game.toml |
| PRD-0468 | The league/multi-game feature set is explicitly scoped as "not exercised end-to-end against a real rival team" in this development environment, since no real rival was available. | Must | Done | README §9 |
| PRD-0469 | `token_budget_per_series` bounds total LLM token spend across an entire 6-game series once/if the LLM banter feature is built. | Should | Done (config exists) | A-005 |
| PRD-0470 | League-mode config values are validated for internal consistency (`min_games_to_pass <= num_games <= max_games_per_team`) at load time. | Should | Done | A-002 |

---

*Continued in the next sections (29–37) covering tunneling/remote play, testing strategy,
documentation, non-functional requirements, error handling, and submission packaging.*
