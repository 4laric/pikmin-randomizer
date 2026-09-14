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

## 4. Six-gate status (native FSM runtime)

| Gate | Status |
|---|---|
| 1 identity/spawn | PASS — native FSM: `source_id=16`, birth XYZ matched |
| 2 movement/animation | PASS — full `stay/appear/move/disappear/stay` cycle + source flight bob |
| 3 attacks/receivers | source-backed N/A (no attack); Piki-contact trigger observed |
| 4 death/corpse | PASS at source level — `drop -> dead` fly-away, no carcass |
| 5 transport/reward | marker-level PASS — `EGG action=attach|drop`; physical Egg is lane 20 |
| 6 cleanup/re-entry | untested — spawn-index flip observed; scene/save re-entry is #397 |

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

## 6. Native candidate (lane 15)

Implemented on a private native worktree, since the maintained line is
integration-owned:

- Branch `opencode/p2-lane15-native` @ `c54bc601` (base native
  `codex/pikmin2-room-preview` `f9e139d8`), worktree `output/native-lane15`,
  private build `output/native-lane15-build`. Commits: `a0030ee7` (FSM),
  `99dfd755` (marker flush), `c54bc601` (host-AI suppression + flight bob).
- Files: `pc_port/pc_p2_qurione.cpp` + `.h`; `include/teki.h` (additive param
  chain); `src/plugPikiNakata/tekibteki.cpp` (`pc_p2_qurione_update` from
  `BTeki::update`, `pc_p2_qurione_suppress_ai` from `BTeki::doAI`). Every hook
  is a no-op for unregistered actors.
- Build: Release, `PIKMIN_NATIVE_JAUDIO=ON`, Ninja `-j 6`; dry run
  `ninja: no work to do`. Executable SHA-256
  `4c8811cd57014615320bf38df198a04c2e132b8dacdf4904f2950933f9efb302`.

### Runtime (green, full lifecycle)

Launched `nectar.exe --experimental-pikmin2-room` with
`PIKMIN_P2_ROOM_WINDOW=960x540` in a working direct-boot arena:

- Centred 960x540 window; `[Pikipelago] P2_ROOM_PREVIEW ... red=20`;
  `[BBFT] Direct boot: Forest of Hope day 2, 20 reds`; no extinction.
- `P2_QURIONE_BIND generator=203001 source_id=16 visual_only=0`;
  `P2_ENEMY_READY species=Qurione ... behavior=native source_FSM=implemented
  reward=P2_Egg`; `P2_QURIONE_EGG ... action=attach`; `P2_QURIONE_BANK`.
- **Full source cycle observed:** `stay -> appear -> move -> disappear -> stay`
  repeated across spawn-index flips, plus a Piki contact firing
  `move -> drop -> dead` with `P2_QURIONE_EGG ... action=drop` and a dead
  fly-away (`P2_QURIONE_DEAD`; y 49 -> 151 -> 252).
- The captured log passes the contract validator
  (`py -3.12 -m experimental.pikmin2_qurione_lifecycle <log>`): identity, ready,
  window, source_cycle, drop_path, egg_attach, egg_drop, exactly_one_drop,
  no_extinction.
- Evidence: `output/p2-qurione-lane15/arena3h.log` (full lifecycle),
  `arena3-final.log` (repeated return cycle), arena
  `output/p2-qurione-lane15/arena3/`.
### Host-AI fix (required to run at all)

The integrated Qurione host runs invalid P1 Chappy AI for the actor; gdb on the
un-suppressed build showed a SIGSEGV in
`TaiWatchOffTerritoryCenterAction::act(Teki&)` (`getNestPosition` path) before
the adapter update. `pc_p2_qurione_suppress_ai()` now short-circuits
`BTeki::doAI()` for owned actors, so the FSM drives them. This was invisible to
the old proxy because its arena never entered active gameplay.

### Remaining unobserved

- Egg primitive: only the `action=drop` marker is emitted; lane 20 owns the
  shared `EnemyID_Egg` primitive, so no physical Egg is released here.
- Glow/appear/disappear/hit effect fidelity and the scale grow/shrink.
- Cleanup/re-entry (#397).
Recorded port adaptations: the carried Egg is reported through markers (lane 20
owns the primitive); Drop fires at half the damage clip (no KEYEVENT frames in
the bank); sight is a distance test; scale/glow/hit effects are not ported.

## 6b. Blockers

1. **Egg primitive** — only the `action=drop` marker is emitted; lane 20 owns the
   shared `EnemyID_Egg` primitive.
2. **Effects/scale** — glow/appear/disappear/hit effects and the scale
   grow/shrink are not ported.
3. **Cleanup/re-entry** — #397 lifecycle remains the shared blocker.
4. **Integration** — the native candidate is not on the maintained line; lane 01
   owns export/acceptance.
## 7. Tests

`py -3.12 -m pytest tests/test_pikmin2_qurione_lifecycle.py -q` → 15 passed.
Coverage: schema/identity, source state machine completeness, anim IDs/parms,
birth invariants (invulnerable, no carcass, two spawn points, 0.05 scale step),
carried-Egg reward boundary, lifecycle/drop sequences, gate coverage,
acceptance-contract markers, and the log validator (cycle, drop path, exactly
one Egg drop, wrong ID, extinction, non-text).
