# Pikmin 2 Titan Dweevil (BigTreasure) ordinary-update FSM host drive (#246)

Lane 32 of the P2 implementation fan-out `PIKMIN2_IMPLEMENTATION_FANOUT.md`
(coordination #186, tracking #454). Child issue
[#246](https://github.com/4laric/pikmin-randomizer/issues/246), parent
[#175](https://github.com/4laric/pikmin-randomizer/issues/175).

Implementation owner: Codex via shared account `4laric`. Executing
agent/session: opencode (deepseek-v4.1-flash), 2026-09-14. This slice starts
from the wave guide `PIKMIN2_NEXT_WAVE.md` and the latest approved pair:
root `3851d4b` (draft `codex/p2-main-review`), native
`f14c6851473ac1161be56c8b98f4f905232f3635` (clean).

Prior slices: [source audit](PIKMIN2_BIGTREASURE_AUDIT.md),
[ownership/teardown contract](PIKMIN2_BIGTREASURE_CONTRACT.md),
[per-element attacks](PIKMIN2_BIGTREASURE_ATTACKS.md),
[host seam](PIKMIN2_BIGTREASURE_SEAM.md),
[conversion](PIKMIN2_BIGTREASURE_CONVERSION.md),
[FSM host binding](PIKMIN2_BIGTREASURE_FSMHOST.md).

## What this slice changes

The integrated baseline ran the BigTreasure host seam from
`pc_p2_hardlanes_update` through the **injected attack shortcut**
(`p2_bigtreasure_host_tick_entry`: pacer -> pick -> `pools.start`); the 12-state
policy stepped only inside `tools/p2_bigtreasure_runtime.cpp`. This slice does
two things:

1. **Ordinary-update FSM host drive.** `pc_p2_hardlanes_update` now steps the
   real 12-state policy from the live game loop, with a single natural-hit
   ingress (no second receiver framework).
2. **Animation keyframe source.** The policy owns no clip lengths, so a new
   lane-owned clock plays the source state animation through the vendored retail
   event player over the lane's `P2_RETAIL_EVENTS_1` motion table and feeds the
   policy its `animEnd` / `keyEvent2` / `keyEvent100` pulses. This is what lets
   the policy leave `Land` in ordinary play.

New lane-owned native files:

- `pc_port/pc_p2_bigtreasure_ordinary.h/.cpp` — engine-free
  `P2BigTreasureOrdinary`: owns one `P2BigTreasureFsmHost` and a bounded (16)
  FIFO of `P2BigTreasureOrdinaryHit`. `tick()` derives the source
  `isAttackLimitTime()` input from the seam pacer (`4 + 2 * liveWeapons`
  seconds, 3x while an unstuck outsider is nearby), applies at most one queued
  natural hit, then steps the policy once per 30 Hz source tick.
- `pc_port/pc_p2_bigtreasure_animclock.h/.cpp` — engine-free
  `P2BigTreasureAnimClock`: state->clip mapping, retail event -> FSM pulse
  translation, and its own `P2BigTreasureMotionBank` + `p2retail::Player`.
- `tools/p2_bigtreasure_ordinary_test.cpp` (5 groups),
  `tools/p2_bigtreasure_animclock_test.cpp` (4 groups),
  `tools/p2_bigtreasure_natural_test.cpp` (end-to-end chain to attack).

Wired seam (additive) in `pc_port/pc_p2_hardlanes.cpp/.h`:

- `pc_p2_hardlanes_bigtreasure_hit(int weapon, float damage, bool bittered)` —
  the natural-hit ingress. `weapon` is a `P2BigTreasureWeapon` coll part, or
  `-1` for the body. The lane-10 receiver / collision proxy is the intended
  caller.
- `bigTreasureTargetInBox()` — the source 225-unit XZ `isAttackLimitTime` box
  test against live Navi/Pikmin, consumed as the drive's `targetInBox`.
- The keyframe clock is loaded from `p2_bigtreasure_events.txt` (the lane's
  motion table); absent table leaves it inactive. The ordinary update steps the
  clock then the drive and logs each phase change as
  `P2_BIGTREASURE_FSM phase=<name> weapons=<n> clip=<clip>`.
- `CMakeLists.txt`: two additive TU lines.

## State -> clip map (source-grounded)

From `include/Game/Entities/BigTreasure.h` `AnimID` and the `State*.cpp`
`init` selections in `native/pikmin2-research`:

| Phase | Clip | Source |
| --- | --- | --- |
| Stay | `appear` | `StateStay::init` blend 0 |
| Land | `appear2` | `StateLand` `startMotion`/Appear2 |
| ItemWait | `wait1` | `StateItemWait::init` blend 2 |
| Wait | `wait2` | `StateWait::init` blend 25 |
| Flick | `flick` | `StateFlick::init` blend 26 |
| DropItem | `dropitem` | `StateDropItem::init` blend 24 |
| Walk | `wait2` | `StateWalk::init` blend 29 (reuses `wait2.bca`) |
| ItemWalk | `move1` | `StateItemWalk::init` blend 28 |
| Dead | `dead` | `StateDead::init` blend 27 |
| PreAttack | `preattack{e,f,g,w}` | `getPreAttackAnimIndex` |
| Attack | `attack{e,f,g,w}` | `getAttackAnimIndex` |
| PutItem | `attackend{e,f,g,w}` | `getPutItemAnimIndex` |

Fire uses its forward variant here; the source picks a fire direction from the
target angle (host work). Event types map `1000 -> animEnd`, `2 -> keyEvent2`,
`100 -> keyEvent100`.

## Interface contract

| Item | Value |
| --- | --- |
| Caller | `pc_p2_hardlanes_update` (ordinary), lane-10 receiver via `pc_p2_hardlanes_bigtreasure_hit` |
| Update phase | 30 Hz source tick, inside the existing BigTreasure debt accumulator (max 4 catch-up ticks) |
| Identity/lifetime | one `P2BigTreasureOrdinary` + one `P2BigTreasureAnimClock` static; reset on `pc_p2_hardlanes_setup`/`_reset`; reuses the existing seam lifetime (4 weapons + Louie) |
| Inputs | `P2BigTreasureOrdinaryFacts` (host facts, including keyframe pulses) + queued hits |
| Result | `P2BigTreasureFsmHostOutput` (damage result, knock-offs, live weapons, body exposure) + FSM phase |
| Failure behavior | inactive seam = no-op; invalid/full hit queue rejects and drops the hit; missing motion table leaves the clock inactive (policy parks in Land); policy actions are the only ownership/pool writers |
| Acceptance cases | `tools/p2_bigtreasure_ordinary_test.cpp`, `tools/p2_bigtreasure_animclock_test.cpp`, `tools/p2_bigtreasure_natural_test.cpp` |

## Evidence (this pass)

**Standalone fixtures** (MinGW64 GCC 16.2.0, `-std=gnu++17 -Wall -Wextra
-Werror`, warning-clean):

- `PASS BIGTREASURE_ORDINARY` (5/5), SHA-256 `8D8CE5E2371B0C6FC9C841507A9FBE8832435F80FC07C177A13EDD723C22B998`.
- `PASS BIGTREASURE_ANIMCLOCK` (4/4), SHA-256 `A4A2B4D443F26613E5E0432444C3C1C426BFD10F345601562FB9CAD5813A2376`.
- `PASS BIGTREASURE_NATURAL` (2/2), SHA-256 `C1F6D512BAD6F8D67A4EA67FB5B448CD1065962386793E16499C2CEF42AA0C23`:
  the keyframe clock + ordinary drive reach `Attack` and fire `startAttack`,
  then natural hits knock off all four weapons to `DropItem`, and death
  releases Louie and confirms the kill.
- Regression: `PASS BIGTREASURE_FSMHOST` (8/8) still green.

**Production compile/link** (private, maintained config): build dir
`output/native-lane32-ordinary-build`, Ninja, Release, JAudio ON,
`PIKMIN_NATIVE_OPTIMIZE=OFF`, test hooks OFF, MinGW GCC 16.2.0.
`[545/545] Linking CXX executable bin\nectar.exe`, exit 0;
`ninja -n pikmin_pc` = `no work to do`. Executable SHA-256
`91AF796FC3C991CAFEEFF51DFBE5B608C7B22633ADC5818585A43A6553F86631`.

**Real-GL runtime (this pass).** Fixture `output/lane32-anim-fixture-02`
built from native `cb8e6d45` (fixture.exe SHA-256
`9410FFA00625B8501914FA79787EDA1333DA7975C2F5DF750E91D6205CBBF3A6`). Run
`output/lane32-anim-runtime-02/437cf39ce8544bb0be9cf467757f02d6`,
`status=passed`, exit 0, stdout SHA-256
`AAABF4A9799FDB7D2569B7009FA46AB71E58B09B6C8AF5D231B374A6E63CEE16`; inputs
`pikmin2-room105` + `bigtreasure-host-stage-01` + `bigtreasure-visual-stage-04`
(full 29-clip stage) on the `pikmin-local` game assets; two PPM captures.

The ordinary keyframe drive ran in the live game loop and advanced the policy
through four animation-driven states:

```text
P2_HARDLANES_READY family=BigTreasure keyframes=1
P2_BIGTREASURE_VISUAL_READY clips=29 pellets=4 pellet_debug=1
P2_BIGTREASURE_FSM phase=Stay weapons=4 clip=appear
P2_BIGTREASURE_FSM phase=Land weapons=4 clip=appear2
P2_BIGTREASURE_FSM phase=ItemWalk weapons=4 clip=move1
P2_BIGTREASURE_FSM phase=ItemWait weapons=4 clip=wait1
P2_BIGTREASURE_WINDOW size=960x540 pos=373,263
[Pikipelago] P2_ROOM_PREVIEW room=room_4x4a_4_conc red=20 isolated=1
```

All pre-existing fixture markers stayed green in the same run
(`P2_BIGTREASURE_HOST_SEAM_PASS`, `P2_BIGTREASURE_FSMHOST_FULL_PASS
knockoffs=4 ... phase=DropItem`, `P2_BIGTREASURE_VISUAL_WAIT1_PASS`,
`P2_BIGTREASURE_VISUAL_DEAD_PASS`, `PASS BIGTREASURE_RUNTIME`), so the add has
no regression on the four-weapon injected fixture. The live run reached
`ItemWait`; the full `PreAttack -> Attack -> startAttack` chain is proven in the
deterministic `BIGTREASURE_NATURAL` fixture above.

## Clip availability audit (lane 32 next-wave row)

- **Source registry:** 30 animation registrations
  (`BigTreasure.h` `AnimID`; `Wait2_2` repeats `wait2.bca`) = 29 unique clips.
- **Converted:** 29/29 clips (167 baked poses) per
  `PIKMIN2_BIGTREASURE_CONVERSION.md`. The `loozy` (King of Bugs) model is not
  converted (unsupported shape matrix type) and stays a debug marker.
- **Staged and loaded:** `bigtreasure-visual-stage-04` stages all 29 clips, and
  the real-GL run above **loaded them** (`VISUAL_READY clips=29`), so the
  earlier "full 171-shape stage is heap-capped" note no longer holds for this
  stage/build.
- **State->clip map:** now defined (table above), source-grounded, and driven
  by the lane's own motion player; no shared visual-bank cross-talk.

## Remaining gaps

- **Receiver routing from a real Pikmin attack volume (lane 10):** the hit
  ingress is ready and the `BIGTREASURE_NATURAL` fixture proves the downstream
  knock-off/finale; the live caller is not integrated. Until then the live run
  reaches `ItemWait` but not a natural weapon knock-off.
- **IK bridge:** `finishIKMotion` is fed as always-true (no IK-system bridge),
  matching the fixture inputs; a real `isFinishIKMotion` query is future work.
- **Fire direction:** the forward `attackf`/`preattackf` variant is used; the
  source target-angle selection is not yet wired.
- **Visual playback:** the shared visual bank still plays its own clip; the
  lane's keyframe clock is the FSM source. Unifying them is a later slice.
- The unconverted loozy model, skeletal playback, material fidelity and finale
  `mPelletDropCode` / pellet configs are unchanged.

## Handoff (lane 32 / opencode deepseek-v4.1-flash / #246)

```text
Concrete source ID and missing gate addressed: 73 BigTreasure (Titan
Dweevil) — FSM host -> ordinary update, animation keyframe source, natural-hit
ingress. Natural arena knock-off still gated on the lane-10 receiver.
Root base/head: 3851d4b; native f14c6851; native head cb8e6d45.
Owned files: pc_port/pc_p2_bigtreasure_ordinary.{h,cpp};
  pc_port/pc_p2_bigtreasure_animclock.{h,cpp};
  pc_port/pc_p2_hardlanes.{h,cpp} (additive); CMakeLists.txt (+2 TU);
  tools/p2_bigtreasure_{ordinary,animclock,natural}_test.cpp.
Private build: output/native-lane32-ordinary-build (Ninja/Release/JAudio ON/
  optimize OFF/hooks OFF); exe SHA-256 91AF796F...F86631; ninja -n no work.
Fixture: PASS BIGTREASURE_ORDINARY, BIGTREASURE_ANIMCLOCK, BIGTREASURE_NATURAL.
Natural vs injected: keyframes from the lane's own motion player; hits enter by
  pc_p2_hardlanes_bigtreasure_hit (lane-10 boundary). Real-GL: run
  lane32-anim-runtime-02/437cf39c... passed, full 29-clip stage, phase
  Stay->Land->ItemWalk->ItemWait in the live loop; four-weapon fixture markers
  unchanged.
Combined-scene impact: none measured; additive lane-owned TUs only.
Next consumer: lane 10 receiver -> pc_p2_hardlanes_bigtreasure_hit.
```
