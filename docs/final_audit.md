# Final Audit

Snapshot as of 2026-07-25, updated after a third pass (the default algorithm's expected-distance
upgrade, a project-wide 150-line-per-file refactor, and this strict structural audit) on top of the
second pass that closed FR-083, FR-087, and both bonus AI brains (see `docs/progress.md` for the
full dated history). This audit follows the 20-point checklist from the working instructions.

## 1. Requirement coverage

Every requirement extracted from the 143-page spec (FR-001..088, NFR-001..008, PROTO-001..004,
TEST-001..007, DOC-001..005, plus Appendix E items E-1..E-55) is listed in
`docs/requirements_traceability.md` with a module, a test, and a status. Summary:

- **Tested** (implemented + automated test passes): the large majority — all core game rules,
  crypto, scent/belief, state machine, strategy (including both bonus brains: tabular Q-learning in
  `strategy/qlearning.py` and LLM banter in `strategy/llm_bluff.py`), FastMCP transport, tunneling
  (`infra/tunnel.py`, ngrok automated + fully unit-tested with faked externals), Orchestrator,
  Gatekeeper, reporting (real git-commit-hash discovery via `infra/vcs.py`, no manual step), the
  FR-083 league audit (`infra/league_audit.py`), Gmail (draft-mode), CLI, live-view rendering logic,
  and the full two-real-process e2e scenario.
- **Implemented** (working, but not independently unit-tested, or a manual-only artifact): the
  live GUI's actual Tkinter widget (smoke-tested manually, not exercised in CI since it needs a
  display), Step-0 hardware declaration emission, ngrok automation (unit-tested with every external
  dependency faked, but never run against a real `ngrok` binary — none was available in this
  development environment).
- **Cut by design** (deliberately not built, not a gap): `claude_api`/`claude_cli` LLM banter
  providers — `build_banter_provider` raises `NotImplementedError` immediately rather than silently
  spending real API credits by default (A-005).
