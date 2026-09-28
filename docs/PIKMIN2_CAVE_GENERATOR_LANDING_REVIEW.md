# Cave generator provider landing review (#129)

Lane `cave-generator-landing-contract-review`, issue #129 (OPEN, parent #586).
Review-only slice: verify the accepted #129 provider landing read-only, assess
mergeability onto the maintained native line, and publish the unblock signal
for live lane yakushima4-p1 (#161). No implementation, no merge, no shared
edits, no gate flips, no ADMIT. All observations below are static/staged
(source-tree reads and three-way content comparison); no runtime run was
executed and no gameplay claim is made.

## 1. Landing file list (native merge e44b5d70)

`e44b5d70f9a7c029682194d9b45ae2e9b8fd6fd1` — "wave-native: merge #129 cave
generator module + reviewed pc_p2_cave.cpp hook" (2026-09-16, 262 insertions).
Parents: `dc0a2f86` + `2c52c039` ("cave-generate-provider: retail cave
generation module behind opt-in setup hook (#129)").

| File | Change | Git blob | SHA-256 of bytes | Size |
|---|---|---|---|---|
| `pc_port/pc_p2_cave_generate.h` | new, 250 lines | `89d0968b6705fa40c61fcbce6f1ed93ef71e57c` | `f083a892dca82ee858090630d87fee077ebd942c7047227f809014570df90f6f` | 10590 |
| `pc_port/pc_p2_cave_generate.cpp` | new, 10 lines | `2c2a25a29e242c849add5fa8570aa6384a5e0399` | `915eeeafef6ff67dd99403a1781d5ca01cd4afec7768ac456197c8142ff93ceb` | 511 |
| `pc_port/pc_p2_cave.cpp` | +2 lines | (post-merge blob `820de48769fba6f01a524c89c1c2f720114bb0e0`) | — | — |

The `.cpp` TU is header-inline by design (no CMakeLists change in the slice;
integrator wires it into PC_PORT_SOURCES under #186 review as follow-on).

## 2. Hook context (exact 2 lines)

In `pc_p2_cave_setup()` at e44b5d70:

- file line 2: `#include "pc_p2_cave_generate.h"` (inserted after line 1
  `#include "pc_p2_cave.h"`, before `pc_p2_cave_nav_diagnostics.h`);
- file line 145: `pc_p2_cave_generate_run(); // lane cave-generate-provider
  (#129): opt-in manifest sidecar only; reviewed hook, pending #186`
  (inserted immediately after the `P2_CAVE_READY` printf, before the
  `if(beasts && floor>=3)` beasts-entry line).

Marker contract for the checker: header declares
`inline bool pc_p2_cave_generate_run()`; TU defines
`kP2CaveGenerateModule`; hook file carries both the include and the call.

## 3. Ancestry and absence (verified read-only)

- `e44b5d70` is an ancestor of NONE of: maintained line `a95040b6`,
  species autofill pin `ce89a039`, yakushima4-p1 native `8f608738`
  (`merge-base --is-ancestor` false in all three directions tested).
- Provider files absent from `a95040b6` and `ce89a039` trees (empty
  `ls-tree`); checker run confirms all-absent on `ce89a039`, `8f608738`,
  and the canonical checkout, all-present on `e44b5d70`.
- Merge-base(`e44b5d70`, `a95040b6`) = `086ed858`.

## 4. Three-way mergeability assessment (pc_p2_cave.cpp only)

- Full-file `git merge-file` (base `086ed858`, ours `a95040b6`, theirs
  `e44b5d70`): exit 7 with 7 conflict regions. The conflicts are dominated
  by unrelated line evolution (species/white support, checkpoint schema v2,
  window title on the target side), NOT by the generator hook.
- Hook-only patch (`git diff dc0a2f86..e44b5d70 -- pc_port/pc_p2_cave.cpp`,
  969 bytes, exactly the 2 added lines): `git apply --check` onto
  `a95040b6` FAILS at both hunks —
  hunk 1 (include): 4th context line differs (`pc_p2_cave_entry_policy.h`
  in provider line vs `Graphics.h` in target);
  hunk 2 (setup call): trailing beasts-adjacent context is absent in the
  target (zero `BEASTS` references in `a95040b6:pc_port/pc_p2_cave.cpp`;
  its `pc_p2_cave_setup()` ends right after the `P2_CAVE_READY` printf).
- The two new files are purely additive (no target counterpart exists).

Conclusion: NOT a clean cherry-pick. Landing needs small manual resolution
at both hook sites (insert include after line 1 regardless of the 4th-line
drift; insert the setup call after the `P2_CAVE_READY` printf with the
beasts-adjacent context dropped), plus adding the two new files. No
semantic overlap with the target-side species/checkpoint/title changes was
found. The hook comment itself records reviewed-but-pending-#186 status.

## 5. Unblock signal for yakushima4-p1 (#161)

The live #161 lane is BLOCKED stating exactly this gap (pins lack the
provider module). Unblock path for the integrator (merge stays
integrator-owned): land `e44b5d70`'s three files onto the P1 native line
with the two manual hook placements above, then #161 can observe real
floor-1 unit staging. Shared-seam review goes through #169/#186; the
`.cpp` TU wiring into PC_PORT_SOURCES is a separate follow-on.

## 6. Checker and tests

`experimental/pikmin2_cave_generator_landing_check.py --native <tree>`
reports per-check presence and exits 0/1. `py -3.12 -m pytest
tests/test_pikmin2_cave_generator_landing_check.py -q` → 7 passed
(synthetic temp trees only; real-pin runs above were executed manually for
this review, not committed as paths).

## 7. Remaining work / honesty notes

- Checker covers presence only, not hook-call ordering, TU wiring, or
  runtime behavior; a present landing is necessary, not sufficient, for #161.
- No gate flipped; no admission claim; captain-safety #632 not applicable
  (no runtime run; recorded here as N/A with the guard reference
  scripts/p2_fixture_captain_guard.h for any future runtime spec).