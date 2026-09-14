# DangoMushi Turn vulnerability + flip hazard policy (#174 / #376)

Lane 25 next bounded slice: the two Segmented Crawbster (94, DangoMushi)
behaviors the #407 native FSM explicitly left out, implemented as an engine-free
decision module.

Implementation owner: Codex via shared account `4laric`. Executing session:
opencode (deepseek-v4.1-flash), 2026-09-13. Native candidate
`opencode/p2-longlegs-fsm` head `e94e521e`, base `f9e139d8` (never pushed to
native origin). Patch: `native-candidates/dangomushi-hazard/`.

## What this slice is

The existing candidate FSM (`opencode/p2-species-snagret` @ `8ae1e5b4`,
`pc_p2_dangomushi.cpp`) reproduces Stay/Appear/Wait/Move/Attack/Turn/Recover/
Flick but records:

> the Turn LOOP_START invulnerability, the falling Rock/Egg child spawner and
> the `dangomushi.brk` material loop are not reproduced

This slice supplies the first two as a pure policy:

- `pc_port/pc_p2_dangomushi_hazard.h` / `.cpp`
- `tools/p2_dangomushi_hazard_test.cpp`
- `CMakeLists.txt`: policy added to `pikmin_pc`; fixture registered as ctest
  `p2_dangomushi_hazard_test`.

The host owns the animation clock, collision parts and the Rock/Egg managers;
the policy decides *what* to spawn, *how long* it lives and *when* the body is
damageable.

## Source mapping

| Behavior | Source fact | Policy |
|---|---|---|
| Vulnerability window | bod0/bod1 become stickable and `EB_Invulnerable` clears only between the turn clip loop-start key and key 3 (`turn` keys 32:0 … 108:3) | `stickable` true only while `turnLoopStartFrame <= frame < turnKey3Frame`; `invulnerable = !stickable` |
| Rock rain | Turn rains 10 `Rock` enemies, 30 s lifetime, around the active captain | `rocksToSpawn` 10 on Turn entry, `rockLifetime` 30 |
| Rock budget | 30 Rocks reserved per Crawbster | `rockBudget` cap; `rocksRemaining` |
| Egg | one `Egg` at home with probability equal to the captain's group share of all Pikmin | `eggRequested` when `eggRoll < activeCaptainGroupShare` |
| Egg budget | 10 Eggs reserved per Crawbster | `eggBudget` cap; `eggsRemaining` |
| Determinism | fixture placement must be reproducible | `rockOffset()` deterministic ring, no engine RNG |

## Six-gate status for this commit

| Gate | Status | Note |
|---|---|---|
| 1. Exact identity and spawn | source-backed audit | Crawbster identity from the audit |
| 2. Autonomous movement and animation | UNTESTED | belongs to the #407 FSM, unchanged |
| 3. Attacks and receivers | PARTIAL | stickable window now modelled; receiver host unchanged |
| 4. Death and corpse | UNTESTED | #407 |
| 5. Actual transport and reward | UNTESTED | lane 06 |
| 6. Cleanup and re-entry | UNTESTED | lane 07 |

Decision-only slice; not a runtime acceptance claim.

## Remaining blockers and next slices

1. **Rock/Egg primitives (lane 20).** `rocksToSpawn`/`eggRequested` cannot become
   real births until the lane-20 primitives exist; the host must not fake them.
2. **Host wiring.** The `#407` `pc_p2_dangomushi.cpp` Turn state must call this
   policy and apply the `EB_Invulnerable`/stickable flags; the P1 proxy host has
   no P2 flag path yet.
3. **`dangomushi.brk` material loop** remains a renderer/#128 item.
4. **True `InteractPress` roll crush and `wallCallback` crash trigger** remain
   host-collision work.

## Integration

Apply `native-candidates/dangomushi-hazard/0001-*.patch` alongside the #407
candidate FSM. The module is additive and engine-free until the Turn state host
and lane-20 primitives exist.
