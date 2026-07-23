# Requirements Traceability Matrix

Status legend: **Planned** (design complete, no code yet) · **In Progress** · **Implemented**
· **Tested** · **Verified** (implemented + tested + manually confirmed working).

This table is updated at the end of every implementation part (see `docs/implementation_plan.md`)
and every entry in `docs/progress.md`.

| Req ID | Module | Test(s) | Status | Docs |
|---|---|---|---|---|
| FR-001 | process boundary (two CLIs, `config/<role>/`) | `tests/e2e/test_two_peer_local_game.py` | Planned | architecture.md §2/§9 |
| FR-002 | `cli.py`, `src/police_thief/__main__.py` | — (`--help` smoke) | Planned | implementation_plan.md Part 1 |
| FR-003 | `domain/state_machine.py` | `tests/unit/test_state_machine.py` | Planned | architecture.md §5 |
| FR-004 | `orchestrator.py` (Deadline Tracker) | `tests/network/test_timeout.py` | Planned | architecture.md §7 |
| FR-005 | `infra/watchdog.py` | `tests/integration/test_orchestrator.py` | Planned | architecture.md §7 |
| FR-006 | `gui/live_view.py` | `tests/unit/test_live_view_render.py` | Planned | architecture.md §1/§4 |
| FR-010 | `domain/board.py`, `config.py` | `tests/unit/test_board.py` | Planned | requirements_analysis.md §2 |
| FR-011 | `domain/board.py` | `tests/unit/test_board.py` | Planned | " |
| FR-012 | `domain/board.py` | `tests/unit/test_board.py` | Planned | " |
| FR-013 | `domain/board.py`, `config.py` | `tests/unit/test_board.py` | Planned | assumptions.md A-003 |
| FR-014 | `domain/board.py` | `tests/unit/test_board.py` | Planned | assumptions.md A-010 |
| FR-015 | `domain/board.py` | `tests/unit/test_board.py` | Planned | " |
| FR-016 | `domain/board.py`, log manager | `tests/integration/test_orchestrator.py` | Planned | architecture.md §6 |
| FR-017 | `domain/board.py` | `tests/unit/test_board.py` | Planned | " |
| FR-018 | `domain/board.py` | `tests/unit/test_board.py` | Planned | requirements_analysis.md §2 |
| FR-020 | `domain/board.py`, `config.py` | `tests/unit/test_board.py` | Planned | assumptions.md A-001 |
| FR-021 | `orchestrator.py` | `tests/integration/test_orchestrator.py` | Planned | " |
| FR-030 | `domain/scent.py` | `tests/unit/test_scent.py` | Planned | requirements_analysis.md §4 |
| FR-031 | `config.py` | `tests/unit/test_config.py` | Planned | " |
| FR-032 | `domain/scent.py`, `strategy/heuristic.py` | `tests/unit/test_scent.py`, `test_strategy.py` | Planned | " |
| FR-033 | `strategy/qlearning.py` (optional) | — | Planned (bonus) | " |
| FR-040 | `domain/crypto.py` | `tests/unit/test_crypto.py` | Planned | protocol.md §3 |
| FR-041 | `domain/crypto.py` | `tests/unit/test_crypto.py` | Planned | " |
| FR-042 | `orchestrator.py`, `domain/crypto.py` | `tests/protocol/` | Planned | protocol.md §3 |
| FR-043 | `domain/crypto.py`, `orchestrator.py` | `tests/unit/test_crypto.py` | Planned | " |
| FR-044 | `orchestrator.py` | `tests/integration/test_orchestrator.py` | Planned | " |
| FR-045 | `gui/replay_viewer.py` | `tests/unit/test_replay_viewer.py` | Planned | architecture.md §7 |
| FR-050 | `infra/mcp_server.py`, `infra/mcp_client.py` | `tests/network/` | Planned | protocol.md §1 |
| FR-051 | `infra/mcp_server.py` | `tests/network/`, `tests/protocol/` | Planned | " |
| FR-052 | `domain/state_machine.py`, `orchestrator.py` | `tests/unit/test_state_machine.py` | Planned | architecture.md §5 |
| FR-053 | `orchestrator.py` (Deadline Tracker) | `tests/network/test_timeout.py` | Planned | architecture.md §7 |
| FR-054 | `infra/watchdog.py` | `tests/integration/test_orchestrator.py` | Planned | " |
| FR-055 | `infra/gatekeeper.py` | `tests/unit/test_gatekeeper.py` | Planned | architecture.md §7 |
| FR-060 | `strategy/base.py` | `tests/unit/test_strategy.py` | Planned | protocol.md §6 |
| FR-061 | `strategy/llm_bluff.py` | `tests/unit/test_strategy.py` | Planned | assumptions.md A-005 |
| FR-062 | `strategy/llm_bluff.py` | `tests/unit/test_strategy.py` | Planned | " |
| FR-063 | `strategy/llm_bluff.py` | `tests/unit/test_strategy.py` | Planned | " |
| FR-064 | `config.py` | `tests/unit/test_config.py` | Planned | " |
| FR-070 | `gui/live_view.py` | `tests/unit/test_live_view_render.py` | Planned | architecture.md §1 |
| FR-071 | `gui/replay_viewer.py` | `tests/unit/test_replay_viewer.py` | Planned | " |
| FR-072 | `gui/live_view.py`, `gui/replay_viewer.py` | manual screenshot | Planned | docs/final_audit.md (future) |
| FR-080 | `infra/gmail_report.py` | `tests/unit/test_gmail_report.py` | Planned | protocol.md §7 |
| FR-081 | `infra/gmail_report.py` | `tests/unit/test_gmail_report.py` | Planned | " |
| FR-082 | `infra/gmail_report.py` | `tests/unit/test_gmail_report.py` | Planned | " |
| FR-083 | `orchestrator.py`, `infra/gmail_report.py` | `tests/integration/` | Planned | " |
| FR-084 | `config.py` | `tests/unit/test_config.py` | Planned | assumptions.md A-002/A-004 |
| FR-085 | `.gitignore` | manual review | Implemented | docs/final_audit.md (future) |
| FR-086 | repo/tag process | manual | Planned | implementation_plan.md Part 18 |
| FR-087 | `infra/gmail_report.py` (declaration) | `tests/unit/test_gmail_report.py` | Planned | " |
| FR-088 | `config/<role>/game.toml` | manual review | Planned | assumptions.md A-012 |
| NFR-001 | package boundaries (`domain/` has no I/O imports) | lint rule + `tests/unit/*` | Planned | architecture.md §1 |
| NFR-002 | `pathlib` usage throughout | manual review + CI on Windows | Planned | — |
| NFR-003 | `orchestrator.py` shutdown path | `tests/network/test_shutdown.py` | Planned | architecture.md §6 |
| NFR-004 | `logging_setup.py` | `tests/unit/test_logging_redaction.py` | Planned | testing_strategy.md §1 |
| NFR-005 | `config.py` | `tests/unit/test_config.py` | Planned | protocol.md §5/§6 |
| NFR-006 | `infra/gatekeeper.py`, `infra/mcp_server.py` | `tests/unit/test_gatekeeper.py` | Planned | architecture.md §7 |
| NFR-007 | Step-0 declaration JSON emitter | manual + schema test | Planned | assumptions.md A-007 |
| NFR-008 | `config.py` (hash check) | `tests/unit/test_config.py` | Planned | protocol.md §5 |
| PROTO-001..004 | `config.py`, `domain/crypto.py`, `infra/mcp_server.py` | `tests/protocol/` | Planned | protocol.md |
| TEST-001..007 | see testing_strategy.md | themselves | Planned | testing_strategy.md |
| DOC-001..005 | `README.md`, `docs/*` | manual review | Planned | this repo |
| BONUS-001 | `strategy/qlearning.py` | optional | Not started | requirements_analysis.md §14 |
| BONUS-002 | `strategy/llm_bluff.py` claude_* providers | optional, disabled by default | Not started | assumptions.md A-005 |

## Coverage check

- Every FR/NFR/PROTO/TEST/DOC ID from `requirements_analysis.md` appears above. ✅
- Every Appendix E (MUST/FORBIDDEN) item 1–55 maps to at least one FR/NFR ID above (cross-reference
  via the "E-##" tags inlined in `requirements_analysis.md`). ✅
- Every Appendix F mandatory-parameters table row is a field in `protocol.md` §5's `game.json`
  schema. ✅

This matrix currently shows the **planning baseline** — all statuses will be updated to
Implemented/Tested/Verified as `docs/implementation_plan.md` parts are completed, tracked in
`docs/progress.md`.
