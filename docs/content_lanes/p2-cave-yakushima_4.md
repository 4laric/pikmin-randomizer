# P0 import contract ? p2-cave-yakushima_4 (lane shard-caves-yakushima-yakushima4-p0, issue #161)

Generation-3 P0 slice. Concrete source-import preparation only: no native
build, no runtime, no ADMIT, no playability claim. Issue #161 stays OPEN.

## Source identity (real decode)

- Source `user/Mukki/mapunits/caveinfo/yakushima_4.txt` on the supported
  local ISO: 5977 bytes, sha256
  `3e3fc04e1131673e22063eb2e395e22e7ac3d4252d2db9223400632696272de0`.
- Decoded with the shared parser `experimental.pikmin2_cave_catalog.parse`
  (imported, never edited). Enemy universe from the read-only research
  `enemyInfo.cpp` (100 names); treasure/cargo universe from the disc pellet
  archive (`otakara_config.txt` + `item_config.txt`, 201 names) via
  `experimental.pikmin2_pod.pellet_catalog` ? the same construction the
  shared cave inventory uses.

## Decoded definition (5 floors, contiguous 1..5)

| Floor | Unit pool | Enemies | Treasures | Gates | Caps |
|---:|---|---:|---:|---:|---:|
| 1 | 2_units_gw_l_conc.txt | 8 | 2 | 0 | 2 |
| 2 | 3_units_h_k_pypes_conc.txt | 8 | 2 | 1 | 0 |
| 3 | 3_units_f_g_m_conc.txt | 9 | 2 | 1 | 4 |
| 4 | 4_units_d_j_n_o_conc.txt | 9 | 2 | 1 | 1 |
| 5 | 1_units_manh_boss_conc.txt | 4 | 0 | 1 | 1 |

Cross-check against the catalogued baseline
(`docs/PIKMIN2_CONTENT_INVENTORY.json` story_caves `yakushima_4`): floor
framing, unit pools, enemy counts and treasure counts all agree ?
`findings` is empty. Floor 1 carries no gates; floor 5 is the lone
boss-pool floor with no treasures.

## Hash and coverage record

- Definition sha256 and byte length are pinned in the adapter and asserted
  by the tests, so retail-tree drift fails loudly.
- Floor coverage is validated as contiguous 1..5; a non-contiguous decode
  raises instead of passing silently.
- Unit-asset closure beyond the referenced pool names (`arc`/`texts.szs`)
  is owned by the shared cave inventory and is explicitly NOT asserted
  here (recorded as a limitation, not a claim).

## Exact P1 blockers

1. No native cave/floor runtime consumes this decode: cave generation
   provider #129; save/progression #132.
2. Asset closure for the referenced unit pools is not verified in this
   slice (shared cave inventory owns unit asset checks).
3. Runtime deps #128/#131/#140/#144/#145/#146 remain open for playable
   acceptance (asset pipeline, squad, treasure ledger, obstacles, hazards,
   fixtures).

All six runtime gates UNTESTED; fixture adoption N/A (kind=tooling
handoff).

## Verification

`py -3.12 -m pytest tests/content_lanes/test_p2_cave_yakushima_4.py -q`
-> 15 passed (real decode pins, pool/coverage checks, per-floor counts,
baseline agreement, shared-importer reuse, blockers; plus missing-ISO,
missing-entry, wrong-shape, non-contiguous-floor, pool-mismatch and
baseline-count negatives).
