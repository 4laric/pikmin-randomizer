# Pikmin 2 BombSarai — carrier FSM integration (#244)

Status: **implemented, fixtures + runtime probes executed, PASS** against
retail GPVE01 rev 0 assets. This slice replaces the runtime harness's
explicit supply/throw events with the lane-owned 13-state carrier FSM
driving the existing bomb/clock/terrain/hover/blast policies through the
arena seam.

## Files

Native lane branch `codex/p2-bombsarai-policy` (lane-owned files only):

- `pc_port/pc_p2_bombsarai_fsm.h` / `.cpp` — new: engine-free 13-state FSM
  policy (Dead, Damage, Wait, BombWait, Move, BombMove, Supply, Release,
  Fall, TakeOff1/2, Flick, BombFlick) transcribed from the audit.
- `pc_port/pc_p2_bombsarai_arena.h` / `.cpp` — rewritten: the seam is now
  FSM-driven. It senses targets from the pinned receiver list, generates
  keyframe pulses from profile timings, applies the tick-indexed host-event
  script, and performs FSM-requested effects (supply/throw) through the
  bomb pool and hover policies.
- `tools/p2_bombsarai_fsm_test.cpp` — new standalone transition fixture.
- `tools/p2_bombsarai_runtime.cpp` — rewritten: map probes + three
  FSM-driven scenarios, no harness events.
- `tools/p2-bombsarai-arena.txt` — unchanged content (defaults now drive
  the full approach scenario); `tools/p2-bombsarai-arena-purple.txt` and
  `tools/p2-bombsarai-arena-death.txt` — new scenario profiles with
  `events` scripts.

## FSM policy design

- One 30 Hz source tick per `update`, matching the lane clock adapter.
- Host-fed inputs: health, carrying flag, stuck census (normal/Purple),
  target sensing (territory / attackable / attack-XZ), waypoint arrival,
  height above ground, animation keyframes (`animEnd`, `keyEvent2`),
  bitter queue, kill event, and the flick roll (uniform [0,1)). The policy
  owns no RNG, no clip lengths, no creature, map or pool state.
- Outputs per tick: current state, entry pulse, `supplyRequested` (Supply
  init side effect, BombSaraiState.cpp:466), `throwRequested` + kind
  (Release lob at KEYEVENT_2, Fall skyward eject at KEYEVENT_2,
  unconditional zero-velocity Death drop on kill), `flickRequested`,
  `fastTakeOff` (TakeOff2 rise factor 6), `untargetable` (informational).
- Shared height gate `getNextStateOnHeight` (BombSarai.cpp:314-340):
  consulted in Wait/BombWait/Move/BombMove only above fp03 (retail 50) or
  past the 5 s state-timer gate. Health ≤ 0 or any stuck Purple forces
  Fall; 1–5 stuck rolls the interpolated flick chance (retail fp31 0.2 →
  fp32 0.8, linear over the clamped census) → Flick/BombFlick by carriage,
  roll failure defaults to Fall.
- Release triggers in BombWait/BombMove in source priority: 15 s carry cap,
  `isTargetAttackable`, attack-radius XZ; bitter queue transits to Fall
  (including mid-BombFlick). Damage finishes on health ≤ 0, no stuck
  Pikmin, or the retail fp40 0.8 s struggle cap; TakeOff1/2 split at 50 %
  of retail max health 1500.

## Seam design decisions

