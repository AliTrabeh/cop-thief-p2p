# Implementation Plan — Police–Thief P2P

Numbered parts, each completed/tested/reviewed before the next starts, per the working
instructions. Mirrors — but is more granular than — the book's own "seven development priorities"
(§10.3): Base Logic → MCP Infra → Strategy → Language+Scent → Cloud+Tunnel → Security → Reporting
Shell. Each part below states goal, files, requirements covered, tests, commands, acceptance
criteria, risks, and dependencies.

## Part 1 — Repository & dev-tool setup
- **Goal**: `uv`-managed project, `src/` layout, ruff/mypy/pytest wired, package skeleton in place.
- **Files**: `pyproject.toml`, `src/police_thief/__init__.py` + empty module stubs per
  `docs/architecture.md` §2, `tests/` tree, `.gitignore` (already done), `main.py` removed (dead
  PyCharm placeholder, replaced by `src/` package + CLI entry point).
- **Requirements**: NFR-002, NFR-005 (config plumbing groundwork).
- **Tests**: `uv run pytest --collect-only` succeeds (no tests yet, but collection doesn't error).
- **Commands**: `uv sync`, `uv run ruff check .`, `uv run mypy src`.
- **Acceptance**: `uv run python -m police_thief --help` prints usage (even if a stub).
- **Risks**: none significant. **Depends on**: nothing.

## Part 2 — Core domain models
- **Goal**: `domain/models.py` dataclasses (Coordinate, Move, GameConfig, Declaration, etc.),
  `domain/board.py` (grid, legal-move check, barrier legality), capture/win detection.
- **Requirements**: FR-010..021, NFR-005, A-003, A-009.
- **Tests (TEST-001)**: valid/invalid moves, boundaries, occupied/blocked cells, barrier legality,
  capture via move-onto-thief, capture via cornering barrier, survival win, config validation
  errors (bad barrier count, mismatched start/board size per A-009).
- **Commands**: `uv run pytest tests/unit/test_board.py -v`.
- **Acceptance**: 100% branch coverage on `domain/board.py`; no illegal state reachable.
- **Risks**: off-by-one on axis origin/start index (A-003) — mitigate with explicit fixtures at
  board edges. **Depends on**: Part 1.

## Part 3 — Config loader
- **Goal**: `config.py` loads+validates `config/game.json` (shared) and `config/<role>/game.toml`
  (private); enforces NFR-005/NFR-008 (byte-identical shared file, hash-checked).
- **Requirements**: NFR-005, NFR-008, PROTO-001, A-002, A-003, A-006, A-009.
- **Tests**: schema-valid/invalid fixtures, hash-mismatch detection between two copies of
  `game.json`, missing-field errors are explicit (not `KeyError` leaking to the user).
- **Commands**: `uv run pytest tests/unit/test_config.py -v`.
- **Acceptance**: loading the book's own example JSON/TOML (transcribed into fixtures) round-trips
  cleanly into `GameConfig`.
- **Depends on**: Part 2 (shares `models.py`).

## Part 4 — Commit-Reveal crypto module
- **Goal**: `domain/crypto.py`: `commit()`, `verify()`, canonical JSON, nonce generation.
- **Requirements**: FR-040..045, PROTO-002.
- **Tests (TEST-003)**: round-trip commit→verify true; tampered move/state/nonce → verify false;
  canonical JSON is stable across key-insertion order; nonce uniqueness (statistical smoke test);
  `secrets.compare_digest` used (not `==`) — grep-based lint check.
- **Commands**: `uv run pytest tests/unit/test_crypto.py -v`.
- **Acceptance**: matches the book's exact `commit()`/`verify()` reference semantics (§5.3.1 code).
- **Depends on**: Part 2.

## Part 5 — Scent / belief-map engine
- **Goal**: `domain/scent.py`: emission/decay formula, belief-map update (Bayesian or heuristic
  posterior), Manhattan-distance default heuristic.
- **Requirements**: FR-030..032.
- **Tests (TEST-002)**: single-deposit decay curve matches the book's ρ=0.10 figure numerically;
  re-emission (thief present multiple turns) converges to the book's ~half-peak-at-turn-8 behavior;
  belief-map normalizes to a valid probability distribution; scent-field values clamp at 0.
- **Commands**: `uv run pytest tests/unit/test_scent.py -v`.
- **Depends on**: Part 2.

## Part 6 — Game state machine
- **Goal**: `domain/state_machine.py`: `GamePhaseMachine` with the exact transition table from
  `docs/protocol.md` §4.
- **Requirements**: FR-052.
- **Tests (TEST-004)**: every legal transition succeeds; every illegal transition raises;
  `TECHNICAL_LOSS` is terminal (no outgoing transitions).
- **Commands**: `uv run pytest tests/unit/test_state_machine.py -v`.
- **Depends on**: Part 1.

## Part 7 — Strategy modules
- **Goal**: `strategy/base.py` (`BrainBase`/`ThiefBrain`/`PoliceBrain` ABCs), `strategy/heuristic.py`
  (default Manhattan+belief-argmax brain), pluggable loading via `[strategy]` config
  (`package.module:Class`).
- **Requirements**: FR-060..061.
- **Tests**: default brain always returns a legal move given any legal board state (property-based
  fuzz test over random boards); pluggable-class loader resolves `module:Class` strings and rejects
  non-`BrainBase` subclasses.
- **Commands**: `uv run pytest tests/unit/test_strategy.py -v`.
- **Depends on**: Parts 2, 5.

## Part 8 — FastMCP P2P transport
- **Goal**: `infra/mcp_server.py` (tool exposure, signature verification before trust),
  `infra/mcp_client.py` (calls into opponent, timeout/retry), `infra/tunnel.py` (ngrok/Localtonet
  lifecycle wrapper, optional for localhost-only dev/test runs).
- **Requirements**: FR-050..051, FR-006.
- **Tests (TEST-005)**: real local FastMCP server+client round-trip on localhost (no tunnel needed
  for tests); malformed payload rejected; unverified signature rejected; timeout triggers retry per
  config.
- **Commands**: `uv run pytest tests/network/ -v`.
- **Depends on**: Parts 3, 4.

## Part 9 — Orchestrator, reliability patterns
- **Goal**: `orchestrator.py` (Single Gateway wiring state machine + strategy + MCP + log +
  deadline tracker + watchdog), `infra/watchdog.py`, deadline-tracker logic inside orchestrator or
  its own module.
- **Requirements**: FR-052..054, architecture.md §6/§7 failure table.
- **Tests**: simulated frozen main loop triggers watchdog shutdown; simulated unresponsive peer
  triggers deadline-tracker technical-loss path; illegal transition attempt is rejected end-to-end.
- **Commands**: `uv run pytest tests/integration/test_orchestrator.py -v`.
- **Depends on**: Parts 2–8.

## Part 10 — Gatekeeper (rate limiting)
- **Goal**: `infra/gatekeeper.py`: Quota Manager, Token Bucket, DOS Detector pipeline.
- **Requirements**: FR-055, NFR-006.
- **Tests**: token-bucket formula matches the book's figure numerically (burst then refill curve);
  DOS detector locks/blocks on anomalous burst; quota manager rejects once daily budget exhausted.
- **Commands**: `uv run pytest tests/unit/test_gatekeeper.py -v`.
- **Depends on**: Part 1.

## Part 11 — Gmail API reporting
- **Goal**: `infra/gmail_report.py`: OAuth2 send-only flow (Appendix A), JSON report construction
  (four deliverables), Gatekeeper-guarded sends.
- **Requirements**: FR-080..082.
- **Tests**: report JSON matches schema exactly (four required files); send path is mocked in CI
  (no real Gmail calls in automated tests — see testing_strategy.md); Gatekeeper blocks a send when
  quota exhausted (integration test with a fake clock).
- **Commands**: `uv run pytest tests/unit/test_gmail_report.py -v`.
- **Depends on**: Parts 9, 10.

## Part 12 — CLI
- **Goal**: `cli.py`: `python -m police_thief peer --role police|thief`,
  `python -m police_thief replay --log <path>`.
- **Requirements**: working instructions "CLI and usability" section; DOC deliverables.
- **Tests**: `--help` output; argument validation errors are clean (no stack trace without
  `--debug`); a scripted local run produces the four JSON deliverables.
- **Commands**: `uv run python -m police_thief --help`.
- **Depends on**: Part 9.

## Part 13 — GUI (live view) and Replay Viewer
- **Goal**: `gui/live_view.py` (Tkinter, local-truth-only heatmap + turn banner),
  `gui/replay_viewer.py` (`verify_step`/`replay`, Verified OK/TAMPERED banner).
- **Requirements**: FR-070..072.
- **Tests**: replay viewer correctly flags a hand-tampered log fixture as `TAMPERED` and a clean log
  as `Verified OK`; live view unit-testable rendering logic separated from the Tkinter main loop so
  it doesn't require a display in CI.
- **Commands**: `uv run pytest tests/unit/test_replay_viewer.py -v`; manual: `uv run python -m
  police_thief replay --log logs/<file>.json` on a real produced log.
- **Depends on**: Parts 4, 9.

## Part 14 — Logging & config polish
- **Goal**: `logging_setup.py` structured logging, verbosity flags, secrets-redaction check.
- **Requirements**: NFR-004.
- **Tests**: log output never contains `credentials`/`token`/nonce-before-reveal substrings
  (regex-based negative test).
- **Depends on**: Part 1 (touches everything, done once things stabilize).

## Part 15 — Full test suite pass + coverage
- **Goal**: everything from `docs/testing_strategy.md` green.
- **Commands**: `uv run pytest -v`, `uv run pytest --cov=src --cov-report=term-missing`.
- **Acceptance**: meaningful coverage on `domain/` and `infra/` (target ≥85% on domain, ≥70%
  overall — GUI Tkinter loop excluded from the ratio, its logic-only parts included).

## Part 16 — Two-peer local E2E demo + scripts
- **Goal**: `scripts/run_police.ps1`, `scripts/run_thief.ps1`, `scripts/run_demo.ps1`,
  `scripts/run_tests.ps1`.
- **Requirements**: TEST-007, working instructions "Demo support".
- **Acceptance**: running both scripts in two terminals completes a real game over localhost
  FastMCP, produces all four JSON deliverables, and the Replay Viewer shows `Verified OK`.

## Part 17 — Documentation pass
- **Goal**: `README.md` (academic-report style per DOC-001), Mermaid diagrams already drafted in
  `architecture.md`/`protocol.md` copied/linked, `docs/progress.md` finalized, `docs/testing_strategy.md`
  cross-checked against actual test files.
- **Requirements**: DOC-001..003.

## Part 18 — Final verification & submission packaging
- **Goal**: `docs/final_audit.md` (20-point audit), submission checklist (Appendix C Table 6),
  `.gitignore` re-verified, annotated tag `v1.0-submission`.
- **Requirements**: FR-085..088, DOC-004..005.
- **Risk carried forward**: two-repo split (A-008) — resolved or explicitly deferred with lecturer
  confirmation before tagging.

---

Order matters where a later part's tests depend on an earlier part's public interface; parts
without a dependency arrow between them (e.g. Part 10 Gatekeeper vs. Part 7 Strategy) may proceed
in either order. `docs/progress.md` tracks actual completion dates and any part re-opened due to a
downstream discovery.
