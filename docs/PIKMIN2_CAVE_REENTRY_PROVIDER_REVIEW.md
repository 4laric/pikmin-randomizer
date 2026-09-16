# Cave cleanup_reentry provider contract review (#488)

Lane `cave-reentry-provider-contract-review`, issue #488 (OPEN, parent #586).
Review-only slice: confirm the lane-11 checkpoint provider is present and
integrated, and publish the exact follow-on contract that closes cave50/51
`cleanup_reentry` for carry state. No runtime run, no native build, no shared
fixture edit, no ADMIT. All six runtime gates stay UNTESTED in this slice;
`cleanup_reentry` PASS is not claimed. All observations below are static
(source-tree reads); staged versus natural labeling applies to any future
run, not to this review.

## 1. Provider presence at the pinned commit (all present)

Pinned worktree base `35755108` ("lane51: generation-2 natural-loop re-sweep
record (#489)", contained in `codex/muse-l74-cave-integrator` and
`deepseek/p2-l51`). Checker
`experimental/pikmin2_cave_reentry_contract.py --native <tree>` reports all
four checks present.

| Artifact | Marker (file:line) | SHA-256 at pin | Size |
|---|---|---|---|
| `engine/pc_port/pc_p2_cave.cpp` | `P2_CAVE_RESTORE species/maturity` printf (:113) | `e4985f3c163afed635e822424a461f8faf616105090bedfda94fe3066e3f6af6` | 19261 |
| `experimental/pikmin2_cave_restart_runtime.py` | `P2_LANE11_WRITE` (:60), `P2_CAVE_TRANSFER_3` (:147), `PASS P2_LANE11_RESTORE` (:51) | `6ddaef04da91ae0a89d2f0a5260724eb4f523a34bd9147d2762bb14b2004075f` | 9853 |
| `tests/test_pikmin2_cave_restart_runtime.py` | 6 validator tests + object-graph test | `5e92acde6c54d7d2778903ef1bba2e3cfaaca83060adaf31beb0a8a9ff66443d` | 3275 |
| `engine/tools/test_p2_cave_transfer.cpp` | `P2_CAVE_TRANSFER_3` header assert (:84) | `4c4238d52683eba5dac02ad0f66ae2d1491282f8fae60e2363e25205af70d2de` | 4667 |

Recent history of these files is on the maintained engine line (batch
reconciliation, hard-lane export, cave hole/geyser visuals). This corrects
cycle 1: the provider is not missing pending lane-11 invariants; it exists
and is integrated at the pin.

## 2. Exact follow-on contract to close cave50/51 cleanup_reentry

Cave50 handoff leaves exactly one gate UNTESTED (`cleanup_reentry`, "No
restart/re-entry run in this slice"; remaining work "Restart/re-entry run
for carry state"). The closing run must, in order:

1. Stage live carriers holding real treasure (cave50/51 carry fixture;
   staged squad positions labeled, never presented as natural spawns).
2. Checkpoint via `pc_p2_cave_checkpoint(false)` and observe
   `P2_LANE11_WRITE ok=1` plus a `P2_CAVE_TRANSFER_3`-headed transfer file.
3. Restart/re-enter and observe `P2_LANE11_READ`, one `P2_CAVE_RESTORE
   species=<n> maturity=<n>` line per live carrier, treasure continuity
   into the re-entered scene, and `PASS P2_LANE11_RESTORE`.
4. PASS is granted only on a fully natural restore; any staged squad,
   injected carrier, or forced transport is labeled and fails the gate.

Entry points the carry fixture must call: the checkpoint write path above
and the existing restore reader; no new native entry points are required
for the observation itself.

Shared versus lane-owned files: `pc_p2_cave.cpp` and the carry
engine/headers are family-owned (muse-cave50, done); `pc_p2_cave_transfer.h`
belongs to cave-multifloor-identity (done); the generate module belongs to
cave-generate-provider (done); the restart runtime/tests are shared
runner-level with no lane owner. Any shared fixture edit requires the
cave50/51 owner AND the caves integration owner (#519/#570) review first;
this review proposes no such edit.

## 3. Checker and tests

`experimental/pikmin2_cave_reentry_contract.py` (`--native` provider
presence, `--log` run-log sequence with verbatim staged flag, exit 0/1).
`py -3.12 -m pytest tests/test_pikmin2_cave_reentry_contract.py -q` →
8 passed, 4 subtests (synthetic temp trees/logs only; real-pin runs above
were executed manually for this review).

## 4. Remaining work / honesty notes

- The staged Bulbmin in the restart validator squad (species=5) is a staged
  input: a future PASS must still prove natural carry/restore around it.
- Presence is necessary, not sufficient, for #161-style re-entry or any
  admission claim. No gate flipped.
- Captain-safety #632 not applicable (no runtime run; recorded here as N/A
  with the guard reference scripts/p2_fixture_captain_guard.h for any
  future runtime spec).