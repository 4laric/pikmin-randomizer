# Sampled clock consumer adoption (#431, #128)

Engine/toolchain lane (08), Codex through shared account `4laric`. This is the
first real consumer migration onto the #431 contract
(`docs/PIKMIN2_SAMPLED_CLOCK_EVENTS.md`, `pc_port/pc_p2_sampled_clock.h`).

## Before

`pc_p2_batch2_draw` derived the displayed pose from the P1 animator phase and
ignored the bank's authored event token:

```cpp
const float phase = frames > 1 ? animator->getCounter() / (frames - 1) : 0.f;
const p2animation::Clip& timing = bank.timing.at(name);
const size_t index = timing.index(phase, corpse);
```

`parseBank` read the `frame:event,...` token and discarded it. Pose selection
and event timing could not be composed, and `pc_p2_batch2` had no event stream.

## After

New `pc_port/pc_p2_batch2_clock.h`:

- `Row` carries `{name, sourceFrames, poseCount, events}`.
- `makeClip(Row)` builds a `p2sampled::Clip`. The bank records only a pose
  count, so pose frames stay empty (uniform sampling) and `Clock::poseIndex()`
  reproduces the legacy `p2animation::Clip::index(phase)` selection exactly.
- `parseEvents()` reads the authored `frame:key,...` token (`-` = none).
- `Cursor` owns one actor's `p2sampled::Clock` and advances it to a source frame
  derived from the authoritative P1 counter. A clip change or a non-forward
  target (P1 loop wrap) restarts the cycle, so authored events fire exactly once
  per forward crossing.

`pc_p2_batch2.cpp` now:

- builds a `p2sampled::Clip` per bank clip, rejecting invalid ones at load;
- keeps a per-actor `Cursor`+clip name, cleared by `pc_p2_batch2_forget` (the
  lane-07 death funnel now reaches it);
- selects the pose from `Clock::poseIndex()` (corpse still uses the last pose);
- logs crossed events as `P2_BATCH2_EVENT key=... clip=... frame=... event=...`
  and exposes `pc_p2_batch2_event_count()` for runtime evidence.

## Migration pattern for other consumers

The same four steps apply to `pc_p2_batch3`, `pc_p2_hardlanes`/
`pc_p2_bigtreasure_visual`, and optionally the bespoke `pc_p2_mamuta` /
`pc_p2_breadbug_actor` counters:

1. Convert the bank row to `p2sampled::Clip` (keep uniform sampling if the bank
   is count-only).
2. Own one `Cursor` per actor; `start` on clip change.
3. Each draw, map the authoritative source frame and `stepTo` it; read
   `poseIndex()` for the pose.
4. Deliver `Step::events` to the family's receiver once; do not re-derive them
   from the displayed pose. Advance the actor's scene generation when addresses
   can be reused.

`pc_p2_batch2_clock.h` is the reusable helper; do not create a second clock.

## Evidence

- Native branch `opencode/p2-lanes789-native`, base `f9e139d8`:
  `0ae8f324` (header from #431) and `d086b78e` (consumer adoption).
- Standalone probes (MinGW g++, `-Wall -Wextra -Werror`):
  `PASS p2_sampled_clock: 46 checks` and `PASS p2_batch2_clock`.
  `tools/test_p2_batch2_clock.cpp` covers legacy-uniform projection parity
  (including clamp edges), event-token parsing/rejection, exactly-once crossing
  across a P1 wrap, pose/event independence, and clip-change restart.
- Production build `output/tracks/p2-lanes789/native-build`: `[7/7] Linking
  CXX executable bin\nectar.exe`; `ninja -n` -> `no work to do`.

## Runtime status

Integration #446 observes `P2_BATCH2_EVENT` in an exact-build Flora lifecycle
run; see [combined evidence](PIKMIN2_INTEGRATION_446.md). This confirms diagnostic
event observation, not a simulation-owned gameplay dispatch path.
No family damage/capture/drop receiver consumes the events yet.

## Non-claims

Not skeletal playback/blending/BTK. Does not change the `P2_*_BANK_1` writers or
`p2animation::Clip`. Does not add a second wall clock. Creating events does not
execute gameplay.
