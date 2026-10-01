# Natural Demon captor: target, approach, attack, capture and drop (#242)

Lane 30 (Bumbling Snitchbug `Demon` ID 32 / Swooping Snitchbug `Sarai` ID 23).
This slice adds the missing enemy-side front end so the private Demon host can
acquire a live captain, approach it and run the source Attack/CatchFly/FallMeck
clocks and the registered drop receiver without fixture-injected frames, targets
or END events.

## What changed

- `pc_port/pc_p2_demon_captor.h` (new): dependency-free source front end. It
  composes the existing `P2DemonTargetGate` (source `getAttackableTarget`
  territory/view/sight/three-second timer) and adds capped-turn approach and the
  grab-range transition to Attack. It never touches captain stick state.
- `tools/p2_demon_captor_test.cpp` (new): standalone policy tests (acquisition
  timer, territory/view/sight rejection, dead/stuck skip, capped turn, approach
  drive, grab-range attack request, invalid-input rejection, reset). Warning
  clean under `-std=gnu++17 -Wall -Wextra -Werror`.
- `pc_port/pc_p2_demon_host.{h,cpp}`: opt-in `enableNatural()`,
  `setNaturalMotions()`, `setNaturalPoseProfiles()` and `naturalPhase()`; a
  `P2DemonCaptor` plus an `updateNatural()` path in `P2DemonHost::update()`.
  Default-off, so fixture modes and the production line are unchanged. A
  `staticMouthCentre()` rest-pose effector is the shared reference for approach
  and grab admission; the animated mouth `CollPart` still carries the sampled
  joint for following. Source clocks advance in 30 fps frames capped to one frame
  per update.
- `tools/p2_demon_host_runtime.cpp`: new `natural` mode. It loads the real
  captain from `naviMgr`, holds it in `NAVISTATE_Walk` (the P1 bridge admits
  capture only from Walk; no input otherwise idles it), and asserts the full
  chain. The Demon target, movement, attack window and capture are not injected.

## Observed evidence (natural, not injected)

Session `output/demon-captor-run-06/693d627dab254b31bfc996c3c6e711e8`,
fixture `output/demon-captor-fixture-06` (`status=built`, expected native head
`57e6a52c`), exe SHA-256
`2F13FA440C6F14E0BF4C8D3D22F23E03CD1F1FBE537911D7806FCD364C02EF1D`,
`960x540` centred window, 20-red baseline arena. An earlier identical run at the
pre-commit head `e67005e8` is `output/demon-captor-run-05/8865cd69aff2401e87d0f7904d4b5665`.

```text
P2_DEMON_HOST_WINDOW size=960x540 pos=373,263 display=1707x1067 centered=1
DEMON_NATURAL_BEGIN host=(0.00,100.00,100.00) captain=(0.00,100.00,160.00)
DEMON_NATURAL tick=90  phase=1 host=(0.00,29.80,100.00)  cap=(...)  (timer)
DEMON_NATURAL tick=120 phase=1 host=(3.89,29.80,123.27)  (approach)
DEMON_NATURAL tick=150 phase=2 host=(6.80,29.80,143.17)  (source Attack window)
DEMON_NATURAL tick=180 phase=3 occupied=1 stuck=1        (real mouth capture)
DEMON_NATURAL tick=240 cap state=36 hp=...               (registered drop)
DEMON_STATE_DAMAGE generation=1 accepted=1 before=100.000 after=90.000
DEMON_STATE_HANDOFF next=0 quenched=1
PASS DEMON_HOST natural_captor_acquire_attack_capture_drop (ticks=296)
```

Regression modes from the same fixture/session: `drop`, `livecapture` and
`teardown` all `PASS`. Standalone `p2_demon_captor_test`, `p2_demon_escape_test`,
`p2_demon_drop_policy_test` and `p2_demon_host_clock_test` all PASS.

## Post-capture gates: escape, interruption, teardown

`natural_escape`, `natural_interrupt` and `natural_teardown` begin from the same
real capture (no injected frame, target, END or capture):

