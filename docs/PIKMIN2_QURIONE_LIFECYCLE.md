# Lane 15 — Honeywisp (Qurione) source lifecycle contract

Disjoint lane-15 slice: Mar and Hanachirashi are owned by the active species
lane #407, so this lane takes the Honeywisp path. Fan-out lane 15 asks to
"reuse the Mar candidate and Honeywisp path; complete the real wind/nectar
lifecycle before expanding variants".

Implementation owner: Codex via shared account `4laric`. Executing
agent/session: opencode (deepseek-v4.1-flash). Root branch
`opencode/p2-lane13-15`; base `codex/p2-main-review` `e514e6d`.

Machine-readable form: `experimental/pikmin2_qurione_lifecycle.py`
(schema `p2-qurione-lifecycle-v1`), tests
`tests/test_pikmin2_qurione_lifecycle.py` (15 passed). Source of truth is the
read-only decomp checkout `native/pikmin2-research` (`Game/Entities/Qurione.h`,
`QurioneState.cpp`, `Qurione.cpp`).

## 1. Source state machine

`QURIONE_Stay/Appear/Disappear/Move/Drop/Dead` (`StateID`), with anims
`wait=0`, `damage=1`, `run=2`, `appear=3` (`appear1`), `hide=4` (`hide1`).

| State | Entry | Exit |
|---|---|---|
| `stay` | hidden at `mSpawnPositions[mSpawnIndex]`, atari off, `ModelHidden`, appear anim stopped | `mUtilityTimer > 1.0` **and** `isAppear()` → `appear` |
| `appear` | atari off, `appear` anim, appear + glow effects | anim `KEYEVENT_END` → `move` |
| `move` | `wait` anim, zero target velocity | distance from spawn > `mFlyDist` → `disappear` |
| `disappear` | atari off, `hide` anim, disappear effect | anim `KEYEVENT_END` → `stay`; cleanup flips `mSpawnIndex` and adds PI to face dir |
| `drop` | `EB_Cullable` off, hit effect, `damage` anim | `KEYEVENT_2` → `dropItem()`; `KEYEVENT_END` → `dead` |
| `dead` | `setAlive(false)`, velocity `(0, fp04, 0)`, `run` anim | `isFlyKill()` → `finishGlowEffect()` and `kill()` |

Natural surface pass: `stay → appear → move → disappear → stay` (the spawn index
flips on each disappear). Hit path: `move → drop → dead`.

Helpers: `isAppear()` is true in Piklopedia mode or when a nearest Pikmin/Navi
is inside `viewAngle`/`sightRadius`; `isFlyKill()` when the actor is not
LOD-visible or `mUtilityTimer > fp05`.

## 2. Birth and invariants

`Qurione.cpp::birth` attaches the carried item, then sets
`QurioneInitialParam(flyDist=200, slideDist=30)`. `onInit` makes the wisp
**invulnerable** (`EB_Invulnerable`) and **untargetable** (`EB_Untargetable`),
disables platform collision / damage anim / leave-carcass / death effect /
lifegauge, sets `EB_BitterImmune`, `mDropGroup = EDG_None`, `mSpawnIndex =
QSPAWN_Start`, `mQurioneScale = 0`, then starts `Stay`.
`flyCollisionCallBack` performs `Move → Drop` only for a colliding Piki.

Parms (`fp01`..`fp05`): flight height 60, pitch rate 2.5, pitch amp 20, death
rate 100, death time 1. `moveFaceDir` flies forward and bobs vertically about
`map minY + fp01` using `fp03 * sin(mPitchRatio)`.

## 3. Reward boundary

The P2 source reward is a carried **Egg** (`EnemyID_Egg` 37) attached to the
`water` joint (`attachItem` → `startCapture`), released once on the `Drop`
`KEYEVENT_2` (`dropItem` → `endCapture`, `mEgg = null`). There is no carcass.

The integrated `engine/pc_port/pc_p2_qurione.cpp` is a **P1 nectar proxy**: it
loads the converted Qurione bank and draws poses but prints
`reward=P1_nectar P2_Egg=unimplemented`. Nectar is not the P2 source reward.

## 4. Six-gate status (contract level, no new runtime claim)

| Gate | Status |
|---|---|
| 1 identity/spawn | pass — integrated proxy: `source_id=16`, birth XYZ matched |
| 2 movement/animation | **blocked** — source Stay/Appear/Move/Disappear cycle not implemented |
| 3 attacks/receivers | pass_injected (P1 `InteractAttack` → nectar); natural Piki collision untested |
| 4 death/corpse | run gate — `dead` is a fly-away (no carcass); `isFlyKill` kill untested |
| 5 transport/reward | **blocked** — P2 Egg attach/drop unimplemented (P1 nectar proxy only) |
| 6 cleanup/re-entry | untested — spawn-index flip + manager recreate |

## 5. Requested native hooks (narrow, additive)

1. `pc_p2_qurione_update(BTeki*)` driving a per-actor Qurione FSM
   (`stay/appear/move/disappear/drop/dead`) with source timings and
   `P2_QURIONE_STATE` markers.
2. A carried-item bridge: `attachItem`/`dropItem` spawning/releasing an Egg
   (`EnemyID_Egg` 37) under the `water` joint, emitting `P2_QURIONE_EGG
   action=attach|drop`.
3. `pc_p2_qurione_fly_collision(BTeki*, Creature*)` from the flight collision
   path to move `Move → Drop` on Piki contact.
4. Reset/forget companion for the per-actor FSM state (already partly present in
   `pc_p2_qurione_reset`/`forget`).
5. Markers must upgrade `P2_ENEMY_READY species=Qurione ... source_FSM=implemented
   ... reward=P2_Egg` when the adapter lands.

Shared receiver/wind semantics stay out of this lane; no shared file is edited.

## 6. Blockers

1. **Source FSM not implemented** — the integrated module is draw/proxy only.
2. **Egg helper ownership** — `EnemyID_Egg` 37 is a shared projectile/reward
   primitive (lane 20 cannon/projectiles owns `Egg` primitives). The carried
   Honeywisp Egg reuses that primitive rather than forking it.
3. **Cleanup/re-entry** — #397 lifecycle remains the shared blocker.
4. **Runtime slot** — a real-GL run must adopt the fan-out baseline (fresh
   overlay, 20-red squad, centred 960x540 window) and record the #404 adoption
   fields.

## 7. Tests

`py -3.12 -m pytest tests/test_pikmin2_qurione_lifecycle.py -q` → 15 passed.
Coverage: schema/identity, source state machine completeness, anim IDs/parms,
birth invariants (invulnerable, no carcass, two spawn points, 0.05 scale step),
carried-Egg reward boundary, lifecycle/drop sequences, gate coverage,
acceptance-contract markers, and the log validator (cycle, drop path, exactly
one Egg drop, wrong ID, extinction, non-text).
