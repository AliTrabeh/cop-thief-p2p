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

## 2026-07-24 — Part 9: Orchestrator + Watchdog

**Files changed**: `src/police_thief/orchestrator.py` (`Orchestrator`, `LogEntry`, own-turn commit/
reveal/apply cycle, incoming COMMIT/REVEAL handling, technical-loss detection), `src/police_thief/
infra/watchdog.py` (`Watchdog`, injectable-clock heartbeat/staleness check), `tests/unit/
test_watchdog.py`, `tests/unit/test_orchestrator.py`, `tests/integration/test_two_peer_game.py`
(two independent `Orchestrator` instances — separate `BoardState` mirrors, no shared memory —
playing a complete game over the real Part-8 FastMCP transport). Moved `tests/unit/conftest.py` to
`tests/conftest.py` so integration tests can reuse it (with a small local duplicate in the
integration test file itself, since `tests/` isn't an importable package under pytest's default
import mode). Added assumption A-017 (per-turn state-machine mapping + turn order: cop moves
first, strict alternation, `VERIFYING` means "opponent confirmed immediate legality" not full
crypto proof, which is deferred to end-of-game per §5.4).

**Requirements completed**: FR-052 (Tested, orchestrator-wired), FR-053 (Tested — Deadline Tracker
is the already-built `MCPPeerClient` retry/timeout policy), FR-054 (Tested), FR-042/FR-043
end-to-end (Tested via a real two-peer game, not just the crypto primitives in isolation), FR-016
(Implemented — barrier placements are always revealed, never silent).

**Bug found and fixed during integration testing**: `infra/mcp_server.py`'s `SequenceTracker`
originally deduplicated by `turn_number` alone, which incorrectly flagged a turn's REVEAL message
as a "duplicate" of that same turn's earlier COMMIT message (both legitimately share one
`turn_number`). Fixed by keying dedup/staleness on `(message_type, turn_number)` instead. This is
exactly the kind of bug the working instructions ask integration tests to catch, and it did.

**Tests executed**: `uv run pytest -q` (109 tests total, whole suite). New tests: 5 Watchdog
tests (alive/stale/shutdown/on-timeout-once/stays-shutdown, all with a `FakeClock`), 9 Orchestrator
unit tests (commit/reveal/apply cycle, technical loss on own-action illegality and on opponent
rejection, incoming COMMIT doesn't mutate the board, incoming REVEAL applies + updates belief
scent, illegal/malformed incoming REVEAL handled distinctly, turn-number advances correctly over 3
cycles), 2 integration tests (a full local game reaching a definitive outcome with both sides'
independent board mirrors agreeing exactly; a short-fused capture scenario detected symmetrically
by both sides). `ruff format`/`ruff check` clean; `mypy src` clean (22 source files).

**Test results**: 109/109 passed.

**Remaining issues**: `FINAL_REVEAL`/end-of-game mutual audit (nonce disclosure + full
commit/reveal cryptographic re-verification) is not yet wired into the Orchestrator — that's the
Replay Viewer's job (Part 13) and will reuse `domain/crypto.py::verify` directly against the
completed `own_log`/`opponent_log`. A true two-OS-process run (vs. today's in-process FastMCP
transport) is still Part 16's job via the CLI.

**Next part**: Part 11 — CLI wiring (peer/replay subcommands actually running games), then Part 13
GUI/Replay Viewer, then Part 12 Gmail reporting.

## 2026-07-24 — Part 13 (Replay Viewer half) + FINAL_REVEAL wiring

