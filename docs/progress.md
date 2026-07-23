# Progress Log

## 2026-07-23 — Phase 1: Requirements analysis & planning

**Files changed**: `docs/requirements_analysis.md`, `docs/architecture.md`, `docs/protocol.md`,
`docs/implementation_plan.md`, `docs/testing_strategy.md`, `docs/assumptions.md`,
`docs/requirements_traceability.md`, `docs/progress.md`, `.gitignore`, initial git repo + push to
`AliTrabeh/cop-thief-p2p`.

**Requirements completed**: none implemented yet — full requirements analysis (FR-001..088,
NFR-001..008, PROTO-001..004, TEST-001..007, DOC-001..005) extracted from the complete 143-page
spec and documented with source citations.

**Tests executed**: none yet (no implementation code exists).

**Test results**: N/A.

**Remaining issues**:
- Full PDF read in two passes: chapters 1–9.4 (printed pages 1–117) read directly; appendices
  D–F (printed pages 117–143, incl. the mandatory parameters table) read via a background
  extraction agent — content cross-verified consistent at the page-117 boundary.
- Two internal spec ambiguities resolved and documented in `docs/assumptions.md`
  (A-001 scoring-table reconciliation, A-002 games-per-rival reconciliation).
- Two-repo submission split (cop/thief) not yet done — tracked as A-008, deferred to Part 18.
- `main.py` (PyCharm placeholder) still present; will be removed in Part 1 once `src/police_thief`
  CLI entry point exists.

**Next part**: Part 1 — repository & dev-tool setup (`uv`-managed `pyproject.toml`, `src/` layout,
ruff/mypy/pytest wiring, package skeleton).

## 2026-07-23 — Part 1: Repository and dev-tool setup

**Files changed**: `pyproject.toml` (uv-managed, fastmcp/pydantic/Gmail deps, ruff/mypy/pytest
config), `uv.lock`, `src/police_thief/{__init__,__main__,cli}.py`,
`src/police_thief/{domain,strategy,infra,gui}/__init__.py`; removed `main.py`.

**Requirements completed**: scaffolding only (no FR/NFR yet — groundwork for NFR-002/NFR-005).

**Tests executed**: `uv run python -m police_thief --help` / `peer --help` (manual, both correct);
`uv run ruff format .` (2 files reformatted, clean after); `uv run ruff check .` (all checks
passed); `uv run mypy .` (no issues, 7 source files); `uv run pytest --collect-only` (0 tests
collected — expected, exit 5, no test files exist yet).

**Test results**: all green / as expected for a scaffold-only part.

**Remaining issues**: none blocking.

**Next part**: Part 2 — core domain models + board/game rules.

## 2026-07-24 — Part 2: Core domain models + board/game rules

**Files changed**: `src/police_thief/domain/models.py` (Coordinate, Role, Direction, full
`GameConfig` pydantic model tree mirroring `config/game.json`), `src/police_thief/domain/board.py`
(`BoardState`, movement/barrier legality, capture/win/stranded detection),
`src/police_thief/domain/scoring.py` (score/technical_loss_score), `tests/unit/conftest.py`,
`tests/unit/test_board.py`, `tests/unit/test_scoring.py`. Two new documented assumptions added:
A-013 (thief-stranded interpretation) and A-014 (technical-loss opponent scoring).

**Requirements completed**: FR-010..021 (board/movement/barriers/capture/scoring), NFR-005 (no
hardcoded constants — everything flows from `GameConfig`), NFR-001 (domain package has zero I/O
imports), A-003/A-009/A-010/A-013/A-014 resolved in code.

