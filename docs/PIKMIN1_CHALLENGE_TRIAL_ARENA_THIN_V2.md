# P1 Challenge Trial arena-thin v2 (#792)

Lane `p1-challenge-trial-arena-thin-v2`, issue #792 (follow-on to blocked
#567), executing #770 Option A. Owns only `scripts/p1_challenge_trial_arena_thin_v2.py`,
`tests/test_pikmin2_challenge_trial_arena_thin_v2.py` and this doc. Consumes
the blocked #567 driver, the landed #649 guarded fixture and the #741
INITSTAGE-CREATE-FINALSETUP order fix READ-ONLY. No native/shared/CMake edits,
no engine change, no ADMIT.

## What this slice does

#770 diagnosed retail chal4 saturation: `me=100` buried sprouts against the
`cap=100` birth total, so `PikiMgr::birth` refuses and the trial squad never
births (`me` incremented at `pikiheadItem.cpp:143`, summed at
`gameStat.cpp:70`).

Gen 3 found no repository `.gen` rewriter, so the slice stopped fail-closed.
Gen 6 consumes the LANDED #795 gen-record thinner read-only
(`trial-arena-gen-thinning-tool`, commit `72149cbe`, 16 tests green): the
script mirrors the retail assets with symlinks, overlays ONLY the thinned
`chal4/default.gen` (buried 100 -> 80, headroom for a 20-squad; every kept
record byte-identical with per-record provenance), writes a thin manifest +
stage package, and verifies the package on the existing `check_stage_package`
path. The thinned arena then feeds a guarded headed run of the landed #649
fixture for the squad-spawn verdict.

Option A ("thin buried sprouts in the staged chal4 arena, no engine change")
requires reducing the `GenObjectPiki` records that spawn buried sprouts
(`generator.cpp:1173`: spawn state 0 births a `PikiHeadItem`). Those records
live inside the staged retail `.gen` binaries (`default.gen`, `plants.gen`),
which the canonical challenge inputs builder stages verbatim with sha256 pins.
No repository utility parses or rewrites the retail `.gen` binary format, and
this lane owns no native/shared file to add a staging hook.

Therefore a correct, divergence-safe thinning cannot be produced from inside
the three owned root files. This slice implements the feasibility gate:
`assess()` classifies the staged gens, refuses to rewrite retail binary
content, and emits the exact blocker + owner route. The real arena confirms
`verdict=blocked`, `blocker=retail-binary-gen-needs-provider`.

## Owner route (fallback per brief)

- Preferred: a generator/placement-provider binary `.gen` rewriter (or a
  native staging hook) that suppresses a subset of buried `GenObjectPiki`
  generators so `me` stays under the cap; consume #649 fixture and #741 fix
  unchanged.
- Alternative: #770 owner B engine counting fix (`pikiheadItem.cpp:143`
  and/or the `PikiMgr` birth arm) with #186 review and the #52 campaign
  contract.

## Verification

`py -3.12 -m pytest tests/test_pikmin2_challenge_trial_arena_thin_v2.py -q`
-> 8 passed. Fail-closed: empty/unknown generator bytes are never rewritten,
missing files raise, and `main` exits 3 (BLOCKED) rather than fabricating a
thinned arena. All six gates UNTESTED; no playability claim.

## Captain safety (#632)

No runtime run executed by this slice (BLOCKED before any headed run, as the
thinned package cannot be produced). Any future runtime run must adopt
`scripts/p2_fixture_captain_guard.h` (sha256
`d2f678c9eda75e151eb534077dff9e30ad36ae4796881d971bbd09945f3c3474`) with
orimaDead/NaviDead/HP<=1 checks, CAPTAIN_DOWN + BLOCKED exit, a parked
captain and no blanket invincibility.