- **Keyframes:** the FSM owns no animation lengths (converter #128 work).
  The seam supplies a pinned per-state schedule (profile `timing` line;
  defaults wait/move/bombwait/bombmove 30, supply/release/fall 10,
  damage 24 = 0.8 s, takeoff1 45 / takeoff2 21 from the audit's
  untargetable-frame counts, flick 20), KEYEVENT_2 at half the state ticks.
  These are harness stand-ins, documented as not retail .bca durations.
- **Target sensing:** nearest alive Navi/Pikmin receiver against retail
  radii — territory 200 (fp09), attackable 100 / 45° (fp20/fp21), attack
  XZ 50 (fp22 `mAttackRadius`). The pinned carrier never turns; the angle
  gate uses the profile yaw. The `approach` scenario releases via the XZ
  gate because the navi sits 90° off facing (attackable angle fails) —
  matching the source's independent gates.
- **Event script:** profile `event` lines (`stuck`, `health`, `kill`,
  `bitter` at a tick) stand in for Pikmin sticking, damage intake, bitter
  spray and kills, which a real host derives from creature interactions.
- **Carrier liveness:** after a scripted kill the seam fails carrier-token
  validation, so the later blast attributes Navi/Pikmin damage to the bomb
  itself (source `mCarrier == nullptr` fallback, bombState.cpp:167-172) —
  exercised live in the `death` scenario.
- **Carrier crash motion:** Fall integrates the retail gravity (560 u/s²)
  to the sampled floor; Damage/Dead are grounded (this is what makes the
  source's grounded-only `bombCallBack` immunity meaningful); TakeOff
  resumes hover, TakeOff2 with the fast rise factor.
- **Pool exhaustion:** with the bomb still in flight, the FSM's repeated
  Supply entries return nullptr (one active bomb per carrier token,
  pool capacity 2 = `mChildNum`) and the carrier cycles harmlessly —
  visible in the `approach` marker stream (Supply at 81/132/183 with no
  `FSM_SUPPLY` birth), matching the source's silent no-payload tolerance.

## Bomb trace radius — resolved

The engine extraction flagged that no disc parm is literally named "bomb
trace radius" and tabulated the candidates sight 700 (fp12) / attackable
range 30 (fp20) / blast 90 (fp22). **None of them is the trace radius:**
fp12 視界距離 and fp20 攻撃可能範囲 are enemy *search* distances consumed by
AI perception, and fp22 is the *damage* volume (`mAttackRadius`) — all
gameplay gates, not collision geometry. The bomb's `MoveTrace` sphere
radius comes from its collision parts, and the extracted
`bomb/enemycoll.txt` gives root radius 20 with child radius 15. The lane
keeps **15** (the child part that contacts the world), already wired in
the arena profile (`bomb ... 15 ...`) and validated by the floor/wall
probes and all three blast landings against real room geometry. Sight 700
and attackable 30 remain unused by this lane (no AI perception); blast 90
is wired as the blast radius, not the trace radius.

## Fixture and runtime evidence (executed this slice)

Standalone, warning-clean (`-std=gnu++17 -Wall -Wextra -Werror`, MinGW GCC
16.2), all pass: bomb, clock, terrain, hover, blast, and the new
`p2_bombsarai_fsm_test` (`PASS BOMBSARAI_FSM`) covering: happy-path
transitions, 15 s carry cap, bitter exits from BombWait/BombMove/BombFlick,
Purple-forced Fall with the altitude/timer gate closed and open, flick
probability at 1 and 5 stuck with success/failure rolls, Flick/BombFlick
END returns, kill-with-payload Death drop from a carrying state and
terminal Dead, Fall finish near floor vs dead-on-arrival, the 50 %
TakeOff1/2 health split and the retail 0.8 s struggle cap.

Runtime fixture against the retail-asset room preview (same build/run
procedure as `PIKMIN2_BOMBSARAI_RUNTIME_EVIDENCE.md`; full log
`output/p2_bombsarai_runtime_run2.log`, gitignored), exit 0. Verbatim
marker stream (condensed only where the FSM idles in a state):

```
P2_BOMBSARAI_FLOOR_PROBE ground=-0.000000 center=5.000000 floor=1
P2_BOMBSARAI_WALL_PROBE_PASS
P2_BOMBSARAI_MAP_PROBES_PASS

P2_BOMBSARAI_SCENARIO_BEGIN scenario=approach
P2_BOMBSARAI_FSM_ENTER scenario=approach state=Wait tick=1
P2_BOMBSARAI_FSM_ENTER scenario=approach state=Supply tick=30
P2_BOMBSARAI_FSM_SUPPLY scenario=approach tick=30
P2_BOMBSARAI_FSM_ENTER scenario=approach state=BombMove tick=40
P2_BOMBSARAI_FSM_ENTER scenario=approach state=Release tick=41
P2_BOMBSARAI_FSM_THROW scenario=approach kind=Release tick=46
P2_BOMBSARAI_FSM_ENTER scenario=approach state=Wait tick=51
(FSM re-enters Supply at 81/132/183 with the bomb in flight: no birth,
 silent pool guard)
P2_BOMBSARAI_BLAST scenario=approach ticks=209 traces=19 floors=1 walls=0 hits=3 carrier_dead=0
P2_BOMBSARAI_HIT scenario=approach id=501 kind=0 damage=500.000 self=1 token=0
P2_BOMBSARAI_HIT scenario=approach id=502 kind=1 damage=10.000 self=0 token=9001
P2_BOMBSARAI_HIT scenario=approach id=503 kind=2 damage=10.000 self=0 token=9001
P2_BOMBSARAI_SCENARIO_PASS scenario=approach

P2_BOMBSARAI_SCENARIO_BEGIN scenario=purple
P2_BOMBSARAI_FSM_ENTER scenario=purple state=Supply tick=30
P2_BOMBSARAI_FSM_ENTER scenario=purple state=BombMove tick=40
P2_BOMBSARAI_FSM_ENTER scenario=purple state=Fall tick=50
P2_BOMBSARAI_FSM_THROW scenario=purple kind=Fall tick=55
P2_BOMBSARAI_FSM_ENTER scenario=purple state=Damage tick=60
P2_BOMBSARAI_FSM_ENTER scenario=purple state=TakeOff1 tick=84
P2_BOMBSARAI_FSM_ENTER scenario=purple state=Move tick=129
P2_BOMBSARAI_BLAST scenario=purple ticks=236 traces=37 floors=1 walls=0 hits=3 carrier_dead=0
P2_BOMBSARAI_SCENARIO_PASS scenario=purple

P2_BOMBSARAI_SCENARIO_BEGIN scenario=death
P2_BOMBSARAI_FSM_ENTER scenario=death state=Supply tick=30
P2_BOMBSARAI_FSM_ENTER scenario=death state=BombMove tick=40
P2_BOMBSARAI_FSM_ENTER scenario=death state=Release tick=41
P2_BOMBSARAI_FSM_ENTER scenario=death state=Dead tick=45
P2_BOMBSARAI_FSM_THROW scenario=death kind=Death tick=45
P2_BOMBSARAI_BLAST scenario=death ticks=201 traces=12 floors=1 walls=0 hits=3 carrier_dead=1
P2_BOMBSARAI_HIT scenario=death id=501 kind=0 damage=500.000 self=1 token=0
P2_BOMBSARAI_HIT scenario=death id=502 kind=1 damage=10.000 self=1 token=0
P2_BOMBSARAI_HIT scenario=death id=503 kind=2 damage=10.000 self=1 token=0
P2_BOMBSARAI_SCENARIO_PASS scenario=death
PASS BOMBSARAI_RUNTIME
```

Reading of the evidence:

- `approach`: the FSM itself walks Wait → Supply (bomb birthed at state
  init, tick 30) → BombMove → Release (XZ attack gate) → Release lob at
  KEYEVENT_2 (tick 46) → Wait; blast at tick 209 routes the retail volume
  (teki 500 self, navi/piki 10 with carrier token 9001).
- `purple`: a scripted Purple stick at tick 50 forces Fall through the
  height gate while carrying; the skyward eject (Fall kind) fires at
  KEYEVENT_2 (tick 55); the carrier crashes, struggles 0.8 s (retail
  fp40), and re-flies via TakeOff1 (full health > 50 % split) to Move and
  a fresh Supply cycle — the full bitter-free recovery loop.
- `death`: a scripted kill at tick 45 (in Release, before its KEYEVENT_2)
  preempts the lob with the unconditional zero-velocity Death drop; the
  blast at tick 201 attributes Navi/Pikmin hits to the bomb itself
  (`self=1 token=0`) because the dead carrier's token fails validation.
- One scenario-layout fix was needed during bring-up: the purple profile
  originally placed a piki 79 units ahead of the carrier, inside the
  retail 100/45° attackable cone, so the FSM legitimately released early;
  the receiver moved to 150 units. This was a profile layout bug, not an
  FSM defect — the FSM behavior was source-correct.

## Remaining open items (unchanged unless noted)

- Keyframe timings are harness stand-ins; converter (#128) should supply
  retail .bca durations and KEYEVENT_2 frames per state, replacing the
  profile `timing` line.
- `kamu_jnt1` capture-joint transform now follows the carrier: the profile
  `joint` is a body-relative offset, rotated by the carrier yaw and added to
  the hover-integrated body origin each tick, so the captured payload rides the
  moving carrier (hover bob + facing) instead of the prior static world point
  (`P2BombSaraiBomb::followJoint` + `P2BombSaraiJoint::compute`,
  `pc_p2_bombsarai_joint.h`). The real animated skeletal joint transform (per
  clip/pose) remains #128 converter work.
- Flick effects (flickStickPikmin knockback/damage) are host-owned and not
  routed to receivers yet; only the FSM decision and `flickRequested`
  output exist.
- Horizontal `walkToTarget` movement is not integrated (pinned carrier);
  Move/BombMove exercise transitions only, `waypointReached` never fires
  in the runtime scenarios.
- Multi-carrier pool behavior against the real shared Bomb manager limit
  and bomb-on-bomb induction (`ip02` = 15 retail) routing remain open.
- Save/resume and cave/day transition semantics for carried/in-flight/
  armed bombs remain open (audit persistence caveat).
- Visual assets still debug markers only.
