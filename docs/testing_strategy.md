# Testing Strategy — Police–Thief P2P

## Principles

- Deterministic core (`domain/`) is tested with plain `pytest`, no mocks needed — it has no I/O.
- Networking tests use a **real local FastMCP server+client pair on localhost** for at least one
  test per behavior (working instructions: "at least one test must use the real local
  communication layer"); mocks are used only for external services that cost money or require
  network access outside localhost (Gmail API, tunneling providers, remote LLM APIs).
- No test ever sends a real Gmail email or calls a real Anthropic/OpenAI/Ollama endpoint; the
  `template` LLM provider is used in all automated tests (matches assumption A-005: no API-credit
  usage). The one Ollama provider that *is* implemented (`strategy/banter_ollama.py`) is tested
  with an injected fake `httpx` transport, never a real HTTP call.
- Coverage target: ≥85% on `domain/`, ≥70% overall (`src/`), tracked via
  `uv run pytest --cov=src --cov-report=term-missing`. Currently ~91–100% on `domain/`, ~84%
  overall.
- Every `src/` module is kept to ≤150 lines by project convention (`docs/architecture.md` §2);
  where a module was split into sibling files for size, its test file was generally split the same
  way, with shared test setup pulled into a leading-underscore helper module that pytest does not
  collect as a test file itself (e.g. `tests/unit/_orchestrator_helpers.py`).

## 1. Unit tests (`tests/unit/`)

| File | Covers | Requirement IDs |
|---|---|---|
| `test_board.py` / `test_board_config.py` | legal/illegal moves, boundaries, occupied cells, barrier placement legality, capture detection (move-onto, cornering barrier), survival win, board/config validation errors | FR-010..021, A-003, A-009 |
| `test_config.py` / `test_peer_config.py` | `game.json`/`game.toml` loading, schema validation (including `extra="forbid"` rejection of unknown fields, PRD-0570), shared-file hash check, negotiable-vs-fixed field enforcement | NFR-005, NFR-008, A-002, A-004, A-006 |
| `test_crypto.py` | commit/verify round-trip, tamper detection (state/move/intent/nonce each independently), canonical JSON stability, nonce uniqueness | FR-040..045 |
| `test_scent.py` | emission/decay formula numeric match to the book's figures, belief-map normalization, clamping at 0 | FR-030..032 |
| `test_state_machine.py` | every legal transition, every illegal transition rejected, `TECHNICAL_LOSS` terminal | FR-052 |
| `test_strategy.py` / `test_strategy_expected_distance.py` / `test_strategy_loader.py` | default heuristic always legal, the expected-distance-over-belief algorithm's specific fixed behaviors (center-seeking under uniform belief, confidence-gated barrier spend, interior-mobility tie-break), pluggable-class loader accepts/rejects correctly, deterministic given a fixed belief-map input | FR-060..061 |
| `test_qlearning.py` | bonus RL brain: legality-fuzz, state discretization, epsilon-greedy/greedy selection, a hand-verified TD update, Q-table save/load round-trip | BONUS-001 |
| `test_llm_bluff.py` | bonus banter: template provider determinism/word-limit, Ollama provider (faked HTTP transport) success/truncation/fallback-on-error, provider factory including the `claude_api`/`claude_cli` `NotImplementedError` path | FR-061..064, BONUS-002 |
| `test_orchestrator.py` / `test_orchestrator_messages.py` | own-turn commit/reveal flow, a crashing pluggable brain becomes a technical loss (not a crash), incoming COMMIT/REVEAL/malformed-message handling | FR-052/053, PRD-0286 |
| `test_gatekeeper.py` | token-bucket refill/burst curve, DOS detector lock, quota manager exhaustion | FR-055, NFR-006 |
| `test_gmail_report.py` | report JSON schema (all four deliverable files), Gatekeeper-guarded send path (mocked transport) | FR-080..082 |
| `test_reporting.py` | the four mandatory deliverable builders (declaration/config/log/result) | FR-082, FR-087 |
| `test_vcs.py` | real git commit hash discovery, graceful fallback to `"unknown"` on any failure | FR-087 |
| `test_league_audit.py` | games-played count vs. league config, malformed/missing/duplicate declaration handling | FR-083 |
| `test_tunnel.py` / `test_tunnel_dispatch.py` | ngrok discovery (binary missing/found, timeout, early exit), `TunnelHandle.stop()` paths, `start_tunnel` provider dispatch (`none`/`manual`/unknown) | FR-006 |
| `test_replay_viewer.py` | clean log → `Verified OK`; hand-tampered log → `TAMPERED`; malformed/missing-field log entries rejected with a clear error, not a crash | FR-071..072, PRD-0405 |
| `test_live_view_render.py` | belief-to-color mapping and grid-render logic, independent of the Tkinter main loop | FR-070 |
| `test_logging_setup.py` | no secrets/nonces-before-reveal in log output | NFR-004 |
| `test_watchdog.py` | heartbeat/staleness detection with an injectable clock | FR-054 |
| `test_peer_runtime.py` | port-already-in-use fails fast with a clear error instead of an unhandled `SystemExit` | PRD-0582 |

## 2. Networking tests (`tests/network/`)

| File | Covers |
|---|---|
| `test_mcp_transport.py` | successful round trip, rejected/malformed/oversized payloads, duplicate- and stale-turn rejection — all over FastMCP's real in-process client/server transport |
| `test_mcp_reachability.py` | Deadline Tracker retry-then-give-up on an unreachable peer, `wait_until_reachable` success/timeout |

Protocol-message-shape validation (missing fields, wrong types, unsupported `schema_version`) is
covered by `infra/protocol.py`'s own Pydantic models plus the malformed/oversized-payload cases in
`test_mcp_transport.py` — there is no separate `tests/protocol/` directory; protocol-layer behavior
turned out to be more naturally tested alongside the transport that carries it.

## 3. Integration tests (`tests/integration/`)

| File | Covers |
|---|---|
| `test_two_peer_game.py` | two independent `Orchestrator` instances (real state machines, real crypto, real board) over the real local FastMCP transport play a complete game to a definitive outcome; capture is detected symmetrically by both sides |
| `test_two_peer_replay.py` | the full log from a real two-orchestrator game independently verifies (`Verified OK`); a hand-tampered copy of that same real log is flagged `TAMPERED` |
| `test_qlearning_game.py` | the bonus Q-learning brains play a full game to a definitive outcome over the same real transport, proving the bonus brain plugs into the real game loop, not just isolated unit-tested decisions |
| `_two_peer_helpers.py` | shared setup (`make_config`/`play_one_turn`/`run_full_game`) for the two `test_two_peer_*.py` files above — not a test file itself |

## 4. End-to-end tests (`tests/e2e/`)

- `test_two_peer_local_game.py`: spawns two real OS subprocesses (`python -m police_thief peer
  --role police ...` / `--role thief ...`) pointed at each other on `127.0.0.1` (no tunnel needed
  for a same-machine test), lets them play a full game, then asserts:
  - both processes exit cleanly,
  - all four JSON deliverables exist and are schema-valid,
  - the Replay Viewer run against the produced log reports `Verified OK`,
  - the winner recorded matches the scoring table given the moves made.
- This is the test invoked by `scripts/run_tests.ps1 -Full` and is the same scenario demonstrated
  live via `scripts/run_demo.ps1`. Runtime varies with how the game actually ends (~65-135s
  observed) since a survival outcome plays all `max_moves` turns while a capture ends early.

## 5. What is intentionally NOT tested automatically

- Real Gmail delivery (would send real email / cost quota) — covered by one manual run documented
  in `docs/progress.md`, with the report set to `mode = "draft"` by default.
- Real ngrok/Localtonet tunnel (requires an external account/network) — covered by a manual demo
  run; automated tests exercise the same code path over localhost without a tunnel.
- `claude_api`/`claude_cli` LLM providers — not exercised anywhere in CI per assumption A-005;
  `test_llm_bluff.py` only checks that requesting either raises `NotImplementedError` immediately,
  never that a real call succeeds.

## 6. Commands

```
uv sync
uv run ruff format --check .
uv run ruff check .
uv run mypy src
uv run pytest -v
uv run pytest --cov=src --cov-report=term-missing
uv run pytest tests/e2e -v          # slower (~65-135s): spawns two real OS subprocesses over real HTTP
uv run pytest -m "not e2e" -q       # fast subset, skips the real-process test
uv run python -m police_thief --help
```
