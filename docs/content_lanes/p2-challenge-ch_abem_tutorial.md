# P2 Challenge 01: ch_ABEM_tutorial — P0 source audit and import contract (#534)

Lane `p2-challenge-ch_abem_tutorial`. Implementation owner: Codex through
shared account `4laric`; executing worker Muse Spark 1.3 (session
`ses_f588f4eb3ffeo17sLakvD7MPiS`). Parent issues #137 (P2 Challenge content),
#136 (Challenge runtime framework). This is a P0 slice only: source audit
and additive import contract. No runtime, no playability claim; the full
content issue stays OPEN.

## Source identity

- Source ID: `ch_ABEM_tutorial` (authoritative; English display title
  unresolved, never guessed).
- Retail path: `user/Mukki/mapunits/caveinfo/ch_ABEM_tutorial.txt` on US
  GPVE01 revision 0.
- SHA-256: `e21f31f7fa5621a5922d9ee54ffb211a8e4f0e797866d70cc1edb98389ab097d`
  (extracted from local disc, matches the lane baseline byte-for-byte).
- Size: 2219 bytes, Shift_JIS with untranslated comment bytes (comments are
  never relied on; structure comes from the brace stream).

## Decoded structure (observed, not assumed)

`# CaveInfo { {c000} 4 2 }` declares 2 floor definitions; both present with
contiguous ranges 1–2. Each floor carries the campaign-compatible section
layout decoded by the shared `experimental.pikmin2_cave_catalog.parse`:
FloorInfo parameters, TekiInfo, ItemInfo, GateInfo, CapInfo (format version 1,
so the cap block is present).

| Floor | Unit pool | Light | Enemies (source order) | Treasures | Caps | Gates |
|---|---|---|---|---|---|---|
| 1 | `1_units_cent3_tsuchi.txt` | `normal_light_cha.ini` | Clover, Tukushi, Ooinu_s, KareOoinu_s (all type 6, plant target counts) | key, gold_medal, silver_medal, wadou_kaichin | none | none |
| 2 | `2_MAT_mid1_nor2_tsuchi.txt` | `normal_light_cha.ini` | Chappy_key, Kochappy_be_dama_red (weight 50), Egg, Clover, Tukushi, Ooinu_s, Ooinu_l, KareOoinu_s, KareOoinu_l | gold_medal, silver_medal, wadou_kaichin | Egg (weight 20, captype 0) | none |

Notable source facts: floor 1 is plants-only (tutorial staging); floor 2
fields a `Chappy_key` carrier (`Chappy` carrying treasure `key`, both genuine
catalog entries) and a `Kochappy_be_dama_red` carrier at weight 50. All
weighted rows are definitions — minimum/weight packing per the shared catalog
semantics — never emitted as placements.

## Catalogued baseline cross-check (all match)

Floors 2; floor timers 100.0 s + 100.0 s; starting roster 50 red leaf Pikmin
only (`pikmin_by_native_color_and_maturity[1] = [50, 0, 0]`, all other rows
zero); bitter sprays 2, spicy sprays 2; UI index 0; treasure-count field 0.
Any drift in these values fails the adapter (`check_metadata`).

## Resource closure (presence + hashes, disc-local)

- Unit pools `user/Mukki/mapunits/units/1_units_cent3_tsuchi.txt` (7 units) and
  `2_MAT_mid1_nor2_tsuchi.txt` (8 units): present, decode via shared `unit_definition`;
  every listed unit resolves both `arc/<unit>/arc.szs` and
  `arc/<unit>/texts.szs` in the disc catalog.
- Light config `user/Abe/cave/normal_light_cha.ini`: present.
- VRBOX is literal `none` on both floors (absent by source, not a gap).
- Hashes of the cave definition and both pools are recorded in
  `manifest.json` (`source_sha256_map`).

## Import contract

`experimental/content_lanes/p2-challenge-ch_abem_tutorial.py` exposes
`run(iso_path, enemyinfo_cpp, lanes_json, output)` returning the manifest and
writing `manifest.json` + `run.log`. It reuses shared parsers by import and
fails closed (ValueError naming the exact defect) on: missing/truncated disc
source, hash mismatch, decode errors, floor gaps, roster drift, baseline
metadata drift, and any resource-closure gap. The manifest is metadata-only
(`generated: false`): per-floor parameters, enemy/treasure/gate/cap
definitions with weight semantics, starting roster, timers, sprays, closure
hashes, and explicit limitations. No coordinates, placements, or completion
semantics are generated.

## Exact native/framework blockers (for P1/P2, not P0)

- Challenge runtime framework (#136): starting color/maturity populations,
  spray grants, per-floor timing, key/exit handling, scoring, retry and
  ordinary/deathless result semantics.
- Cave generation and actor contracts (#129, active #468, lanes 34–51;
  species/family owners #128/#130/#131/#140–#146): floor topology, unit
  instantiation, enemy/treasure binding. `Egg` (37) and carrier tokens
  (`Chappy_key`) resolve against admitted-actor contracts at promotion time.
- Content integration (#137, designated integrator): review disposition of
  this packet; no shared-file changes ship from this lane.

## Validation evidence

- `tests/content_lanes/test_p2_challenge_ch_abem_tutorial.py`: 19 passed
  (decode, stage/metadata checks, malformed/missing-input boundaries,
  metadata-only manifest shape). Hermetic; real-source validation runs
  through the adapter main and is logged, not pytest.
- Real run: `manifest.json` + `run.log` under the lane output directory;
  hashes in the run log.