**Files changed**: `src/police_thief/gui/replay_viewer.py` (`verify_step`/`replay`/`load_log`/
`verify_log_file`, matching the book's own §7.5 reference code), `src/police_thief/orchestrator.py`
(`produce_final_reveal`, `_receive_final_reveal`, `export_log` — the end-of-game mutual audit,
FR-045), `tests/unit/test_replay_viewer.py`, four new tests appended to `tests/integration/
test_two_peer_game.py`.

**Requirements completed**: FR-045 (Tested — full mutual audit, not just the crypto primitive),
FR-071 (Tested).

**Tests executed**: `uv run pytest -q` (121 tests total, whole suite). New: 10 replay-viewer unit
tests (clean/tampered/missing-nonce verify_step, replay stopping at first tamper, load_log error
paths, verify_log_file round-trip); the integration suite now runs a complete two-peer game through
to FINAL_REVEAL, exports both sides' logs, confirms they're byte-identical, and confirms `replay()`
reports `Verified OK` on the real log and `TAMPERED` once a single field is corrupted afterward.
This is the first fully closed loop from strategy decision through cryptographic audit. `ruff
format`/`ruff check` clean; `mypy src` clean (23 source files).

**Test results**: 121/121 passed.

**Remaining issues**: the Replay Viewer's GUI presentation (Verified OK/TAMPERED banner, screenshot
deliverable) is still pending — today it's a pure verification function with no display; `gui/
live_view.py` (the live belief-heatmap GUI) hasn't been started; CLI `peer`/`replay` subcommands
still raise `NotImplementedError`.

**Next part**: CLI wiring for `replay` (straightforward, wraps `verify_log_file`), then `peer`
(wires config loading + Orchestrator + FastMCP transport into a real runnable process), then the
Tkinter live GUI, then Gmail reporting.

## 2026-07-24 — Reporting deliverables, Gmail automation, structured logging

**Files changed**: `src/police_thief/infra/reporting.py` (`build_declaration`/
`build_config_snapshot`/`build_result`/`write_match_deliverables` — the four mandatory per-match
JSON files, Appendix F Table 20), `src/police_thief/infra/gmail_report.py` (OAuth2 send-only Gmail
flow, Gatekeeper-guarded, `draft`/`send` mode split so no test or default demo run ever touches a
real mailbox), `src/police_thief/logging_setup.py` (structured logging + secrets/nonce redaction
filter), `tests/unit/test_reporting.py`, `tests/unit/test_gmail_report.py`, `tests/unit/
test_logging_setup.py`. Also added `Orchestrator.technical_loss_role` (which side's action caused
a disqualification) and `reject_own_commit`, needed by `build_result` to score technical losses
correctly per assumptions.md A-014.

**Requirements completed**: FR-080, FR-081, FR-082 (all Tested), NFR-004 (Tested).

**Tests executed**: `uv run pytest -q` (135 tests total, whole suite). New: 3 reporting tests
(capture/technical-loss result JSON shape, all-four-files-written-and-valid-JSON), 5 Gmail tests
(MIME encoding, a fake-service send round trip, draft mode never calling a service, send mode
using an injected service, send mode correctly blocked once the Gatekeeper's token bucket is
drained), 5 logging tests (credentials/token filename redaction, nonce-in-JSON redaction,
unrelated messages untouched, logger namespacing), plus 2 new orchestrator tests for
`technical_loss_role` attribution and `reject_own_commit`. Added a `[[tool.mypy.overrides]]` for
the untyped `googleapiclient`/`google.oauth2`/`google.auth` packages (no py.typed marker
upstream). `ruff format`/`ruff check` clean; `mypy src` clean (26 source files).

**Test results**: 135/135 passed.

**Remaining issues**: FR-083 (mutual daily-log audit / games-played-count verification) is a
league-level, multi-game-series concern not yet wired — it depends on Part 16's actual multi-game
CLI loop, which doesn't exist yet. CLI `peer`/`replay` subcommands still raise
`NotImplementedError`; `gui/live_view.py` hasn't been started.

**Next part**: CLI wiring (`replay` first, then `peer` via a new `peer_runtime.py` module tying
config + Orchestrator + FastMCP + reporting together), then the Tkinter live GUI, then demo
scripts and documentation.

## 2026-07-24 — Part 16: CLI wiring, peer runtime, real two-process demo, e2e test

**Files changed**: `src/police_thief/cli.py` (`peer`/`replay` subcommands fully wired, no more
`NotImplementedError`), `src/police_thief/peer_runtime.py` (new — loads config, resolves the
strategy brain, runs the FastMCP HTTP server, drives the turn loop via `board.moves_made % 2`
parity polling per assumptions.md A-017, writes deliverables + Gmail report at game end),
`src/police_thief/infra/mcp_client.py` (`MCPPeerClient.wait_until_reachable` — a ping-based
handshake wait), `config/game.json` + `config/police/game.toml` + `config/thief/game.toml` (real
config files, not just fixtures), `tests/e2e/test_two_peer_local_game.py` (spawns two real OS
subprocesses), `scripts/run_police.ps1`, `scripts/run_thief.ps1`, `scripts/run_demo.ps1`,
`scripts/run_tests.ps1`.

**Requirements completed**: FR-006 (tunneling not yet added, but real HTTP peer processes work),
TEST-007 (Tested), working-instructions "CLI and usability" + "Demo support" sections.

**Two real bugs found and fixed via manual + automated real-process testing** (not caught by the
in-process integration tests, which is exactly why a real-process test is required):
1. The first mover's connection-retry budget (a few attempts meant for *mid-game* hiccups) was
   being exhausted before the opponent's process had even finished starting its server, when two
   independently-launched processes don't start at exactly the same instant. Fixed by adding
   `MCPPeerClient.wait_until_reachable()` — a patient `ping()`-based handshake wait before the
   turn loop begins, decoupled from the in-game retry policy.
2. My own e2e test harness (not product code) deadlocked: calling `.communicate(timeout=60)`
   sequentially on two concurrently-running subprocesses can hang if the second process's own
   stdout PIPE buffer fills before anyone drains it. Fixed by redirecting each subprocess's output
   to its own file instead of a PIPE.
3. (Observed, not a bug) real HTTP transport opens a fresh MCP client session per message
   (init/notify/SSE/close) rather than reusing a connection, so a real two-process game takes
   several seconds per turn under load — much slower than the in-process integration tests. The
   e2e test's timeout was sized generously (240s) to account for this; a connection-reuse
   optimization is a documented future improvement, not required for correctness.

**Manual verification**: ran two real `python -m police_thief peer` processes against each other
directly (not through pytest) twice; both times the game completed with both sides' independently
reported results agreeing exactly (outcome, moves, final positions), all four JSON deliverables
were written, the Gmail draft-mode report was written to disk (no real API call), and
`python -m police_thief replay --log <the produced log>` printed `Verified OK`.

**Tests executed**: `uv run pytest -q` (138 tests, whole suite including e2e, ~74s);
`uv run pytest --cov=src --cov-report=term-missing -m "not e2e" -q` (82% overall coverage on the
fast subset; domain package 91-100% per module, well above the 85% target — `cli.py`/
`peer_runtime.py` show 0% only because their coverage comes exclusively from the e2e test,
excluded from that particular run). `ruff format`/`ruff check` clean; `mypy src` clean (27 source
files).

**Test results**: 138/138 passed.

**Remaining issues**: `gui/live_view.py` (Tkinter live belief-heatmap GUI + screenshot deliverable)
still not started; tunneling (ngrok/Localtonet) for cross-machine play isn't wired (today's demo is
localhost-only, which is sufficient for the local two-terminal demo requirement but not for playing
a real remote rival). README.md academic report and Mermaid diagram copies, `docs/final_audit.md`,
and the two-repo submission split (A-008) are still pending.

**Next part**: `gui/live_view.py` (Tkinter, local-truth-only), then README.md + final audit.

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
