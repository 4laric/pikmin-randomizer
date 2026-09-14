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
- **Combined build of this candidate.** The candidate `engine/` snapshot was
  reconstructed into a clean native build tree (`output/p2-lane27-build-src`,
  1666 files) and configured at `output/p2-lane27-build`
  (Ninja/Release/MinGW, `PIKMIN_NATIVE_JAUDIO=ON`) with the baseline
  `CMakeLists.txt`. `cmake --build . --target pikmin_pc -j 6` →
  `[529/529] Linking CXX executable bin\nectar.exe` (exit 0). `ninja -n` →
  `no work to do.` Production executable SHA-256
  `66CCDF87B15F79504371EAEC1688A4419A177226F86628DAFF83793F7A338630`. All 15
  hard-lane translation units compiled (objects present: hardlanes, 7 bombsarai,
  7 bigtreasure).

Limits:

- The rebuild reconstructs the root snapshot in a clean tree; it is not the
  maintained native build and does not run any runtime/GL arena gate. The #128
  visual/material gaps below are unchanged.
- This verifies compilation and linking only. The hard-lane call sites still
  interact with the #446-reconciled `pc_p2_batch2`/family hooks at runtime, so
  lane 01 should still run the affected suite on the maintained native line.

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

## Lane 25 slice 2 included (Crawbster hazard)

This tranche also lands the queued lane-25 `pc_p2_dangomushi_hazard` policy
(engine-free Turn vulnerability window + Rock/Egg spawner decisions), mirroring
the #446 pure-policy integrations:

- `engine/pc_port/pc_p2_dangomushi_hazard.{h,cpp}`
- `engine/tools/p2_dangomushi_hazard_test.cpp`
- `CMakeLists.txt`: `PC_PORT_SOURCES` entry plus `p2_dangomushi_hazard_test`

Rebuild evidence in the same reconstructed tree: `pikmin_pc` relinked
(`[5/5]`, exit 0; executable SHA-256
`86CADA5C46370E6FC1B1423C0126A4F8540172EA42ACB5B32672F90B177C55FC`),
`p2_dangomushi_hazard_test` PASS. Runtime host wiring for the window/hazard
still belongs to the #407 Crawbster FSM and lane 20 Rock/Egg primitives.

## Lane 26 follow-up included (Man-at-Legs shell pool)

This tranche also carries the lane-26 shell-pool budget:

- `engine/pc_port/pc_p2_long_legs_fsm.{h,cpp}`: `shellsInFlight` input gates the
  `shotLoop` shell request against the source pool of 10.
- `engine/tools/p2_long_legs_fsm_test.cpp` plus ctest `p2_long_legs_fsm_test`.

Rebuild evidence in the same reconstructed tree: `pikmin_pc` relink (`[5/5]`,
exit 0; executable SHA-256
`4E05EAC4637AF7D31E73EFA361BC40B568CE8D58999B56EDAAF5676541BF4A53`),
`p2_long_legs_fsm_test` and `p2_dangomushi_hazard_test` 2/2 PASS.

The tranche also carries the lane-26 FSM host and foot-crush application:
`pc_port/pc_p2_long_legs.cpp` ticks `pc_p2_long_legs_fsm` from the draw path and
applies the landing foot press as an `InteractFlick` to nearby Pikmin. Rebuild
evidence: `pikmin_pc` relink exit 0; executable SHA-256
`F6D65CC83CADD60185A48A7888F0F84FC36BF3D9DF6C59895CF35A7C255F3331`; `ninja -n`
no work. Runtime state evidence for the host is recorded on
`opencode/p2-longlegs-fsm-root` (`docs/PIKMIN2_LONG_LEGS_RUNTIME.md`).



