# P2 Challenge ch_MAT_t_hunter_otakara ? P0 source audit and import contract (#555)

Lane `p2-challenge-ch_mat_t_hunter_otakara`. Implementation owner: Codex through
shared account `4laric`; executing worker Muse Spark 1.3 (session
`ses_f588f4eb3ffeo17sLakvD7MPiS`). Parent issues #531 (lane plan), #137 (P2
Challenge content), #136 (Challenge runtime framework), #569 (autofill pool).
This is a P0 slice only: source audit and additive import contract. No runtime,
no playability claim; the full content issue stays OPEN.

## Source identity

- Source ID: `ch_MAT_t_hunter_otakara` (authoritative; English display title
  unresolved, never guessed).
- Retail path: `user/Mukki/mapunits/caveinfo/ch_MAT_t_hunter_otakara.txt` on US
  GPVE01 revision 0.
- SHA-256: `25b3cfe3a9c95a77710facb0633326e33857781129477161724696e532cee4be`
  (1371 bytes; extracted from local disc, matches the lane baseline exactly).
- Stage identity: table order 13, UI index 23; a treasure-hunter stage
  (`treasure_count_field` 6 of 10 listed treasures are required).

## Decoded structure (observed, not assumed)

`# CaveInfo { {c000} 4 1 }` declares 1 floor definition; floor range 1?1.
The campaign-compatible section layout is decoded by the shared
`experimental.pikmin2_cave_catalog.parse` (format version 1, so a CapInfo block
is present but empty).

| Field | Value |
|---|---|
| Unit pool | `1_MAT_manp_2_conc.txt` |
| Light | `normal_light_cha.ini` |
| VRBOX | `none` (absent by source) |
| Rooms (f005) | 1 |
| Return geyser (f007) | 1 (present) |
| Alpha attribute (f011) | 2 |
| Beta attribute (f012) / hidden floor (f013) | 0 / 0 |
| Enemy max (f002) / item max (f003) | 11 / 10 |
| Route ratio (f006) | 0.0 |

### Teki roster (weighted definitions, not placements)

| Source token | Resolved enemy | Carried treasure | Weight | Type |
|---|---|---|---|---|
| `FireOtakara_be_dama_red` | FireOtakara | be_dama_red | 10 | 5 |
| `WaterOtakara_be_dama_blue` | WaterOtakara | be_dama_blue | 10 | 5 |
| `GasOtakara_flower_blue` | GasOtakara | flower_blue | 10 | 5 |
| `FireOtakara_be_dama_red` | FireOtakara | be_dama_red | 20 | 1 |
| `WaterOtakara_be_dama_blue` | WaterOtakara | be_dama_blue | 20 | 1 |
| `GasOtakara_flower_blue` | GasOtakara | flower_blue | 20 | 1 |
| `ElecOtakara_wadou_kaichin` | ElecOtakara | wadou_kaichin | 20 | 1 |

Type 5 vs type 1 is the source placement class; weights pack as
minimum count (weight // 10) plus selection weight (weight % 10) under the
shared catalog semantics. Four elemental Otakara each carry a treasure; the
carried treasures resolve against the retail pellet catalog.

### Item roster (target treasures, all weight 10)

`key`, `saru_head`, `badminton`, `turi_uki`, `toy_cat`, `chocolate_l`,
`toy_ring_c_blue`, `ichigo_l`, `ahiru_head`, `bird_hane` ? 10 listed, 6
required by `treasure_count_field`. No gates, no caps.

## Catalogued baseline cross-check (all asserted)

Floors 1; floor timer 180.0 s; legacy time 300.0; bitter/spicy sprays 0/0;
UI index 23; table order 13; treasure-count field 6; starting roster 25 flower
Pikmin each for native colors 0, 1, 2 and 4 (`[[0,0,25],[0,0,25],[0,0,25],
[0,0,0],[0,0,25],[0,0,0],[0,0,0]]`). Any drift fails `check_metadata`.

## Resource closure (presence + hashes, disc-local)

- Unit pool `user/Mukki/mapunits/units/1_MAT_manp_2_conc.txt`: present,
  decodes via shared `unit_definition`; SHA-256
  `3c595cd7d3dbdb7bc2f9e45a64b2535108b747619099fe094edaf986597f7813`.
- Units: `item_cap_conc`, `way3_conc`, `way4_conc`, `wayl_conc`, `way2_conc`,
  `way2x2_conc`, `room_manh7x7p_9_conc` ? every one resolves both
  `arc/<unit>/arc.szs` and `arc/<unit>/texts.szs` in the disc catalog.
- Light config `user/Abe/cave/normal_light_cha.ini`: present.
- Hashes of the cave definition and the unit pool are recorded in
  `manifest.json` (`source_sha256_map`).

## Import contract

`experimental/content_lanes/p2-challenge-ch_mat_t_hunter_otakara.py` exposes
`run(iso_path, enemyinfo_cpp, lanes_json, output)` returning the manifest and
writing `manifest.json` + `run.log`. It reuses shared parsers by import and
fails closed (ValueError naming the exact defect) on: missing/truncated disc
source, hash or size mismatch, decode errors, floor gaps, roster/carried/weight
drift, unexpected gate or cap rows, baseline metadata drift, and any
resource-closure gap. The manifest is metadata-only (`generated: false`):
per-floor parameters, enemy/treasure/gate/cap definitions with weight
semantics, starting roster, timers, sprays, closure hashes, and explicit
limitations. No coordinates, placements, spawn instances, or completion
semantics are generated.

## Exact native/framework blockers (for P1/P2, not P0)

- Challenge runtime framework (#136): starting color/maturity populations,
  spray grants, per-floor timing, TheKey/exit handling, scoring, retry and
  ordinary/deathless result semantics. The host `chal0` fixture is not
  Challenge-mode evidence.
- Cave generation and actor contracts (#129, active #468, lanes 34?51;
  species/family owners #128/#130/#131/#140?#146): floor topology, unit
  instantiation, treasure/actor binding. The four Otakara actors and their
  carried treasures resolve at the catalog level; runtime admission is a
  promotion-time dependency, not a P0 blocker.
- Content integration (#137, designated integrator #437): review disposition
  of this packet; no shared-file changes ship from this lane.

## Validation evidence

- `tests/content_lanes/test_p2_challenge_ch_mat_t_hunter_otakara.py`: 26 passed
  (decode, carried-treasure resolution, stage/metadata checks,
  malformed/missing-input boundaries, metadata-only manifest shape).
  Hermetic; real-source validation runs through the adapter main and is
  logged, not pytest.
- Real run: `manifest.json` + `run.log` under the lane output directory;
  hashes recorded in the run log.
