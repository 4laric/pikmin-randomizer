# P1 Challenge Forest — P0 source audit and import contract (issue #564)

Owner: Codex through shared account `4laric`. Lane `p1-challenge-forest`,
source `stages/chal1.ini`, level key `challenge:forest`, native area id 1,
stage_info index 17. P0 only: no build, no runtime, no ADMIT, no asset
redistribution. Full content issue stays OPEN for P1/P2.

## Source identity

- Lane source: `stages/chal1.ini` with stage directory `stages/chal1/`
  (`default.gen` required, `plants.gen` present in reference).
- Disc hash: unavailable in this slice — no legal `--assets` path is
  configured, so no disc hash is claimed. Exact missing prerequisite:
  a legal assets root containing `dataDir/stages/chal1.ini`,
  `dataDir/stages/chal1/default.gen`, and the decoded geometry target
  `dataDir/courses/stage1/forest.mod`.
- Staged derived-copy reference (read-only, not disc evidence):
  `chal1.ini` sha256
  `54b3e0a5f84a7a93e6521e569a2c96b106102227551434e62ba77861ec4fea6d`
  (2471 bytes), `default.gen` 16019 bytes, `plants.gen` 4944 bytes.
- Inventory baseline `docs/PIKMIN2_CONTENT_INVENTORY.json` covers P2
  Challenge/stages only; P1 `chal1.ini` has no pinned disc hash there.
  Source IDs from `docs/PIKMIN_CONTENT_IMPORT_LANES.json` (lane entry
  `p1-challenge-forest`) are authoritative for identity.

## Decoded definitions (from reference bytes, carried verbatim by adapter)

- `navi_start`: 0.0, 0.0 (original coordinates preserved).
- `map_file`: `courses/stage1/forest.mod` (same terrain model as the
  campaign Forest of Hope; Challenge differs in generator placement).
- `day_multiply`: 1.4; `dayMgr numsettings`: 5 (schedule preserved,
  not a duration or route-feasibility claim).
- `new_room`: one starting room, index 0, radius 4.0, centre 0.0, 0.0.
- Floor coverage: exactly one layout — `floors: 1`,
  `floor_ids: ["challenge:forest"]`. No cave floors, no timers/roster
  beyond the Challenge definition itself.

## Resource closure

Validated by file identity only (`experimental/content_lanes/p1-challenge-forest.py`
`validate_resource_closure`): `chal1/default.gen` required,
`chal1/plants.gen` recorded, geometry presence confirmed against the
decoded `map_file`. Generator rows are definitions, never expanded into
actor counts — the adapter exposes no placement emitter.

## Adapter and tests

- `experimental/content_lanes/p1-challenge-forest.py`: `decode_chal1_ini`,
  `validate_resource_closure`, `source_sha256_of_bytes`,
  `build_import_contract` plus lane identity constants.
- `tests/content_lanes/test_p1_challenge_forest.py`: 16 focused tests —
  valid reference shape, empty/missing/malformed inputs, duplicate rooms,
  missing generator/geometry/hash, identity-only closure, contract
  preservation and drift rejection, byte hashing.

## Native/framework blockers (exact, no playability claim)

1. Ten-destination navigation: `challenge:forest` level key must accompany
   area id 1 through map select, launch and travel (#100 scope).
2. Independent persistence: per-level-key cache/card/check routing with
   campaign/challenge save isolation (#100 scope).
3. Timed/scored AP campaign checks, routing and retry/reconnect semantics
   separate from story destinations (#52); runtime dependency #6 per issue.
4. No placement/collision/water/route/balance claims until P1 private
   runtime on pinned inputs with the current starting-Pikmin overlay and a
   fresh centred 960×540 fixture.

## Delivery

Focused test log:
`output/workflow/content-expansion/p1-challenge-forest/pytest.log`.
Source audit:
`output/workflow/content-expansion/p1-challenge-forest/source-audit.json`.
Tooling handoff:
`output/workflow/content-expansion/p1-challenge-forest/handoff.json`.
Packet: `output/deepseek-wave/inbox/content-564-p0.md`.
