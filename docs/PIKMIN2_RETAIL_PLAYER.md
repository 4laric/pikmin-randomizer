# Retail animation event playback

Issue #259. Implementation owner: Codex (shared GitHub account 4laric).

`engine/pc_port/pc_p2_retail_player.h` consumes the source-backed `p2retail::Motion`
tables described in `PIKMIN2_MOTION_EVENTS.md`. This is a separate player from the
generic source clock: retail SysShape discards loop overshoot; the generic clock
preserves it. Choose deliberately when adopting either interface.

The contract follows `sysShape.cpp` Animator::animate in the local Pikmin 2
research source: advance in source frames; dispatch keys only when their frame
is less than the integer timer; invoke the loop-end receiver before deciding
whether to rewind. A receiver can call `finishMotion()` to continue through the
outro. Otherwise the last preceding loop-start becomes the timer, remaining
overshoot is discarded, and that update stops. Completion clamps to duration-1
and emits type 1000 with frame=duration once, after setting completed state.

Call `start(motion)`, then `advance(sourceFrameDelta, receiver)`. The host owns
time scaling, pausing, source-file identity checks and receiver lifetime. No
wall clock, actor pointer or family FSM is installed by this header. Restart or
cancel during a callback stops the old dispatch and returns Replaced. Nested
advance returns Reentrant. Invalid input is refused before advancing. Callbacks
must not destroy the player and should not throw; callback exceptions do not
roll back time or receiver effects. Generation checks do not provide actor
lifetime safety.

Validation: the compiled C++ probe tests strict timing, overshoot discard,
callback-requested outro, one-shot END, invalid inputs, cancellation, restart,
and reentrant dispatch. It also plays all 29 locally imported Queen, Baby and
KingChappy clips through completion and compares all 61 authored events in
order, plus 29 implicit END events: 203 checks passed. The Python suite compiles
the probe with C++17 and warnings-as-errors; without local assets it still runs
the synthetic checks. No assets are committed.

Run with MinGW on PATH:

```text
py -3.12 -m unittest tests.test_pikmin2_motion_events
```

This batch provides the tested shared mechanism. Live family adoption and
gameplay sign-off remain separate work.

## Frame positioning (#262)

`seek(frame)` follows SysShape `setCurrFrame`: select the first authored key
at or after the integer destination and clear both completed and finish-motion
flags. It emits nothing immediately. For example, seeking to 3.75 retains a key
at frame 3; that key fires when a subsequent advance reaches 4. Earlier keys are
not replayed. Equal-frame keys retain their authored order.

`seekKey(type)` selects the first occurrence of an authored type; type 1000
selects the last frame, as does `seekLastFrame()`. A missing key leaves state
unchanged. Seeking after completion rearms END. Unlike the original unchecked
API, this interface refuses negative, nonfinite and out-of-clip destinations
(`frame >= duration`), and refuses seeks while inactive.

A successful seek increments generation, including same-frame seeks. A seek
from a receiver therefore returns Replaced from the old advance rather than
continuing its stale event sequence. The next host update uses the new position.
This is intentional callback safety; do not depend on the original animator's
mutable linked-list continuation within a callback. The receiver lifetime and
nonthrowing requirements above still apply.

Validation: 480 compiled checks across synthetic cases and the same 29 real
clips. Every one of their 61 authored keys is also tested as a seek destination,
comparing the complete remaining event suffix and implicit END. Seven focused
Python test methods pass, including generic clock and native-counter regression
coverage. This header-only change has no production consumer yet, so validation
compiles the actual header/probe with warnings-as-errors; no game rebuild or
natural gameplay claim is attached to this batch.
