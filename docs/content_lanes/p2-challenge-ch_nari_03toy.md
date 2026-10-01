# P0 import contract: P2 Challenge 06 ch_NARI_03toy (issue #540)

Implementation owner: Codex through shared account `4laric`; executing
contributor Muse Spark 1.3, lane `p2-challenge-ch_nari_03toy`, P0 only.
Parent content issue #137; coordination #531; source coverage #109.
No native build, no gameplay runtime, no ADMIT, no playability claim.
Full content issue stays OPEN for P1/P2.

## Source identity

- Source ID `ch_NARI_03toy` (authoritative; English display title unresolved,
  source ID and UI index govern).
- Retail path `user/Mukki/mapunits/caveinfo/ch_NARI_03toy.txt`, read from a
  local legal US GPVE01 revision 0 disc image via
  `experimental.pikmin2_assets.disc_files`.
- Expected SHA-256
  `d74b49ac3d9a2388288b9cb868dd8717ff893fd522453b309740519be841f03c`
  (canonical `docs/PIKMIN2_CONTENT_INVENTORY.json` `source_sha256` entry,
  mirrored in `docs/PIKMIN_CONTENT_IMPORT_LANES.json`).
- Encoding `shift_jis`; caveinfo brace framing parsed by shared
  `experimental.pikmin2_cave.tree`.

## Catalogued stage metadata (baseline, not decoded output)

| Field | Value |
|---|---|
| Floors | 2 (`floor_seconds` [100.0, 150.0]) |
| Challenge table order | 2; UI index 5 |
| Starting Pikmin | 100 flower Blue (native color/maturity row 2); all other rows zero |
| Sprays | bitter 2, spicy 2 |
| `legacy_time` | 0.0; `treasure_count_field` 0 |
| Runtime parents | framework #136, content #137, generator #129, actors #130/#131 |

The adapter cross-checks candidate details against these pins
(`cross_check_catalog`) and reports any divergence field by field.

## Reserved files (this lane only)

- `experimental/content_lanes/p2-challenge-ch_nari_03toy.py` — isolated
  import-contract adapter. Filename carries hyphens per the lane plan, so it
  is not dotted-path importable; consumers and tests load it from its exact
  reserved path via `importlib`. Shared parsers are reused, never forked.
- `tests/content_lanes/test_p2_challenge_ch_nari_03toy.py` — 12 synthetic
  boundary tests (malformed framing, count/range/overlap defects, hash
  mismatch, missing catalogs, absent source); pin-consistency test reads the
  two canonical JSON docs.
- This spec.

## Contract entry points

- `source_prerequisites()` — exact retail inputs: GPVE01 rev 0 image exposing
  the stage path plus `user/Abe/Pellet/us/pelletlist_us.szs` and
  `user/Matoba/challenge/stages.txt`; decomp `enemyInfo.cpp` enemy ID set.
- `verify_source(data)` — SHA-256 gate against the catalogued pin; raises on
  mismatch. No bytes are ever invented.
- `decode_structure(text)` — framing plus floor-range/unit-pool table, no
  enemy catalogs needed.
- `check_floor_coverage(floors)` — gapless 1-based coverage of exactly the 2
  catalogued floors.
- `decode_full(text, enemy_ids, treasure_ids)` — shared
  `pikmin2_cave_catalog.parse` semantics; raises `MissingPrerequisite`
  without catalogs; re-checks floor totals against the catalogue.
- `resource_closure_requirements(structure)` — exact per-pool disc paths still
  needed (`units/<pool>`, per-unit `arc.szs`/`texts.szs`); arc unit names stay
  pending until pool texts are read.
- `audit_packet(...)` — P0 packet; without source bytes it records
  `decoded: false` with the exact missing list.

## Actual-source status in this environment

Retail bytes are **unavailable**: no GPVE01 ISO exists on this host and no
extracted `user/Mukki/...` tree is present (searched `C:/Users/alari`).
Byte-level decode therefore stays an explicit missing prerequisite; the
delivered value is the tested boundary plus the pin/coverage contract above.

## Exact blockers for later phases (not P0 defects)

- P1 runtime needs accepted pins from #136 (Challenge framework: starting
  populations, sprays, per-floor timing, keys/exits, scores, retry/result
  semantics), #137 (content batch), #129 (cave generator), #130/#131
  (actor/species admission for every referenced enemy/treasure).
- Weighted roster rows remain definitions; enemy admission status of this
  stage's roster is unresolved until its bytes are decoded against catalogs.
- Localized display name (`ch_NARI_03toy` English title) unresolved by policy;
  extract later, never guess.

## Limitations

- Weights/counts are definition inputs, not spawn instances or placements.
- No seeded topology, hole selection, radial distribution, restart identity.
- Metadata is not runtime acceptance; nothing here is playable content.