**Tests executed**: `uv run pytest tests/unit -v` (25 tests: board legality/bounds/barriers/
capture/survival/thief-stranded/config-validation, scoring for capture/survival/technical-loss);
`uv run ruff format .` + `uv run ruff check .` (clean); `uv run mypy src` (no issues, 10 source
files — mypy is now scoped to `src/`, not `tests/`, since strict untyped-def checking on test
functions isn't a useful signal; see docs/testing_strategy.md).

**Test results**: 25/25 passed.

**Remaining issues**: none blocking. `domain/scent.py` (Part 5), `domain/crypto.py` (Part 4), and
`domain/state_machine.py` (Part 6) are still unimplemented — `GameConfig`/`BoardState` are ready for
them to build on.

**Next part**: Part 3 (config file loader) folded into upcoming parts as needed; proceeding to
Part 4 — Commit-Reveal cryptographic module — next, since it has no dependency on the config-file
I/O layer beyond the already-complete `GameConfig` shape.

## 2026-07-24 — Part 4: Commit-Reveal cryptographic module

**Files changed**: `src/police_thief/domain/crypto.py` (`commit`/`verify`/`generate_nonce`/
`hash_state`, canonical-JSON payload), `tests/unit/test_crypto.py`.

**Requirements completed**: FR-040, FR-041 fully (Tested); FR-042/FR-043 crypto primitives done,
end-to-end message-sequencing and DQ-wiring deferred to the Orchestrator (Part 9).

**Tests executed**: `uv run pytest tests/unit/test_crypto.py -v` (9 tests: round-trip, tamper
detection on each of state/move/intent/nonce independently, nonce freshness + 1000-sample
uniqueness smoke test, canonical-JSON byte-identical construction); `ruff format`/`ruff check`
clean; `mypy src` clean (11 source files).

**Test results**: 9/9 passed.

**Remaining issues**: none blocking.

**Next part**: Part 6 — game state machine (`domain/state_machine.py`).

## 2026-07-24 — Part 6: Game state machine

**Files changed**: `src/police_thief/domain/state_machine.py` (`GamePhaseMachine`, exact transition
table from docs/protocol.md §4), `tests/unit/test_state_machine.py`.

**Requirements completed**: FR-052 (state-machine core; orchestrator wiring still pending Part 9).

**Tests executed**: `uv run pytest tests/unit -q` (45 tests total now, all passing); `ruff format`/
`ruff check` clean; `mypy src` clean (12 source files).

**Test results**: 45/45 passed (11 new for the state machine: happy-path cycle, TECHNICAL_LOSS
reachable from 3 states, TECHNICAL_LOSS terminal against every possible target, 5 parametrized
illegal-transition-rejected-and-state-unchanged cases).

**Remaining issues**: none blocking.

**Next part**: Part 5 — scent/pheromone belief-map engine (`domain/scent.py`).

## 2026-07-24 — Part 5: Scent/pheromone belief-map engine

**Files changed**: `src/police_thief/domain/scent.py` (`ScentField` emission/decay,
`belief_map`/`most_likely_position`), `tests/unit/test_scent.py`. New assumption A-015 documenting
that the exact spatial falloff shape is an implementation choice (only center intensity, decay
rate, and field size are mandatory per Appendix F Table 16).

**Requirements completed**: FR-030 (Tested), FR-031 (Implemented — no mid-game mutation path for
pheromone params exists at all, which is the strongest way to guarantee "fixed before game start"),
FR-032 (belief map Tested; the heuristic brain that consumes it is Part 7).

**Tests executed**: `uv run pytest tests/unit -q` (55 tests total); new scent tests include an
exact numeric match of the decay formula, a reproduction of the book's own Figure 5 half-peak-at-
turn-7 curve, re-emission steady-state, belief-map normalization (sums to 1), and argmax tracking
the scent source. `ruff format`/`ruff check` clean; `mypy src` clean (13 source files).

**Test results**: 55/55 passed.

**Remaining issues**: none blocking.

**Next part**: Part 7 — strategy modules (`strategy/base.py`, `strategy/heuristic.py`).

## 2026-07-24 — Part 7: Strategy modules

**Files changed**: `src/police_thief/strategy/base.py` (`BrainBase`/`ThiefBrain`/`PoliceBrain`,
`BeliefView`, `build_belief_view`, `MoveAction`/`BarrierAction`), `src/police_thief/strategy/
heuristic.py` (default Manhattan+belief-argmax brains for both roles, cop-only barrier-cornering
`_decide_move` override), `tests/unit/test_strategy.py`. New assumption A-016 documenting the
`_decide_move` cop-vs-both-roles ambiguity and the decision to make it cop-only in the default
strategy (while leaving the hook available to any brain).

**Requirements completed**: FR-060 (Tested — pluggable brain interface + default heuristic),
FR-064 (Implemented via `WorldConfig.hint_max_words`, already validated). FR-061/062/063 (LLM
bluff-only text channel) deferred to a later part alongside FastMCP infra, since they need the
`[trash_talk]`/`[llm]` config sections wired to a real provider.

**Tests executed**: `uv run pytest tests/unit -q` (63 tests total); new strategy tests cover:
legal-action guarantee for both brains, thief evasion / cop pursuit direction correctness, cop
barrier-cornering when the believed thief cell is adjacent, determinism given a fixed view, and
that a thief brain fed a decoy scent trail cannot distinguish it from the real cop (the local-truth
boundary holds for strategies, not just the GUI). `ruff format`/`ruff check` clean; `mypy src`
clean (15 source files).

**Test results**: 63/63 passed.

**Remaining issues**: none blocking. Pluggable-class loading from a `package.module:Class` string
(the config-driven half of FR-060) is deferred to the config-loader work alongside FastMCP infra.

**Next part**: Part 8 — FastMCP P2P transport + message protocol.

## 2026-07-24 — Part 8: FastMCP P2P transport + message protocol

**Files changed**: `src/police_thief/infra/protocol.py` (`MessageType`, `RejectReason`,
`ProtocolMessage`, `ProtocolResponse`), `src/police_thief/infra/mcp_server.py` (`build_server`,
`SequenceTracker` for duplicate/stale detection, oversized-payload guard), `src/police_thief/infra/
mcp_client.py` (`MCPPeerClient` with timeout + bounded retry — the Deadline Tracker), `tests/
network/test_mcp_transport.py`.

**Requirements completed**: FR-050 (Tested), FR-051 schema/sequencing half (Implemented; signature
verification wiring is Part 9, once real commit/reveal data flows through), NFR-006 (Tested —
oversized payloads rejected before reaching any handler), PROTO-001..004 (Tested).

**Tests executed**: `uv run pytest tests/network tests/unit -q` (93 tests total). Networking tests
use FastMCP's real client/server stack over its in-process transport (a genuine MCP protocol round
trip — real serialization, tool dispatch, and error propagation — without needing an open socket in
CI); cover: successful round trip, handler rejection returned (not raised) to the caller, duplicate
turn rejected idempotently, stale turn rejected, malformed payload doesn't crash the server,
oversized payload rejected, and an unreachable peer raises `PeerUnreachableError` after retries
exhaust. `ruff format`/`ruff check` clean; `mypy src` clean (20 source files).

