# Fuefuki follow-locomotion policy (#245)

Successor of the Fuefuki binding seam (`P2_FUEFUKI_BINDING.md`) and the
remaining "follow locomotion has no P1 follow-teki equivalent" gap. This slice
implements the ActTeki follower half of the whistle-theft contract — the beetle
footmark trail and the per-Pikmin footprint seek — as an engine-free policy and
connects it to the live host's real Pikmin movement API. Source revision:
projectPiki/pikmin2 632af93787b9c95b63f0c13be32b161375ce3a96 (US GPVE01 rev 0),
read-only under native/pikmin2-research.

## Where the missing behavior came from

The earlier slices implemented *who the beetle holds* (interference policy) and
*which state it is in* (FSM), but a held Pikmin did not move: the source follow
action is `PikiAI::ActTeki`, and P1 has no equivalent. This slice ports that
action's decision logic and gives the host a movement command to apply.

- `Fuefuki.cpp::Obj::updateFootmarks` (509) + `Game::Footmarks`
  (`src/plugProjectKandoU/gameFootmark.cpp`): the beetle drops up to 10 marks,
  one every `|frameCounterDelta| > 2.5` frames, skipping a step shorter than 20
  units from the previous mark.
- `PikiAI::ActTeki` (`src/plugProjectKandoU/aiTeki.cpp`): `init` (27),
  `exec` (62), `makeTarget` (119), `test_0` (178), `setTimer` (254) with
  `FOLLOW_DISTANCE 100`.

## Lane-owned files

- `pc_port/pc_p2_fuefuki_follow.h` — `P2FuefukiFootmarks` (mirrors
  `Game::Footmarks`, alloc 10, recency `get`) and `P2FuefukiFollowController`
  (beetle trail recording + per-follower `makeTarget`/`test_0`/`setTimer`).
- `tools/p2_fuefuki_follow_test.cpp` — policy fixture (this slice).
- `tools/p2_fuefuki_follow_binding_test.cpp` — seam fixture.
- `tools/p2_fuefuki_follow_runtime.cpp` — real-GL runtime fixture
  (`P2_FUEFUKI_FOLLOW_RUNTIME_EVIDENCE.md`).
- `pc_port/pc_p2_fuefuki_binding.h` — optional `followerSample`/`followDrive`/
  `randFloat` host callbacks, `P2FuefukiFollowMove` output, per-tick drive.
- `pc_port/pc_p2_hardlanes.cpp` — live host adapter over the real `pikiMgr`
  squad and the Napkid beetle vehicle.

## Host contract

- Fixed 30 Hz ticks, no wall clock. The beetle position/velocity come from the
  per-tick `P2FuefukiProbeResult` (`x,z,vx,vz`); follower positions come from
  the optional `P2FuefukiFollowerSampleFn`. A `false` sample skips that
  follower for the tick without releasing it (the FSM still owns release).
- The controller emits one `P2FuefukiFollowMove` per held Pikmin per tick:
  `stop` (source `mTargetVelocity = 0` in TFS_Parent / on arrival) or
  `speed` + unit `dir` (source `Piki::setSpeed(mMoveSpeed, dirToFootprint)`).
  `hasMove == false` means no decision (unclaimed / missing sample).
- Claims/releases mirror the interference policy exactly: `claim` on an
  accepted cast tick, `release` on the suspend/panic release and on kill.
- Randomness (`0.5 * randFloat() + 0.5`, `setTimer`) comes from the optional
  `P2FuefukiRandFn`; a deterministic LCG is used when it is absent. The
  controller never touches captain ownership.

## Source fidelity notes

- `makeTarget` is reproduced literally: the source never updates
  `distanceToFootstep` inside the scan, so the first mark within
  `FOLLOW_DISTANCE` walking the recency list from oldest to newest wins. The
  lane's fixture pins that exact selection rather than a "nearest" reading of
  the comment.
- The source's second `dist < FOLLOW_DISTANCE/2` direction-blend branch is
  unreachable (the earlier branch returns); it is kept for fidelity.
