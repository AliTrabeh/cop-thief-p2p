# Protocol — Police–Thief P2P

Wire-level companion to `docs/architecture.md`. All field names below match the book's own worked
examples (Appendix B) exactly, so config files are drop-in compatible with the spec's grading
expectations.

## 1. Transport

FastMCP over HTTP, each peer running **both** roles:
- **Server half**: exposes `@mcp.tool` functions (e.g. `receive_move`) that the opponent calls.
- **Client half**: calls the opponent's exposed tools using the opponent's tunnel URL.

Each peer's local FastMCP server is exposed publicly via a tunneling tool (ngrok / Localtonet),
since most peers sit behind NAT (FR-006, PROTO §2.4.1).

`mcp.run(transport="http", host="0.0.0.0", port=<my_port>)` — port comes from
`config/<role>/game.toml → [network].my_port`, never hardcoded.

## 2. Canonical serialization

Every hashed or cross-verified payload uses canonical JSON:

```python
json.dumps(payload, sort_keys=True, separators=(",", ":"))
```

sorted keys + fixed separators ⇒ both peers hash byte-identical input regardless of dict
construction order or local JSON library whitespace defaults (PROTO-002).

## 3. Commit-Reveal cryptographic protocol (FR-040..045)

```
H_commit = SHA256( State ‖ Move ‖ Intent ‖ Nonce )
```
- `‖` = concatenation via canonical-JSON serialization of a single object
  `{"state": ..., "move": ..., "intent": ..., "nonce": ...}` (not naive string concatenation).
- `State` — hash of the board state this move is based on (prevents replay across turns).
- `Move` — the chosen physical action (movement direction or barrier placement).
- `Intent` — `"truth"` or `"lie"` flag for the accompanying hint/banter (only meaningful at a
  capture-claim moment — see FR-044).
- `Nonce` — `secrets.token_hex(16)`, fresh every commit, never `random`.

### 4-phase sequence per turn

| Step | Direction | Payload | Purpose |
|---|---|---|---|
| 1. Commit | mover → opponent | `H_commit` only | Lock in a move without revealing it |
| 2. Acknowledge | opponent → mover | `{"locked": true}` | Confirm receipt before any reveal proceeds |
| 3. Reveal | mover → opponent | `{"move": ..., "hint": ...}` (nonce **not** included yet) | Opponent can act on the move; nonce stays secret |
| 4. Final Reveal / Audit | both ways, game end | `{"nonces": [...]}` | Full retroactive verification of every commit this game |

### Verification

```python
def verify(state, move, intent, nonce, h_commit) -> bool:
    payload = json.dumps(
        {"state": state, "move": move, "intent": intent, "nonce": nonce},
        sort_keys=True,
        separators=(",", ":"),
    )
    recomputed = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    return secrets.compare_digest(recomputed, h_commit)
```

Any mismatch ⇒ `TAMPERED`, hard technical disqualification (FR-043), no appeal.

## 4. Game state machine (wire-relevant states)

`WAITING_FOR_OPPONENT → COMPUTING_MOVE → COMMITTING → AWAITING_REVEAL → VERIFYING →
WAITING_FOR_OPPONENT`, with `TECHNICAL_LOSS` reachable from `COMPUTING_MOVE`, `AWAITING_REVEAL`,
`VERIFYING`. See `docs/architecture.md` §5 for the diagram; `domain/state_machine.py` for the
authoritative transition table.

## 5. Shared, signed config — `config/game.json`

Byte-identical on both sides (NFR-008); schema mirrors Appendix F exactly.

