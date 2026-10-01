# Natural Sarai captor: FSM target, approach, attack, capture, carry and drop (#242/#457)

Lane 30 (Swooping Snitchbug `Sarai` ID 23 / Bumbling Snitchbug `Demon` ID 32).
This slice wires the previously isolated Sarai policy/FSM (`pc_p2_sarai_policy.h`,
`pc_p2_sarai_fsm.h`) onto the native two-mouth visual host so the private Sarai
host can acquire a live `naviMgr` captain, approach it, run the source Attack
capture window, attach the captain to a real mouth `CollPart`, carry it through
CatchFly and deliver a one-time damaging FallMeck drop, with no fixture-injected
frames, targets, END events, captures or drops.

## What changed

- `pc_port/pc_p2_sarai_captor.h` (new): dependency-free natural front end. It
  composes the Sarai source `getAttackableTarget` geometry from
  `pc_p2_sarai_policy.h` (`targetable`, `viewHalfAngle`'s `PI * DEG2RAD *
  mViewAngle` expression, territory/sight gates, alive/floor/self/stick
  filters) and adds capped-turn approach and the grab-range transition. It never
  touches captain stick state.
- `pc_port/pc_p2_sarai_host.{h,cpp}`: opt-in `enableNatural()`,
  `setNaturalMotions()`, `setNaturalPoseProfiles()`, `naturalPhase()`,
  `occupied()`, `captureWindowTicks()`, `forceDrop()` and `release()`, plus an
  `updateNatural()` path in `P2SaraiHost::update()`. It advances the isolated
  `p2sarai::Fsm` with live facts each frame, starts the matching source motion
  (wait1/move1/attack1/waitact2/waitact1) from the shared retail table, samples
  the matching pose bank, and reacts to the FSM outputs. Default-off, so the
  fixture-driven and production lines are unchanged.
- `tools/p2_sarai_captor_test.cpp` (new) and a CTest registration: standalone
  acquisition-timer, territory/view/sight, candidate-filter, capped-turn,
  approach-drive, grab-range and invalid-input tests. Warning clean under
  `-std=gnu++17 -Wall -Wextra`.
- `tools/p2_sarai_host_runtime.cpp`: new `capture` and `capture_idle` modes.
  The existing visual/pose mode is unchanged.

## Shared bridge reuse (unchanged)

The captain attachment reuses the existing P1/P2 captain bridge
(`pc_demon_capture`, `pc_demon_forced_release`, `pc_demon_owned_by`,
`pc_demon_owner_lost`, `pc_demon_release`) as the common mouth-stick captor.
No bridge, Navi, NaviState or teki semantics were changed; the bridge is only
called, never edited. Ownership/lifetime stays generation-qualified through
`P2SaraiHost::ownerToken()`. No second captain framework was introduced.

## Chain

1. `updateNatural()` builds the Sarai `TargetQuery`/`TargetCandidate` from the
   live captain against the stable rest mouth effector and steps
   `P2SaraiCaptor` (source three-second acquisition gate, territory/view/sight,
   capped turn, approach drive).
2. The FSM runs Wait/Move until `targetPresent` and the state motion ends, then
   enters Attack. The source `attackMayCatch()` window (`16 < frame <= 30`)
   raises `attemptCatch`.
3. In the window the host calls `pc_demon_capture` with the real
   `mMouths[0]` `CollPart` and its owner token; the captain is admitted from
   Walk (or Idle for `capture_idle`).
4. Attack END enters CatchFly; the sampled animated mouth carries the captain
   through the source clip while the captain stays in Walk/Idle.
5. FallMeck Key3 (`event.type == 3`) calls `pc_demon_forced_release` for a
   single 10-damage registered drop; the bridge detaches and the captain
   recovers to Walk.

## Observed evidence (natural, not injected)

Native head `d689d3d5b61b900e00d16c322d7142b9ae67ebde`, private build
`output/native-lane30-rebase-build` (`ninja -n pikmin_pc` = no work to do),
fixture built by `output/p2-main-review/scripts/build_pikmin2_fixture.py`.

Sarai fixture `output/p2-sarai-fsm-fixture-01` (`status=built`, clean source),
executable SHA-256
`0318EDAD87BA571912186A508394D3C21EA0E494EE0B27FC62A4FF882EC50EFD`.
Session `output/sarai-fsm-run-02/5667120ca5e64616aa279682714aace9`,
`PIKMIN_P2_ROOM_WINDOW=960x540`, 20-red baseline arena.

```text
P2_SARAI_HOST_WINDOW size=960x540 pos=373,263 display=1707x1067 centered=1
[capture] SARAI_NATURAL_BEGIN mode=capture target=Walk host=(0.00,100.00,100.00) captain=(0.00,100.00,160.00) state=0 neutral=0.0
[capture] SARAI_NATURAL mode=capture tick=120 phase=2 host=(1.99,29.80,111.94) cap=(-0.18,0.00,159.81) hp=100.0 state=0 stuck=0 occupied=0 window=0
[capture] SARAI_NATURAL mode=capture tick=210 phase=2 host=(6.96,29.80,148.08) cap=(-5.53,12.11,183.04) hp=100.0 state=0 stuck=1 occupied=1 window=16
[capture] SARAI_NATURAL mode=capture tick=600 phase=4 host=(6.96,29.80,148.08) cap=(9.68,35.37,178.91) hp=100.0 state=0 stuck=1 occupied=1 window=16
[capture] SARAI_NATURAL mode=capture tick=630 phase=1 host=(13.14,29.80,166.50) cap=(10.24,0.00,180.78) hp=90.0 state=36 stuck=0 occupied=0 window=16
PASS SARAI_HOST natural_captor_acquire_attack_capture_carry_drop (ticks=670 carry=410 hp=90.0 target=Walk)

[capture_idle] SARAI_NATURAL_BEGIN mode=capture_idle target=Idle host=(0.00,100.00,100.00) captain=(0.00,100.00,160.00) state=17 neutral=11.0
[capture_idle] SARAI_NATURAL mode=capture_idle tick=210 phase=2 host=(6.76,29.80,148.52) cap=(-17.36,12.11,176.73) hp=100.0 state=17 stuck=1 occupied=1 window=16
PASS SARAI_HOST natural_captor_acquire_attack_capture_carry_drop (ticks=675 carry=413 hp=90.0 target=Idle)

PASS SARAI_HOST model_two_mouths_pose_follow_teardown
```

The `capture` mode asserts acquisition/approach, the source Attack window, an
admitted capture on the real `mMouths[0]` part, at least 20 sustained carry
ticks with the captain in Walk, exactly one damaging drop and recovery; the
`capture_idle` mode repeats the chain with the captain genuinely Idle.

Demon regression fixture `output/p2-demon-sarai-regression-fixture-01`
(`status=built`, clean source), executable SHA-256
`D5B8B6C9F5C94764CD8BD1349ABBFDA3398506E5B68815A67F061EA285ABF836`.
Session `output/demon-sarai-regression-run-02/e1056a87c6db4ef297624b332b0ede3b`:

```text
PASS DEMON_HOST natural_captor_acquire_attack_capture_drop (ticks=299)
PASS DEMON_HOST natural_idle_captor_acquire_attack_capture_drop (ticks=297)
PASS DEMON_HOST ordinary_spawned_captor_acquire_attack_capture_drop (ticks=857)
PASS DEMON_HOST injected_capture_catchfly_drop_recovery
PASS DEMON_HOST live_owner_mouth_capture_release
PASS DEMON_HOST teardown
```

Standalone lane-30 headers (`p2_sarai_captor_test`, `p2_sarai_fsm_test`,
`p2_sarai_policy_test`, `p2_demon_captor_test`, `p2_demon_escape_test`,
`p2_demon_drop_policy_test`, `p2_demon_host_clock_test`) all PASS.

## Post-capture gates: escape, interruption, teardown (engine-free this round)

The lane reuses the shared P1/P2 captor bridge unchanged
(`pc_demon_capture`, `pc_demon_forced_release`, `pc_demon_release`,
`pc_demon_owner_lost`, `pc_demon_scene_exit`) and the registered
`NaviDemonEscapeState`; no shared bridge/state file was edited. Two lane-owned
additions make the Sarai route concrete:

- `pc_port/pc_p2_sarai_lifecycle.h` (new, engine-free): the lane's explicit
  transcription of the shared binding contract (owner generation token, mouth
  slot, stick object/part, revoked authority) plus the shared
  `P2DemonEscapeWindow`. `P2SaraiHost` uses it as the single occupancy/authority
  source (`occupied()`, capture, escape observation, interruption, release,
  scene exit) while still delegating every real side effect to the bridge.
- `tools/p2_sarai_captor_lifecycle_test.cpp` (new, CTest): escape-window
  accumulation and transfer, interruption clearing the stick pointers/authority,
  and teardown inert after release.

The fixture gains three modes that must be run next round (GL was not run this
round). All three begin from the same real natural capture with no injected
frame, target, END or capture:

```text
SARAI_HOST_MODE=natural_escape
  P2_SARAI_HOST_WINDOW size=960x540 ... centered=1
  SARAI_NATURAL_ESCAPE arm token=... input=controller_dpad_simulated lift=...
  SARAI_NATURAL_ESCAPE state=DemonEscape tick=... detached=1 edges=...
  PASS SARAI_HOST natural_captor_voluntary_escape (ticks=... edges=...)
SARAI_HOST_MODE=natural_interrupt
  PASS SARAI_HOST natural_captor_interruption_release_teardown (ticks=...)
SARAI_HOST_MODE=natural_teardown
  SARAI_NATURAL_TEARDOWN release state=0 ground=1
  PASS SARAI_HOST natural_captor_grounded_release_teardown (ticks=...)
```

`natural_escape` feeds synthesised production controller D-pad edges through
`Navi::doAI` (input-simulated controller state, not physical input) and raises
the frozen host 60 units so the source `Fall` state spans more than one frame.
`natural_interrupt` calls the shared forced-release entry (10 damage / 200
speed); `natural_teardown` uses the production grounded release.

## Limits / remaining work

- No patrol or turn-to-scan state is transcribed; the natural fixture uses the
  room-wide territory/sight the Demon lane also uses. Retail constants are
  narrower.
- The Sarai host is fixture-owned and not registered as a native teki actor; an
  ordinary spawned Sarai and native teki identity remain open.
- The captain state is held in Walk/Idle (a bridge-contract accommodation
  labelled in the fixture), not synthesised input.
- Admission uses the rest-pose effector while the carry follows the sampled
  animated joint; rendered mesh selection is not yet synchronised.
- Escape/interruption/teardown fixture modes land this round but their GL
  evidence, generated-seed admission and terrain/water/platform handling remain
  separate gates.