- `natural_escape`: a fixture `Kontroller` subclass feeds the production
  `Controller::updateCont()` contract alternating `KBBTN_DPAD_LEFT`/`RIGHT`
  edges, so `Navi::doAI`'s real `keyClick` sampling drives
  `pc_demon_escape_tick` with the engine RNG. This is **input-simulated
  controller state**, not physical keyboard input. The fixture raises the frozen
  host (whose live mouth still carries the real captain) 60 units so the source
  `Fall` state is observable before it grounds. It asserts mouth detach, entry
  into `NAVISTATE_DemonEscape`, return to `Walk` on `mGroundTriangle`, and no
  stale `getStickObject()`/`getStickPart()`.
- `natural_interrupt`: an external bounded forced release (`host.forceDrop`,
  10 damage / 200 speed) interrupts the carry; asserts detach, null stick
  pointers, revoked bridge authority, live captain, registered `DemonDrop`
  admission, then inert stale owner token, owner teardown and scene teardown.
- `natural_teardown`: production grounded `pc_demon_release` detaches without
  damage, keeps `Walk`, then owner and scene teardown stay inert.

Session `output/demon-captor-escape-run-01/66c8f4d3c53d47acbed4b654cafd21ff`,
fixture `output/demon-captor-escape-fixture-01` (`status=built`, expected native
head `920e2a80`), exe SHA-256
`88A298DECE9EC6A8250603BFB40A3CB18A5EE64182892E561C109F4545639F48`, `960x540`
centred window. Regressions `natural`, `drop`, `livecapture` and `teardown` pass
from the same fixture/session.

```text
DEMON_NATURAL_ESCAPE arm token=1 input=controller_dpad_simulated lift=89.80
DEMON_NATURAL_ESCAPE state=DemonEscape tick=188 cap=(1.03,58.96,186.88) detached=1 edges=23
PASS DEMON_HOST natural_captor_voluntary_escape (ticks=201 edges=36)
DEMON_STATE_BEGIN generation=1 actual_y=-400.000 target_y=-200.000
PASS DEMON_HOST natural_captor_interruption_release_teardown (ticks=173)
DEMON_NATURAL_TEARDOWN release state=0 ground=1
PASS DEMON_HOST natural_captor_grounded_release_teardown (ticks=164)
```

## Ordinary spawned captor (manager-bound, no fixture-placed captain)

`ordinary` is the product-path mode. The production manager setup binds the
Demon host to an actor the arena actually spawned and enables the natural front
end, so the production per-actor hook
(`pc_p2_demon_manager_update_actor` -> `P2DemonHost::update`) drives acquisition,
approach, the source Attack window, `pc_demon_capture`, CatchFly/FallMeck and the
registered drop. The fixture only enables the mode and observes; it never loads
its own host, never positions the captain and never issues a frame, target, END,
capture or drop.

How the bindable actor is spawned and bound:

- `scripts/preview_pikmin2_room.generator()` builds the private stage's
  `chal0/default.gen` with exactly one enemy generator: the Dwarf Bulborb
  template (`TEKI_Chappy`) placed at `(185, 0, -180)`, the only enemy in the
  converted room. Its generator id is `385875968`, teki type `3`.
- `pc_p2_demon_manager_setup()` with `PIKMIN_DEMON_ORDINARY=1` finds that single
  spawned actor (explicit identity `PIKMIN_DEMON_ORDINARY_GENERATOR`/
  `PIKMIN_DEMON_ORDINARY_TYPE`, or the unique `TEKI_Chappy` fallback), loads the
  staged converted `demon0.mod` with `demon-mouths.txt`, preloads the attack/
  CatchFly/FallMeck pose banks, binds via `pc_p2_demon_manager_bind`, seats the
  host at the actor's spawned position and calls `enableNatural`.
  `pc_p2_demon_manager_update_actor` no longer snaps a natural host to the anchor
  each frame (the anchor is the lifetime/identity token); non-natural hosts keep
  the original following behaviour. Default-off: with the env unset all existing
  manager and fixture behaviour is unchanged.
- The converted Demon assets are staged from the known-good session
  (`demon0.mod`/`demon17.mod`, `attack1_*.mod`, `waitact*.mod`, the `demon*.txt`
  mouth/pose/event banks); no new conversion is introduced.

