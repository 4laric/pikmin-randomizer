# Shared source-frame clock and event cursor

Engine lane, Codex through shared account 4laric; [#247](https://github.com/4laric/pikmin-randomizer/issues/247), parent #128.

`engine/pc_port/pc_p2_source_clock.h` is a header-only C++17 component. It owns
source time and returns crossed event markers. It does not call actors, apply
damage, read a wall clock or choose a sampled model. Family owners translate
validated source events into their own native receivers.

## Contract

- Durations are source-frame units in `[1, 1000000]`. Position runs from zero to
  duration for a one-shot; `finished()` becomes true at duration. `poseFrame()`
  clamps to duration minus one so existing pose selectors do not wrap a completed
  one-shot to its first pose.
- Looping clips play the intro once and repeat `[loopBegin, loopEnd)`. Events
  after the loop are rejected because this clock does not implement an outro.
  Disabling the loop or adding an outro requires a new explicit clip transition.
- Events are sorted by source frame, preserving equal-frame source order. IDs
  are caller-defined and may repeat. Non-finite/out-of-range frames are rejected.
- The first positive, unpaused advance includes events at zero. Zero advance,
  pause, and repeated draw calls emit nothing. A regular advance emits `(old,new]`.
  Reaching a loop boundary emits loop-begin events for the new cycle, even when
  the update ends exactly at that boundary. Intro events do not recur.
- `advance(delta)` takes source-frame units; `advanceSeconds(dt, sourceFps)` is
  an explicit conversion. Both reject negative/non-finite inputs. Pausing freezes
  time without accumulating a catch-up delta inside this component.
- `start()`/`restart()` create a new generation and reset pause. `seek()` also
  invalidates earlier batches, discards crossed events, preserves pause, and
  does not emit the event exactly at its destination. Nonloop terminal seeks
  are allowed; loop-end seeks are rejected. Failed start/seek preserves state.
- `cancel()` invalidates pending batches. `current(batch)` checks generation
  and active state. Generations persist across cancellation within this clock;
  exhaustion refuses replacement. Batches belong only to their originating
  clock instance, and are not asynchronous object-lifetime tokens.
- A call allows at most 256 wraps and 4096 emitted events; clip input allows at
  most 4096 events. A budget error returns no events and changes no clock state.
  The host must explicitly handle the error or subdivide the elapsed interval;
  silently discarding the elapsed time would lose gameplay events.

## Family adoption

Select one authoritative simulation clock. An existing P1 compatibility actor
continues to use its P1 motion counter; map its positive delta to source units
as `pc_p2_tank_phase.h` does. Detect a native restart, seek or motion replacement
explicitly and restart/seek the cursor. Do not treat a backwards counter as
elapsed time, or drive the same actor from wall-clock time as well.

For a P2-owned FSM, advance from simulation dt and the source clip rate, respecting
the game's pause state. Then choose visual poses from `poseFrame()` independently:

```cpp
auto batch = clock.advance(deltaSourceFrames);
if (!batch) { /* Explicit error handling; state and events were not consumed. */ }
else {
    for (const auto& event : batch.events) {
        if (!clock.current(batch)) break; // A previous receiver changed the clip.
        // Family receiver handles event.id; no callback lives inside Clock.
    }
    // Read the CURRENT clip after receivers, which may have changed it.
    // size_t pose = currentVisualClip.index(float(clock.poseFrame()));
}
```

Dispatch a successful batch once. The component does not remember which events
your external receiver has executed. A host must also validate actor lifetime
around reentrant calls; `current()` cannot be called on a destroyed object.
Source-event metadata alone is not proof of collision/damage/capture behavior.

## Concrete consumers and validation

`engine/tools/test_p2_source_clock.cpp` exercises the actual Bulblax profile
parser and sampled-pose selector: with poses at 0, 15 and 29, advancing to source
frame 12 still returns a marker at frame 10 while displaying pose 15. Advancing
zero frames does not repeat it. The marker is synthetic engineering data, not
a claimed Queen gameplay event. The same executable drives the clock with the
existing Tank P1-to-source counter mapping.

The probe covers pause, equal-frame ordering, exact boundaries, restart/seek,
clip replacement/cancellation, one-shot completion, loop intro/wraps, equivalent
split/combined advances, malformed values and transactional budget failures.

```powershell
# Use a shell with the compiler and its runtime DLLs on PATH.
py -3.12 -m unittest tests.test_pikmin2_source_clock
```

This batch provides the reusable component and compiled consumer examples.
Existing live actors and the Bulblax wall-clock display have not been migrated.
Family owners can adopt it within their native milestones. Full skeletal
skinning, blending, BTK playback and live receiver acceptance remain separate.
