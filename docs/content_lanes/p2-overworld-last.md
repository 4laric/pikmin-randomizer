# P0 source audit: P2 overworld course `last` (Wistful Wild)

Lane p2-overworld-last, issue #151, parent #531. P0 ONLY. No claim of
playability; full content acceptance and all runtime dependencies stay OPEN.

## Source identity

- Retail file: `user/Abe/stages.txt` (loaded by `Game::Stages` via
  `loadFromFile(this, "user/Abe/stages.txt", ...)` in
  `src/plugProjectKandoU/gameStages.cpp:357`).
- Decomp revision: `632af9378` (read-only `native/pikmin2-research`).
- Recorded inventory hash for this file: **none**
  (`docs/PIKMIN2_CONTENT_INVENTORY.json` `source_sha256` has no
  `user/Abe/stages.txt` entry; lane plan `source_sha256` is null).
  The actual retail bytes were NOT available in this slice, so no retail
  hash is claimed. Exact prerequisite: stage a legal copy read-only from a
  legally owned P2 disc (e.g. `C:/Users/alari/Downloads/PIKMIN2 for
  GAMECUBE.iso`) and rerun the adapter CLI below.
- Course: `last` (Wistful Wild), expected at index 3 of 4 courses
  (`MAX_LEVELS (4)`, `include/Game/gameStages.h`).

## Decoded schema (source-backed, not invented)

`Stages::read`: int16 course count, then one `CourseInfo::read` per course.
`CourseInfo::read` keyword order: `name`, `folder`, `abe_folder`, `model`,
`collision`, `waterbox`, `mapcode`, `farm`, `route`, `start` (3 floats),
`startangle` (1 float + 1 discarded trailer token), `LimitGenInfo`
(count + name/minimum_day/maximum_day/day_limit rows), `LoopGenInfo`
(same shape), `CaveOtakaraInfo` (count + cave-id/otakara-count/filename
rows), final `mGroundOtakaraMax` int.

Resource closure joins mirror `Stages::createMapMgr`: `folder`+model,
`folder`+collision, `folder`+waterbox, `folder`+mapcode, `folder`+farm,
`abe_folder`+route.

## Adapter and contract

`experimental/content_lanes/p2-overworld-last.py` implements the isolated
P0 adapter: strict order-dependent decode, `last`-at-index-3 selection,
defect validation (empty paths, inverted/negative schedules, duplicate
cave ids, negative counts), byte-exact sha256, and a metadata-only
manifest. Hard negative contract: `placements_emitted` is always False;
generator rows are definitions, never actor counts.

CLI reproduction (requires staged legal source; fails closed otherwise):

```powershell
py -3.12 experimental/content_lanes/p2-overworld-last.py --source <path-to-stages.txt> --manifest-out <manifest.json>
```

## Required-inventory coverage (metadata only)

| Required item | Manifest fields | Status |
|---|---|---|
| terrain/collision/water | collision, waterbox, mapcode, model | metadata-only |
| generator day schedules and regrowth | limit_gen, loop_gen | metadata-only (definitions, not placements) |
| buried/enemy-held treasure | caves[].otakara_count, ground_otakara_max | metadata-only |
| Onions/ship/bridges/gates | farm, route | metadata-only |
| all cave entrances and return anchors | caves[].cave_id, caves[].filename | metadata-only |

## Exact native/framework blockers (P1 prerequisites, unchanged)

Runtime import waits on validated publications from existing owners:
#128, #130, #131 (actor/assets/species and hazards), #132 (surface days,
saves and progression), #140, #144, #145, #146. Cave generation seams
stay with #129 / lanes 34-51 / #468; P2 Challenge framework with #136.
Propose scoped shared reviews to those owners; no shared edits made here.

## Tests and evidence

`tests/content_lanes/test_p2_overworld_last.py`: 17 focused tests
(synthetic happy path + closure joins + 16 malformed/missing-input
boundary cases). All synthetic fixtures are labeled SYNTHETIC and assert
no retail fact. Run:

```powershell
py -3.12 -m pytest tests/content_lanes/test_p2_overworld_last.py -q
```

## Remaining work

- Stage the legal `user/Abe/stages.txt`, record its sha256, run the CLI,
  attach the manifest.
- P1/P2 activation requires dependency publications and updated scoped
  ownership; this P0 slice makes no runtime or admission claim.
