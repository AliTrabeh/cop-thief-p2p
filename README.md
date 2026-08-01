# Police–Thief P2P

Distributed Cops-and-Robbers over a Peer-to-Peer Network — final project for the *AI Orchestration*
course (University of Haifa, 2026), per the lecturer's specification (`police_thief_p2p.pdf`,
kept out of this repo — see [Known Limitations](#known-limitations)).

> **Repository role: thief-owned.** Per the submission spec's two-repository requirement, this repo
> is the thief (robber) side. Cop-owned counterpart (same codebase and history, cross-linked):
> **https://github.com/AliTrabeh/cop-thief-p2p**

This README is the **academic report** required by the submission spec (not just install
instructions). Deep-dive documents live in [`docs/`](docs/); this file summarizes and links to them.

## 1. The Dec-POMDP model this project implements

The lecturer's spec frames the problem as a 2-agent **Dec-POMDP**
`⟨n, S, {Aᵢ}, P, R, {Ωᵢ}, O, γ⟩`: two sovereign agents (cop, thief) acting on a shared discrete
board, each with **partial observability** — neither agent ever sees the true objective board
state `S`, only its own position and a locally-derived belief about the other agent, built from a
pheromone-style scent trail (Chapter 4/6 of the spec).

This project implements:
- **State space** — a `grid_size × grid_size` board (default 7×7, negotiable upward), agent
  positions, barriers, move/barrier counters (`src/police_thief/domain/board.py`).
- **Action space** — 4-directional movement (N/S/E/W) + STAY for both agents, plus barrier
  placement for the cop (`src/police_thief/domain/models.py::Direction`,
  `strategy/base.py::BarrierAction`). Diagonal movement does not exist as a representable action
  at all (see `docs/assumptions.md` A-010).
- **Observation model `Ωᵢ`** — a per-agent scent/pheromone field (`domain/scent.py`) that decays
  each turn and is re-emitted at the depositing agent's current cell; each agent's belief
  `b(s) = P(opponent at s | scent received)` is a normalized posterior over this field
  (`scent.py::belief_map`), never the true opponent position.
- **Reward `R`** — the scoring table in `config/game.json → scoring`, matching the lecturer's
  mandatory parameters table exactly (capture/survival/tie/technical-loss point values).

See `docs/requirements_analysis.md` §1–4 and `docs/architecture.md` for the full mapping from the
spec's chapters to this codebase's modules, with numbered requirement IDs (FR-xxx/NFR-xxx) tracing
every implemented behavior back to a specific paragraph of the spec.

## 2. Peer-to-peer architecture: FastMCP and the tunneling trade-off

There is **no central server, judge, or shared game state**. Each side runs its own OS process,
each exposing a [FastMCP](https://gofastmcp.com/) tool server (`infra/mcp_server.py`) *and* acting
as an MCP client into the opponent's server (`infra/mcp_client.py`) — a symmetric P2P design, not a
disguised client-server one (`docs/architecture.md` §1, §9).

**Why FastMCP.** The spec requires the two peers to communicate via the Model Context Protocol,
reusing the same tool-calling substrate the course's earlier labs use for agent-to-agent
communication, rather than inventing a bespoke socket protocol.

**The tunneling trade-off.** For genuinely remote play (a real league match against another
group's machine), each side must expose its local FastMCP server publicly — the spec recommends a
local tunneling tool (ngrok / Localtonet) for NAT traversal. `infra/tunnel.py` automates **ngrok**
end-to-end (starts it, discovers the assigned public URL via ngrok's own local admin API, tears it
down on shutdown); for any other tool (Localtonet included, since its local API isn't something
this project could verify without guessing — see `docs/assumptions.md` A-018), set
`[tunnel].provider = "manual"` in `config/<role>/game.toml` and paste the public URL your tool gives
you into `manual_public_url`. `provider = "none"` (the default) skips tunneling entirely.
Localhost-only play (the two-terminal demo below) needs no tunnel at all.

**Why a real per-message session costs more than an in-process call.** Every `MCPPeerClient.send()`
opens a fresh MCP client session (initialize → notify → SSE → close) rather than reusing one
long-lived connection. This is simple and matches the Deadline Tracker's retry-per-call model
cleanly, but it means a real two-process game takes several seconds per turn (see
`docs/progress.md`'s Part 16 entry) — a documented, deliberate simplicity-over-latency trade-off,
not a bug.

## 3. Anti-cheat: Commit-Reveal over SHA-256

Every move is committed before it's revealed (`domain/crypto.py`, matching the spec's own reference
`commit()`/`verify()` code almost verbatim):

```
H_commit = SHA256(State ‖ Move ‖ Intent ‖ Nonce)
```

canonical JSON (`sort_keys=True`) so both peers hash byte-identical input; the nonce
(`secrets.token_hex(16)`) stays secret until the end of the game, when both sides reveal every
nonce (`orchestrator.py::produce_final_reveal`/`_receive_final_reveal`) and independently replay
the full log through `gui/replay_viewer.py::verify_step`/`replay`, producing `Verified OK` or
`TAMPERED` — never a blind trust of a centrally-issued hash. See `docs/protocol.md` §3 for the full
4-phase sequence diagram.

## 4. Strategy: the default heuristic (and how to plug in your own)

The shipped default (`strategy/heuristic.py`) is a deterministic policy over each agent's own
belief map: the cop moves to **minimize**, and the thief to **maximize**, the *expected* Manhattan
distance under the full belief distribution `E_{c~b}[dist(pos, c)]` — the Bayes-optimal single-step
action for that objective, not just distance to the single most-likely cell (`argmax_s b(s)`). That
distinction matters most exactly when it's cheap to get right and costly to get wrong: at the start
of a game, before any scent exists, belief is uniform and a plain argmax degenerately ties on the
agent's own start cell; the expected-distance policy instead moves purposefully toward the board's
center (minimizing/maximizing average distance to every cell), and converges to the same behavior
as a simpler heuristic once belief sharpens around the true position later in the game. The cop
additionally only spends a barrier once belief at the target cell is genuinely concentrated (not a
near-uniform guess), and the thief breaks near-ties in favor of staying away from board edges/
corners (more future escape routes against a cop trying to corner it). See
`strategy/heuristic.py`'s module docstring for the full reasoning and `tests/unit/test_strategy_expected_distance.py`
for the regression tests that lock in each fix. No reinforcement learning is used by default — the
spec explicitly frames RL as one optional tool among several, not a requirement
(`docs/requirements_analysis.md` §4, BONUS-001) — though a tabular Q-learning brain is available as
an opt-in, never-the-default alternative (`strategy/qlearning.py`).

**Pluggability.** `config/<role>/game.toml → [strategy]` points at any `package.module:Class`
subclassing `BrainBase` (see `docs/protocol.md` §6); the loader
(`strategy/base.py::load_brain_class`) validates the class before running it. This lets a rival
group swap in a smarter cop/thief brain — including an RL-trained one — without touching the
networking, crypto, or board layers at all.

**LLM usage.** Per the spec's own recommendation, an LLM (if configured at all) is only ever used
for free-text banter/trash-talk, never for the move decision itself. `strategy/llm_bluff.py`
implements two zero-cost providers — `template` (canned phrases, offline, the default) and `ollama`
(local self-hosted model, no per-token billing) — wired into `peer_runtime.py` so a game logs a
short in-character line after each own move, entirely outside the commit-reveal protocol. This
project's default `[llm].model = "template"` per `docs/assumptions.md` A-005, since the user's
standing instructions are to avoid consuming Anthropic API credits unless the spec explicitly
requires it — it doesn't; `claude_api`/`claude_cli` are deliberately left unimplemented for the same
reason (see Known Limitations).

## 5. Files changed / project structure

```
src/police_thief/
├── domain/        # deterministic game rules — board, scent, crypto, state machine (no I/O)
├── strategy/       # pluggable police/thief decision-making (BrainBase + heuristic)
├── infra/          # networking, rate limiting, reporting, Gmail (all the I/O)
├── gui/            # live belief-heatmap view + Replay Viewer
├── config.py        # config/game.json + config/<role>/game.toml loader
├── orchestrator.py   # the Single Gateway: state machine + crypto + strategy + protocol
├── peer_runtime.py   # wires config + Orchestrator + FastMCP into a runnable process
└── cli.py            # `python -m police_thief peer|replay`

config/            # real, working config (not just test fixtures)
scripts/           # PowerShell demo/test runners
tests/             # unit / network / integration / e2e
docs/              # requirements, architecture, protocol, plan, testing strategy, assumptions,
                   # traceability matrix, progress log, final audit, status board, PRD
```

Every module above with more than ~150 lines' worth of logic is actually split across several
same-purpose files (e.g. `orchestrator.py` + `orchestrator_turn.py` + `orchestrator_messages.py` +
`orchestrator_types.py`) — a project-wide 150-line-per-file convention. See `docs/architecture.md`
§2 for the exact current file map and `docs/progress.md` for the full, dated history of every
implementation part.

**Two more planning docs worth knowing about:** `docs/STATUS.md` gives a one-page, phase-by-phase
status board (18 implementation phases + 2 bonus phases, done/in-progress/not-started at a glance)
— the fastest way to answer "what's left." `docs/PRD.md` is the full product requirements document:
611 individually numbered, prioritized requirements (`PRD-0001`–`PRD-0611`) covering every subsystem
in more granular detail than the `FR-xxx`/`NFR-xxx` IDs in `docs/requirements_traceability.md`.

## 6. Running it

Requires Python 3.11+ and [`uv`](https://docs.astral.sh/uv/).

```powershell
uv sync
```

### Two-terminal demo (recommended — see it actually communicate over the network)

Terminal 1:
```powershell
.\scripts\run_police.ps1
```
Terminal 2:
```powershell
.\scripts\run_thief.ps1
```

Both peers bind to localhost (ports 8801/8802 by default, see `config/police/game.toml` and
`config/thief/game.toml`), play a complete game, write the four mandatory JSON deliverables to
`logs/<game-id>/`, and print the result. Add `--gui` to either script's underlying command
(`uv run python -m police_thief peer --role police --gui ...`) to see the live local-truth-only
belief heatmap.

### Single-terminal demo

```powershell
.\scripts\run_demo.ps1
```
Starts both peers as background jobs, waits for completion, and runs the Replay Viewer on the
resulting log automatically.

### Replay verification

```powershell
uv run python -m police_thief replay --log logs/<game-id>/police/log_<game-id>_g01.json
```
Prints `Verified OK` or `TAMPERED`.

### League audit (FR-083)

```powershell
uv run python -m police_thief audit --group-id my-team --logs-dir logs --config-dir config
```
Scans `logs/` recursively for this team's own `declaration_`/`result_<game_id>.json` pairs and
reports games played against `min_games_to_pass`/`max_games_per_team` from `config/game.json`.

### Tests

```powershell
.\scripts\run_tests.ps1          # fast subset (skips the ~1-minute real-subprocess e2e test)
.\scripts\run_tests.ps1 -Full    # everything, including the e2e test
```
or directly:
```powershell
uv sync
uv run ruff format --check .
uv run ruff check .
uv run mypy src
uv run pytest -m "not e2e" -v
uv run pytest --cov=src --cov-report=term-missing -m "not e2e"
uv run python -m police_thief --help
```

## 7. Testing strategy summary

218 tests across unit / network / integration / e2e (`docs/testing_strategy.md` for the full
breakdown): deterministic domain logic tested without I/O; FastMCP networking tested over its real
in-process transport (genuine protocol round trips, no sockets needed in CI); two full
two-orchestrator games (default heuristic brains, and separately the bonus Q-learning brains) tested
over that same real transport through to a cryptographically-verified `Verified OK` replay; and an
end-to-end test that spawns **two real OS subprocesses** communicating over real HTTP, confirming
they independently agree on the outcome and produce all four JSON deliverables.
Domain package coverage is 91–100% per module; overall ~84% (CLI/peer-runtime coverage isn't
captured by `coverage.py` across subprocess boundaries without extra plumbing — see
`docs/testing_strategy.md`).

## 8. Requirements traceability

Every requirement extracted from the lecturer's spec (functional, non-functional, protocol,
testing, documentation — `FR-xxx`/`NFR-xxx`/`PROTO-xxx`/`TEST-xxx`/`DOC-xxx`) is tracked in
`docs/requirements_traceability.md` against the module that implements it, the test that verifies
it, and its current status. `docs/assumptions.md` documents every place the spec was ambiguous,
internally inconsistent, or silent, and the interpretation chosen — including two internal
contradictions found in the source spec itself (games-per-rival count, capture-scoring numbers)
that are resolved there rather than silently picked one way.

## 9. Known limitations

- **Two-repository submission split not yet done.** The spec requires two separate GitHub repos
  (cop-owned, thief-owned), cross-linked. This project currently lives in one repository
  (`AliTrabeh/cop-thief-p2p`) for development convenience. See `docs/assumptions.md` A-008.
- **Tunneling is automated for ngrok only; not end-to-end tested against a real remote rival.**
  `infra/tunnel.py`'s ngrok automation is unit-tested with every external dependency faked (no real
  `ngrok` binary was available in this development environment); it hasn't yet been run against a
  real `ngrok` install or a genuinely remote opponent. Note that starting a tunnel exposes *this
  peer's own port* publicly — the discovered public URL still has to be given to your rival
  out-of-band (chat/email) so they can set it as *their* `opponent_url`; there's no automatic
  exchange of tunnel URLs between peers.
- **`claude_api`/`claude_cli` LLM banter providers are deliberately not implemented.**
  `strategy/llm_bluff.py` implements `template` (default, zero-cost, offline) and `ollama` (local,
  zero-cost) providers in full; requesting `claude_api`/`claude_cli` raises `NotImplementedError`
  immediately rather than silently spending real API credits by default (`docs/assumptions.md`
  A-005). This is a deliberate cost boundary, not a missing feature.
- **The bonus reinforcement-learning brain (`strategy/qlearning.py`) has not been benchmarked
  against the default heuristic.** It's implemented, tested for legality and for actually learning
  (a hand-verified TD update), and plugs into a real two-orchestrator game end to end — but no
  win-rate comparison against the heuristic brain has been run.
- **The lecturer's PDF is intentionally not in this repository** (copyrighted, "all rights
  reserved" — see `docs/assumptions.md` A-011); this README and `docs/` cite section/appendix
  numbers instead of reproducing the text.
- **What's left before `v1.0-submission` is now entirely human steps, not missing code**: the
  live-view/Verified-OK screenshots for the submission checklist, a real (non-draft) Gmail send
  test against a live account, the real team roster in `config/<role>/game.toml`, and a decision on
  the two-repository split. See `docs/STATUS.md` Phase 18 for the exact, current list.