- **Planned** (needs a human, not more code): the mutual cross-team half of the games-played audit
  (this peer's own side is now automated; comparing against the rival team's logs is inherently
  out-of-band, same as A-018's tunnel-URL exchange), the two-repo submission split (A-008), the
  submission screenshots, and a real (non-draft) Gmail send test.

No requirement was silently dropped; every "Planned" row states what's missing and why.

## 2. Every functional requirement has an implementation

True for all FR-xxx rows marked Tested or Implemented in the traceability matrix. The remaining
exceptions (the two-repo split, submission screenshots, a real Gmail send) are explicitly called
out as Planned, with the reasoning in `docs/progress.md`'s per-part entries and `README.md`'s Known
Limitations section.

## 3. Every critical requirement has a test

Yes — game rules, crypto (including tamper detection on each committed field independently),
scoring, state-machine legality, the full commit→reveal→final-reveal→audit cycle, and the FastMCP
transport (including duplicate/stale/malformed/oversized-payload rejection) all have dedicated
automated tests. The one true end-to-end path (two real OS processes playing a full game over real
HTTP) is exercised by `tests/e2e/test_two_peer_local_game.py`, not just simulated.

## 4. The project installs from a clean environment

`uv sync` installs `fastmcp`, `pydantic`, and the Google API client libraries from `pyproject.toml`
with a committed `uv.lock`. Verified during this session (fresh `uv sync` run, `Installed N
packages`, no errors).

## 5. Imports succeed

`uv run python -m police_thief --help` runs cleanly. Every module imports without error (proven by
the full test suite passing, since pytest imports every test module which imports the corresponding
source module).

## 6. Formatting passes

`uv run ruff format --check .` — clean at every commit in this session (verified repeatedly; the
project has zero outstanding formatting diffs).

## 7. Linting passes

`uv run ruff check .` — clean (`All checks passed!`) at every commit in this session.

## 8. Type checking passes or documented justified exceptions exist

`uv run mypy src` — clean, 46 source files (up from 28 before the 150-line-per-file split — same
code, more, smaller files), strict mode, zero errors. One documented exception:
`[[tool.mypy.overrides]]` for `googleapiclient`/`google.oauth2`/`google.auth` (no upstream
`py.typed` marker), plus one inline `# type: ignore[no-untyped-call]` on the one untyped Google API
call site (`infra/gmail_report.py::get_gmail_service`). `mypy` is intentionally scoped to `src/`
only (not `tests/`) — strict untyped-def checking on test functions isn't a useful signal; see
`docs/testing_strategy.md`.

## 9. Tests pass

`uv run pytest -q` — 210 tests (209 in the fast subset + the real-two-process e2e test), all
passing. Re-verified fresh as part of this structural-audit pass: `uv sync` from scratch, every
module in `src/police_thief` imported individually with no failures (46/46), `ruff format --check`/
`ruff check`/`mypy --strict` all clean, and the e2e test re-run standalone and confirmed green
(observed runtime varies 65-135s depending on whether the game ends in an early capture or plays
out to the full `max_moves` survival case).

## 10. Two real peers communicate locally

Verified twice manually (two `python -m police_thief peer` processes launched independently,
against each other on localhost, no tunnel) and once via the automated e2e test
(`tests/e2e/test_two_peer_local_game.py`, spawning two real OS subprocesses). Both manual runs and
the automated test completed a full game with both sides' independently-computed results agreeing
exactly on outcome, move count, and final positions.

## 11. A complete game can finish

Yes — every real/integration run in this session reached a definitive `Outcome` (capture or
survival), never left hanging. `max_moves` (config-enforced) provides a hard upper bound regardless
of strategy behavior.

## 12. Invalid moves are rejected

`domain/board.py`'s legality checks reject out-of-bounds moves, moves into barriers, and diagonal
moves (which don't exist as a representable value at all). At the protocol layer, an illegal
revealed move is rejected by the receiving side and ends the game as a technical loss for the
offending side (`orchestrator.py::_receive_reveal`, tested in
`tests/unit/test_orchestrator.py::test_receive_reveal_with_illegal_move_causes_technical_loss`).

## 13. Peer state remains synchronized

Every integration and e2e test asserts the two independent `BoardState` mirrors (one per
`Orchestrator`, one per OS process in the e2e case) agree exactly on outcome, positions, and move
count at game end — proof the message exchange alone (never shared memory) kept them in sync.

## 14. Shutdown is clean

`peer_runtime.py`'s `finally` block always cancels the FastMCP server task and (if a GUI was shown)
destroys the Tkinter window, regardless of how the turn loop exited (normal completion, technical
loss, or an unresponsive opponent). One known cosmetic issue: cancelling a running `uvicorn`
server task logs an `ERROR`-level traceback for the cancelled ASGI lifespan — noisy, but does not
affect correctness (the four JSON deliverables are written correctly every time this was observed).

## 15. README commands are accurate

Every command in `README.md` §6 was run during this session (`uv sync`, the two-terminal demo, the
single-terminal demo, `replay`, and the full test/lint/type-check sequence) and matches what's
documented.

## 16. No secrets are committed

`.gitignore` excludes `credentials.json`, `token.json`, `config/**/secrets.json`, `.env`, and the
lecturer's copyrighted PDF. `git log` for this repository contains no credential material (the repo
was created fresh for this project; no history to scrub).

## 17. No placeholder TODOs remain in required functionality

`cli.py`'s `peer`/`replay` subcommands are fully implemented (no more `NotImplementedError`). The
remaining "Planned" items (LLM banter, multi-game audit, two-repo split) are absent modules, not
TODO-stubbed functions pretending to work — they simply don't exist yet, which is the honest state
per the working instructions ("do not create placeholder implementations and claim they are
complete").

## 18. No dead files or obsolete duplicate implementations remain

The original PyCharm placeholder (`main.py`) was removed in Part 1 once `src/police_thief` existed.
No duplicate/superseded modules remain from this session's development. Re-verified explicitly in
the 2026-07-25 structural audit: every symbol defined in the files created by the 150-line-per-file
split was checked to have at least one real usage outside its own definition (none orphaned), no
top-level symbol name is defined more than once anywhere in `src/`, and `git status --ignored`
shows nothing untracked except the expected caches/venv/IDE folders and the gitignored lecturer PDF.

## 19. The project is understandable to the lecturer

`README.md` explains the Dec-POMDP framing, the P2P architecture and its FastMCP/tunneling
trade-off, the commit-reveal anti-cheat protocol, and the strategy pluggability point, each with
citations back to specific spec sections. `docs/architecture.md` and `docs/protocol.md` give full
Mermaid diagrams (sequence, state machine) and exact schemas. `docs/assumptions.md` documents every
interpretive decision with its reasoning, so a reviewer can judge each one independently rather than
having to guess why something was built a particular way.

## 20. The final submission includes all required deliverables

**Not yet complete** — remaining before `v1.0-submission` can be tagged, and every remaining item
now needs a human decision or real credentials, not more code:
- Split into two cross-linked GitHub repos, or get lecturer confirmation a single repo is
  acceptable for this submission (A-008).
- Capture the live-view heatmap screenshot and the Replay-Viewer `Verified OK` screenshot for the
  submission checklist (Appendix C Table 6) — both are functionally proven to work in this session
  but the actual image artifacts haven't been captured.
- Send a real end-of-game report email (currently only exercised in `draft` mode, which is this
  project's deliberate safe default — see `docs/assumptions.md` A-005 for the parallel LLM-cost
  reasoning) to confirm the OAuth2 flow works against a real Google account.
- Fill in the real team roster (`group_name`/`group_id`/`members`) in `config/<role>/game.toml`,
  replacing development placeholders (A-012).
- Tag `v1.0-submission` once the above are done.

**Resolved since the previous revision of this audit**: the real GitHub commit hash is no longer a
manual step — `infra/vcs.py::current_commit_hash()` runs `git rev-parse HEAD` at runtime and
`peer_runtime.py` uses its result directly, satisfying Appendix F's mandatory rule 5 automatically.

## Exact commands used for this audit

```
uv sync
uv run ruff format --check .
uv run ruff check .
uv run mypy src
uv run pytest -q
uv run pytest --cov=src --cov-report=term-missing -q
uv run python -m police_thief --help
uv run python -m police_thief peer --help
uv run python -m police_thief replay --help
```

## Known limitations (repeated from README.md for completeness)

See `README.md` §9. In short: the two-repo split, submission screenshots, a real Gmail send test,
and the real team roster are the concrete remaining gaps, and every one of them needs a human, not
more code (tunneling was closed in an earlier pass — ngrok is now fully automated and unit-tested,
though not yet run against a real ngrok install or remote rival; FR-083's league audit and FR-087's
real commit hash were closed in this pass; both bonus AI brains, RL and LLM banter, are now
implemented and tested); everything else in the spec that this project claims to implement has a
passing automated test or a documented manual verification.