```json
{
  "schema_version": "1.2",
  "agreed_between": ["group-a", "group-b"],
  "board_and_agents": {
    "grid_size": 7,
    "num_agents": 2,
    "thief_start": [3, 3],
    "cop_start": [0, 0],
    "axis_origin_corner": "top-left",
    "axis_start_index": 0
  },
  "world": {
    "map_area": "New York",
    "hint_max_words": 15
  },
  "movement_and_barriers": {
    "move_set": ["N", "S", "E", "W", "STAY"],
    "max_barriers": 14,
    "max_moves": 35,
    "survival_threshold": 35
  },
  "scoring": {
    "capture_cop": 20, "capture_thief": 5,
    "survival_cop": 5, "survival_thief": 10,
    "tie_score": 2, "technical_loss": 0
  },
  "pheromones": {
    "pheromone_center_intensity": 0.9,
    "pheromone_decay": 0.10,
    "pheromone_grid_size": 5
  },
  "network_and_league": {
    "response_timeout_sec": 30, "watchdog_timeout_sec": 60,
    "num_games": 6, "diversity_reward": 10,
    "min_games_to_pass": 2, "max_games_per_team": 10,
    "token_budget_per_series": 200000
  },
  "rate_limiter_gatekeeper": {
    "requests_per_minute": 30, "concurrent_requests": 2,
    "retry_backoff_sec": 5, "max_retries": 3, "queue_depth": 100
  }
}
```

Note: this project's default `num_games` is `6` (Appendix F Table 18, Fixed) — see
`docs/assumptions.md` A-002 for why the book's own JSON example ships with `1` (a schema-demo
placeholder, not the real value).

Field ↔ code mapping: config keys map 1:1 to `domain.models.GameConfig` dataclass fields; no field
is ever read by a name not present in this schema (NFR-005).

## 6. Private per-peer config — `config/<role>/game.toml`

Never shared with the opponent; never imported into the same process as the other side's file
(§2.4.2 mandatory separation).

```toml
version = "1.10"

[game]
group_name = "My-Team"
group_id   = "my-team"
sub_game_number = 1
members = ["id-1001", "id-1002"]
repos = { cop = "https://github.com/you/repo", thief = "https://github.com/you/repo" }

[network]
my_port = 8802                                  # this peer's FastMCP server port
opponent_url = "http://127.0.0.1:8801/mcp"       # the only thing I know about the opponent
turn_timeout_seconds = 180

[tunnel]                                         # this project's own extension, not in the book's example (assumptions.md A-018)
provider = "none"                                # "none" (localhost) | "ngrok" (automated) | "manual" (e.g. Localtonet)
manual_public_url = ""                           # only used when provider = "manual"

[strategy]                                       # optional: point at your brain subclass
# thief_class  = "my_team.strategy:MyThiefBrain"
# police_class = "my_team.strategy:MyPoliceBrain"

[trash_talk]                                     # optional: HOW banter is produced (never the move)
# provider = "template"    # template (0 tokens, default) | ollama | claude_api | claude_cli

[llm]
model = "template"                                # this project's default (see assumptions A-005)
step_deadline_seconds = 30

[email]
recipient = "rmisegal+uoh26finalgame@gmail.com"
mode = "draft"                                    # "draft" while developing; "send" for real matches
```

## 7. Required per-match JSON deliverables (Appendix F Table 20)

| File | Contents |
|---|---|
| `declaration_<game_id>.json` | Pre-game fixed match data: groups, members, repos, model, timestamps, GitHub commit hash used this game (FR-087). |
| `config_<game_id>_g<NN>.json` | Snapshot of the agreed `config/game.json` for this specific game in the series. |
| `log_<game_id>_g<NN>.json` | Full turn-by-turn game log for cryptographic audit by the Replay Viewer. |
| `result_<game_id>.json` | Final outcome, emailed independently by both sides (FR-081). |

All four share a common `game_uid`; `game_id` is never reused across different rival matchups
(§9.4, Table 20 notes).

## 8. Error / rejection semantics

Every tool call response distinguishes:
- `accepted: false, reason: "invalid_signature"` — commit/reveal verification failed.
- `accepted: false, reason: "illegal_move"` — move fails `domain.board` legality check.
- `accepted: false, reason: "stale_turn"` — turn/sequence number doesn't match expected next turn.
- `accepted: false, reason: "duplicate"` — already-processed turn number, idempotently ignored.
- `accepted: false, reason: "malformed"` — schema validation failed before any semantic check runs.

No stack traces are ever sent to the opponent or shown to an end user outside `--debug` mode
(security requirement, working instructions §"Security and robustness").
