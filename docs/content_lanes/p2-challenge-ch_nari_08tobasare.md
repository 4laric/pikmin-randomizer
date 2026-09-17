# P0 import contract: P2 Challenge 25 ch_NARI_08tobasare (issue #557)

Implementation owner: Codex through shared account `4laric`; executing
contributor Muse Spark 1.3, lane `p2-challenge-ch_nari_08tobasare`, P0 only.
Parent content issue #137; coordination #531; source coverage #109; parent #569.
No native build, no gameplay runtime, no ADMIT, no playability claim.
Full content issue stays OPEN for P1/P2.

## Source identity

- Source ID `ch_NARI_08tobasare` (authoritative; English display title
  unresolved, source ID and UI index govern).
- Retail path `user/Mukki/mapunits/caveinfo/ch_NARI_08tobasare.txt`, read from a
  local legal US GPVE01 revision 0 (Pikmin 2) disc image via
  `experimental.pikmin2_assets.disc_files`.
- Expected SHA-256
  `1ba97d8165e7d29257620b08565e7273dd2529328e565cc09ba5fc4d220832db`
  (canonical `docs/PIKMIN2_CONTENT_INVENTORY.json` `source_sha256` entry,
  mirrored in `docs/PIKMIN_CONTENT_IMPORT_LANES.json`).
- Encoding `shift_jis`; caveinfo brace framing parsed by shared
  `experimental.pikmin2_cave.tree`.

## Catalogued stage metadata (baseline, not decoded output)

| Field | Value |
|---|---|
| Floors | 2 (`floor_seconds` [150.0, 100.0]) |
| Challenge table order | 18; UI index 24 |
| Starting Pikmin | 50 total: row0 flower 25, row1 flower 20, row3 flower 5; rows 2/4/5/6 empty |
| Sprays | bitter 2, spicy 0 |
| `legacy_time` | 0.0; `treasure_count_field` 0 |
| Runtime parents | framework #136, content #137, generator #129, actors #130/#131 |

The adapter cross-checks candidate details against these pins
(`cross_check_catalog`) and reports divergence field by field.

## Reserved files (this lane only)

- `experimental/content_lanes/p2-challenge-ch_nari_08tobasare.py` ? isolated
  import-contract adapter. Filename carries hyphens per the lane plan, so it is
  not dotted-path importable; consumers and tests load it from its exact
  reserved path via `importlib`. Shared parsers are reused, never forked.
- `tests/content_lanes/test_p2_challenge_ch_nari_08tobasare.py` ? 16 synthetic
  boundary tests (10 subtests); pin-consistency test reads the two canonical
  JSON docs.
- This spec.

## Contract entry points

- `source_prerequisites()` ? exact retail inputs: GPVE01 rev 0 image exposing
  the stage path plus `user/Abe/Pellet/us/pelletlist_us.szs` and
  `user/Matoba/challenge/stages.txt`; decomp `enemyInfo.cpp` enemy ID set.
- `verify_source(data)` ? SHA-256 gate against the catalogued pin; raises on
  mismatch. No bytes are ever invented.
- `decode_structure(text)` ? framing plus floor-range/unit-pool table; walks the
  real section layout (floor parameters followed by enemy/treasure/gate rosters,
  plus the versioned cap block) so multi-floor files are not misread as a flat
  parameter list. No enemy catalogs needed.
- `check_floor_coverage(floors)` ? gapless 1-based coverage of exactly the 2
  catalogued floors.
- `decode_full(text, enemy_ids, treasure_ids)` ? shared
  `pikmin2_cave_catalog.parse` semantics; raises `MissingPrerequisite` without
  catalogs; re-checks floor totals against the catalogue.
- `starting_population(roster)` ? validates the 7x3 native color/maturity
  roster and totals it (50 here); the color-index mapping is not asserted.
- `stage_contract(details, roster)` ? metadata-only spray/timer/roster pins plus
  the explicit unsupported-reference list.
- `resource_closure_requirements(structure)` ? exact per-pool disc paths still
  needed (`units/<pool>`, per-unit `arc.szs`/`texts.szs`); arc unit names stay
  pending until pool texts are read.
- `audit_packet(...)` ? P0 packet; without source bytes it records
  `decoded: false` with the exact missing list.

## Actual-source status in this environment

Retail bytes are **unavailable**: no GPVE01 (Pikmin 2) disc image exists on this
host, and no extracted `user/Mukki/...` tree is present. The only local disc
image is `GPIE01` (Pikmin 1), which the shared reader correctly rejects. Byte
decode therefore stays an explicit missing prerequisite; the delivered value is
the tested boundary plus the pin/coverage contract above.

## Exact blockers for later phases (not P0 defects)

- P1 runtime needs accepted pins from #136 (Challenge framework: starting
  populations, sprays, per-floor timing, TheKey/hole/geyser exits, scoring,
  ordinary vs deathless completion, retry reset), #137 (content batch), #129
  (cave generator), #130/#131 (actor/species admission for every referenced
  enemy/treasure).
- Weighted roster rows remain definitions; enemy admission status of this
  stage's roster is unresolved until its bytes are decoded against catalogs.
- Localized display name (`ch_NARI_08tobasare` English title) unresolved by
  policy; extract later, never guess.
- The host `chal0` fixture is not evidence of Challenge mode; do not treat it as
  such.

## Limitations

- Weights/counts are definition inputs, not spawn instances or placements.
- No seeded topology, hole selection, radial distribution, restart identity.
- Metadata is not runtime acceptance; nothing here is playable content.
- All six arena gates are UNTESTED in this P0 tooling slice by design.
## P1 import path (lane p2-challenge-ch-nari-08tobasare-p1; no re-implementation)

`validate_p1_manifest()` checks a P0 manifest carries everything the P1
runtime import needs (2 decoded floors with unit pools + enemy/treasure
rosters, 7-row starting roster totalling 50 at cells [0][2]/[1][2]/[3][2],
timers [150.0, 100.0], sprays bitter 2 / spicy 0, ui_index 24) and normalizes
a staging dict; anything else raises fail-closed via `ImportContractError`.
`stage_run_layout()` writes a private run layout: `stage-manifest.json`
(validated copy), `p1-input-package.json` (stage key, floors, squad total 50,
timers, sprays, ui 24) and `run-plan.json` (ordered observation plan: fresh
arena + starting-Pikmin overlay + centred 960x540 boot, captain guard FIRST
with orimaDead/NaviDead/HP<=1 and CAPTAIN_DOWN + BLOCKED, live-squad check,
collision/routes/actors markers, honest six-gate evidence). `p1_main()` drives
it from a manifest file; `main()` is a thin CLI. All decode helpers are the
P0 ones in this same file; no parser was forked.

P1 validation evidence: `P1ImportTests`, 14 focused tests (valid manifest,
wrong cave, floor count, empty enemies, missing unit pool, wrong squad total,
missing pinned cell, bad timer, wrong sprays, wrong ui, three-file layout
write + package schema/squad assertions, bad-manifest and missing-file
rejections, end-to-end `p1_main`), all green alongside the 16 P0 tests
(30 passed total). No runtime run, no build, no shared edits; all six gates
UNTESTED. The runtime boot (leased build, fresh arena, guard adoption, live
observation) remains explicitly future work once the host toolchain recovers.