- Footmark cadence: the source compares integer frame counters with `> 2.5`
  (>=3 retail frames at 60 fps). The bridge runs on the FSM's 30 Hz clock and
  uses a time accumulator with `footmarkInterval = 2.5/60 s` so the wall-clock
  cadence is preserved; the exact frame-quantised edge is not. The first
  update always records (source `mLastUpdateTime == 0` vs a live frame timer).

## Live host application (labeled approximation)

`pc_p2_hardlanes.cpp` applies the command to the real P1 Pikmin:

```
piki->setSpeed(move.speed, Vector3f(dirX, 0, dirZ));   // faithful source drive
piki->mVolatileVelocity.set(dirX * piki->mMoveSpeed, 0, dirZ * piki->mMoveSpeed);
```

The `setSpeed` call is the source-faithful path, but P1's `ActFree` overwrites
`mTargetVelocity` inside `Creature::updateAI` before `Creature::moveVelocity`
each frame, so the drive alone produces no sustained motion. The second line
seeds the volatile impulse channel (`Creature::mVolatileVelocity`, already used
for flicks) so the follow motion is actually realized until a dedicated P1
follow action exists. This is an **explicit approximation**, not source
parity: it is an impulse channel, it bypasses `ActFree`'s own steering, and it
should be removed when provider lane 12 (captains/squad follow interface)
supplies the real action. Startup logs
`follow_locomotion=actteki_volatile_approx`.

## Fixture evidence

```
g++ -std=c++17 -Wall -Wextra -Werror -Ipc_port tools/p2_fuefuki_follow_test.cpp -o ../p2_fuefuki_follow_test.exe
../p2_fuefuki_follow_test.exe             # PASS p2_fuefuki_follow_test
g++ -std=c++17 -Wall -Wextra -Werror -Ipc_port tools/p2_fuefuki_follow_binding_test.cpp -o ../p2_fuefuki_follow_binding_test.exe
../p2_fuefuki_follow_binding_test.exe     # PASS p2_fuefuki_follow_binding_test
```

Coverage (policy): mark ring cap 10 and recency order; the 20-unit spacing
filter; first-update recording and the 30 Hz interval; malformed delta
rejection; claim/release idempotence; TFS_Parent -> TFS_Footprint acquisition;
oldest-within-`FOLLOW_DISTANCE` target selection; 0.5/1.0 near-speed bounds from
an injected `randFloat`; arrival -> Parent with a re-armed timer; far-follower
full speed; unit direction. Coverage (seam): claim registers a follower and the
first tick emits a stop then a move; the emitted near speed and direction; owner
death releases the follower and stops commands; a failed sample skips the
follower; the seam is inactive unless both callbacks are supplied.

The existing Fuefuki fixtures were re-run after the header change with no
regression: `p2_fuefuki_interference_policy_test`, `p2_fuefuki_fsm_test`,
`p2_fuefuki_binding_test`, `p2_fuefuki_suspend_fallback_test` all PASS.

## Real-GL runtime (PASS)

`tools/p2_fuefuki_follow_runtime.cpp` was executed on a real SDL2/OpenGL
window against the retail room: the real squad claim produced 3 followers and
follower 1 walked 70.0 → 50.0 units toward the beetle in 8 frames (stopping at
the source arrival threshold), with zero ownership writes and held Pikmin left
in `FreeMode`. Markers, provenance and the exact commands are in
`P2_FUEFUKI_FOLLOW_RUNTIME_EVIDENCE.md`.

## Remaining gaps

- **No dedicated P1 follow action.** The volatile impulse is an approximation;
  sustained steering, collision response and the final approach stop need the
  provider-12 follow action or an equivalent `ActTeki` port in the Piki AI.
- **Beetle locomotion.** The Napkid proxy is static, so followers converge on
  the trail instead of trailing a moving beetle; a moving beetle needs a real
  actor/placement (provider 09 assets + #186 arena).
- **Panic state.** Released followers still stay in `PIKISTATE_Normal` (no
  verified P1 panic state); reclaim continues through the real whistle gather.
