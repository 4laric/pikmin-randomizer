# Mar airborne-reach technique (#709)

Bounded technique producer for the mar29 kill-completion gap. Downstream
consumer: `shard-enemies-2-mar29-observer` (#375, blocked gen 8). Reusable for
the flying family (#166). Implementation owner: Codex through shared account
4laric. Root-only: no native/family/shared edits, no runtime, no ADMIT. All six
runtime gates UNTESTED here.

## Verified gap (from #375, hash-pinned)

`output/workflow/autofill/planning-shards/enemies-2/prepared/mar29-observer/docs/PIKMIN2_MUSE_MAR_HANDOFF.md`
sha256 `0acdb20f786d50a714a76bc77b2e26e6345ba522764308d08566bf94ae89da66`:

- Integrated #687 turned the original no-damage defect into real natural damage:
  health `3000.00 -> 270.00` with 167 events, no injection, captain safe.
- Damage then **stalled at 270 HP** for ~9400 ticks until the app exited.
- Cause: the P1-port Mar returns to source flight height (fp01=80) between
  ATTACK windows, and the grounded squad cannot convert the last ~9%.

## Read-only cadence basis (integrated #687 + source)

Integrated `pc_port/pc_p2_mar.cpp` (species line, #687):

| Constant | Value | Role |
|---|---|---|
| `FLIGHT_HEIGHT` (fp01) | 80.0 | hover; out of grounded reach |
| `AIR_WAIT_TIME` (fp03) | 3.0 | hover wait before a move re-target |
| `SWOOP_HEIGHT` | 10.0 | CHASE descent while closing |
| `LAND_HEIGHT` | 3.0 | ATTACK touchdown |
| `TOUCHDOWN_BAND` | 12.0 | `finishFlying()` gate (<= band above ground) |
| `MAX_ATTACK_RANGE` (fp20) | 200.0 | attackable range (xz) |
| `ATTACKABLE_ANGLE` | 0.785398 | 45 deg (attackable cone) |
| `ATTACK_HOVER_SPEED` | 12.0 | Walk/Run velocity served during ATTACK |

State cadence: `WAIT(80) -> [target] CHASE(10) -> [dist<200 & angle<45deg] ATTACK(3, finishFlying) -> blow -> startFlying -> WAIT(80)`.

Source decomp (@632af937): sticking Pikmin drives `TAIAdescent -> TAIAlandingMar`
(descent/landing, `TAImar.cpp:716-717`); takeoff is `TAIAtakeOffMar` /
`timerTakeOff`. Retail therefore gives a **longer grounded window when Pikmin
stick**, which the port reaches via the ATTACK touchdown plus `finishFlying`.

## Technique (checkable; fail-closed)

Preconditions - all must hold before any step executes:

1. Mar bound: `P2_MAR_BIND generator=375001 source_id=29`.
2. Squad ready and at/above the required size: `P2_MUSE_MAR_READY squad>=N`.
3. Mar alive: a positive `P2_MUSE_MAR_HP` sample.
4. Captain safe: no `P2_FIXTURE_CAPTAIN_DOWN` (#632 adopted first).
5. Finite geometry: no `=nan`/`(nan`.

Cadence (the observer executes in order):

1. **wait_for_chase** - only move when `P2_MAR_STATE state=chase`.
2. **preposition_squad** - stand grounded on Mar's xz approach path, inside the
   45-degree entry cone, so the first grounded frame is already in reach.
3. **throw_on_landing** - during the low window (`state=attack` and height
   `<= 12`), throw Pikmin to stick; sticking triggers/holds the retail
   descent-landing and lengthens the grounded window.
4. **swarm_attack** - issue real Attack orders; re-engage ONLY Pikmin whose live
   action is not Attack (re-issuing onto an already-attacking Pikmin cancels the
   in-flight strike - the #687 finding).
5. **reclump_after_blow** - after `P2_MAR_BLOW` scatters the squad, re-clump
   stragglers at Mar's height within ~1 s of the blow, before Mar rises out of
   the band.
6. **hold_between_windows** - while `state=wait/move` (rise to 80), hold under
   the next approach; never chase Mar at hover height.
7. **complete_kill** - only when health reaches 0 then `P2_MAR_DEAD`; gates
   4/5/6 are then claimed downstream (#375).

Timing/positioning/throw constraints enforced by the adapter:

- Attacks/throws/re-clumps are refused unless `height <= TOUCHDOWN_BAND (12)`.
- Re-engaging a Pikmin already in the Attack action is refused.
- The cadence must contain at least one throw during the low window.
- The hold step must be at hover (`state in {wait, move}`), and the entry
  geometry must be inside `MAX_ATTACK_RANGE` and the entry cone.

## Validation plan the #375 observer can execute

1. Adopt `scripts/p2_fixture_captain_guard.h` (#632) first: orimaDead/NaviDead/
   HP<=1 checks, CAPTAIN_DOWN exits BLOCKED, parked captain, no blanket
   invincibility; record guard/source hashes.
2. Run the owned guarded fixture with real Attack orders and the throw cadence
   above; record `P2_MAR_STATE`, `P2_MAR_POS`, `P2_MAR_BLOW`, `P2_MUSE_MAR_HP`.
3. Assert the technique adapter (`experimental/pikmin2_mar_airborne_reach_technique.py`)
   reports `preconditions`, `reachable`, `captain_guard`, `no_nan` true and the
   executed `cadence` valid.
4. Assert the low window converts: a health decrement during the window, and
   progress past the 270-HP stall; the kill completes (`health=0` then
   `P2_MAR_DEAD`).
5. Only then claim gates `death_corpse` / `transport_reward` / `cleanup_reentry`
   (receipt/adapter path is already present from #668); until observed, all six
   gates stay UNTESTED.

## Boundaries and remaining work

- No duplication of `pc_p2_mar.cpp` / #687 fixture / #668 receipt files; those
  are read-only inputs here.
- The technique is a producer for the observer, not a runtime claim: this lane
  runs no engine, so all six gates are UNTESTED.
- If the low window still cannot convert the last hit, the remaining lever is a
  family cadence change on #166 (extend the landing window / takeoff timer),
  which needs existing-owner review - out of this lane's scope.
- Captain safety #632: N/A for this planning/technique slice; any future runtime
  must adopt the guard above and record fresh hashes.
