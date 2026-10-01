# Authoritative native counter adapter

Codex engine lane, [#252](https://github.com/4laric/pikmin-randomizer/issues/252).
`engine/pc_port/pc_p2_native_counter.h` adapts simulation-owned animation counters
to the [source clock](PIKMIN2_SOURCE_CLOCK.md). It owns no actor pointers, draw
hooks, wall clock, or damage receivers. Family implementations supply observations
from their native animation update.

## Binding and observation

`bind(sourceClip, nativeLastFrame, motionSerial)` requires a valid source clip
of at least two frames, a finite positive native last-frame value, and a nonzero
serial strictly greater than this adapter's last accepted serial. The caller
increments the serial on every motion instance, including restarting the same
motion ID. Cancellation preserves the serial high-water mark.

`observe(serial, nativeCounter, loopOrdinal)` maps the counter with:

```
sourceFrame = nativeCounter / nativeLastFrame * (sourceDuration - 1)
```

This is the existing Tank visual mapping, evaluated in double precision. Unlike
the legacy visual helper's clamping, the adapter rejects counters outside the
declared native span. Families must supply valid authoritative observations.

The first motion starts at source frame zero, loop ordinal zero. A repeated
counter/ordinal emits no events, including while the native motion is paused.
Skipped observations deliver all crossed events within the source-clock budget.
For looping clips the ordinal counts actual wraps since bind/seek; source frame
must be inside the loop after the first wrap. Multiple wraps are accepted up to
the per-call budget, even if the local counter ends higher than it started.

Do not infer the ordinal from a counter decrease: native motion restart, rewind
and loop wrap can produce the same observation, and several loops can occur
between draws. A family whose native animator cannot expose that distinction
must add an update/event hook before using this for gameplay. Drawing a pose
alone does not provide authoritative event timing.

## Discontinuities and completion

- Bind a new increasing serial on motion replacement/restart. Prior returned
  batches cease to be current, even if the source clip is identical.
- `seek(newSerial, nativeCounter)` requires another increasing serial, discards
  skipped events, invalidates old batches, and resets the loop ordinal to zero.
  Seek itself does not replay an event at its destination.
- `finish(serial)` consumes the remaining one-shot interval only when the host
  reports an actual nonloop END. Repeated END or terminal observations emit no
  duplicates. Interruption uses cancel/rebind, never finish, because replaying
  an interrupted attack's remaining events would be incorrect.
- A mismatched serial, backwards counter/ordinal, invalid number/range or loop
  END request is refused. Budget failures leave both clock and observation
  position unchanged, so an explicit smaller observation can be retried.
- Check `current(batch)` between reentrant receiver calls; a receiver can change
  the motion or cancel the adapter. External actor lifetime remains host-owned,
  and batches must be consumed once on their originating adapter only.

## Consumer example

For the existing Tank mapping, a 31-frame native animation uses last frame 30.
A 61-frame source clip uses last frame 60. An observation at native counter 15
therefore reaches source frame 30 and crosses an engineering marker at frame 20.
The compiled probe uses the actual `p2tankvisual::frame` helper to verify this
mapping. Markers in this probe are test data, not extracted enemy damage events.

The adapter suite covers this example, repeated observations, source-end events,
explicit completion, stale serials, same-clip replacement, seek invalidation,
intro/loop behavior, several skipped loops, invalid input and transactional
budget failure/retry. Run it with the other timing suites:

```powershell
# Compiler and runtime DLLs must be on PATH.
py -3.12 -m unittest tests.test_pikmin2_source_clock
```

This is a reusable engine adapter plus compiled consumer evidence. No family's
live AI has been migrated and no new game build is required for this header-only
batch. The previous source clock/Bulblax consumer is already integrated at
`7d4255b` on `codex/pikmin2-room-preview` with its full native runtime evidence.
The maintained separate native checkout has concurrent family work and was not
modified by this batch; new native candidates should include the clock commits
`c5f07653` and `eb69578b` when restoring from that checkout instead of `engine/`.
