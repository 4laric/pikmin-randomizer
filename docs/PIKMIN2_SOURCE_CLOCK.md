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
Existing live actors have not been migrated. Family owners can adopt it within their native milestones. Full skeletal
skinning, blending, BTK playback and live receiver acceptance remain separate.

## Native display adoption (#249)

The dependent display batch adds `pc_p2_display_clock.h` and wires it into
`pc_p2_bulblax_visual.cpp`. Each selected clip owns a clock; all displays of that
clip share its time. Setup starts clocks after loading, reset clears them, and
draw updates clocks once from a common SDL timestamp before choosing poses.

The adapter preserves the noninteractive viewer's 30 source frames/second wall
time, including continued playback during a game pause. It is deliberately not
a gameplay adapter and accepts no event metadata. Unsigned millisecond deltas
handle SDL tick wrap when successive updates are less than one complete uint32
tick period apart (about 49.7 days). Larger intervals cannot be distinguished.
If a gap exceeds the source-clock wrap budget, this event-free adapter explicitly
seeks to the modulo phase and logs `P2_BULBLAX_CLOCK visual_gap_seek`.

Compiled tests compare phase over 10,000 millisecond updates and sampled poses
at representative integer-source frames; they cover zero elapsed time, wrap,
long gaps and reset. Double accumulation can differ at exact nearest-pose ties
from the old float multiplication. No source bank/material/placement changes.
The actual display translation unit compiles with the production Release flags.
The combined native build and bounded display acceptance subsequently passed below.

## Combined native validation — 2026-09-13

Native `eb69578b`, including the source clock `c5f07653`, was built from the
private native-engine-timing worktree with Release, JAUDIO enabled, IPO enabled,
and native CPU optimization disabled. The full `pikmin_pc` target passed.
Production executable SHA256:
`8b2406100fd1e1999c05b43c7df22f4c602d53f891ce195c01b645fe46133624`.

The existing Bulblax fixture was rebuilt against those objects with its input
provenance and both Ninja freshness checks. Fixture SHA256:
`7d5a1b58e914fc9dade0dfcf2d6b0d99cf07ae7c11a4de5e616a40ca1497f92a`.
Machine-local evidence is under the engine root worktree:
`output/timing-runtime01/build/provenance.json` and
`output/timing-runtime01/validation/result.json`.

| Mode | Clip | Result |
|---|---|---|
| Queen | wait1 | PASS |
| Baby | move | PASS |
| KingChappy | move1 | PASS |
| Disabled | No imported display | PASS |

Each enabled mode changed sampled poses, cleared/reloaded the display, preserved
source identity/XYZ/yaw, retained the expected squad, and left actor/reward counts
unchanged. All four matched the disabled control's GX warnings. Captures were
inspected for each species; Queen's reset image is empty and KingChappy is visible
after reload. Queen's black/silver material, Baby's flat bright shading and
KingChappy's terrain intersection remain known issues from the earlier fixture.

This validates the native timing consumer and display reset/reload, not boss
combat, all clips, material fidelity, simulation pause or natural gameplay.
Long-gap and tick-wrap behavior are covered by the compiled adapter tests; no
49-day native run was performed. Existing fixed player/QA packages are unchanged.
