# TODO

Root-level pointer file (Appendix E item 50: every repo must include a PRD file, a PLAN file, and
TODO files). Kept short and current; see `docs/STATUS.md` "Phase 18 open items" for full detail on
each entry below.

## Needs a human decision or credentials (not more code)

- [x] **Two-repository split** — done 2026-07-29. Confirmed mandatory (no waiver option) via
      full-text search of the spec; split into `cop-thief-p2p` (cop-owned) and
      `cop-thief-p2p-thief` (thief-owned, mirrored history), cross-linked READMEs, `repos` config
      field updated. See `docs/assumptions.md` A-008.
- [ ] **Submission screenshots** — capture the live-view heatmap and Replay Viewer `Verified OK`
      banner as image artifacts for the Appendix C Table 6 checklist.
- [ ] **Real Gmail send test** — `infra/gmail_report.py` is only exercised in `draft` mode so far;
      send one real end-of-game report against a live Google account (OAuth2 consent required).
- [ ] **Real team roster** — replace the development-placeholder `group_name`/`group_id`/`members`
      in `config/<role>/game.toml` with real student identifiers before submission.
- [ ] **Tag `v1.0-submission`** — once the four items above are resolved.

## Known partial implementation

- [ ] **Rival-pairing enforcement** (Appendix E "one game per rival counts toward the league")
      — `config.PeerGameIdentity.opponent_group_id` and the declaration JSON now record who the
      opponent was; `infra/league_audit.py` does not yet cross-check that a re-played rival is
      excluded from the count. Scoped as too large/fragile to add safely without a fuller redesign
      of the audit pass; revisit if time allows.

## In progress

- [ ] Finish the direct PDF-vs-code verification pass over the remaining chapters (1-4, 6-11,
      Appendices A-D) — Appendix E, Appendix F, and the Chapter 5 crypto protocol have already been
      verified line-by-line against the book with zero remaining gaps beyond the two items above.
