# P0 source audit on real bytes: P2 overworld course last (Wistful Wild)
 
Lane p2-overworld-last-p0-real-source, issue 151. P0 ONLY. No claim of
playability; full content acceptance and all runtime dependencies stay OPEN.
 
## Source identity (observed, not assumed)
 
- Retail file user/Abe/stages.txt extracted read-only from the verified local ISO
  C:/Users/alari/Downloads/PIKMIN2 for GAMECUBE.iso (disc offset 770327488,
  size 3275) via experimental.pikmin2_assets.disc_files. Staged lane copy:
  prepared/last-p0-output/stages.txt.
 - Observed sha256 4de9008c99e799b99b2746c0156846eeb7ad50895ad110fc7f2070db6de1fff8,
  3275 bytes. Recorded in manifest-real.json and asserted by the real-bytes test.
 - Course last (Wistful Wild) at index 3 of 5 courses
(tutorial, forest, yakushima, last, test_map).
 
## Corrections to the synthetic-only revision
 
The prior adapter encoded three wrong assumptions, all corrected here against
the observed bytes: course count is 5 not 4; there is no farm keyword
(keyword order is name, folder, abe_folder, model, collision, waterbox,
mapcode, route, start, startangle, literal end trailer); each course sits in
brace blocks; # starts an end-of-line comment; cave ids are brace-wrapped
({l_01}); the startangle trailer token is the literal word end.
 
## Decoded last summary (real bytes)
 
- Start position -3300, 0, -850; start angle -130 degrees.
- Resource closure: model user/Kando/map/last/last.bmd,
  collision user/Kando/map/last/collision.bin,
  waterbox user/Kando/map/last/waterbox.txt,
  mapcode user/Kando/map/last/mapcode.bin,
  route user/Abe/map/last/route.txt.
- LimitGenInfo: 1 row (0-1.txt, days 0 to 1, limit 1). LoopGenInfo: 0 rows.
- CaveOtakaraInfo: 3 rows: l_01 with 17 from last_1.txt,
  l_02 with 13 from last_2.txt, l_03 with 21 from last_3.txt.
- Ground-otakara max: 5. No placements emitted, ever.
 
## Adapter and contract
 
experimental/content_lanes/p2-overworld-last.py implements the isolated P0
adapter against the observed grammar: comment stripping, brace blocks,
strict order-dependent decode, last-at-index-3 selection, brace-wrapped cave
ids, defect validation (empty paths, inverted or negative schedules,
duplicate cave ids, negative counts), byte-exact sha256, metadata-only
manifest with placements_emitted always False.
 
CLI reproduction (from the prepared root):
 
    py -3.12 experimental/content_lanes/p2-overworld-last.py --source <stages.txt> --manifest-out <manifest.json>
 
Real-source manifest: prepared/last-p0-output/manifest-real.json.
 
## Required-inventory coverage (metadata only)
 
- terrain/collision/water: collision, waterbox, mapcode, model.
- generator day schedules and regrowth: limit_gen, loop_gen (definitions only).
- buried/enemy-held treasure: caves otakara counts, ground_otakara_max.
- Onions/ship/bridges/gates: route (no farm field exists in retail bytes).
- all cave entrances and return anchors: cave ids and filenames.

## Exact blockers (P1 prerequisites)
 
Runtime import waits on validated publications: 128, 130, 131 (actors),
132 (surface days, saves, progression), 140, 144, 145, 146. Per the
launch brief, 129 cave-generate-provider and 132 cave-multifloor-identity
are now done and integrated; surface save/progression and receipt
publications remain the P1 gate. P1 remains gated on validated surface
save/progression and receipt publications. No shared edits made here.
 
## Tests and evidence
 
tests/content_lanes/test_p2_overworld_last.py: 23 focused tests (synthetic
happy path plus closure joins, malformed and missing-input boundary cases,
plus the recorded real-bytes decode of course last). Run from the prepared root:
 
    py -3.12 -m unittest tests.content_lanes.test_p2_overworld_last -v
 
Test log: prepared/last-p0-output/test-real.log. No runtime or admission claim.

## P1 runtime import + surface-session acceptance

Lane p2-overworld-last-p1-surface-session, issue 151 (this slice). Consumes
the integrated generic contract `surface-session-provider-contract` (#132,
schema `p2-surface-session-1`, module
`experimental/pikmin2_surface_session_contract.py`) instead of inventing
local day/save semantics. No parser fork: the P1 path reuses
`load_source_bytes`, `decode_course_file`, `select_course`,
`validate_course`, `resource_closure` and `build_manifest`.

### New adapter surface

- `load_surface_contract()` - loads the integrated #132 module (package
  import, else file fallback), refuses a missing module or a non-
  `p2-surface-session-1` schema with an explicit prerequisite message.
- `stage_run_layout(manifest, run_dir, source_path=None)` - stages the decoded
  real-source manifest into a private run layout
  (`<run_dir>/overworld-last/manifest.json` + `run-metadata.json` with schema
  `p2-overworld-last-p1-run-1`, source + manifest SHA-256 pins, contract
  schema, boundaries, `ledger_writes=false`, `placements_emitted=false`).
  Refuses a populated layout, a placement-emitting manifest or a non-`last`
  course. No ledger writes.
- `surface_session_script(manifest, start_day=1)` - the boundary script over
  the contract's existing events only: day transition (`begin_day`),
  save/reload (`sunset`,`save`,`reload`), receipt replay
  (`deliver_receipt` twice with the same identity/slot -> second rejected
  exactly-once), exit/reentry (`enter_cave`,`exit_cave` twice). Cave ids come
  from the decoded manifest.
- `drive_surface_session(manifest, start_day=1)` - runs the script through the
  contract checker, records per-step accept/reject plus per-boundary totals,
  and probes every `MISSING_INTEGRATION` item (native sunset driver, save
  serializer, receipt ledger endpoint, generator-cache restore) as rejected.
  Explicitly `existing_behavior_only=true`, `runtime_claim=false`.

### CLI

    py -3.12 experimental/content_lanes/p2-overworld-last.py \
      --source <stages.txt> --manifest-out <manifest.json> \
      --p1-run-out <run-dir> --surface-report <report.json>

Observed on the staged legal source (sha256 4de9008c...):
`boundary=day_transition accepted=1/1`,
`boundary=save_reload accepted=3/3`,
`boundary=receipt_replay accepted=1 rejected=1 (duplicate exactly-once)`,
`boundary=exit_reentry accepted=4/4`, `missing_integration=4`,
`runtime_claim=False`.

### Existing behavior vs missing integration

Day monotonicity, sunset snapshot, snapshot save/reload, exactly-once receipt
replay and cave exit/reentry carry-over are the contract's existing, engine-
free behavior. The four `MISSING_INTEGRATION` items are real native work
(NOT existing behavior) and are recorded as rejected prerequisites, not
assumed. All six arena gates stay UNTESTED; no playability or runtime claim.

### Tests

`tests/content_lanes/test_p2_overworld_last.py`: 36 focused tests total (23 P0
+ 13 P1) covering staging happy/refusal paths, boundary coverage, duplicate
receipt rejection, missing-integration recording, contract-schema/missing-
module refusal, missing-source prerequisite, and the real-source P1
stage-and-drive path. No runtime or admission claim.
