# Challenge stage-select boot path: probe verdict + minimal selector (issue #669)

Lane `challenge-stage-select-boot`, generation 2. Implementation owner: Codex
through shared GitHub account `4laric`. Consumer: stopped lane
`p2-challenge-ch_nari_01kusachi-p1` (#533, blocked rev 4). No ADMIT, no
shared/native/family edits, no runtime run; all six runtime gates UNTESTED.

## Probe verdict: no existing fixture selects a P2 caveinfo stage

- `--experimental-challenge-level` (`engine/pc_port/pc_bbft.cpp:47-52`,
  maintained HEAD): accepts exactly one char `0-4` mapped to P1 area IDs.
  P2 `ui_index` 3 lives in a different namespace; passing `3` boots P1
  spring, not ch_NARI_01kusachi. No P2 path exists here.
- Host-mode module #651 (`native/pc_port/pc_p2_challenge_mode.{h,cpp}` on
  its lane branch, NOT in maintained HEAD): pure `selectByUiIndex` logic
  over a caller-supplied table, header-inline, with no maintained CMake
  registration and no engine boot hook of its own (per its own lane record:
  "maintained registration + engine boot hook remain gates"). No boot path.
- Guarded fixture #649 (`SLOT_RE ^chal[0-4]$` in
  `experimental/pikmin2_challenge_runtime_inputs.py` on its lane branch):
  P1 stages only. No P2 path.
- Staged kusachi layout (commit `380610a3`, 18 tests): P1 run-layout
  staging + markers + spec with pinned source
  (`ch_NARI_01kusachi.txt`, sha256 `b8d232f4...34bb8d85`, ui_index 3,
  1 floor, 180 s, 50 blue leaf, sprays 1/2). Nothing to wire into: there
  is no selectable boot target.

No selection mechanism was invented: the verdict above is read-only.

## Minimal selector candidate (this lane, root-side only)

`experimental/pikmin2_challenge_stage_select_boot.py` (new, owned):
`select_stage` validates an exact P2 stage key against the canonical plan
+ inventory pins (category, cave_id/path, floors, roster matrix, timers,
sprays, indices, recorded source sha) and returns the boot-selection
record; `render_boot_request` serializes it as `P2_CHALLENGE_STAGE_SELECT_1`
text. P1 `chal<N>` slots are refused as a different namespace; unknown
keys, pin drift, malformed matrices/timers, and incomplete records all
fail closed (9 tests + 13 subtests pass). No native consumer exists yet.

## Precise missing hook (for owner review before landing)

- Engine boot flag accepting a P2 stage key (e.g.
  `--experimental-challenge-stage <cave_id>`); reusing
  `--experimental-challenge-level` would misboot P1 spring for ui_index 3.
- Registration of a decoded P2 stage table (host-mode `selectByUiIndex`
  is the pure-logic precedent) with maintained CMake/CTest wiring
  (#651 owned files; #186 review required).
- Guarded-fixture `SLOT_RE` extension beyond `^chal[0-4]$` (#649 owned
  files; owner review required).

## Packet

- This lane: branch `codex/autofill-challenge-stage-select-boot`, base
  `36b868391e62cccf37d992aa2f796f3cc9c6dc31`, this commit (3 new files).
- Consumed read-only: kusachi layout `380610a3`; host-mode/guard facts
  from their lane branches (no commits consumed, no files copied).
- Downstream consumer: `p2-challenge-ch_nari_01kusachi-p1` (#533, blocked
  rev 4) — hand this packet plus the missing-hook list to its owner and
  the integrator (#437).
- Remaining work: native hook + registration + guarded extension (all
  owner-reviewed); then a real private boot with fixture adoption.