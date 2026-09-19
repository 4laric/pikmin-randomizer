# Yakushima4 floor-boundary save persistence adapter (issue #784)

First bounded slice of the yakushima4 save/persistence work traced by the #779
pin-discovery handoff (e28c1c16) for downstream consumer
`shard-caves-yakushima-yakushima4-p1` (#161, blocked). Tooling only: the adapter
validates the floor-boundary checkpoint write/read/validate sequence, persisted
floor/roster state and day/progression anchors against the landed #132 cave-save
contract. No engine edits, no runtime, no ledger/admission writes, no ADMIT.
All six arena gates UNTESTED.

## Pinned contracts (read-only)

| Contract | Worktree commit | Artifacts |
|---|---|---|
| Cave save | `8aaf6cf6` | `pc_port/pc_p2_cave_transfer.h:17-121` wire format; `pc_port/pc_p2_cave.cpp:123-169` `pc_p2_cave_checkpoint`; `tools/test_p2_cave_transfer.cpp` schema asserts |
| Dayclock anchors | `4fff74c7` | `singleGameSection.cpp:216` `advanceDayCount`; `:183/:209` `CaveDayEndState` init/exec; `mCaveSaveData`/`mCurrentCaveID`/`mCurrentFloor` |
| Surface session | `7b6d25df` | schema `p2-surface-session-1` checker; save-after-sunset and course-matched reload rules |

Floor-1 reference pin: native `88188a1e3d687132baf4c2ab7c01b3c752ef4500`
(the #161 floor-1 traversal evidence, cited for reference only). Root base
`36b868391e62cccf37d992aa2f796f3cc9c6dc31`.

## Checkpoint wire format enforced

`P2_CAVE_ENTRY_<schema>` / `P2_CAVE_TRANSFER_<schema>` (`schema` 1/2/3), a
32-lowercase-hex token, floor, health, survivor count, then `species maturity`
rows. Schema 1 carries Blue/Red/Yellow/Purple, 2 adds White, 3 adds Bulbmin;
the transfer schema is bumped to the newest carried species and never
downgraded. Unknown schema, bad token, unsupported floor, bad health/count,
species unsupported by the schema, bad maturity and trailing data are all
refused with the same clause names the engine reports (`header`, `Pikmin`,
`trailing data`).

## Persisted floor/roster state

Floor id (contract-supported range), a nonempty living-squad census whose size
matches the declared census, and a NAV topology reference (`rooms`/`links`)
from the #161 traversal evidence. Missing or inconsistent state fails closed.

## Day / progression anchors

`day_count` (1..29; the engine repeats day 29 to stay inside the 30-entry diary
tables), `mCurrentCaveID`, `mCurrentFloor`, `CaveDayEndState` (`init`/`exec`)
and `mCaveSaveData` state. The audit also requires the checkpoint, floor state
and anchors to agree on floor and survivor count.

## Exact floor-boundary procedure

1. Read `P2_CAVE_ENTRY_<schema>` at the floor boundary and parse it through
   `validate_checkpoint_text`.
2. Collect the living-squad census plus the NAV topology reference into the
   floor state and validate with `validate_floor_boundary_state`.
3. Record the day/progression anchors and validate with `validate_day_anchors`.
4. Assemble the plan with `audit_floor_boundary`, which cross-checks floor and
   census agreement and returns the contract citations.
5. For the write side, render the transfer with
   `format_floor_boundary_transfer` (schema bumped, 9-significant-digit health)
   exactly as `pc_p2_cave_checkpoint` does.

## Fail-closed blockers (exact)

`invalid-pin`, `missing-section`, `absent-provider`, `malformed-record`,
`malformed-state`, `malformed-anchors`, `out-of-scope-floor`, `header`,
`Pikmin`, `trailing data`, `mismatched-floor`, `mismatched-census`. `blockers()`
collects them without raising; missing inputs are blockers, never a pass.

## Tests

`py -3.12 -m pytest tests/test_pikmin2_yakushima4_save_persistence.py -q`
(also runnable via unittest): 19 tests + 14 subtests, all synthetic, no engine
files, no runtime.

## Remaining work

- Higher floors 2-5 (this slice refuses floor >= 3 with `out-of-scope-floor`).
- Species admission for the floor rosters.
- Engine wiring: the adapter validates artifacts; landing it in the engine's
  floor-boundary path is a separate engine-change slice under #186 review.
- Downstream consumer `shard-caves-yakushima-yakushima4-p1` (#161) remains
  blocked pending that engine wiring.
