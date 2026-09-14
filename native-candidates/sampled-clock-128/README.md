# Native handoff: sampled-animation clock/event contract (#431, parent #128)

This directory carries a **reviewable, unapplied** native candidate. It was
produced in a separate private native worktree on branch
`opencode/p2-sampled-clock-128`; the maintained native checkout and
`native/build-randomizer` were not touched and nothing was pushed to native
origin. See `provenance.json` for exact commits and hashes.

## Contents

- `0001-pc_port-header-only-sampled-animation-clock-event-.patch` — `git format-patch`
  of the candidate commit (apply with `git am`). Base
  `f9e139d86afab0b7581599f2178ee1a95dcf33af`.
- `pc_p2_sampled_clock.h` — header-only contract, depends only on the existing
  `pc_p2_animation.h`.
- `test_p2_sampled_clock.cpp` — compiled probe.

## What it provides

`namespace p2sampled` provides `Clip` (sampled pose frames + authored events +
loop bounds) and `Clock`, which advances in source frames and exposes:

- `poseIndex()` — nearest baked pose via the existing
  `p2animation::Clip::index` selector, independent of event history; and
- `Batch::events` — crossed `(frame,key)` events in stable source order, once per
  crossing.

Delivery follows the shared source-clock policy (#247): entry events included on
the first positive advance, `(old,new]` thereafter, looping intro/repeat,
one-shot completion with a clamped pose frame, pause/seek/generation
invalidation, and transactional 256-wrap/4096-event budget rejection. `parse()`
reads the canonical `P2_ANIM_CLOCK_1` text emitted by
`experimental/pikmin2_animation_clock.py`.

## Verification

```powershell
g++ -std=c++17 -Wall -Wextra -Werror tools/test_p2_sampled_clock.cpp -o p2_sampled_clock.exe
./p2_sampled_clock.exe   # PASS p2_sampled_clock: 46 checks
```

## Non-claims

Header-only candidate. No production consumer is migrated here, no full-game
rebuild or runtime/gameplay acceptance is claimed, and this does not add
skeletal skinning, blending, BTK playback or a second wall clock. Adoption is a
per-family follow-up owned by the family modules.
