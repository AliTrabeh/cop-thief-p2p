# Project Status Board

Single source of truth for "what phase is the project in, and how done is it" — a phase-level
complement to `docs/requirements_traceability.md` (which tracks individual FR/NFR IDs) and
`docs/PRD.md` (which tracks individual product requirements). Update this file at the end of every
implementation part, alongside `docs/progress.md`.

**Status legend**: 🟢 Done · 🟡 In Progress · 🔴 Not Started · ⚪ Deferred/Blocked (needs a decision,
not more coding) · 🎁 Bonus (not required for the core grade)

Overall: **19 of 20 phases done** (including both bonus phases), 1 phase partially open (submission
packaging, and that's now down to items only a human can finish — see below). 205/205 automated
tests passing in the fast subset (plus the real two-subprocess e2e test), ~84% overall coverage.
Core game is fully playable end-to-end today, including both optional bonus AI brains.

## Phase board

| # | Phase | Status | % | Owner module(s) | Notes |
|---|---|---|---|---|---|
| 1 | Repository & dev-tool setup | 🟢 Done | 100% | `pyproject.toml`, `src/` layout | ruff/mypy/pytest wired, `uv`-managed |
| 2 | Core domain models (board, moves, barriers, capture) | 🟢 Done | 100% | `domain/board.py`, `domain/models.py` | 100% branch coverage target met |
| 3 | Config loader (shared `game.json` + private `game.toml`) | 🟢 Done | 100% | `config.py` | includes `shared_config_hash` NFR-008; now rejects unknown fields (`extra="forbid"`) |
| 4 | Commit-Reveal cryptographic module | 🟢 Done | 100% | `domain/crypto.py` | matches book's reference `commit()`/`verify()` |
| 5 | Scent / pheromone belief-map engine | 🟢 Done | 100% | `domain/scent.py` | decay/re-emission formulas numerically tested |
| 6 | Game state machine | 🟢 Done | 100% | `domain/state_machine.py` | full legal/illegal transition table tested |
| 7 | Strategy modules (default heuristic + pluggable loader) | 🟢 Done | 100% | `strategy/base.py`, `strategy/heuristic.py` | a crashing pluggable brain now becomes a clean technical loss instead of taking down the peer process |
| 8 | FastMCP P2P transport + tunneling | 🟢 Done | 100% | `infra/mcp_server.py`, `infra/mcp_client.py`, `infra/tunnel.py` | ngrok automated; not yet run against a real ngrok binary or real remote rival |
| 9 | Orchestrator + Watchdog + Deadline Tracker | 🟢 Done | 100% | `orchestrator.py`, `infra/watchdog.py` | Single Gateway pattern |
| 10 | Gatekeeper (rate limiting) | 🟢 Done | 100% | `infra/gatekeeper.py` | Token Bucket + Quota Manager + DOS Detector |
| 11 | Gmail API reporting | 🟡 Mostly done | 90% | `infra/gmail_report.py` | code path tested only in `draft` mode; real OAuth2 send against a live account not yet confirmed |
| 12 | CLI | 🟢 Done | 100% | `cli.py` | `peer` + `replay` + new `audit` subcommands |
| 13 | GUI (live belief-heatmap view) + Replay Viewer | 🟡 Mostly done | 95% | `gui/live_view.py`, `gui/replay_viewer.py` | logic fully tested (replay viewer now also rejects a structurally-corrupt log with a clear error); live-view screenshot artifact for submission still pending |
| 14 | Logging & config polish | 🟢 Done | 100% | `logging_setup.py` | secret-redaction filter tested |
| 15 | Full test suite pass + coverage | 🟢 Done | 100% | `tests/` | 205 tests in the fast subset (+1 e2e), ~84% overall / 91–100% on `domain/` |
| 16 | Two-peer local E2E demo + scripts | 🟢 Done | 100% | `scripts/*.ps1`, `tests/e2e/` | real two-OS-process game, verified over real HTTP; fixed a real output-dir collision bug in the standalone demo scripts (see below) |
| 17 | Documentation pass | 🟢 Done | 100% | `README.md`, `docs/*.md` | academic-report style, traceability matrix, assumptions log |
| 18 | Final verification & submission packaging | 🟡 In Progress | ~80% | `docs/final_audit.md` | every remaining item now needs a human (real credentials, real roster, a policy decision) — see open items below |
| 19 🎁 | Bonus: Reinforcement-learning brain (`strategy/qlearning.py`) | 🟢 Done | 100% | `strategy/qlearning.py` | tabular Q-learning, BONUS-001; opt-in via `[strategy]` config, never the default |
| 20 🎁 | Bonus: LLM trash-talk / banter (`strategy/llm_bluff.py`) | 🟢 Done | 100% | `strategy/llm_bluff.py` | BONUS-002; `template` (default, offline) + `ollama` (local, zero-cost) providers implemented; `claude_api`/`claude_cli` deliberately left unimplemented (raises clearly) per A-005's no-default-spend policy |

## Newly closed this session (2026-07-24, implementation pass)

Beyond the two bonus AI brains above, several concrete gaps and one real bug were closed:

- **FR-087 (real commit hash)** — `infra/vcs.py::current_commit_hash()` now runs `git rev-parse
  HEAD` at runtime instead of writing the placeholder `"unknown"`; the declaration JSON's
  `github_commit` field is correct without a manual step.
- **FR-083 (league audit)** — `infra/league_audit.py` + a new `python -m police_thief audit`
  CLI subcommand count this team's own games played against `min_games_to_pass`/
  `max_games_per_team`, from real deliverable files on disk.
- **Robustness** — a pluggable strategy that raises an exception now becomes a clean technical
  loss instead of crashing the peer process; unknown/typo'd config fields are rejected at load
  time; a structurally-corrupt (but syntactically valid JSON) log file is rejected with a clear
  error instead of a raw `KeyError`; a port-already-in-use startup failure now raises a clear
  `PeerRuntimeError` instead of an unhandled `SystemExit` (uvicorn calls `sys.exit()` internally
  on a bind failure, which asyncio propagates specially — this needed a proactive port probe, not
  just a try/except).
- **Bug fix** — `scripts/run_police.ps1`/`run_thief.ps1` (the README's "recommended" two-terminal
  demo) both defaulted `--output-dir` to the *same* directory for both roles, so running them
  exactly as documented meant one side's deliverables silently overwrote the other's. Fixed to
  match `run_demo.ps1`'s already-correct per-role subdirectories.

## Phase 18 open items (everything left needs a human, not more code)

1. **Two-repository split** — the spec asks for two separate GitHub repos (cop-owned,
   thief-owned), cross-linked. Currently everything lives in one repo
   (`AliTrabeh/cop-thief-p2p`) for development convenience. Needs either an actual split or
   explicit lecturer sign-off that one repo is acceptable (`docs/assumptions.md` A-008). ⚪ Deferred — needs your decision.
2. **Submission screenshots** — the live-view heatmap and the Replay Viewer's `Verified OK`
   banner both work (proven by tests + manual runs) but the actual image artifacts for the
   Appendix C Table 6 checklist haven't been captured yet.
3. **Real Gmail send test** — `infra/gmail_report.py` is only exercised in `draft` mode so far;
   a real end-of-game report email against a live Google account (OAuth2 flow) hasn't been sent.
   Needs real `credentials.json`/interactive OAuth consent — can't be done without you.
4. **Real team roster** — `config/<role>/game.toml`'s `group_name`/`group_id`/`members` are still
   development placeholders; needs real student identifiers before submission (A-012).
5. **Tag `v1.0-submission`** — once 1–4 above are resolved.

## How this maps to the PRD

`docs/PRD.md` breaks every one of these phases down into individually numbered, testable product
requirements (600+ of them, growing as gaps close). This file answers "what phase are we in"; the
PRD answers "what, exactly, does 'done' mean for this phase, item by item."
