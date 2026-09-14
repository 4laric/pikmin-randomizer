# Groink volley policy (#199, parent #169)

This successor to native `756515d5` leaves the existing single-shell arena and
its runtime evidence unchanged. It adds `pc_p2_groink_volley.h/.cpp` and a focused
test; no shared hooks or CMake target changes are installed.

Source: projectPiki/pikmin2 revision
`632af93787b9c95b63f0c13be32b161375ce3a96`, read-only local research checkout.
`MiniHoudaiShotGun.cpp` constructor allocates six nodes; `emitShotGun` attempts
three simultaneous emissions, skips unavailable nodes, marks emission zero as
primary, and perturbs each direction axis by a random value in [-0.1, 0.1].
`doUpdateCommon` visits active nodes in list order and appends completed nodes
to the inactive list. `sysCommonU/node.cpp::CNode::add` appends, not prepends.

The new pool preserves those capacity/order rules while reusing the tested
single-shell integration, gravity and terminal sweep. Host-provided samples
are normalized random values in [0,1]; this does not reproduce the source RNG
sequence. Only available-node samples are used. Invalid attempted emission
inputs reject atomically, which is an explicit host validation rule rather
than source behavior for malformed inputs.

The host supplies an already transformed/aimed muzzle and speed. Call `emit`
once at the source attack event 4, not once every rendered frame or throughout
the event's duration. This pool does not determine aim lock or advance the
attack animation. Source `StateAttack` pauses at event 2 for aiming, emits at
event 4, and pauses at event 5 for return rotation; those FSM transitions are
still a separate task.

Call `update` once per authoritative 30 Hz tick, using the existing bounded
clock and a real terrain callback such as `P2GroinkMapTrace::trace`. A null
callback or invalid timestep/owner rejects without mutation. A refused trace
recycles only that shell with an invalid terminal and continues visiting other
active nodes; it never uses the single-shell policy's optional straight-line
fallback. The host should surface an update failure rather than call it a hit.

After each update, consume `terminalCount()` entries from `terminals()` before
the next tick. Each receipt retains its slot, primary designation and final
y-minus-ten sweep even if a subsequent emission reuses that slot. Slot numbers
are storage identities, not durable actor IDs. Reset the pool and source clock
on scene teardown. The host owns timing, receivers, effects and pointer lifetime.

Validation (MinGW, C++17, `-Wall -Wextra -Werror`):

```powershell
g++ -std=c++17 -Wall -Wextra -Werror -Ipc_port tools/p2_groink_volley_test.cpp pc_port/pc_p2_groink.cpp pc_port/pc_p2_groink_volley.cpp -o <private-output>/test.exe
```

The test executes overlapping volleys, full/partial capacity, source list order,
spread/primary flags, simultaneous impacts, reuse without erased terminal
metadata, invalid input, trace failure, reset and 60 Hz host-to-30 Hz driving.
Its traces are synthetic. This is compiled/executed policy evidence, not a
three-shell native rendering or natural combat test. Previous live single-shell
floor/wall evidence does not establish those new acceptance levels.

Next integration request: compile this new translation unit and replace the
arena's single policy with the pool; draw all active slots and retain/consume
each terminal receipt. Validate a visible three-shell volley and two overlapping
volleys through the real map before adding receivers. Damage, source particles,
full attack FSM, revival, tracking and material fidelity remain unfinished.

## Live volley fixture milestone

`tools/p2_groink_volley_runtime.cpp` is a private replacement App entry point.
It retains the stable arena loader/draw and real MapMgr adapter, includes the
pool implementation in its single fixture translation unit, and deliberately
injects two fire commands at source ticks 40 and 44 after aim lock. This is not
an attack FSM or natural target acquisition. The inherited native build is
`756515d5`; fixture dependencies are snapshotted by the Python repository's
`scripts/build_pikmin2_fixture.py`. No shared CMake/hooks were changed.

Executed fixture `output/groink-volley-runtime-fixture-04`:

| Placement | Actual emitted-shell evidence |
| --- | --- |
| Owner 0,0,0; target 0,0,250 | Six floor impacts, 246 trace calls, final tick 85 |
| Owner 200,0,230; target 200,0,480 | Six wall impacts, 58 trace calls, final tick 55 |

Both report six distinct slots, two primary shells, zero remaining active shells,
successful pool reset/re-emission, exit zero and `PASS GROINK_VOLLEY_RUNTIME`.
Preceding direct floor/free-space/wall probes have their counters reset before
emission and are not counted as shell evidence. The reset check is pool-local,
not full scene/heap teardown. The standalone pool test also passes after the
configured-include-root adjustment.

The fresh-run helper `tools/p2_groink_volley_run.py` verifies executable
provenance, stages private overlays, checks receipts, bounds runtime and writes
`verification.json` with input/output hashes. Example (prepend MinGW bin to PATH):

```powershell
py -3.12 tools/p2_groink_volley_run.py --root-worktree <Python-worktree> --assets <local-assets> --room <converted-room> --stage <Groink-stage> --fixture <fixture-output> --output <private-runs> --expected-contact floor
```

Private evidence under `output/groink-volley-runtime-sessions`:
floor `5932c1abb0a64fa0bbfa3dc7e075dd3b`, wall
`f2f2cf5361d74c1dbe25dc9170f89332`. Each contains verification, stdout/stderr
and captures. Readback now flushes pending renderer batches. Visual inspection
confirms Groink and overlapping colored diagnostic shell markers, but the
captures do not clearly resolve all six shells simultaneously; that visual
acceptance remains open. The later spread capture does not establish shell
visibility. These debug markers are not source projectile effects. Material
accuracy and animated muzzle alignment also remain unvalidated.

## Next bounded work: source attack-state contract

Read-only audit of `MiniHoudaiState.cpp:267-380` and
`MiniHoudaiShotGun.cpp:1286-1303,1732-1743,1976-1993` establishes:

- Attack init clears wait/health-gauge timers and target velocity, then starts
  the attack animation. Event 2 clears the wait timer, stops motion and starts
  aiming/charge. Event 3 ends charge and produces smoke.
- Stopped motion resumes only with lock-on and a positive wait timer. This is
  required in both the aiming and finished-rotation branches; finish alone
  does not resume motion. The timer increments after that check each update.
- Event 4 uses the exact source guard `!isFinishMotion() || !(health <= 0)`.
  Do not replace this OR with AND. Health/flick handling resumes stopped motion
  and requests finish before processing animation events.
- Event 5 clears the timer, stops motion and marks rotation finished, clearing
  lock-on but retaining active rotation. Return rotation chooses the wrapped
  equivalent of zero, steps by at most 0.025 radians and tests the resulting
  error against 0.01. Completion clears rotation and sets lock-on again.
- END resolves death first, then flick, territory/home, another attack, or
  target/path locomotion. The latter branches require actor/target ownership
  and must not be invented by a stationary fixture.

Next heartbeat should claim a bounded attack-controller child issue under #169,
translate pause/resume and rotation/event semantics with source-timed tests,
then connect it to the pool in the private fixture. Keep source animation-event
advancement separate from fixed-clock render count. The visual six-shell gate,
natural targeting/combat, receivers, corpse/revival and full scene lifecycle
remain open; Groink is not implemented yet.