**Test results**: 93/93 passed.

**Remaining issues**: signature/commit verification isn't wired into `mcp_server.py`'s handler yet
— that's the Orchestrator's job (Part 9), since the networking layer must not contain game rules
(architecture.md §3). A true two-OS-process HTTP round trip (vs. today's in-process transport) is
exercised in the Part 16 end-to-end demo, not unit/network tests.

**Next part**: Part 9 — Orchestrator, reliability patterns (Watchdog/Deadline Tracker wiring).

## 2026-07-24 — Part 10 (Gatekeeper) done early, out of order

**Files changed**: `src/police_thief/infra/gatekeeper.py` (`TokenBucket`, `QuotaManager`,
`DOSDetector`, `Gatekeeper` 3-stage pipeline), `tests/unit/test_gatekeeper.py`.

**Requirements completed**: FR-055 (Tested), NFR-006 Gatekeeper half (Implemented; the MCP-endpoint
half of NFR-006 lands with Part 8).

**Why out of order**: Gatekeeper has no dependency on FastMCP/networking and is fully deterministic
given an injectable clock, so it was cheap to finish now rather than block on Part 8.

**Tests executed**: `uv run pytest tests/unit -q` (86 tests total); new tests use a `FakeClock` to
deterministically test token-bucket drain/refill/capacity-cap, quota-window reset, DOS-detector
burst-lock (and that it doesn't self-heal without `reset()`), and the full 3-stage pipeline's
verdicts. `ruff format`/`ruff check` clean; `mypy src` clean (17 source files).

**Test results**: 86/86 passed.

**Remaining issues**: none blocking.

**Next part**: Part 8 — FastMCP P2P transport + message protocol.

## 2026-07-24 — Part 3 (deferred config loader) + strategy class loader

**Files changed**: `src/police_thief/config.py` (`load_game_config`, `shared_config_hash`,
`load_peer_config`, `PeerConfig` model tree mirroring `config/<role>/game.toml`),
`src/police_thief/strategy/base.py` (`load_brain_class` — resolves `package.module:Class` config
strings into `BrainBase` subclasses), `tests/unit/test_config.py`, additions to
`tests/unit/test_strategy.py`.

**Requirements completed**: NFR-005 (Tested — config-driven, no hardcoded constants), NFR-008
(Tested — shared-config hash is whitespace-invariant but change-sensitive), FR-060's pluggable
loading half (Tested).

**Tests executed**: `uv run pytest tests/unit -q` (77 tests total); new config tests cover
round-tripping the book's own JSON/TOML examples, missing-file/invalid-JSON/invalid-TOML/schema-
violation error paths (all raising `ConfigError` with a clear message, never a bare
`KeyError`/`FileNotFoundError`), and hash equality/inequality under whitespace vs. real changes;
new strategy-loader tests cover valid spec resolution and three distinct rejection paths
(malformed spec, non-`BrainBase` class, unknown attribute). `ruff format`/`ruff check` clean;
`mypy src` clean (16 source files).

**Test results**: 77/77 passed.

**Remaining issues**: none blocking. `config.py` doesn't yet enforce NFR-008's *cross-peer*
byteidentical check (that requires two peers to exchange hashes over FastMCP, Part 8/9) — today it
only proves the hash function itself is well-behaved.

**Next part**: Part 8 — FastMCP P2P transport + message protocol.
