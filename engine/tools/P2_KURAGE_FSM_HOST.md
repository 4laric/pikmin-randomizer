# Kurage/OniKurage flight-FSM host and autonomous Attack suction (lane 29, #243)

Lane 29 / native worktree `output/native-lane29` (branch
`opencode/p2-lane29-jellyfloat`) based on the approved native baseline
`f14c6851473ac1161be56c8b98f4f905232f3635`, then `4edb7bad` for the Lesser
slice. This document covers two slices:

1. **Lesser** — move the transcribed source Kurage flight lifecycle onto the
   bounded real host and connect the ordinary **Attack** state to the suction
   admission scan (the lane's primary remaining natural gate).
2. **Greater** — add the OniKurage (id 72) variant and its source `Drop` state.

The player-visible actor is still the private bounded host, not an ordinary
generated `TEKI_Frog`; that replacement is tracked separately.

## Lesser slice

`pc_port/pc_p2_kurage_arena.{h,cpp}`:

- Opt-in FSM authority: `pc_p2_kurage_arena_fsm_enable/enabled/state/altitude`.
  When enabled, the host's vertical motion and state come from
  `p2kurage::Fsm` (Wait/Move/Chase/Attack/...) instead of the preview sine.
- `getSearchedTarget` host approximation `findSuctionTarget()`: the first live
  Pikmin inside the source vertical suction window (`inSuctionWindow`) and
  `mAttackRadius` whose sticker is not the owner.
- The source Attack state starts the retail `attack.bca` clock
  (`pc_p2_retail_player.h`) on entry and consumes its KeyEvent 2/1 as the
  `p2kurage::In::keyEvent`; during the open suction interval the host calls
  `pc_p2_kurage_receiver_scan_admit`, so ordinary Attack itself initiates
  capture.  `p2retail::Player` advances in animation frames (30 fps), not
  seconds.
- `pc_p2_kurage_arena_set_owner_facts(hasHealth, bittered)` supplies the source
  bitter/zero-health pause gates; owner death
  (`pc_p2_kurage_arena_update(delta, false)`) releases through the existing
  captured-scale-restoring receiver path.
- `tools/p2_kurage_runtime.cpp`: `--flight-fsm-admission` and
  `--flight-fsm-death`.
- `tools/run_kurage_flight_fsm.py`: prepares a fresh room session from a base
  session and runs one scenario, recording a JSON provenance row and log.

## Greater (OniKurage) slice

- `pc_p2_kurage_arena_set_greater(true)` reconstructs the shared `Fsm` with
  `Variant::Greater`, which switches the pitch numerics and registers the
  OniKurage-only `Drop` state (`pc_p2_onikurage_fsm.h`).  `Pikmin` suction is
  OniKurage's Kurage-verbatim loop on the shared receiver, so it needs no new
  path.
- `pc_p2_kurage_arena_set_captain_held(bool)` is the labelled host seam for the
  Attack-END -> `Drop` route.  Real captain capture (`InteractSarai`, two mouth
  slots) is lane 12 provider work and stays **BLOCKED**; the seam exists only so
  the source `Drop` fall can be exercised.
- While in `State::Drop` the host integrates gravity (`kDropGravity`) and feeds
  `velocityY`/`dropShouldFinish` facts to the FSM.
- `tools/p2_kurage_runtime.cpp`: `--flight-fsm-greater` and
  `--flight-fsm-greater-drop`.

## Ordinary generated-actor slice

`pc_port/pc_p2_kurage_teki.{h,cpp}` — the real consumer (a generated
`TEKI_Frog` bound by the `p2-kurage-teki.txt` sidecar through
`GameCoreSection::finalSetup`):

- `pc_p2_kurage_teki_fsm_enable(true)` is opt-in; the default binding-only path
  (draw + receiver) is unchanged.
- When enabled, `pc_p2_kurage_teki_tick` runs the same source flight lifecycle
  and Attack-suction scan as the arena host: it drives the actor's `mSRT.t.y`
  from `p2kurage::Fsm`, starts the retail `attack.bca` clock on Attack entry
  and consumes KeyEvent 2/1, and admits nearby Pikmin while the suction window
  is open.
- Probes: `pc_p2_kurage_teki_fsm_enabled/state/auto_admissions/fsm_ticks`.
- Three source-faithfulness fixes found by this path: `attackPlaying` is set on
  a successful player start; only stomach-attached Pikmin count toward the
  source fall/flick threshold (mouth-travel Pikmin do not); the isolated
  preview leaves the day/UI overlay active, so the fixture clears it before
  arming (the arena scenarios already ran with it clear).
- `tools/p2_kurage_runtime.cpp` gains `--receiver-auto-fsm`;
  `tools/run_kurage_automatic_binding.py` gains `--scenario binding|auto-fsm`.

## Greater captain capture (lane 12 consumer)

`pc_port/pc_p2_kurage_arena.{h,cpp}` now composes the live captain with lane 12's
`P2CaptainPolicy` (`pc_p2_captain_policy.h`, #130) and the OniKurage
`MouthSlots` policy (`pc_p2_onikurage_mouth.h`):

- `pc_p2_kurage_arena_set_captain_target(P2CaptainPolicy*, captain, Navi*)`.
  The policy owns identity/ownership; the host owns the family-local capture
  during the Attack suction window and the bounded attach while held.
- Capture uses the source `getSearchedTarget`/`naviSearchAdmit` window; the
  slot policy (`capture`, `advanceDefaultOffset`, `isNaviSuck`) drives the FSM
  `naviSucked`/`naviSuckFinished`, so a real capture (not the earlier seam)
  routes Attack END -> `Drop`.
- Source-faithful release: the captain stays held through `Drop` -> `Land` ->
  `Ground`, and `GroundFlick`'s KEY3 `flickNearby` (real `flick2.bca`) releases
  it with the source `sep *= 50` knockback (`releaseCaptured` + `onDeath`), so
  the captain is never lost or duplicated.  Owner death and `kill` still release.
- Probes: `pc_p2_kurage_arena_captain_occupied/captured`.
- The isolated room has one real `Navi` mapped to captain A; captain B is a
  nominal present slot so the source zero-control guard is satisfied.  This is
  a labelled lane-29 bounded adapter, not lane-12 live-adapter acceptance (the
  lane-12 doc records the live `Navi`/`NaviMgr` adapter as its next slice).
- `tools/p2_kurage_runtime.cpp`: `--flight-fsm-greater-captain`.

## Real source animation clocks and the flick behavior

The bounded 30-frame motion-END stand-in is replaced, for non-Attack states, by
lane 08's sampled-animation contract (`pc_p2_sampled_clock.h`, #431):

- Durations come from the source BCA ANF1 headers; events come from
  `enemyanimmgr.txt`.  `dead1` 96f ({33,"2"},{93,"3"}), `wait` 35f (loop 0..34),
  `move1` 60f (loop 0..59), `type1` 75f ({32,"2"}), `type2` 20f (loop 0..19),
  `flick1` 60f ({16,"2"}), `flick2` 60f ({20,"2"},{30,"3"}).
- On each state change the host starts that state's clip; the crossed source
  events become FSM `KeyEvent`s and loop-wraps/one-shot completion become
  `motionFinished`.  Attack keeps the retail `attack.bca` Player that also owns
  the suction window.  States without an imported clip fall back to the bounded
  timer.
- `out.flickStick` (Kurage `flickStickPikmin`) now ejects the receiver-held
  Pikmin via `pc_p2_kurage_receiver_release_all`; `out.flickNearby` is logged.
- `tools/p2_kurage_runtime.cpp`: `--flight-fsm-stuck-flick` — admit a Pikmin,
  let the source fall timer pass the shake time, enter FlyFlick, and the real
  `flick1.bca` KEY2 ejects it.

## Per-state converted pose selection

`pc_port/pc_p2_kurage_visual.{h,cpp}` now loads the converted per-motion pose
mods (the 10 `Kurage/*.mod` the converter already produced), not just
wait/attack:

- `pc_p2_kurage_visual_shape(motionBase)` returns the pose for a source motion
  base name; `pc_p2_kurage_visual_motion_for_state(state)` maps the FSM state.
- Both hosts draw the pose for the current FSM state (arena host and the
  ordinary sidecar-bound actor), so the actor no longer shows only wait/attack.
  Missing pose files keep the wait/attack fallback.
- `P2_KURAGE_VISUAL_POSES lesser_optional=N/8 greater_optional=N/8` reports how
  many optional poses shipped per variant; `P2_KURAGE_POSE motion=<name>
  variant=<Lesser|Greater> available=1` logs each drawn state.
- `tools/run_kurage_flight_fsm.py`: `--models <dir>` copies the Lesser poses as
  `kurage_<motion>.mod`; `--greater-models <dir>` copies the OniKurage poses as
  `onikurage_<motion>.mod`.  Both accept the flat `<motion>.mod` converted
  layout or the `<motion>/patched.mod` material layout.  The Greater host draws
  the OniKurage pose when present and falls back to the Lesser pose.
- The material layout is lane 09's opt-in two-stage export
  (`experimental.pikmin2_kurage_envmap`, #286; it composes the #282 base-opacity
  fix and adds the NORMAL-generated environment stage with the `_UNUSED10=0xE6`
  marker consumed by the integrated `pc_p2_envmap` bridge):
  `py -3.12 -m experimental.pikmin2_kurage_envmap --model <enemy.bmd> --mod <converted pose.mod> --output <fresh>/<motion>`.
  Run `output/p2-lane29-envmap-01`: shipped `kurage_wait.mod` SHA-256
  `721A3316…b8e0` (the export's `after` hash), frame captured to
  `kurage-host-flight.ppm`.

This still does not animate within a pose (each converted MOD is a single static
pose); it selects the correct static source pose per state.

## Host walkToTarget (Move patrol / Chase pursuit)

The FSM leaves movement to the host ("walkToTarget movement"). The arena host now
implements it:

- `State::Move`: a deterministic patrol point within `kPatrolRadius` of the
  spawn (LCG); the host flies toward it at `kPatrolSpeed`, and the reported
  `distToTargetXZ` drives the source Move arrival (`< 25` units -> Wait).
- `State::Chase`: fly toward the searched Pikmin/captain target.
- Other states hover (no horizontal motion). A new patrol point is chosen on
  each Move entry.
- `tools/p2_kurage_runtime.cpp`: `--flight-fsm-patrol` (target parked out of
  range so the Wait -> Move path runs).

## Ordinary actor movement

The sidecar-bound generated actor now flies under the same FSM walkToTarget as
the arena host (Move patrol / Chase pursuit), not just the P1 proxy's ground
behavior:

- `pc_p2_kurage_teki_tick` drives the actor's `mSRT.t` vertically (FSM
  `heightVelocity`) and horizontally (patrol/Chase at `kPatrolSpeed`), and feeds
  `distToTargetXZ` back to the FSM.  Binding-only consumers are unchanged.
- `tools/run_kurage_automatic_binding.py --scenario auto-fsm-move`.

## Natural death cycle

The arena host consumes the FSM death outputs: `out.deathProcedure`/`bodyBomb`
(the Dead KEY3), `out.kill` (Dead END), plus `downEffect`/`flickEffect` logs.
On `out.kill` the host releases any held captain, releases the receiver's
Pikmin, marks itself dead and leaves the field.

- `pc_p2_kurage_arena_killed()` reports the Dead END.
- `tools/p2_kurage_runtime.cpp`: `--flight-fsm-death-cycle` — admit a Pikmin,
  set owner health 0, let the source `dead1.bca` clock run to its KEY3
  procedure, and verify the END releases the Pikmin with restored scale.

## Suction-candidate stability

The admission scenarios intermittently timed out because `Piki::mayIstick()`
rejects `PIKISTATE_LookAt`/`Flick`, which the live Piki AI can enter while
approaching a flying actor.  The fixture now re-asserts `PIKISTATE_Normal` when
it places the candidate (`placeCandidate`), so it stays stick-eligible.  Ordinary
admission 5/5 and arena admission 4/4 after the change (previously intermittent).

## Fixture stabilization

The private fixture birthed a Piki with only `init()` + a direct `mMode`
assignment.  Drawn free before capture (as the admission paths do), it could
fault in `ViewPiki::refresh -> CollInfo::updateInfo -> Vector3f::multMatrix`.
The fixture now mirrors the known-good init (`initColor`/`setFlower`), which
removed the crash across every scenario (0 crashes in 6/6 runs each of
admission/death/greater/greater-drop/ingestion/kill/transfer/stageexit).

## Evidence

Private build `output/native-lane29-build` (Ninja Release/MinGW gcc 16.2.0,
JAudio ON, test hooks OFF), `ninja -n pikmin_pc`: no work to do.
`bin/nectar.exe` SHA-256
`1BB6EAF75001C714A6E8856FB1344069F6D8C3F6AF1F54426D85B2E190701CCA`.

Fixture `output/p2-lane29-onikurage-fixture-01` (provenance `status=built`);
`fixture.exe` SHA-256
`BEB02FCE581226E5F8298E7FC859EF19AC312671905B8BD35DB7D61A074EA852`.  All runs
use `PIKMIN_P2_ROOM_WINDOW=960x540` (centred `373,263`) and a 20-red squad.

Greater captain route held through to GroundFlick (real `flick2.bca` KEY3):

```
P2_KURAGE_CAPTAIN_CAPTURED captain=0 epoch=1
state=11 (Drop) -> state=6 (Land) -> state=7 (Ground) -> state=10 (GroundFlick)
P2_KURAGE_FLICK_NEARBY
P2_KURAGE_CAPTAIN_RELEASED captain=0 state=10
PASS KURAGE_RUNTIME flight_fsm_greater_captain
```

Ordinary actor flies under FSM control:

```
P2_KURAGE_AUTO_FSM_ARMED ordinary_actor=1 enabled=1
P2_KURAGE_AUTO_FSM_MOVE_PASS moved=195.4 state=1
PASS KURAGE_RUNTIME ordinary_actor_fsm_patrol
```

Host walkToTarget (Move patrol -> Wait arrival):

```
P2_KURAGE_FSM state=1 (Wait) t0 -> state=2 (Move) t204 -> state=1 t322
P2_KURAGE_PATROL_PASS moved=72.0 from=-0.1,1.0 to=-5.3,67.8
PASS KURAGE_RUNTIME flight_fsm_patrol
```

Natural death (real `dead1.bca` KEY3 + END kill):

```
P2_KURAGE_FSM state=0 motion=1 ... ticks=204
P2_KURAGE_DEATH_PROCEDURE
P2_KURAGE_BODY_BOMB
P2_KURAGE_KILL
P2_KURAGE_DEATH_CYCLE_PASS killed=1 recv=0 piki_alive=1 scale_restored=1
PASS KURAGE_RUNTIME flight_fsm_death_cycle
```

Per-state converted poses, Lesser + Greater (10 + 10 mods shipped):

```
P2_KURAGE_VISUAL_POSES lesser_optional=8/8 greater_optional=8/8
P2_KURAGE_POSE motion=wait variant=Greater available=1
P2_KURAGE_POSE motion=attack variant=Greater available=1
P2_KURAGE_POSE motion=type1 variant=Greater available=1
```

Stuck -> flick -> eject (real `flick1.bca` KEY2):

```
P2_KURAGE_FSM state=1 motion=6 altitude=150.000 vy=-79.966 ticks=0
P2_KURAGE_FSM state=4 motion=10 altitude=98.650 vy=28.235 ticks=68
P2_KURAGE_FSM state=9 motion=3 altitude=100.374 vy=-62.244 ticks=340
P2_KURAGE_FLICK_STICK released=1
P2_KURAGE_STUCK_FLICK_PASS flick_released=1 alive=1 scale_restored=1 state=9
PASS KURAGE_RUNTIME flight_fsm_stuck_flick
```

Greater captain capture (lane 12 consumer):

```
P2_KURAGE_CAPTAIN_CAPTURED captain=0 epoch=1
P2_KURAGE_CAPTAIN_CAPTURED_PHASE captain=A state=Captured
P2_KURAGE_CAPTAIN_RELEASED captain=0 state=6
P2_KURAGE_GREATER_CAPTAIN_PASS captured=1 drop=1 released=1 occupied=0
PASS KURAGE_RUNTIME flight_fsm_greater_captain
```

Ordinary generated actor (frog profile, sidecar `P2_KURAGE_TEKI_1 1 201001 0`):

```
P2_KURAGE_AUTO_BIND_PASS generator=201001 type=0 source=GameCoreSection::finalSetup ...
P2_KURAGE_AUTO_FSM_ARMED ordinary_actor=1 enabled=1
P2_KURAGE_AUTO_FSM_ADMISSION_PASS state=4 auto=1 attach=1 stomach=1
PASS KURAGE_RUNTIME ordinary_actor_fsm_admission
```

Arena variants:

```
P2_KURAGE_FSM_ADMISSION_PASS variant=57 state=4 auto=1 attach=1 stomach=1 altitude=74.6
PASS KURAGE_RUNTIME flight_fsm_admission

P2_KURAGE_FSM_DEATH_PASS released=1 alive=1 scale_restored=1 state=4
PASS KURAGE_RUNTIME flight_fsm_interrupt

P2_KURAGE_ARENA_VARIANT variant=Greater id=72
P2_KURAGE_FSM_ADMISSION_PASS variant=72 state=4 auto=1 attach=1 stomach=1 altitude=67.7
PASS KURAGE_RUNTIME flight_fsm_admission

P2_KURAGE_ARENA_VARIANT variant=Greater id=72
P2_KURAGE_FSM_DROP_PASS variant=72 drop_seen=1 landed_state=6 altitude=75.7
PASS KURAGE_RUNTIME flight_fsm_greater_drop
```

Standalone policy gates (warning-clean `-std=gnu++17 -Wall -Wextra -Werror`):
`p2_kurage_flight_policy_test PASS checks=35`, `p2_kurage_fsm_test PASS
checks=35`.

## Admission gates

| Gate | Status | Note |
|---|---|---|
| A Identity/content | PARTIAL | Kurage (57) and OniKurage (72) variants run; the generated `TEKI_Frog` ordinary actor runs the Kurage FSM when the sidecar opts in. Visuals remain the private adapter. |
| B Source behavior | PARTIAL | FSM flight for both variants on the arena host and ordinary actor; real per-state source animation event/duration clocks; the converted per-state source pose is drawn for each FSM state. No within-pose skeletal playback, and states without an imported clip still use the bounded motion-END. |
| C Combat/receivers | PASS (bounded host + ordinary actor) | Ordinary Attack suction autonomously admits and attaches a live Pikmin in both hosts; Greater captures and releases a live captain through lane 12's policy. |
| D Death/drop/transport | PARTIAL | Natural FSM death releases owned Pikmin/captain and the host leaves the field; no corpse/pellet/Onion transport yet, and OniKurage `Drop` is not the Pikmin cargo path. |
| E Lifetime | PARTIAL | FSM-death and owner-death release restore scale; late birth/recycled address not exercised. |
| F Persistence | UNTESTED | No restart/save path in this slice. |
| G Product/mixed scene | UNTESTED | Private opt-in host, not a generated-session launch. |

## Remaining

Moving suction joint (converted MOD omits JNT1), within-pose skeletal playback
(the converted MODs are per-state static poses; only the source event/duration
clocks and per-state pose selection are adopted), replacing the underlying P1
Frog proxy behavior/motion with the full Jellyfloat host (the FSM currently
drives vertical motion while the P1 proxy still animates), materials/opacity,
corpse/reward, restart and generated-seed admission all remain open.  The Greater captain capture uses a lane-29 bounded
Navi adapter; lane 12's live `Navi`/`NaviMgr` host adapter is still the provider
gate for captain health/switch/knockout fidelity.
