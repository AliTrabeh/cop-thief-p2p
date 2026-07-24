# Project Status Board

Single source of truth for "what phase is the project in, and how done is it" — a phase-level
complement to `docs/requirements_traceability.md` (which tracks individual FR/NFR IDs) and
`docs/PRD.md` (which tracks individual product requirements). Update this file at the end of every
implementation part, alongside `docs/progress.md`.

**Status legend**: 🟢 Done · 🟡 In Progress · 🔴 Not Started · ⚪ Deferred/Blocked (needs a decision,
not more coding) · 🎁 Bonus (not required for the core grade)

Overall: **17 of 18 core phases done**, 1 phases partially open (submission packaging), 2 bonus
phases not started. 146/146 automated tests passing. Core game is fully playable end-to-end today.

## Phase board

| # | Phase | Status | % | Owner module(s) | Notes |
|---|---|---|---|---|---|
| 1 | Repository & dev-tool setup | 🟢 Done | 100% | `pyproject.toml`, `src/` layout | ruff/mypy/pytest wired, `uv`-managed |
| 2 | Core domain models (board, moves, barriers, capture) | 🟢 Done | 100% | `domain/board.py`, `domain/models.py` | 100% branch coverage target met |
| 3 | Config loader (shared `game.json` + private `game.toml`) | 🟢 Done | 100% | `config.py` | includes `shared_config_hash` NFR-008 |
| 4 | Commit-Reveal cryptographic module | 🟢 Done | 100% | `domain/crypto.py` | matches book's reference `commit()`/`verify()` |
| 5 | Scent / pheromone belief-map engine | 🟢 Done | 100% | `domain/scent.py` | decay/re-emission formulas numerically tested |
| 6 | Game state machine | 🟢 Done | 100% | `domain/state_machine.py` | full legal/illegal transition table tested |
| 7 | Strategy modules (default heuristic + pluggable loader) | 🟢 Done | 100% | `strategy/base.py`, `strategy/heuristic.py` | RL/LLM bonus brains are separate phases below |
| 8 | FastMCP P2P transport + tunneling | 🟢 Done | 100% | `infra/mcp_server.py`, `infra/mcp_client.py`, `infra/tunnel.py` | ngrok automated; not yet run against a real ngrok binary or real remote rival |
| 9 | Orchestrator + Watchdog + Deadline Tracker | 🟢 Done | 100% | `orchestrator.py`, `infra/watchdog.py` | Single Gateway pattern |
| 10 | Gatekeeper (rate limiting) | 🟢 Done | 100% | `infra/gatekeeper.py` | Token Bucket + Quota Manager + DOS Detector |
| 11 | Gmail API reporting | 🟡 Mostly done | 90% | `infra/gmail_report.py` | code path tested only in `draft` mode; real OAuth2 send against a live account not yet confirmed |
| 12 | CLI | 🟢 Done | 100% | `cli.py` | `peer` + `replay` subcommands |
| 13 | GUI (live belief-heatmap view) + Replay Viewer | 🟡 Mostly done | 95% | `gui/live_view.py`, `gui/replay_viewer.py` | logic fully tested; live-view screenshot artifact for submission still pending |
| 14 | Logging & config polish | 🟢 Done | 100% | `logging_setup.py` | secret-redaction filter tested |
| 15 | Full test suite pass + coverage | 🟢 Done | 100% | `tests/` | 146 tests, ~80% overall / 91–100% on `domain/` |
| 16 | Two-peer local E2E demo + scripts | 🟢 Done | 100% | `scripts/*.ps1`, `tests/e2e/` | real two-OS-process game, verified over real HTTP |
| 17 | Documentation pass | 🟢 Done | 100% | `README.md`, `docs/*.md` | academic-report style, traceability matrix, assumptions log |
| 18 | Final verification & submission packaging | 🟡 In Progress | ~60% | `docs/final_audit.md` | see open items below — this is the only phase blocking a `v1.0-submission` tag |
| 19 🎁 | Bonus: Reinforcement-learning brain (`strategy/qlearning.py`) | 🔴 Not started | 0% | — | optional per spec (BONUS-001); no code exists yet |
| 20 🎁 | Bonus: LLM trash-talk / banter (`strategy/llm_bluff.py`) | 🔴 Not started | 0% | — | optional per spec (BONUS-002); config sections exist and default to zero-cost `template` mode, but no provider reads them yet |

## Phase 18 open items (the only thing between "done" and "submission-ready")

These are the concrete, named remaining tasks — every one of them is a decision or a manual step,
not unwritten core logic:

1. **Two-repository split** — the spec asks for two separate GitHub repos (cop-owned,
   thief-owned), cross-linked. Currently everything lives in one repo
   (`AliTrabeh/cop-thief-p2p`) for development convenience. Needs either an actual split or
   explicit lecturer sign-off that one repo is acceptable (`docs/assumptions.md` A-008). ⚪ Deferred — needs your decision.
2. **Submission screenshots** — the live-view heatmap and the Replay Viewer's `Verified OK`
   banner both work (proven by tests + manual runs) but the actual image artifacts for the
   Appendix C Table 6 checklist haven't been captured yet.
3. **Real Gmail send test** — `infra/gmail_report.py` is only exercised in `draft` mode so far;
   a real end-of-game report email against a live Google account (OAuth2 flow) hasn't been sent.
4. **Real commit hash in the declaration JSON** — `peer_runtime.py` currently writes the
   placeholder `"unknown"` for `commit_hash`; the real per-game value has to be filled in at
   submission time (Appendix F mandatory rule 5) since a running process can't know the hash of
   the commit that produced it.
5. **Tag `v1.0-submission`** — once 1–4 above are resolved.
6. **FR-083** — the mutual daily-log / games-played-count audit for a multi-game league series
   isn't wired yet (only matters once actually playing a 6-game series against a rival team).

## How this maps to the PRD

`docs/PRD.md` breaks every one of these phases down into individually numbered, testable product
requirements (600+ of them). This file answers "what phase are we in"; the PRD answers "what,
exactly, does 'done' mean for this phase, item by item."
