# Testing Strategy — Police–Thief P2P

## Principles

- Deterministic core (`domain/`) is tested with plain `pytest`, no mocks needed — it has no I/O.
- Networking tests use a **real local FastMCP server+client pair on localhost** for at least one
  test per behavior (working instructions: "at least one test must use the real local
  communication layer"); mocks are used only for external services that cost money or require
  network access outside localhost (Gmail API, tunneling providers, remote LLM APIs).
- No test ever sends a real Gmail email or calls a real Anthropic/OpenAI/Ollama endpoint; the
  `template` LLM provider is used in all automated tests (matches assumption A-005: no API-credit
  usage).
- Coverage target: ≥85% on `domain/`, ≥70% overall (`src/`), tracked via
  `uv run pytest --cov=src --cov-report=term-missing`.

## 1. Unit tests (`tests/unit/`)

| File | Covers | Requirement IDs |
|---|---|---|
| `test_board.py` | legal/illegal moves, boundaries, occupied cells, barrier placement legality, capture detection (move-onto, cornering barrier), survival win, board/config validation errors | FR-010..021, A-003, A-009 |
| `test_config.py` | `game.json`/`game.toml` loading, schema validation, shared-file hash check, negotiable-vs-fixed field enforcement | NFR-005, NFR-008, A-002, A-004, A-006 |
| `test_crypto.py` | commit/verify round-trip, tamper detection (state/move/intent/nonce each independently), canonical JSON stability, nonce uniqueness | FR-040..045 |
| `test_scent.py` | emission/decay formula numeric match to the book's figures, belief-map normalization, clamping at 0 | FR-030..032 |
| `test_state_machine.py` | every legal transition, every illegal transition rejected, `TECHNICAL_LOSS` terminal | FR-052 |
| `test_strategy.py` | default heuristic always legal, pluggable-class loader accepts/rejects correctly, deterministic given a fixed belief-map input | FR-060..061 |
| `test_gatekeeper.py` | token-bucket refill/burst curve, DOS detector lock, quota manager exhaustion | FR-055, NFR-006 |
| `test_gmail_report.py` | report JSON schema (all four deliverable files), Gatekeeper-guarded send path (mocked transport) | FR-080..082 |
| `test_replay_viewer.py` | clean log → `Verified OK`; hand-tampered log → `TAMPERED`; partial/corrupt log handled without crashing | FR-071..072 |
| `test_logging_redaction.py` | no secrets/nonces-before-reveal in log output | NFR-004 |

## 2. Protocol tests (`tests/protocol/`)

- Every FastMCP tool message type: commit, acknowledge, reveal, final-reveal/audit.
- Invalid payloads: missing fields, wrong types, oversized payload (NFR-006 size-limit check).
- Unsupported `schema_version` is rejected with a clear error, not a silent partial parse.
- Duplicate turn-number messages are idempotently ignored.
- Stale / out-of-order turn-number messages are rejected.
- Invalid state transitions attempted via a crafted message are rejected by the orchestrator, not
  just the state machine in isolation (defense in depth).

## 3. Networking tests (`tests/network/`)

- Successful local FastMCP connection (server+client on localhost, no tunnel).
- Failed connection (server not started / wrong port) — client surfaces a clean error.
- Timeout — server deliberately delayed beyond `response_timeout_sec`; client's Deadline Tracker
  retries then reports technical loss.
- Malformed / partial data — server returns a clean rejection, does not crash.
- Multiple sequential messages processed in order.
- Graceful shutdown — orchestrator closes the MCP connection and flushes logs on `GAME_OVER`.

## 4. Integration tests (`tests/integration/`)

- Two in-process `Orchestrator` instances (real state machines, real crypto, real board, **fake**
  MCP transport via an in-memory transport double, or real localhost FastMCP — prefer real) play a
  complete short game (small board, low `max_moves`) to a definitive winner.
- Invalid move injected mid-game is rejected, game continues.
- Winner detection matches the scoring table exactly for capture / survival / tie scenarios (one
  test per scenario in FR-018).
- Simulated peer crash mid-game triggers Watchdog/Deadline-Tracker recovery path, ending in a
  well-defined technical-loss result, not a hang.
- Tampered commit injected mid-game is caught by the receiving side's verification and by the
  end-of-game mutual audit.

## 5. End-to-end tests (`tests/e2e/`)

- `test_two_peer_local_game.py`: spawns two real OS subprocesses (`python -m police_thief peer
  --role police ...` / `--role thief ...`) pointed at each other on `127.0.0.1` (no tunnel needed
  for a same-machine test), lets them play a full game, then asserts:
  - both processes exit cleanly,
  - all four JSON deliverables exist and are schema-valid,
  - the Replay Viewer run against the produced log reports `Verified OK`,
  - the winner recorded matches the scoring table given the moves made.
- This is the test invoked by `scripts/run_tests.ps1`'s "full e2e" mode and is the same scenario
  demonstrated live via `scripts/run_demo.ps1`.

## 6. What is intentionally NOT tested automatically

- Real Gmail delivery (would send real email / cost quota) — covered by one manual run documented
  in `docs/progress.md`, with the report set to `mode = "draft"` by default.
- Real ngrok/Localtonet tunnel (requires an external account/network) — covered by a manual demo
  run; automated tests exercise the same code path over localhost without a tunnel.
- `claude_api`/`claude_cli` LLM providers — not exercised anywhere in CI per assumption A-005;
  covered by a narrow unit test that only checks the provider interface is implemented, using a
  stub instead of a real network call.

## 7. Commands

```
uv sync
uv run ruff format --check .
uv run ruff check .
uv run mypy .
uv run pytest -v
uv run pytest --cov=src --cov-report=term-missing
uv run pytest tests/e2e -v          # slower, spawns real subprocesses
uv run python -m police_thief --help
```
