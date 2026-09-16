# Lane 51 — Item-5 independent QA checker + evidence audit (parent #468, lane issue #489)

Lane 51 / opencode Muse Spark 1.3 contributor session `ses_f57d3a2ffffeFz7p5aqD2xsqzw` /
parent spec #468, lane issue #489.
Mode: **Independent QA preparation**. QA/report tooling only; no production
source is edited on either branch.

## Concrete slot class / routine addressed; missing model piece

- **Routine addressed:** the missing independent regression matrix for item 5
  (the end-to-end "come back with yellow" loop). Lane 40 checks the seeded
  table/layout graph, lane 47 assembles the whole-chain QA report, lane 48
  validates bud acquisition alone — but no module scored the three item-5
  sub-parts (48 natural bud acquisition, 49 real water/elec geometry, 50
  gate/pool carry blocking) together against one log with a fail-closed
  natural/staged/proxy/missing verdict per row.
- **New modules:** `experimental/pikmin2_cave_item5_qa.py` (7-row matrix +
  CLI) and `native/tools/p2_cave_item5_qa.cpp` (standalone engine-free C++
  gate over the same markers). Both consume the actual l48/l49/l50 marker
  grammars verbatim; no marker was renamed or redefined.
- **Missing model piece it defines for consumers:** the item-5 row contract
  (`p2-cave-item5-qa/1`): `natural_acquisition` (NATURAL/STAGED/MOCKED/MISSING),
  `real_geometry` (REAL/PROXY/MISSING), `carry_blocked_closed`,
  `gate_open_credit`, `water_gating`, `hole_gating`, `timeline`
  (PASS/FAIL/MISSING, with `STAGED_OPEN` when a staged recolour opens the gate).
  The whole report passes only when every row is at its natural value; any
  other row fails and is named in `remaining` with its owning lane.
- **Boundary respected:** generator (41), rooms (44), geometry engine (45),
  items/receipts (46), bud actor (48), converter/meshes (49) and carry physics
  (50) are untouched. No second generator or checker was forked; lane-40 and
  lane-47 semantics are reused as-is.

## Root base/head; native base/head; dirty state; ordered commits

- Root worktree `C:\Users\alari\pikmin-randomizer\output\dsw\l51-root`, branch
  incl. base `c4d3c9b9b6ffadfa2d1c5a72f0d4fb6cb9c5b87a` (clean at start).
- Native worktree `C:\Users\alari\pikmin-randomizer\output\dsw\native-l51`,
  base `6da0364f5756cdcea80805939f2cb0d929a25cdc`.
- Dirty state at handoff: three new root files + this handoff (untracked until
  committed below) and one new native file `tools/p2_cave_item5_qa.cpp`
  (untracked; the leased build report records
  `native_dirty: ?? tools/p2_cave_item5_qa.cpp`). No tracked file is modified
  on either branch. Generated evidence stays under ignored
  `output/workflow/paid-scale/l51/` (never committed).
- Ordered commits (this slice, root branch `deepseek/p2-l51`):
  1. `3fb828a5 lane51: item-5 independent QA checker and focused tests (#489)`
  2. this handoff commit (`lane51: cave item-5 QA handoff (#489)`).
  Native branch `deepseek/p2-l51-native`:
  1. `6b288a3b lane51: standalone item-5 QA gate (#489)`.

## Owned files; generator hooks and provider/consumer agreements

Owned (new, additive only):

- `experimental/pikmin2_cave_item5_qa.py` — marker parser (malformed-tolerant,
  indexed), per-row evaluators, `evaluate()` over one log or merged multi-run
  logs, CLI (`--log` repeatable, `--receipts`, `--seed`, `--out`; exit 0 only
  on full pass).
- `tests/test_pikmin2_cave_item5_qa.py` — 19 focused tests (parser, acquisition,
  geometry, carry, timeline, determinism, multi-log merge, CLI rejection).
