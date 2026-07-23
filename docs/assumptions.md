# Assumptions & Ambiguity Resolutions

The lecturer's PDF is the primary source of truth (see `docs/requirements_analysis.md`). Per the
book's own stated convention, **Appendix F (the mandatory parameters table) is the single binding
source for every numeric/config value**; everything else is illustrative. Where the book is
ambiguous, internally inconsistent, or silent, this document records the interpretation chosen and
why, so it can be revisited easily.

---

### A-001 — Scoring-table numbers: §3.5 walkthrough vs. Appendix F Table 17

§3.5 Table 2 illustrates scoring with capture/survival point placeholders while narratively
discussing symmetry; Appendix F Table 17 gives the authoritative fixed values (capture_cop=20,
capture_thief=5, survival_cop=5, survival_thief=10, tie=2, technical_loss=0). **Decision:** Table 17
values are used everywhere in code and config; §3.5 is treated as narrative motivation only.

### A-002 — Games-per-rival: "one counted game" (Appendix E, item 52) vs. "6 games, Fixed" (Appendix F, Table 18 #1)

Appendix E's cross-check list states each rival pair plays exactly one *counted* game (extra
games permitted but not scored, to prevent score inflation). Appendix F Table 18 states the number
of games in a series vs. one rival is 6 (Fixed). The example `config/game.json` in Appendix B ships
with `"num_games": 1` and its accompanying prose explicitly resolves this: `num_games` is described
as exempt from the general per-field negotiation rule and as **overridden by the league's actual
game-count requirement** (§9) — the `1` in the example JSON is a schema-demonstration placeholder,
not the real mandated value.
**Decision:** treat Appendix F Table 18 (`num_games = 6`, Fixed) as authoritative for a real league
series; `config/game.json`'s `network_and_league.num_games` field defaults to `6` in this project,
with `1` reserved only for local single-game smoke-testing/demo runs (explicitly labeled as such).

### A-003 — Board size vs. start-position pairing

§3.3 states board size and start points are drawn from a small set of pre-validated combinations
(not arbitrary), giving the formula relating grid size to start-corner distance, and shows
`7×7 → thief [3,3], cop [0,0]` as the running example (matching the Appendix B JSON sample and
Appendix F Table 13 defaults). **Decision:** ship `7×7 / thief[3,3] / cop[0,0]` as this project's
default `config/game.json`, since it is both the Table 13 default and the only fully-worked example
in the book. Larger boards (e.g. negotiated up from the Table 13 *Minimum* of 7×7) must keep
`cop_start`/`thief_start` symmetric per the same rule; the board module validates this at load time
rather than hardcoding only 7×7.

### A-004 — `num_games` status classification

Table 18 marks `num_games` "Fixed", yet the book calls out cop/thief `[network_and_league]` values
as generally negotiable-with-a-floor. **Decision:** treat every Table 18 row exactly as labeled
(mostly Fixed) — Fixed rows are validated at config-load time and any deviation is treated as a
technical failure per E-19-style disqualification logic, consistent with "Fixed = must not change
at all; deviation disqualifies."

### A-005 — LLM API cost tier

The book offers four LLM modes (`template`, `ollama`, `claude_api`, `claude_cli`) with `claude_api`
and `claude_cli` explicitly billed. The user's standing project instructions say: do not
intentionally use the Anthropic API or consume API credits, and do not add a required
`ANTHROPIC_API_KEY` dependency, unless the spec explicitly requires it. The spec does not require
any specific mode — `template` is the documented zero-cost default fallback.
**Decision:** this project's default `[llm].provider` is `template` (and `ollama` as the
recommended free upgrade path if a local model is available). `claude_api`/`claude_cli` are
implemented as optional, disabled-by-default provider plugins for completeness/extensibility, never
exercised in default config, CI, or the local two-peer demo.

### A-006 — Watchdog timeout value

§8.4.2's worked code sample uses `timeout_sec=180` as an illustrative default; Appendix F Table 19
gives `watchdog_timeout_sec = 60` (Negotiable) as the binding default. **Decision:** config default
is 60s (Table 19); the code sample's 180s is not used.

### A-007 — Hardware/Step-0 fairness enforcement

§5.5 requires a Step-0 hardware/software declaration but explicitly leaves normalization of
cross-hardware performance differences as a human/manual judgment call, not something the code
enforces algorithmically. **Decision:** the project emits a machine-readable Step-0 declaration
JSON (OS, CPU core count, RAM, GPU/VRAM if present, model versions) as a deliverable, but does not
attempt automatic fairness scoring — this is intentionally out of scope, matching the book.

### A-008 — Two-repo submission vs. this single dev repository

Appendix C mandates two separate GitHub repos (one "owned" by the cop side, one by the thief side)
per submitting group, cross-linked. During development this project lives in a single repository
(`AliTrabeh/cop-thief-p2p`) for convenience of iteration by one contributor.
**Decision:** documented as a known gap to close before final submission — either (a) split into
two repos late in the process (e.g. via `git subtree`/mirrors) once both peer packages are stable,
or (b) confirm with the lecturer whether a single shared-access repo satisfies the "two accesses,
cross-linked" requirement for a solo/duo submission. Tracked in `docs/progress.md` and the final
audit; not blocking early implementation phases.

### A-009 — Barrier count vs. move count vs. board size interaction

The book does not specify what happens if `max_barriers` or `max_moves` are negotiated far beyond
the board's cell count (e.g. barriers ≥ free cells). **Decision:** validate at config-load time that
`max_barriers < grid_size² − 2` (leaving room for both agents and at least one free path), raising a
config-validation error rather than silently clamping — matches the book's "no external judge, code
enforces the constitution" philosophy (§3.2).

### A-010 — Diagonal/8-neighbor movement

The working instructions' generic template mentions diagonal/8-neighbor movement as something
"if required by the PDF, implement exactly." The PDF explicitly forbids diagonal movement (E-13/
E-14, "no alkasonim" iron rule). **Decision:** 4-directional + STAY only; diagonal movement is not
implemented at all (not even as a disabled option), since the book treats it as a hard technical
rule, not a configurable game variant.

### A-011 — The lecturer's PDF is not committed to the repository

The PDF is marked "© Dr. Segal Yoram — כל הזכויות שמורות" (all rights reserved). Redistributing the
full copyrighted course text inside a (possibly public) GitHub repo risks a copyright issue and is
not requested by any deliverable in the spec (the deliverables reference *content from* the book,
not the book itself). **Decision:** `.gitignore` excludes `police_thief_p2p.pdf`; the repo instead
cites section/appendix numbers in `docs/requirements_analysis.md` and this file. If the lecturer
requires the PDF itself to be attached, it can be added to a private submission channel outside
Git, or the user can confirm redistribution is permitted and this decision can be reversed.

### A-012 — Single-contributor project

The working instructions describe a team ("every team member", "credit to all members"). This
session has one user/contributor. **Decision:** team-identity fields (`group_name`, `members`) in
`config/game.toml` are populated with placeholder/single-member values the user can edit before
a real league match; not a blocker for implementation.