Fixture/session: `output/demon-ordinary-fixture-01` (`status=built`, expected
native head `75780452139de5004e9d30c74c5f33ecb54cd57c`, exe SHA-256
`59233286016377DEA32A990FF32C5BD7C371A8BC26CCC0A4BA898C7FD5ED2674`), session
`output/demon-ordinary-run-01/a3872390075e4e2780897638ac286318`, `960x540`
centred window, 20-red baseline arena. Helper `output/run_demon_ordinary.py`.

```text
P2_DEMON_HOST_WINDOW size=960x540 pos=373,263 display=1707x1067 centered=1
DEMON_ORDINARY_BIND generator=385875968 type=3 anchor=(148.79,0.00,-149.01) captain=(121.49,0.00,157.90)
DEMON_ORDINARY tick=420 phase=2 cap=(122.70,0.00,157.51) hp=100.0 state=0 stuck=0 bound=0
DEMON_ORDINARY tick=480 phase=3 cap=(158.91,8.46,152.18) hp=100.0 state=0 stuck=1 bound=1
DEMON_STATE_BEGIN generation=1 actual_y=-400.000 target_y=-200.000
DEMON_STATE_DAMAGE generation=1 accepted=1 before=100.000 after=90.000
DEMON_ORDINARY tick=840 phase=1 cap=(156.54,0.00,108.80) hp=90.0 state=36 stuck=0 bound=0
PASS DEMON_HOST ordinary_spawned_captor_acquire_attack_capture_drop (ticks=865)
```

The anchor actor is the spawned `TEKI_Chappy`; the captain's `(121.49,0,157.90)`
is its untouched arena start (the `DEMON_ORDINARY_BIND` line prints it before any
capture). Regressions from the same fixture/session all PASS: `natural`,
`natural_escape`, `natural_interrupt`, `natural_teardown`, `drop`,
`livecapture`, `teardown`.

Fixture-driven / approximation notes (not natural):

- No patrol or turn-to-scan state is transcribed, so the ordinary enable widens
  the view cone to 360 degrees and the territory/sight radii to cover the room;
  retail view-angle and territory constants are narrower. Approach speed (30),
  turn cap (20 deg) and grab range (12) keep the natural-fixture values.
- The captain is held in `NAVISTATE_Walk` (state only, never repositioned)
  because the P1 bridge admits capture only from Walk.
- Admission still uses the rest-pose mouth effector while the stick follows the
  sampled animated joint.

## Limits

- The captain is held in Walk for the duration of the approach because the P1
  bridge only admits capture from Walk; this is a bridge-contract accommodation,
  not an injected capture. Retail P2 targets idling captains; relaxing the bridge
  state gate is a shared (#186) decision and is not done here.
- The `natural*` modes use a fixture-placed starting offset and captain; they are
  not a generated-seed or manager-spawned encounter. The separate `ordinary` mode
  above is the manager-bound spawned-captor path and leaves the captain at its
  arena start.
- Rendered animated-mouth parity is not established; admission uses the rest
  effector while the stick follows the sampled joint.
- Water/platform/slope terrain, scene teardown during drop, and `Sarai` ID 23
  source actor remain separate gates.
- The escape gate enters through `Navi::doAI` but its D-pad source is synthesised
  controller state, not a physical keyboard/device edge, and the frozen host is
  repositioned 60 units so the Fall state spans more than one frame; neither is
  an injected capture, frame, target or END.

Reproduction: stage the demon conversion from a known-good session (pose banks,
`demon-mouths.txt`, `demon-retail-events.txt`, `demon*.mod`) into a fresh
`preview_pikmin2_room.prepare()` arena, copy `fixture.exe`, then run
`DEMON_HOST_MODE=natural PIKMIN_P2_ROOM_WINDOW=960x540 fixture.exe
--experimental-pikmin2-room` (helper `output/run_demon_natural.py`). For the
ordinary spawned-captor path stage with `output/run_demon_ordinary.py` and run
`DEMON_HOST_MODE=ordinary`; the fixture sets `PIKMIN_DEMON_ORDINARY=1` plus the
`385875968`/`3` anchor identity itself.
