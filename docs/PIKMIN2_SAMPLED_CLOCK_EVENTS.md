# Sampled-animation clock/event contract (#431, parent #128)

Engine lane, Codex through shared account `4laric`. This is the converter-facing
contract that lets the growing sampled-pose roster drive **pose playback** and
**gameplay event timing** from one source-frame cursor without conflating them.

It complements, and does not replace, the shared source clock (`p2source::Clock`,
#247) and the retail event player (`p2retail::Player`, #259): those own source
time and event cursors generically. This contract binds an authored clip's
sampled pose frames and its event frames into one round-trippable record and
defines pose selection as a pure projection of the clock.

## Problem

The batch-2 sampled banks carry authored event frames in their text
(`experimental/pikmin2_batch2_core.py::bank_text` writes `frame:event`) but the
native reader ignored them, and pose selection was a separate phase expression
derived from the P1 animator (`pc_p2_batch2.cpp:268-271`). Consumers diverged:

- `pc_p2_batch2`/`pc_p2_batch3` use nearest sampled frame, no events.
- `pc_p2_bigtreasure_visual` uses a floor pose index plus `p2retail::Player`.
- `pc_p2_long_legs` has no bank and no timing contract.
- `pc_p2_mamuta`/`pc_p2_breadbug_actor` use bespoke counter math.

## Contract

Source time is independent of pose-bank density. A consumer advances the clock in
source frames and reads two independent results:

- `Clock.pose_index()` — the nearest sampled pose to `Clock.pose_frame()`, with
  ties keeping the lower index. Identical selection to
  `p2animation::Clip::index` when the bank is fully sampled; independent of event
  history.
- `Batch.events` — authored `(frame, key)` events crossed by that advance, in
  stable source order, returned exactly once per crossing.

Delivery semantics follow the shared source clock (#247), so adoption does not
introduce a second timing policy:

- First positive, unpaused advance includes events at frame 0; regular advances
  emit `(old, new]`.
- Looping clips play the intro `[0, loop_begin)` once and repeat
  `[loop_begin, loop_end)`; loop-begin events fire for the new cycle. Outro
  events after the loop are rejected.
- A one-shot completes at `duration`; `pose_frame()` clamps to `duration - 1` so a
  finished clip does not wrap to its first pose.
- Pause freezes time without accumulating catch-up. `seek()` invalidates earlier
  batches and discards crossed events. A call allows at most 256 wraps and 4096
  emitted events; a budget rejection consumes nothing.
- Invalid, negative and non-finite advances are refused without changing state.

## Canonical format

`experimental/pikmin2_animation_clock.py` defines `P2_ANIM_CLOCK_1`, a bounded
ASCII/LF text form that carries the sampled source frames and the events
together:

```text
P2_ANIM_CLOCK_1 <clip_count>
clip <name> <duration> <loop_begin> <loop_end> <pose_count> <event_count>
poses <source_frame> ...
event <source_frame> <key>
```

`loop_end == -1` is a one-shot. `render_clock_bank()` / `parse_clock_bank()` are
byte-stable. `bank_clips()` reconstructs existing `P2_*_BANK_1` rows as
count-only clips (uniform sampling) and preserves their event token exactly; the
canonical form is authoritative for exact sampled frames.

## API

```python
from experimental.pikmin2_animation_clock import Clock, manifest_clip

clip = manifest_clip(manifest['species']['Armor']['clips'][0])
clock = Clock(); clock.start(clip)
batch = clock.advance(source_frames)          # Batch(events=Occurrence...)
pose = clip.pose_index(clock.pose_frame())    # or clock.pose_index()
for event in batch.events:                    # independent of `pose`
    receiver(event.frame, event.key)
```

`CONSUMERS` records the adoptable modules and the code each replaces.

## Consumer mapping

| Consumer | Adopts | Replaces |
|---|---|---|
| `pc_p2_batch2` (dweevil/flora/ground/cannon/waterwraith) | source-frame pose index + event stream from `p2-*-bank.txt` | per-draw P1 counter phase + event-free `Clip::index` |
| `pc_p2_batch3` | same shared helper | duplicated batch2 draw math |
| `pc_p2_hardlanes` / `pc_p2_bigtreasure_visual` | one cursor for pose + events | floor pose index + separate retail player |
| `pc_p2_long_legs` | nothing this batch (bind pose only) | n/a |
| `pc_p2_mamuta` | optional migration | bespoke anchor frame math |
| `pc_p2_breadbug_actor` | optional migration | `p2breadbugcargo::select` |

## Consumers migrated

Armor (first consumer, integrated) and Hana (Creeping Chrysanthemum, source 84; lane 08 slice 1, `pc_p2_hana_events.h` + `pc_p2_hana.cpp`): the attack1 key-2 bite / key-3 swallow and flick key-2 events are dispatched from the sampled clock, proven exactly-once per attack re-entry in a 960x540 runtime (four re-entries, bite frame 18 each) with the runtime-layer caveat that `pc_p2_hana.cpp` skips an update when `dt > 0.5 s`, so a hitch larger than that drops its delta before it reaches the clock. See `docs/PIKMIN2_LANE08_DEEPSEEK_HANDOFF.md` for the migration pattern.

## Native handoff

The native consumers are C++. A header-only candidate
(`native/pc_port/pc_p2_sampled_clock.h`) and a compiled probe
(`native/tools/test_p2_sampled_clock.cpp`) were produced in a separate private
native worktree and committed as a reviewable patch under
`native-candidates/sampled-clock-128/`. The maintained native checkout and
`native/build-randomizer` were not touched, and nothing was pushed to native
origin. Adoption is a per-family follow-up owned by the family modules.

## Validation

```powershell
py -3.12 -m pytest tests/test_pikmin2_animation_clock.py -q
```

The focused suite covers canonical round-trip stability, manifest/bank
reconstruction, native-nearest pose matching, pose/event independence, event
ordering and exactly-once crossing, intro/loop/repeat, one-shot completion,
split/combined advances, pause/seek/generation invalidation, and transactional
budget and invalid-input rejection.

## Non-claims

- Not full skeletal playback, not mesh/joint blending, not BTK/material animation.
- No live actor is migrated in this batch and no gameplay/runtime acceptance is
  claimed. Existing `P2_*_BANK_1` writers and `p2animation::Clip` are unchanged,
  and no second wall clock is introduced. P1-backed proxies keep their P1 motion
  counter.
- Source event metadata alone does not execute damage, capture, sound or drops.
