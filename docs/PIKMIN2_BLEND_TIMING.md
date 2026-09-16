# Dual-track animation timing

Issue #265, parent #128. Codex implementation through shared account 4laric.

`engine/pc_port/pc_p2_blend_player.h` coordinates two retail Players. It provides
the timing/event portion of SysShape BlendAnimator; it does not blend meshes,
joints, sampled shapes or materials. No live family is migrated by this batch.

Start tracks 0 and 1 with `startTrack`, then `startBlend(duration)`. Each update
takes blend time, primary source-frame delta and secondary source-frame delta
separately. Match the units of blend time to duration; animation deltas are
source frames. A disabled blend advances only track 0. An enabled blend advances
track 0, then track 1, then the blend timer. Authored events include their track
index. Completion calls `end(duration)` once after marking completion; this is
the equivalent of END_BLEND (2000), kept separate from integer-frame events to
preserve a fractional blend duration.

`progress()` exposes the normalized blend timer. The renderer applies its
chosen blend function and weights to that value. Completion leaves both tracks
enabled and updating until `endBlend()` is called, following the source.
`endBlend()` resets blend timing and completion but leaves both track positions
intact. `finishTrack` requests a retail outro; `seekTrack` resets that track's
completion/finish flags. Starting a track does not restart the blend timer.

Source comparison: local Pikmin 2 research `src/sysGCU/sysShape.cpp`,
BlendAnimator::startBlend, endBlend and animate. Deliberate safety differences:
zero/nonfinite/negative blend durations are refused instead of dividing by zero;
all deltas are checked before either track advances (including unused deltas);
callback mutations stop the old update with Replaced. No implicit time scaling,
promotion of track 1, or synthetic gameplay event is introduced.

Callbacks must not destroy the coordinator and should not throw. A private
exception unwinds dispatch after a successful start/seek/end/cancel mutation;
only that internal exception is caught. Already delivered effects are not
rolled back. On an interrupted track, any retained undispatched keys remain
eligible on its next update unless the host restarts/seeks/cancels that track.
Nested advance is refused. This protects dispatch state, not receiver lifetime.

Validation: 40 compiled coordinator checks cover disabled/enabled tracks,
independent speeds, authored loops/outros, event ordering, fractional duration,
completion once, invalid inputs without partial advancement, callback ending,
cancellation, completion restart and reentrant advance. Run with MinGW on PATH:

```text
py -3.12 -m unittest tests.test_pikmin2_blend_player tests.test_pikmin2_motion_events tests.test_pikmin2_source_clock
```

Eight test methods pass; retail playback additionally passes 480 checks with
29 real clips. These compile the actual headers with warnings-as-errors. Live
P2-native family adoption, renderer blending and natural gameplay validation
remain open under #128. P1-backed proxies retain their authoritative P1 events.
