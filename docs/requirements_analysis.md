# Requirements Analysis — Police–Thief P2P (AI Orchestration Final Project)

Source of truth: `police_thief_p2p.pdf` ("מרוץ שוטר-גנב מבוזר ברשת עמיתים", Dr. Segal Yoram,
University of Haifa, AI Orchestration course, 2026, book version 3.0.0 / demo code version 3.0.0).
Kept local-only (copyrighted, not redistributed — see `docs/assumptions.md` A-011).

Every requirement below has a stable ID. IDs are referenced from `requirements_traceability.md`,
`architecture.md`, and code docstrings/tests where relevant. Per the book's own stated convention
(Foreword, "מה מחייב ומה רק ממחיש"): **only Appendix ו (F), the mandatory parameters table, binds
numeric/config values.** Everything else in the book (figures, worked examples, e.g. the 10×10
belief-map illustration in §6.4, the 7×7 arena figure in §3.3) is illustrative unless restated as a
MUST/FORBIDDEN rule in Appendix ה (E) or a Fixed/Minimum/Negotiable row in Appendix ו (F). This
document tags every requirement with its binding status.

Legend: **[MUST]** binding rule (Appendix E numbering preserved as E-##), **[FIXED]**/**[MIN]**/
**[NEG]** = Appendix F status column, **[REC]** recommended/non-binding, **[ILLUS]** illustrative
example only.

---

## 1. Functional Requirements — Process & Distribution Model

- **FR-001** [MUST, E-1/E-2] Cop and thief run as two fully independent OS processes. No shared
  memory, shared files, or shared Python objects between them, ever — not even for testing. Source:
  §2.2, §2.4.2 (mandatory separation box), Appendix E items 1–2.
- **FR-002** [MUST, E-3] The project exposes a defined package entry point / sub-package structure
  usable by the grader (`python -m police_thief ...`). Source: Appendix D run commands, E-3.
- **FR-003** [MUST, E-4/E-5] Game states are managed by an explicit state machine; any transition
  not in the transition table is rejected (`ValueError`). Source: §8.3, E-4/E-5.
- **FR-004** [MUST, E-6/E-7] A timeout mechanism (Deadline Tracker) prevents indefinite waiting on
  the peer; a Watchdog process detects a stuck/frozen local main loop. Source: §8.4, E-6/E-7.
- **FR-005** [MUST/FORBIDDEN, E-8/E-9] The human-facing live GUI shows **only** the local peer's
  true state (own position + own belief map); it must **never** render the full objective board
  state (`S` from the Dec-POMDP tuple). Source: §7.2 "Local Truth" box, E-8/E-9.
- **FR-006** [MUST, E-10] A local tunneling tool (ngrok / Localtonet) exposes each peer's local
  FastMCP server on a public URL so remote rivals can connect (NAT traversal). Source: §2.4.1, E-10.

## 2. Functional Requirements — Board, Movement, Barriers

- **FR-010** [MIN=7×7, Table 13 #1] Board size, configurable, minimum 7×7. Loaded from
  `config/game.json → board_and_agents.grid_size`, never hardcoded (FR-010 ⇒ NFR-005). Source §3.3.
- **FR-011** [FIXED=2, Table 13 #2] Exactly two agents (one cop, one thief).
- **FR-012** [NEG] Row-major coordinate system; first index corner and axis start index are
  negotiable per Table 13 #3–#4 (defaults: top-left corner, index 0).
- **FR-013** [NEG, Table 13 #5–#6] Thief start position (default center) and cop start position
  (default a corner) are negotiable but must be symmetric distances from any corner (§3.3 formula:
  `4·(row+col) = grid_size² − 1`... i.e. board-size/start-point pairs are pre-validated combinations,
  not arbitrary — see `config/game.json` example: 7×7 board ⇒ thief [3,3], cop [0,0]).
- **FR-014** [FIXED, Table 15 #1; MUST/FORBIDDEN E-13/E-14] Movement is strictly 4-directional
  orthogonal (N/S/E/W) plus STAY; diagonal movement is forbidden and must be rejected by code, not
  merely discouraged. Source: §3.4 "חוק המחסום"/"חוקי ברזל", E-13/E-14.
- **FR-015** [MIN=14, Table 15 #2] The cop may place at most `max_barriers` barriers over a game
  (minimum 14). A barrier occupies one orthogonally-adjacent cell to the cop's current position at
  placement time. Source §3.4.
- **FR-016** [MUST/FORBIDDEN, E-15/E-16] Barrier placement must be announced publicly and
  immediately (recorded in the shared log for audit); lying about barrier placement is forbidden and
  automatically detectable via log/board-state cross-check.
- **FR-017** [MIN=35, Table 15 #3–#4] Maximum 35 total moves per game; the thief is declared winner
  (by survival) after surviving 35 of its own steps without capture. Source §3.5, Table 15.
- **FR-018** [MUST, E-46/E-47/E-48] Capture conditions (from the scoring/win table, §3.5, and
  Appendix E cross-check items): (a) cop moves onto the thief's cell and truthfully files a Capture
  Claim; (b) a barrier is placed on the thief's current cell ("cornered"); (c) the thief fails to
  make a legal move when required by the rules. All three are scored as a successful capture.

## 3. Functional Requirements — Scoring

- **FR-020** [FIXED, Table 17] Scoring values, loaded from `config/game.json → scoring`, never
  hardcoded: capture (cop=20, thief=5), survival (cop=5, thief=10), tie=2, technical_loss=0.
  Source §3.5 Table 2 (illustrative walk-through) reconciled against Appendix F Table 17
  (authoritative values — see `docs/assumptions.md` A-001 for the reconciliation).
- **FR-021** [MUST] A side that incurs a technical disqualification (crypto mismatch, illegal state
  transition, protocol violation, false capture/barrier claim) scores 0 regardless of in-game
  performance. Source §3.5, §5.3.2, E-19/E-22.

## 4. Functional Requirements — Scent / Pheromone Belief Model

- **FR-030** [FIXED, Table 16] Emission/decay model, loaded from config, never hardcoded:
  `τ_ij(t+1) = max(0, (1−ρ)·τ_ij(t) + Δτ_ij)`, deposit intensity 0.9, decay rate ρ=0.10 per full
  turn, 5×5 emission field around the depositing agent. Source §4.3.
- **FR-031** [MUST, E-23] Scent-model parameters are fixed **before** game start (Step-0) and must
  not change mid-game.
- **FR-032** [ILLUS→REC] Each side maintains a private Bayesian belief map `b(s) = P(thief=s | hints)`
  over the opponent's likely position, updated from received scent/hints only — never from the true
  board state. The book's own worked examples (§4.4, §6.4) use a Manhattan-distance heuristic over
  `argmax_s b(s)` as the default/illustrative decision rule; this is a recommended baseline
  (`BrainBase`), not a mandated algorithm (§6.2, §6.3.1 "two equal alternatives without RL").
- **FR-033** [REC] Optional reinforcement-learning strategy module (single-agent Q-learning with
  ε-greedy, Bellman update) may replace the heuristic; not required. Source §6.3.

## 5. Functional Requirements — Cryptographic Anti-Cheat Protocol

- **FR-040** [MUST, E-17] Commit-Reveal protocol over SHA-256 is mandatory for every move.
  `H_commit = SHA256(State ‖ Move ‖ Intent ‖ Nonce)`, canonical JSON payload
  (`json.dumps(..., sort_keys=True, separators=(",", ":"))`) so both peers hash byte-identical
  input. Source §5.3, code sample p.36–37.
- **FR-041** [MUST, E-18] The nonce is generated via `secrets.token_hex(16)` (cryptographically
  secure, never `random`) and kept secret until the per-turn Reveal step.
- **FR-042** Protocol steps, 4-phase: (1) Commit — send `H_commit` only; (2) Acknowledge — opponent
  confirms receipt/lock; (3) Reveal — send Move + Hint (nonce still hidden); (4) Final Reveal /
  Audit — at game end, all nonces are revealed for full retroactive verification. Source §5.3.2,
  Figure 6 sequence diagram.
- **FR-043** [MUST, E-19] Any commit/reveal mismatch on verification (`verify()` /
  `secrets.compare_digest`) is a hard technical disqualification — score 0, no appeal, logged as
  `TAMPERED`.
- **FR-044** [MUST, E-20/E-21/E-22] Hints are recorded for later audit; capture claims and barrier
  claims are declared truthfully only at the moment of the claim; false claims are forbidden and
  void the move / trigger disqualification.
- **FR-045** [MUST] End-of-game mutual audit: each side replays the full log, recomputes SHA-256 for
  every step, and independently reaches "Verified OK" — this must not be blind trust of a
  centrally-issued hash. Source §5.4, §7.4/§7.5 (Replay Viewer `verify_step`/`replay` code).

## 6. Functional Requirements — Networking / P2P Transport

- **FR-050** [MUST] Each peer runs FastMCP as **both** an MCP server (exposing `@mcp.tool` functions,
  e.g. `receive_move`) and an MCP client (calling the opponent's exposed tools). No central relay.
  Source §2.3, code sample p.12.
- **FR-051** [MUST] Every incoming tool call cryptographically verifies the sender's signature/commit
  before being accepted as a legal move; unverified moves are never trusted. Source §2.3.2 code
  sample.
- **FR-052** State machine (Orchestrator-owned) transitions:
  `WAITING_FOR_OPPONENT → COMPUTING_MOVE → COMMITTING → AWAITING_REVEAL → {VERIFYING | TECHNICAL_LOSS}
  → WAITING_FOR_OPPONENT`, with `TECHNICAL_LOSS` reachable (dashed transitions) from
  `COMPUTING_MOVE`, `AWAITING_REVEAL`, and `VERIFYING` on any rule violation. `TECHNICAL_LOSS` is
  terminal. Source §8.3, Figure 11 + transition-table code sample.
- **FR-053** [MUST] Deadline Tracker: every FastMCP request carries a timestamp + expiry deadline; on
  timeout, retry per a fixed policy, then report technical-loss on repeated failure. Never block
  indefinitely on an unresponsive peer. Source §8.4.1.
- **FR-054** [MUST] Watchdog: monitors the local main loop's heartbeat; on staleness beyond
  `watchdog_timeout_sec`, persists state and performs a controlled shutdown (never a silent crash).
  Source §8.4.2, code sample p.67.
- **FR-055** [MIN, Table 19] Gatekeeper rate-limiting pipeline (Quota Manager → Token-Bucket limiter
  → DOS Detector) guards all outgoing calls (Gmail API, and recommended for the MCP tool endpoint
  too). Token-bucket update rule: `tokens ← min(C, tokens + r·Δt)`, allow iff `tokens ≥ 1`. Source
  §9.3.1–9.3.2, Figure 13/14.

## 7. Functional Requirements — Strategy Modules

- **FR-060** [MUST, E per §6.2] Strategy is a pluggable module, selected via the private
  `config/game.toml → [strategy]` section: `thief_class` / `police_class` in
  `package.module:Class` form, subclassing `BrainBase`/`ThiefBrain`, overriding `_pick_move` (and
  `_decide_move` for the thief's barrier-avoidance choice). Empty ⇒ default heuristic runs.
  Source §6.2, Appendix F Table 22.
- **FR-061** [REC, E-25] The LLM should not be fed the move-decision itself — only used for
  free-text banter/hint generation — to avoid hallucinated/illegal moves; this is a recommendation,
  not a hard rule, but violating it carries a real correctness risk the book flags explicitly.
- **FR-062** [MUST/FORBIDDEN, E-26/E-27] Any language-model output is confined to free-text banter
  channels; it is forbidden to use the "language" channel for anything beyond text (i.e., it can
  never carry protocol/move data).
- **FR-063** [FIXED options, Table 21] LLM modes: `template` (offline phrase bank, 0 tokens,
  default fallback), `ollama` (local, no API cost), `claude_api` (Anthropic API, billed — Haiku
  recommended), `claude_cli` (Claude Code CLI subscription, highest cost tier). `every_n_steps`
  throttles LLM calls. Source §6.5, Table 21. **Per the user's explicit standing instruction: do not
  use the Anthropic API / consume API credits unless required — default this project's `[llm]`
  config to `template` or `ollama`, never `claude_api`.**
- **FR-064** [NEG=15, Table 14 #2] Hint/banter word limit, default 15 words/turn.

## 8. Functional Requirements — GUI / Replay / Observability

- **FR-070** [MUST] Live GUI (Tkinter or equivalent) renders: own true position, own belief heatmap
  (color intensity ⇒ posterior probability), and a turn banner (`YOUR TURN` / `LOCKED`) synced to
  the local state machine — never the opponent's or the objective board. Source §7.3.
- **FR-071** [MUST, E per §7.4] A Replay Viewer is a mandatory deliverable: it loads the final game
  log (e.g. `logs/police_match.json`), replays every recorded step, recomputes each commitment
  hash, and stamps `Verified OK` (green) or `TAMPERED` (red, disqualifying) — using the game's own
  commit-reveal verification, not a blind central trust mechanism. Source §7.4–7.5, Figure 10.
- **FR-072** [MUST] A screenshot of the belief-map Live GUI and a screenshot of the Replay screen
  showing `Verified OK` are required submission artifacts (Appendix C Table 6).

## 9. Functional Requirements — Reporting, League, Submission

- **FR-080** [MUST, E-28/E-30] Gmail API integration is OAuth2, send-only scope
  (`gmail.send` only — least privilege), rate-limited via the Gatekeeper pipeline. Source Appendix A,
  §9.3.1, E-28/E-30.
- **FR-081** [MUST, E-32/E-34/E-35] At game end, each side automatically emails a structured JSON
  completion report (never free text) to the lecturer's address; both sides send independently;
  conflicting reports about the same game ⇒ 0 to both. Source §9.3, E-32/34/35.
- **FR-082** [Files, Table 20] Four mandatory per-match JSON deliverables:
  `declaration_<game_id>.json` (pre-game: groups, members, repos, model, timestamps),
  `config_<game_id>_g<NN>.json` (agreed game-parameter snapshot),
  `log_<game_id>_g<NN>.json` (full crypto-auditable game log),
  `result_<game_id>.json` (final outcome for league scoring). All share `game_uid`; `game_id` never
  reused across different matchups.
- **FR-083** [MUST, E-36/E-37/E-38] Mutual daily-log audit before final scoring; games-played count
  verified at the start of every game; lying about games-played count is forbidden.
- **FR-084** [FIXED=6 per rival / MIN=2 pass / FIXED≤10 total, Table 18] League counters: 6 games per
  rival pairing (fixed), diversity reward 10 (fixed) for beating a new rival, minimum 2 games played
  for a passing grade, maximum 10 games per group. Reconciled with the "one counted game per rival"
  language in the cross-check appendix — see `docs/assumptions.md` A-002.
  Token budget per series ≈200,000 (negotiable), must be reported by email.
- **FR-085** [MUST, E-39/E-40] Never leak secrets/credentials, even unilaterally; `.gitignore` must
  exclude `credentials.json`, `token.json`, and any per-peer "secret constitution" data.
- **FR-086** [MUST, E-41/E-49/E-50] Submission is frozen via an annotated git tag
  `v1.0-submission` (not "last commit on main"); two GitHub repos (cop, thief) per group,
  cross-linked (each README links to the other repo — 4 links total across both groups' JSON);
  each repo contains README.md (academic report), `config/`, a PRD file, a PLAN file, and TODO
  files.
- **FR-087** [MUST, E-53] The signed declaration's commit-hash field must be updated to match the
  actual GitHub commit used, every game (code may change between games).
- **FR-088** [MUST, E-44/E-45] Every team member has access/credit on the repos; the team uses a
  unique, space-free identity name (for automated league-report parsing).

## 10. Non-Functional Requirements

- **NFR-001** Deterministic core game logic (board, movement, scoring, crypto) is fully isolated
  from networking and UI code — unit-testable without sockets or a GUI.
- **NFR-002** Windows-compatible (`pathlib`, no POSIX-only assumptions); developed and demoed on
  Windows 11 / Python 3.13.
- **NFR-003** Graceful shutdown and resource cleanup: MCP connections closed, logs flushed, on both
  normal game-over and Watchdog-triggered shutdown.
- **NFR-004** Structured logging, configurable verbosity, secrets never logged.
- **NFR-005** [MUST, E-12] No hard-coded board dimensions, network addresses, ports, or scoring
  constants — all loaded from `config/game.json` (shared, signed) / `config/game.toml` (private).
- **NFR-006** [MUST, E-29] DoS-defense guard on the FastMCP tool endpoint (payload size limits,
  request-type allow-list) in addition to the Gmail-side Gatekeeper.
- **NFR-007** [MUST, E-24] Step-0 computational-fairness declaration: hardware/OS/model spec
  published as JSON before the game series starts, normalized reasoning about compute differences
  is out of scope for automated enforcement (human/manual check). Source §5.5.
- **NFR-008** [MUST, E-11] Both sides' shared config file must be byte-identical (verified via a
  hash of `config/game.json`), i.e. a symmetric, cryptographically-locked contract.

## 11. Protocol Requirements

- **PROTO-001** Config schema is versioned (`schema_version` field in `config/game.json`,
  e.g. `"1.2"`) for quick recognition across game series.
- **PROTO-002** Canonical JSON serialization for every hashed payload:
  `json.dumps(obj, sort_keys=True, separators=(",", ":"))`.
- **PROTO-003** FastMCP tool surface (minimum): a move-submission tool (`receive_move` or
  equivalent) that accepts `(signed_move, signature)` and returns `{"accepted": bool, "move": ...}`,
  never trusting an unverified payload.
- **PROTO-004** Message content aligns to the 4-phase commit-reveal sequence (§5.3.2): Commit →
  Acknowledge → Reveal → Final Reveal/Audit.

## 12. Testing Requirements

See `docs/testing_strategy.md` for the full breakdown; summary IDs:
- **TEST-001** Unit: board/movement/barrier/capture legality, scoring table, config loading/
  validation.
- **TEST-002** Unit: scent emission/decay formula, belief-map update.
- **TEST-003** Unit/Protocol: commit/verify round-trip, tamper detection, canonical-JSON stability.
- **TEST-004** Protocol: state-machine transition table (legal + illegal transitions rejected).
- **TEST-005** Networking: FastMCP tool call success/failure/timeout/malformed payload, Gatekeeper
  token-bucket behavior.
- **TEST-006** Integration: two local peer processes complete a full game via real FastMCP+tunnel-
  free localhost transport, end with a mutually-verified `Verified OK` replay.
- **TEST-007** E2E: CLI-driven two-peer demo script produces all four JSON deliverables and a
  correct winner.

## 13. Documentation & Deliverable Requirements

- **DOC-001** README.md per repo = academic report (Appendix C §2 required contents: Dec-POMDP
  model description; FastMCP/tunneling tradeoffs; strategy explanation incl. RL if used; belief-map
  and GUI screenshots; Verified-OK replay screenshot; link to partner repo).
- **DOC-002** Mermaid diagrams: component diagram, P2P message sequence, game state machine, turn
  flow, failure-handling flow.
- **DOC-003** `docs/progress.md` updated per implementation part (date, files changed, requirements
  covered, tests run/results, remaining issues).
- **DOC-004** `docs/final_audit.md` per the 20-point audit in the working instructions, cross-
  referenced against this traceability table.
- **DOC-005** Submission checklist (Appendix C Table 6 + Appendix H checklist, §11.5) satisfied
  before tagging `v1.0-submission`.

## 14. Bonus / Optional

- **BONUS-001** Reinforcement-learning strategy module (Q-learning, §6.3) — optional, not required
  for a passing grade.
- **BONUS-002** `claude_cli`/`claude_api` LLM modes for richer banter — optional, higher cost tier;
  **not adopted by default** per the user's standing instruction to avoid Anthropic API credit
  usage; `template` is this project's default.

## 15. Grading Criteria (Four Metrics of Success, §11.4, Table 4)

1. **Coordination** — P2P protocol management, FastMCP, turn sync between two sovereign peers
   without a central judge.
2. **Adaptation** — symmetric belief-map construction from scent + hints under partial
   observability.
3. **Integrity** — no false capture claims; Commit-Reveal + SHA-256 + full end-of-game audit.
4. **Architecture** — Gatekeeper/Orchestrator separation of concerns; code that stays maintainable
   under change.

Code-quality points are scored separately and **must not** affect league match outcome (E-55).
