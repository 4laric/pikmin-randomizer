# Snagret source policy (#174 / #376)

Lane 25 bounded slice: an engine-free, deterministic implementation of the
shared burrow/emerge/peck machinery for SnakeCrow (34, Burrowing Snagret) and
SnakeWhole (70, Pileated Snagret).

Implementation owner: Codex via shared account `4laric`. Executing session:
opencode (deepseek-v4.1-flash), 2026-09-13. Native candidate
`opencode/p2-longlegs-fsm` head `94e9ecc6`, base `f9e139d8` (never pushed to
native origin). Patch: `native-candidates/snagret-policy/`.

## What this slice is

The lane already had a source audit
([PIKMIN2_SNAGRET_CRAWBSTER_AUDIT.md](PIKMIN2_SNAGRET_CRAWBSTER_AUDIT.md)), a
P1-proxy native display/corpse path, and a separate DangoMushi source FSM
(`pc_p2_dangomushi.cpp`, native `8ae1e5b4`, #407). This slice adds the missing
Snagret source policy:

- `pc_port/pc_p2_snagret_fsm.h` / `.cpp`: Stay(buried)/Appear1/Appear2/
  Wait/Walk/Home/Attack/Eat/Struggle/Disappear/Dead, per-species parameters.
- `tools/p2_snagret_fsm_test.cpp`: an engine-free compiled fixture.
- `CMakeLists.txt`: policy added to `pikmin_pc`; fixture registered as ctest
  `p2_snagret_fsm_test`.

The policy owns no game object. The host supplies spatial booleans
(`targetInTerritory`, `targetInHome`, `facingTargetWithin30`,
`targetInPeckBox`), animation keys, latch/shake state and a random roll, and
performs the requested peck/dive/hop/drop effects. `targetForward/Lateral` are
used for pure peck-box selection.

## Source mapping

| Behavior | Source fact | Policy |
|---|---|---|
| Burrow minimum | fp12 2.5 s Burrowing, 0.5 s Pileated | `buriedMinSeconds` |
| Emerge | target in territory surfaces 120 units away; fp01 0.6 picks `appear1` over `appear2` | `Stay -> Appear1/Appear2` via `roll` |
| Surfacing heal | `lifeIncrement` 10 | `output.surfaced` |
| Dive | no target for fp11 2.5/0.5 s, or the stuck-Pikmin shake threshold; dive key 2 flicks nearby | `Wait -> Disappear`, `output.diveFlick` |
| Peck boxes | near/normal/far ±30, right 50..110, left −110..−50 (Pileated shifts forward) | `selectPeckBox()` |
| Strike points | 40/120/190/90/90 (Burrowing), 60/150/220/120/120 (Pileated) | `strikeForward()` |
| Attack | at key 4 re-pecks if a mouth slot is free and a target remains | `attackKey4` + `mouthSlotFree` |
| Struggle | latched head Pikmin; 1.5 s | `Wait/Walk/Attack -> Struggle` |
| Pileated pursuit | `run1` hop on key 2; translate only within 30°, else pivot; Home outside territory, Wait inside home | `Walk`/`Home` + `runKey2` |
| Death | treasure thrown from `kutijnt1`; carriable `type5` corpse | `dropTreasure`, `leaveCorpse` |
| Bitter immunity | only while buried | `bitterImmune = Stay` |

Documented gaps: `Eat` (assembly-retained `getAttackPiki`/mouth swallow) is not
modelled; captop swallow is host-only and captains are never swallowed.

## Six-gate status for this commit

| Gate | Status | Evidence |
|---|---|---|
| 1. Exact identity and spawn | source-backed audit | audit identity table; no runtime spawn here |
| 2. Autonomous movement and animation | BLOCKED | needs the actor, SnakeJointMgr neck bend and animation clock |
| 3. Attacks and receivers | PARTIAL (policy) | peck boxes/strike points/re-peck tested; receivers and poison unwired |
| 4. Death and corpse | PARTIAL (policy) | drop/corpse intents tested; no runtime death path |
| 5. Actual transport and reward | UNTESTED | depends on lane 06 |
| 6. Cleanup and re-entry | UNTESTED | needs the actor lifecycle host |

Source-mechanics increment only; not playable or family-complete evidence.

## Remaining blockers and next slices

1. **Actor + neck joint.** No `SnakeJointMgr` equivalent in the port; the beak
   cannot reach a strike point until the joint callback exists.
2. **Mouth slots and poison.** Three `kamujnt1..3` slots, one Pikmin each, and
   White Pikmin poison 300 are host-side.
3. **DangoMushi parity.** The #407 Crawbster FSM still needs its Turn LOOP_START
   invulnerability window and Rock/Egg spawner (blocks the flip-hazard gate).
4. **Animation key events** from lane 08 for appear/dive/hit/run markers.
5. **Day-end surface behavior** for the two Snagrets belongs to the enemy/placement
   lanes.

## Integration

Apply `native-candidates/snagret-policy/0001-*.patch` on the maintained native
line after lane 01 reconciles the #407 species candidate. The module is
additive and engine-free until a reviewed host wires it up.
