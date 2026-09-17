# P2 Challenge host-mode consumer (#651)

Cross-partition prerequisite for challenge-0/1/2/3 P1 scopes. Implementation
owner: Codex through shared GitHub account 4laric; contributor Muse Spark 1.3
via OpenCode. Private worktrees:
`.../challenge-3/prepared/challenge-host-mode-root` (root) and
`.../challenge-host-mode-native` (native).

## What this consumes (never forks)

The DONE framework contract is consumed as an artifact:
`experimental/pikmin2_challenge_framework_contract.py` (producer commit
`b9bb55f0`, cherry-picked into this private root as `728e7492`; 3 pure-add
files, no conflicts). This consumer imports `COLORS`, `HAPPA`,
`ContractError` and delegates scoring to `compute_score` - the stage-table
parser is never reimplemented.

## Host-mode semantics implemented (root consumer)

`experimental/pikmin2_challenge_mode.py`:

- `stage_select(stages, ui_index)` - select by the contract's `ui_index`.
- `starting_state(stage)` - apply the contract `roster` (PikiContainer
  colour x happa) and `bitter_sprays` / `spicy_sprays` exactly; `time_left`
  = the first floor's `floor_seconds`.
- `tick(state, seconds)` - `mTimeLimit` countdown; `timeout` ends the
  attempt; further ticks are no-ops.
- `descend(state)` - floor advance that replaces the timer with that
  floor's contract extension; refuses to descend past the last floor.
- `check_end(state, pikmin_left, captain_dead, gave_up)` - engine-order end
  states: `captain_down`, `give_up`, `extinction`.
- `result(state, deathless)` - ordinary vs deathless boundary plus score
  delegated to the contract's `compute_score`.
- `retry(state)` - resets attempt-local state (timer, floor, pokos, end
  state, population) while preserving persistent clear/high-score.

## Explicitly unsupported (never approximated)

`coop_2p`, `key_completion`, `result_screen` - exposed by
`unsupported_semantics()` and carried in every `result()` as
`unsupported=[...]`. `treasure_count_field` semantics remain unproven in the
contract.

## Captain safety #632 (mandatory for any runtime run)

Adopt `scripts/p2_fixture_captain_guard.h` (sha256
`d2f678c9eda75e151eb534077dff9e30ad36ae4796881d971bbd09945f3c3474`) in the
native fixture: check `orimaDead`, `NaviDead` and HP<=1 before pause/movie
returns and each observed tick; emit `CAPTAIN_DOWN` and exit BLOCKED; park
the captain outside attack reach when not testing captain hits; no blanket
invincibility; protected observation is labelled and cannot prove captain
damage. `check_end(..., captain_dead=True)` already prefers captain-down
over any other end state, so a dead captain can never be papered over.

## Native surface

`native/pc_port/pc_p2_challenge_mode.{h,cpp}` (stage select, squad/spray
application, `mTimeLimit` countdown with per-floor extension, retry/reset
boundary, markers) and `native/tools/p2_challenge_mode_fixture.cpp` (guarded
fixture). No shared-file edits without #186 review.

## Validation

- `tests/test_pikmin2_challenge_mode.py`: 19 passed (stage select, start
  state, countdown/timeout, descend extension, end-state ordering, result
  score delegation, deathless boundary, retry reset/persistence, unsupported
  exposure).
- All six runtime arena gates remain UNTESTED; no playability claim.

## Downstream consumers

challenge-0 (#600), challenge-1 (#601), challenge-2 (#602), challenge-3
(#603) P1 scopes.