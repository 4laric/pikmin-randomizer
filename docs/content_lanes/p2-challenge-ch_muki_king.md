# P0 source audit: P2 Challenge stage `ch_MUKI_king` (issue #542)

Lane p2-challenge-ch_muki_king, parent #531, recovery #568. P0 ONLY. No claim
of playability; full content acceptance and all runtime dependencies stay OPEN.

## Source identity

- Retail file: `user/Mukki/mapunits/caveinfo/ch_MUKI_king.txt` (loaded per
  floor through `user/Mukki/mapunits/caveinfo/` in
  `src/plugProjectKandoU/baseGameSection.cpp:2244`, via
  `Cave::CaveInfo::load`).
- Recorded sha256: `c2d773778e26aad2dc36defbb40540d54a7ddd48d0e1a59c604db58765fd35aa`
  (`docs/PIKMIN_CONTENT_IMPORT_LANES.json` lane entry and
  `docs/PIKMIN2_CONTENT_INVENTORY.json` `source_sha256`).
- The actual retail bytes were NOT on disk in this slice, so no fresh hash
  observation is claimed. Exact prerequisite: extract read-only from a
  legally owned P2 disc (e.g. `C:/Users/alari/Downloads/PIKMIN2 for
  GAMECUBE.iso`) and rerun the adapter CLI below; the adapter refuses
  mismatched bytes.
- Decomp revision: `632af9378` (read-only `native/pikmin2-research`).

## Decoded schema (source-backed, not invented)

`CaveInfo::load` reads the file as a TEXT stream (`STREAM_MODE_TEXT`).
`CaveInfo::read`: cave parms (`mFloorMax`, `c000`, 1..128) + int
floor-block count + `FloorInfo` blocks. `FloorInfo::read`: floor parms
(f000 floor-first, f001 floor-last, f002 teki max, f003 item max, f004 gate
max, f014 cap max, f005 rooms 1..15, f006 route ratio 0..1, f007 escape
fountain, f008 unit file, f009 lighting file, f00A vrbox, f010 hole-clogged,
f011/f012/f013 alpha/beta/hidden enums, f015 version, f016 waterwraith
timer, f017 seesaw) + teki list + item list + gate list + cap list iff
version >= 1.

Row shapes: teki = token + weight + gen-type (`CaveGenType` 0..8);
`TekiInfo::read` token grammar = optional `$N` drop prefix (digit 1-9, else
PikminOrLeader) + enemy name matched against `gEnemyInfo[]` + optional
`_treasure` held suffix. Item = name + weight. Gate = name + life + weight.
Cap = empty byte, else an embedded teki row.

Text-grammar facts: `Parameters::read` consumes (id, size, value) parms;
`Parameters::write` emits tab-`# name` comments, so `#` starts a comment.

## Catalog baseline (carried, not decoded here)

From the lane plan (itself sourced from `user/Matoba/challenge/stages.txt`
at plan time): 5 floors, roster/maturity matrix (20/20/0/10/0/0/0 leaf at
native-color rows), bitter 2 / spicy 2, floor timers 5x100.0 s, ui_index 9,
table_order 29. The adapter preserves these verbatim and cross-checks
decoded floor coverage (contiguous 1..5) against them.

## Adapter and contract

`experimental/content_lanes/p2-challenge-ch_muki_king.py`: strict
structural decode, sha256-vs-recorded gate, contiguous-coverage validation,
weight sums mirroring `getTekiWeightSum`/`getItemWeightSum`/
`getGateWeightSum`, resource closure (unit/lighting/vrbox files per floor),
metadata-only manifest. Hard negative contract: `placements_emitted` is
always False; weighted rows are definitions, never actor counts. Unknown
parm ids and unknown enemy tokens are explicit errors, never skipped.

CLI reproduction (requires staged legal source; fails closed otherwise):

```powershell
py -3.12 experimental/content_lanes/p2-challenge-ch_muki_king.py --source <path-to-ch_MUKI_king.txt> --manifest-out <manifest.json>
```

## Required coverage (metadata only)

| Item | Manifest fields | Status |
|---|---|---|
| 5-floor coverage | floors[].first/last vs catalog 5 | metadata-only |
| source IDs / enemy tokens | teki[].enemy validated vs gEnemyInfo | metadata-only |
| roster/maturity | catalog_baseline matrix | preserved baseline |
| sprays | catalog_baseline bitter/spicy | preserved baseline |
| timers | catalog_baseline floor_seconds | preserved baseline |
| resource closure | unit/lighting/vrbox files | metadata-only |

## Exact native/framework blockers (P1 prerequisites, unchanged)

Runtime import waits on validated publications from existing owners: #136
(Challenge runtime framework), #137 (Challenge content), #129 (cave
generation/seams), #130/#131 (actors/species). Propose scoped shared
reviews to those owners; no shared edits made here.

## Tests and evidence

`tests/content_lanes/test_p2_challenge_ch_muki_king.py`: 20 focused tests
(synthetic happy path + weight sums + version gate + drop/treasure grammar
+ 14 malformed/missing-input boundary cases + live decomp-registry name
check). All cave-shaped fixtures labeled SYNTHETIC; no retail fact asserted.

```powershell
py -3.12 -m pytest tests/content_lanes/test_p2_challenge_ch_muki_king.py -q
```

## Remaining work

- Stage the legal `ch_MUKI_king.txt`, verify sha256 vs recorded, run the
  CLI, attach the manifest.
- P1/P2 activation requires dependency publications and updated scoped
  ownership; this P0 slice makes no runtime or admission claim.
