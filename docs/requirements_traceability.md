# Requirements Traceability Matrix

Status legend: **Planned** (design complete, no code yet) · **In Progress** · **Implemented**
· **Tested** · **Verified** (implemented + tested + manually confirmed working).

This table is updated at the end of every implementation part (see `docs/implementation_plan.md`)
and every entry in `docs/progress.md`.

| Req ID | Module | Test(s) | Status | Docs |
|---|---|---|---|---|
| FR-001 | process boundary: `cli.py`/`peer_runtime.py` (two independent OS processes, separate `config/<role>/`) | `tests/e2e/test_two_peer_local_game.py` (spawns two real OS subprocesses) | Tested | architecture.md §2/§9 |
| FR-002 | `cli.py`, `src/police_thief/__main__.py` | `--help` smoke; exercised by every e2e/manual run | Tested | implementation_plan.md Part 1 |
| FR-003 | `domain/state_machine.py` | `tests/unit/test_state_machine.py` | Tested | architecture.md §5 |
| FR-004 | `infra/mcp_client.py` (Deadline Tracker: timeout+retry+`wait_until_reachable`), `infra/watchdog.py` (Watchdog) | `tests/network/test_mcp_transport.py`, `tests/unit/test_watchdog.py` | Tested | architecture.md §7 |
| FR-005 | `gui/live_view.py::render_grid` (GUI, primary requirement); the same local-truth boundary is also enforced in `strategy/base.py::BeliefView`/`build_belief_view` | `tests/unit/test_live_view_render.py`, `tests/unit/test_strategy.py::test_thief_brain_never_sees_the_cops_true_position_directly` | Tested | architecture.md §7 |
| FR-006 | `infra/tunnel.py` (`start_ngrok_tunnel`/`start_tunnel`/`TunnelHandle`), wired into `peer_runtime.py` via `config/<role>/game.toml → [tunnel]`; ngrok fully automated, Localtonet/other tools via `provider="manual"` (assumptions.md A-018) | `tests/unit/test_tunnel.py` (11 tests, all external deps injected/faked — no real ngrok binary needed) | Tested | architecture.md §1/§4, assumptions.md A-018 |
| FR-010 | `domain/board.py`, `domain/models.py` | `tests/unit/test_board.py` | Tested | requirements_analysis.md §2 |
| FR-011 | `domain/models.py` | `tests/unit/test_board.py` | Tested | " |
| FR-012 | `domain/models.py` | `tests/unit/test_board.py` | Tested | " |
| FR-013 | `domain/models.py` | `tests/unit/test_board.py` | Tested | assumptions.md A-003 |
| FR-014 | `domain/board.py` | `tests/unit/test_board.py` | Tested | assumptions.md A-010 |
| FR-015 | `domain/board.py` | `tests/unit/test_board.py` | Tested | " |
| FR-016 | `domain/board.py` (barrier legality itself); public announcement/log recording is implicit in `orchestrator.py`'s REVEAL message (every barrier placement is revealed, never silent) | `tests/unit/test_board.py`, `tests/unit/test_orchestrator.py` | Implemented | architecture.md §6 |
| FR-017 | `domain/board.py` | `tests/unit/test_board.py` | Tested | " |
| FR-018 | `domain/board.py` | `tests/unit/test_board.py` | Tested | requirements_analysis.md §2, assumptions.md A-013 |
| FR-020 | `domain/scoring.py`, `domain/models.py` | `tests/unit/test_scoring.py` | Tested | assumptions.md A-001 |
| FR-021 | `domain/scoring.py`; full wiring in `orchestrator.py` (Part 9) | `tests/unit/test_scoring.py` | Tested (scoring fn) / Planned (end-to-end) | assumptions.md A-014 |
| FR-030 | `domain/scent.py` | `tests/unit/test_scent.py` | Tested | requirements_analysis.md §4, assumptions.md A-015 |
| FR-031 | `domain/models.py` (PheromoneConfig is fixed-at-parse; no mid-game mutation path exists) | `tests/unit/test_scent.py` | Implemented | " |
| FR-032 | `domain/scent.py` (belief_map/most_likely_position); `strategy/heuristic.py` (default brains) | `tests/unit/test_scent.py`, `tests/unit/test_strategy.py` | Tested | " |
| FR-033 | `strategy/qlearning.py` (optional) | — | Planned (bonus) | " |
| FR-040 | `domain/crypto.py` | `tests/unit/test_crypto.py` | Tested | protocol.md §3 |
| FR-041 | `domain/crypto.py` | `tests/unit/test_crypto.py` | Tested | " |
| FR-042 | `orchestrator.py` (produce_commit/produce_reveal/confirm_reveal_accepted) | `tests/unit/test_orchestrator.py`, `tests/integration/test_two_peer_game.py` | Tested | protocol.md §3 |
| FR-043 | `domain/crypto.py`; DQ wiring in `orchestrator.py::_fail` | `tests/unit/test_crypto.py`, `tests/unit/test_orchestrator.py` | Tested | " |
| FR-044 | `domain/board.py` (capture/barrier outcomes are derived automatically from real board state, never self-reported by either side, which structurally prevents a false claim per E-22 rather than detecting one after the fact) | `tests/unit/test_board.py`, `tests/integration/test_two_peer_game.py::test_capture_is_detected_symmetrically_by_both_sides` | Implemented (by construction) | " |
| FR-045 | `orchestrator.py` (produce_final_reveal/_receive_final_reveal/export_log), `gui/replay_viewer.py` (verify_step/replay) | `tests/unit/test_replay_viewer.py`, `tests/integration/test_two_peer_game.py` | Tested | architecture.md §7 |
| FR-050 | `infra/mcp_server.py` (build_server/submit_message), `infra/mcp_client.py` (MCPPeerClient) | `tests/network/test_mcp_transport.py` | Tested | protocol.md §1 |
| FR-051 | `infra/mcp_server.py` (schema validation + sequence tracking; signature verification wiring is Part 9) | `tests/network/test_mcp_transport.py` | Implemented (schema/sequence) / Planned (signature check) | " |
| FR-052 | `domain/state_machine.py`; wired into `orchestrator.py` | `tests/unit/test_state_machine.py`, `tests/unit/test_orchestrator.py` | Tested | architecture.md §5 |
| FR-053 | `infra/mcp_client.py` (MCPPeerClient timeout+retry) | `tests/network/test_mcp_transport.py::test_unreachable_peer_raises_after_retries` | Tested | architecture.md §7 |
| FR-054 | `infra/watchdog.py` | `tests/unit/test_watchdog.py` | Tested | " |
| FR-055 | `infra/gatekeeper.py` (TokenBucket/QuotaManager/DOSDetector/Gatekeeper) | `tests/unit/test_gatekeeper.py` | Tested | architecture.md §7 |
| FR-060 | `strategy/base.py` (BrainBase/ThiefBrain/PoliceBrain, build_belief_view), `strategy/heuristic.py` (default brains) | `tests/unit/test_strategy.py` | Tested | protocol.md §6, assumptions.md A-016 |
| FR-061 | `strategy/llm_bluff.py` (Part 8) | `tests/unit/test_strategy.py` | Planned | assumptions.md A-005 |
| FR-062 | `strategy/llm_bluff.py` (Part 8) | — | Planned | " |
| FR-063 | `strategy/llm_bluff.py` (Part 8) | — | Planned | " |
| FR-064 | `domain/models.py::WorldConfig.hint_max_words` | `tests/unit/test_board.py` (config validation) | Implemented | " |
| FR-070 | `gui/live_view.py` (render_grid/belief_to_color/turn_banner_*, `LiveView` Tkinter widget), wired via `peer_runtime.py`'s `--gui` flag | `tests/unit/test_live_view_render.py` (render logic); real widget smoke-tested manually (needs a display) | Tested (logic) / Implemented (widget) | architecture.md §1 |
| FR-071 | `gui/replay_viewer.py` (verify_step/replay/load_log/verify_log_file) | `tests/unit/test_replay_viewer.py`, `tests/integration/test_two_peer_game.py` | Tested | " |
| FR-072 | `gui/live_view.py` (Implemented); `gui/replay_viewer.py` (Tested) | manual screenshot pending for the final submission | Implemented (functionality) / Planned (screenshot artifact) | docs/final_audit.md (future) |
| FR-080 | `infra/gmail_report.py` (send-only scope, Gatekeeper-guarded) | `tests/unit/test_gmail_report.py` | Tested | protocol.md §7 |
| FR-081 | `infra/gmail_report.py::report_match_result`, `infra/reporting.py::build_result` | `tests/unit/test_gmail_report.py`, `tests/unit/test_reporting.py` | Tested | " |
| FR-082 | `infra/reporting.py` (all four deliverable files) | `tests/unit/test_reporting.py` | Tested | " |
| FR-083 | daily-log audit / games-played verification not yet wired | — | Planned | " |
| FR-084 | `domain/models.py::NetworkAndLeagueConfig` (num_games=6, diversity_reward=10, min_games_to_pass=2, max_games_per_team=10, all Fixed per Table 18) | `tests/unit/test_config.py::test_load_game_config_round_trips_the_books_own_example` | Tested | assumptions.md A-002/A-004 |
| FR-085 | `.gitignore` | manual review | Implemented | docs/final_audit.md §16 |
| FR-086 | repo/tag process | manual, not yet done | Planned | implementation_plan.md Part 18, docs/final_audit.md §20 |
| FR-087 | `infra/reporting.py::build_declaration` (writes a `commit_hash` field; `peer_runtime.py` currently passes the placeholder `"unknown"` — the real per-game commit hash must be supplied manually per Appendix F mandatory rule 5, it can't be derived from inside the running process) | `tests/unit/test_reporting.py` | Implemented (placeholder value; real value is a manual per-game step) | docs/final_audit.md §20 |
| FR-088 | `config/<role>/game.toml::PeerGameIdentity` (group_name/group_id/members structure exists; real team roster is user-supplied) | `tests/unit/test_config.py` | Implemented (structure); manual (real roster) | assumptions.md A-012 |
| NFR-001 | package boundaries (`domain/` has no I/O imports) | manual review (no lint rule yet) + `tests/unit/*` all run without sockets/GUI | Implemented | architecture.md §1 |
| NFR-002 | `pathlib` used throughout (`config.py`, `cli.py`, `peer_runtime.py`, `reporting.py`, `gui/replay_viewer.py`) | manual review; every test runs on Windows in this session | Implemented | — |
| NFR-003 | `peer_runtime.py::run_peer`'s `finally` block (server task cancellation, GUI teardown) | `tests/e2e/test_two_peer_local_game.py`, manual two-process runs (clean exit + correct deliverables every time) | Tested | architecture.md §6 |
| NFR-004 | `logging_setup.py` (RedactionFilter, configure_logging/get_logger) | `tests/unit/test_logging_setup.py` | Tested | testing_strategy.md §1 |
| NFR-005 | `config.py` (`load_game_config`/`load_peer_config`) | `tests/unit/test_config.py` | Tested | protocol.md §5/§6 |
| NFR-006 | `infra/gatekeeper.py`, `infra/mcp_server.py` (oversized-payload guard) | `tests/unit/test_gatekeeper.py`, `tests/network/test_mcp_transport.py` | Tested | architecture.md §7 |
| NFR-007 | Step-0 declaration JSON emitter | manual + schema test | Planned | assumptions.md A-007 |
| NFR-008 | `config.py::shared_config_hash` | `tests/unit/test_config.py` | Tested | protocol.md §5 |
| PROTO-001..004 | `config.py` (schema_version), `domain/crypto.py` (canonical JSON), `infra/protocol.py` (ProtocolMessage/ProtocolResponse), `infra/mcp_server.py` (tool surface + sequencing) | `tests/network/test_mcp_transport.py` | Tested | protocol.md |
| TEST-001..006 | see testing_strategy.md | themselves | Tested | testing_strategy.md |
| TEST-007 | `tests/e2e/test_two_peer_local_game.py` (real two-OS-process game via `python -m police_thief peer`) | itself | Tested | testing_strategy.md |
| DOC-001..005 | `README.md` (academic report), `docs/architecture.md`/`docs/protocol.md` (Mermaid diagrams), `docs/progress.md`, `docs/final_audit.md`, Appendix C Table 6 checklist | manual review | Implemented (DOC-005 submission checklist still has open items — see final_audit.md §20) | this repo |
| BONUS-001 | `strategy/qlearning.py` | optional | Not started | requirements_analysis.md §14 |
| BONUS-002 | `strategy/llm_bluff.py` claude_* providers | optional, disabled by default | Not started | assumptions.md A-005 |

## Coverage check

- Every FR/NFR/PROTO/TEST/DOC ID from `requirements_analysis.md` appears above. ✅
- Every Appendix E (MUST/FORBIDDEN) item 1–55 maps to at least one FR/NFR ID above (cross-reference
  via the "E-##" tags inlined in `requirements_analysis.md`). ✅
- Every Appendix F mandatory-parameters table row is a field in `protocol.md` §5's `game.json`
  schema. ✅

Updated through the tunneling gap-closure pass (2026-07-24, see `docs/progress.md` for the dated
history of every part). Remaining genuinely open items: `strategy/llm_bluff.py` (FR-061/062/063,
BONUS-002), FR-083 (multi-game-series log/count audit), FR-086 (git tag) and the two-repo split
(assumptions.md A-008) — all called out explicitly in `docs/final_audit.md`.