- `native/tools/p2_cave_item5_qa.cpp` — standalone STL-only gate printing
  `acquisition/geometry/block/open_credit/water/timeline` PASS/FAIL per row;
  exit 0 only on full pass. Deliberately **not** wired into CMakeLists (shared
  file owned by lane 50's reservation; compiles directly with g++).
- this document.

Generator hooks: none. No shared file (`teki.h`, `gameCaveInfo`,
`pc_p2_cave.*`, CMake, …) was touched; no `native/CMakeLists.txt` edit was
needed or made.

Provider/consumer agreements used as-is (read-only audit, no countersignature
changes):

- lane 48 `P2_CAVE_BUD_*` + `P2_CAVE_ROOMS_GRANT natural_acquire=` contract
  (incl. `P2_POM_*` aliases) from `experimental/pikmin2_cave_lane48_natural.py`;
- lane 49 `P2_CAVE_GEOMETRY_NODE/READY/DRAW/GATE_DENKI` real-mesh contract
  (`class=real proxy=0`, `READY real>=4 geometry=real`);
- lane 50 `P2_CAVE_GATES_1` / `P2_CAVE_CARRY_DOOR/VOLUME/PLAN/OPEN/BLOCKED/PHASE`
  contract from `pc_p2_cave_carry.h` (`carry_block elec/water` ↔ `key
  yellow/blue`; `carrying=1` = carrier evidence);
- lane 46 `P2_CAVE_ITEM_RECEIPT new=` exactly-once semantics;
- lane 44 `P2_CAVE_ROOMS_TIMELINE` fresh/yellow/full tags;
- lane 40 six-item contract numbering for the mapping below.

## What is already integrated; what is actually new

- Already integrated on the bases: lanes 34–47 (schema, growth, leaves,
  item/gate placement, buds, AP logic, spike/checker, native generator, live
  hook, proxy rooms, real geometry/egate, physical items/receipt, QA sweep);
  lane 48's bud actor + validator and lane 49's water converter + real meshes
  exist on their own branches (audited here, not merged); lane 50's carry
  blocking exists as uncommitted work in `output/dsw/native-l50` (audited
  here, not copied).
- Actually new: the 7-row item-5 matrix, its two implementations, the audit of
  the real l48/l49/l50 logs below, and the synthetic full-pass control proving
  the matrix is not fail-always. No production behavior is new.

## Build evidence line (native commit, exe SHA-256, ninja -n)

Canonical lease `output/muse-wave/control/leased_run.py`, private build dir
`output/msw/native-cave51-paid-build`, native `6da0364f` (dirty only with the
new tool file):

- `build-1789528163956484900`: configure + `p2_cave_transfer_test`, exit 0,
  log sha256 `0e02a4d6…287f740`. Target builds; `ninja -n` no-work dry run
  recorded in the same leased sequence (exit 0).
- Standalone QA tool via the same lease:
  `build-1789528283696804300`, `g++ -std=c++17 -O2`, exit 0;
  exe `output/workflow/paid-scale/l51/audit/p2_cave_item5_qa.exe`
  sha256 `98fd58eadf8e2ed48705a3866abb054515422518d12e02bfb573524896d39473`.
- Root tests: `py -3.12 -m pytest tests/test_pikmin2_cave_item5_qa.py -q`
  → **19 passed**.

## Fixture / seed used; observed generation evidence with exact paths

Floor `forest_1` floor 1, frozen seed `468001` throughout. No new live run was
launched for this slice (full natural sweep is blocked until lane 50 and
integration publish a frozen pin); the audit below scores the lanes' own
captured logs read-only:

- `output/dsw/l48-out/run-1/buds-run.log` → `output/workflow/paid-scale/l51/audit/l48-salt0.json`
  (sha256 `26f87fab…c0146`).
- `output/dsw/l49-out/rooms-preview/preview-a/geometry-run.log` →
  `output/workflow/paid-scale/l51/audit/l49-salt0.json` (sha256 `0f22972d…218407`).
- `output/dsw/l50-out/run-1/carry-run.log` (+ `p2-cave-gates.txt` plan) →
  `output/workflow/paid-scale/l51/audit/l50-run1.json` (sha256 `2542cc78…bd7e4`).
- Synthetic full-pass control (clearly labelled injected, proves the matrix can
  pass): `audit/synthetic-full-pass.log` → `audit/synthetic-full-pass.json`
  (sha256 `8cfc7469…6fc02a`); C++ gate exit 0
  (`build-1789528330458641400.log`, sha256 `31f9e7f7…c7fd28`).
- Cross-tool agreement on the real logs: C++ gate prints
  `acquisition=PASS … timeline=PASS / FAIL p2 cave item5 qa` on l48 and
  `acquisition=FAIL geometry=PASS … timeline=PASS / FAIL` on l49
  (`build-1789528311682024100.log`, `build-1789528317008585400.log`),
  matching the Python rows exactly.

Reproduction (from `output/dsw/l51-root`):

```powershell
py -3.12 -m experimental.pikmin2_cave_item5_qa --log C:/Users/alari/pikmin-randomizer/output/dsw/l48-out/run-1/buds-run.log --out C:/Users/alari/pikmin-randomizer/output/workflow/paid-scale/l51/audit/l48-salt0.json
```

Expect `evidence_class=PARTIAL`, `natural_acquisition=NATURAL`,
`carry_*=MISSING` (exit 1 — partial evidence, not a tool failure).

## Acceptance contract 1-6 results (injected vs natural)

Lane-40 contract items mapped onto the item-5 rows (real-lane evidence only;
nothing mocked is reported as natural):

| # | Contract item | Result on current evidence | Evidence class |
|---|---|---|---|
| 1 | Generation invariant | PASS — engine layouts with `generation_pass=true` (lanes 41/48) | **natural** (prior lanes; not re-run here) |
| 2 | Seed determinism | PASS — 468001 vs 468002 tables differ; conversions byte-identical across salts (lanes 40/48/49) | **natural** (prior lanes) |
| 3 | Re-roll invariance | PASS — salt 0 vs 7 keep table/requirements (lanes 40/41/48/49) | **natural** (prior lanes) |
| 4 | Reachability | PASS (model) — only the water choke + required elec leaf/gate; l50's `P2_CAVE_GATES_1` plan now names 4 blocking doors | **natural** plan, live block unproven |
| 5 | End-to-end loop | **PARTIAL** — acquisition NATURAL (l48), geometry REAL (l49), but carry block/open/credit unproven (l50 run stops at `block_assign`; all `BLOCKED` lines `carrying=0`; no `OPEN`, no receipts, no timeline) | split: **natural** (48/49 sub-parts) + **missing** (50 sub-part) |
| 6 | Failure handling | PASS — negative controls `retry_required` (lane 40); l50 parser fail-closed (uncommitted) | **natural** (40) |

Item-5 matrix on the real logs (this slice's audit):

| Row | l48 log | l49 log | l50 run-1 log |
|---|---|---|---|
| natural_acquisition | NATURAL | STAGED (staged recolour, no bud) | MISSING (no bud/grant markers in carry fixture) |
| real_geometry | MISSING (proxy rooms run) | REAL (4 real nodes, READY real=4, DRAW real, DENKI accepted) | REAL* (plan `geometry=real`; meshes are the dry-unit reuse, not l49's water unit) |
| carry_blocked_closed | MISSING | MISSING | FAIL (plan present, 37 BLOCKED lines but all `carrying=0`; no carrier evidence) |
| gate_open_credit | MISSING | MISSING | MISSING (no OPEN, no receipts) |
| water_gating | MISSING | MISSING | FAIL (no `carrying=1` water block) |
| hole_gating / timeline | PASS | PASS | MISSING (carry fixture emits no timeline) |

`*` Integration gap filed below: l50's current plan instantiates
`p2cave_room_north3_1_tsuchi.mod` (dry reuse) on the water nodes, not l49's
real `room_kingchap_b_tsuchi` water unit — the two branches have not been
reconciled yet.

Six arena gates (species-gate format required by the workflow contract): all
**N/A (source-backed)** — this slice adds QA tooling only, no actor, no
spawner, no receiver, no death/corpse, no transport and no lifecycle change on
either branch; there is no arena behavior to grade.

## Re-roll / restart / cross-seed result (or named remaining dependency)

- **Re-roll:** not re-run live here; prior-lane evidence (l48 salt 0/7
  byte-identical bud markers; l49 salt 0/7 identical models, differing grid
  coords) stands and is cited, not duplicated.
- **Restart:** not evaluated — needs the lane-11 checkpoint pass; unchanged.
- **Cross-seed:** not re-run live; lane-40 `check_determinism` remains the
  authority.
- **Named remaining dependency:** `muse-cave50` (issue #488). The full natural
  runtime sweep — bud → natural yellow → gate opens → red carry crosses and
  credits exactly once → water blocks non-blue → hole behind only required
  gates, all on one frozen integrated pin — cannot run until lane 50 lands its
  block/open/credit loop and integration publishes the frozen cave pin. This
  lane's checker is ready to score that run unchanged.

## Known limitations; next consumer; ONE exact reproduction command

Limitations:

- The checker scores marker evidence; it cannot itself produce a floor or prove
  engine geometry. A full PASS on the synthetic control is labelled injected
  and is never a generation PASS.
- Water walkability is converter-side (`ATTR_Water` tagging, proven offline by
  lane 49 parsing the delivered `room.mod`); no live water-query marker exists
  yet, so the matrix has no `water_walkable_live` row by design.
- l50's fixture currently opens the gate with a staged recolour
  (`pc_p2_set_species(..., P2SpeciesYellow)` in `preview_p2_cave.inc`); the
  matrix reports that shape as `STAGED_OPEN`, never natural.
- Findings filed on owning lanes:
  - lane 50 (#488): carry fixture stops at `block_assign`; no `carrying=1`
    block, no `OPEN`, no receipt, no timeline in
    `output/dsw/l50-out/run-1/carry-run.log`; gate opens via staged recolour.
  - lane 50 × lane 49 (#488/#487): l50's water nodes reuse the dry
    `north3_1_tsuchi` unit instead of l49's real `room_kingchap_b_tsuchi`.
  - lane 48 follow-up (known): seeded per-bud count N not yet carried through
    the lane-44 bridge; blue acquisition still staged.

Next consumer: lane 50 (run the block→natural-open→exactly-once-credit loop,
  then score it with this checker), then the integrator (lane 01) for the
  frozen pin re-sweep that closes item 5.

ONE exact reproduction command (from `output/dsw/l51-root`):

```powershell
py -3.12 -m experimental.pikmin2_cave_item5_qa --log C:/Users/alari/pikmin-randomizer/output/dsw/l50-out/run-1/carry-run.log --out C:/Users/alari/pikmin-randomizer/output/workflow/paid-scale/l51/audit/l50-run1.json
```

Expect `carry_blocked_closed=FAIL` (`no_carrying_block_observed`),
`gate_open_credit=MISSING` (`no_gate_open`), exit 1 — the precise open
sub-part lane 50 still has to demonstrate.
