# Hard-lane engine reconciliation candidate (#244 / #446)

Private reconciliation candidate for the queued item in
[`PIKMIN2_INTEGRATION_446.md`](PIKMIN2_INTEGRATION_446.md):

> **Hard-lane export `87204df` and species root `3f4a0aa`:** larger runtime
> reconciliation remains ... do not transplant their old engine.

This branch adds the current hard-lane family modules to the review baseline so
lane 27 (Careening Dirigibug, #244) can build a normal spawned-actor runtime
against a reviewable engine, without replacing the whole engine snapshot.

- Branch: `opencode/p2-lane27-reconcile`
- Baseline: `codex/p2-main-review` @ `bc9bfad`
- Source: maintained native line `codex/pikmin2-room-preview` @ `f9e139d8`,
  exported from private worktree `output/native-lane26`
- Implementation owner: Codex via shared `4laric`. Executing session:
  opencode (deepseek-v4.1-flash), 2026-09-13.

## What changed

Additive hard-lane family files copied byte-for-byte from the maintained native
line (66 files), covering the three batch-2 hard lanes:

- `pc_port/pc_p2_hardlanes.{h,cpp}` — shared registration seam
- BombSarai (#244): `pc_p2_bombsarai_{arena,blast,bomb,fsm,hover,map_trace,terrain}.*`, `pc_p2_bombsarai_clock.h`
- Fuefuki (#245): `pc_p2_fuefuki_{binding,fsm}.h`, `pc_p2_fuefuki_interference_policy.h`
- BigTreasure (#246): `pc_p2_bigtreasure_{,attacks,fsm,host,map_trace,motion,visual}.*`
- Demon policy header `pc_p2_demon_drop_policy.h`
- Family tools/tests and Arena profiles under `engine/tools/` (policy probes and
  runtime probes; no binaries).

Shared-file hook hunks (small and separately identifiable, applied to the
baseline files, not copied wholesale):

| File | Hunk |
|---|---|
| `pc_port/pc_p2_preview.cpp` | `#include "pc_p2_hardlanes.h"` and `pc_p2_hardlanes_setup();` |
| `src/plugPikiKando/gameCoreSection.cpp` | include, `pc_p2_hardlanes_update();`, `pc_p2_hardlanes_draw(gfx);` |
| `CMakeLists.txt` | hardlanes + bombsarai + bigtreasure sources in `PC_PORT_SOURCES` |

Four pre-existing baseline files in this family were updated to the maintained
native versions because the lane's newer source-traced policy supersedes them:
`pc_p2_fuefuki_interference_policy.h`, `tools/P2_FUEFUKI_AUDIT.md`,
`tools/P2_FUEFUKI_INTERFERENCE_POLICY.md`,
`tools/p2_fuefuki_interference_policy_test.cpp`.

## Explicitly not done

- No wholesale `engine/` export. Divergent baseline modules
  (`pc_p2_queen`, `pc_p2_king`, `pc_p2_sokkuri`, `pc_p2_armor`,
  `pc_p2_*material*`, `pc_p2_batch2`, …) are preserved untouched, per the #446
  warning to keep current upstream/King/renderer/actor hooks.
- No main merge, no native-origin push, no player package change.

## Verification

Performed:

- All `#include "pc_p2_*"` references in the copied hard-lane sources resolve to
  files present in the candidate engine (0 missing).
- All hard-lane `.cpp` translation units are present exactly once in
  `PC_PORT_SOURCES`.
- Copied files are byte copies of the maintained native line that currently
  builds a full `pikmin_pc` in private worktree `output/native-lane26`
  (`[523/523]`, exe SHA-256 `83B319A1…`).

Not performed:

- **No combined build of this root candidate.** The root `engine/` snapshot has
  no independent build here; combined-build and suite verification must run on
  the maintained native line after lane 01 ingests this batch. In particular the
  hard-lane sources call into `pc_p2_batch2`/family hooks whose baseline versions
  were reconciled by #446, so a compile check is required before merge.

## Known lane-27/runtime gaps (not closed by this candidate)

- BombSarai visual bank / `kamu_jnt1` joint and Fuefuki animation source remain
  #128-gated.
- BigTreasure motion staging is 2/29 clips.
- The ordinary spawned carrier actor, capture joint, bomb lifecycle and
  interruption still need host wiring and a natural runtime run; the existing
  BombSarai `PASS BOMBSARAI_RUNTIME` evidence is a lane fixture, not an ordinary
  encounter.

## Recommended integration steps for lane 01

1. Build the maintained native line after applying this batch (or export from it)
   and run the affected suite.
2. If `pc_p2_batch2`/shared hooks conflict, prefer the baseline (#446) versions
   and adapt the hard-lane call sites rather than reverting baseline modules.
3. Publish the pinned native commit and update the family status tables.
