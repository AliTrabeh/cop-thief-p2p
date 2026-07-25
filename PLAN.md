# Plan

Root-level pointer file (Appendix E item 50: every repo must include a PRD file, a PLAN file, and
TODO files). The actual plan lives in `docs/`, kept there rather than duplicated here so it has one
source of truth:

- **`docs/implementation_plan.md`** — the full, numbered part-by-part build plan (20 parts: repo
  setup → domain models → crypto → scent engine → state machine → strategy → P2P transport →
  orchestrator → rate limiting → Gmail reporting → CLI → GUI/replay → logging → tests → e2e demo →
  docs → final verification, plus 2 bonus parts). Each part states goal, files, requirements
  covered, tests, commands, acceptance criteria, risks, and dependencies.
- **`docs/STATUS.md`** — current status of every part against that plan (phase board + open items).
- **`docs/progress.md`** — chronological log of what was actually done, in the order it happened.
- **`docs/PRD.md`** — the 600+ individually numbered product requirements the plan is built from.

See `TODO.md` for the current concrete open items.
