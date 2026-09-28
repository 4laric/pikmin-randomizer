# ch_MIYA_trap P1 runtime import (issue #560)

Lane `p2-challenge-ch-miya-trap-p1`, generation 2. Owner: Codex through shared
account 4laric. This lane owns ONLY the three content-lane files:

- `experimental/content_lanes/ch_miya_trap.py`
- `tests/content_lanes/test_ch_miya_trap.py`
- `docs/content_lanes/ch_miya_trap.md`

The P0 decode helpers live in the sibling P0 adapter
`experimental/content_lanes/p2-challenge-ch_miya_trap.py` (owned by lane
`p2-challenge-ch_miya_trap`, done); they are imported read-only and never
edited or forked.

## Source contract (exact stage key, not display title)

Stage `ch_MIYA_trap` (`user/Mukki/mapunits/caveinfo/ch_MIYA_trap.txt`,
sha pin `e5b2a21c...`): 1 floor, floor timer [300.0], starting population
total 25 at cell [3][2], sprays bitter 2 / spicy 2, ui_index 26. The P1
manifest must preserve all of these; anything else is refused fail-closed.

## P1 import path (this lane; no re-implementation)

`validate_p1_manifest()` checks a P0 manifest carries everything the P1
runtime import needs (the 1 decoded floor with unit pool + enemy/treasure
rosters, the 7-row starting roster totalling 25 at [3][2], the [300.0]
timer, sprays 2/2, ui 26) and normalizes a staging dict; anything else
raises fail-closed. `stage_run_layout()` writes a private run layout:
`stage-manifest.json` (validated copy), `p1-input-package.json` (stage key,
floors, squad total 25, timers [300.0], sprays 2/2, ui 26) and
`run-plan.json` (ordered observation plan: fresh arena + starting-Pikmin
overlay + centred 960x540 boot, captain guard FIRST with orimaDead/NaviDead/
HP<=1 and CAPTAIN_DOWN + BLOCKED, live-squad check, collision/routes/actors
markers, honest six-gate evidence). `p1_main()` drives it from a manifest
file; `main()` is a thin CLI. All decode constants and helpers come from
the P0 adapter; no parser was forked.

P1 validation evidence: `P1MiyaTrapTests`, 15 focused tests (valid manifest,
P0-reuse check, wrong cave, floor count, empty enemies, missing unit pool,
wrong squad total, missing pinned cell, bad timer, wrong sprays, wrong ui,
three-file layout write + package schema/squad/timer assertions,
bad-manifest and missing-file rejections, end-to-end `p1_main`), all green.
No runtime run, no build, no shared edits; all six gates UNTESTED. The
runtime boot (leased build, fresh arena, guard adoption, live observation)
remains explicitly future work once the host toolchain recovers.

## Honest blockers

Host MinGW fails silently (exit 1, no output, even on a trivial compile),
so no native syntax check, leased build, or GL fixture run was possible in
this lane. No simulation was substituted.
