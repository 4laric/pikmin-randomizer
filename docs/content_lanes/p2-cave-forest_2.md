# P0 import contract — forest_2 (lane p2-cave-forest_2, #155)

Lane: `p2-cave-forest_2` (category `p2-cave`), issue #155, phase P0 only.
Source entry: `forest_2`, definition file
`user/Mukki/mapunits/caveinfo/forest_2.txt` (4368 bytes on the local
GPVE01 rev 0 disc, sha256
`a8eaa17832af6ca5bb71b603501302c7ea6cf62b1a103c7c5978516d0fd8d5be`).
No native worktree, build, or runtime belongs to this slice.

## Catalogued contract (5 floors)

| Floor | Unit pool | Enemies | Treasures |
|---|---|---|---|
| 1 | 2_ABE_nor1_cen2_metal.txt | UjiB, UjiA ×3 | fire_helmet |
| 2 | 1_ABE_ari_metal.txt | Tank | chocoichigo_l, diamond_red |
| 3 | 1_units_white_metal.txt | WhitePom, Qurione, DaiodoGreen, KareOoinu_s, KareOoinu_l, Clover | gum_tape |
| 4 | 3_ABE_sak1_sak2_hit1_tsuchi.txt | GasHiba | g_futa_kajiwara, kinoko_doku |
| 5 | 1_units_snake_tsuchi.txt | SnakeCrow (+radar_b cargo), Egg, KareOoinu_l, KareOoinu_s, Zenmai | — |

Floor 5's catalogued token `SnakeCrow_radar_b` decodes to base enemy
`SnakeCrow` carrying treasure `radar_b` (native first-underscore split;
`radar_b` is a genuine pellet-list treasure). The contract check encodes
exactly this rule and refuses to degrade `KareOoinu_s`-style IDs.

## Adapter (`experimental/content_lanes/p2-cave-forest_2.py`)

Isolated per-source layer over the EXISTING shared parsers
(`experimental.pikmin2_cave_catalog.parse`,
`experimental.pikmin2_cave.unit_definition`,
`experimental.pikmin2_pod.pellet_catalog`,
`experimental.pikmin2_assets.disc_files`) — reused, never forked:

- `collect(iso, decomp_root)` — disc catalog plus enemy/treasure ID sets
  from the read-only decomp `enemyInfo.cpp` and the on-disc pellet list.
- `read_blob` / `decode` — fail-closed reads (`FileNotFoundError` on
  absent inputs, `ValueError` on malformed definitions or truncation).
- `check_contract` — decoded floors vs the table above; drift returns
  mismatch strings, never silent correction.
- `check_closure` — every decoded unit needs its `arc.szs` + `texts.szs`
  on disc; gaps return blocker strings.
- `build_packet` / `run` — metadata packet (`packet.json`); weighted rows
  stay definitions, `generated` is always false.

## Verified P0 result (live decode, this host)

- 5/5 floors decoded; contract mismatches: none.
- All 5 unit pools decoded (8 + 8 + 1 + 9 + 1 units); unit asset closure:
  complete, 0 missing.
- Tests: `tests/content_lanes/test_p2_cave_forest_2.py` — 12 passed
  (synthetic malformed/missing/drift plus the live-decode test, which
  skips cleanly without a local disc image).

## Exact blockers (framework, not decode failures)

- P1/P2 runtime import needs the existing owners' contracts: caves #129,
  assets #128, species #131, saves #132, #140/#144/#145/#146.
- Promotion needs species admission per the roster ledger; unadmitted
  floor roster members block promotion, not this preparatory packet.
- No playability is claimed; the full content issue stays OPEN.

## Boundaries

Owns only the three reserved files. No shared parser/schema edits, no
native hooks, no asset redistribution. Evidence and runtime state live
under `output/workflow/content-expansion/p2-cave-forest_2/`; the
integrator packet is `output/deepseek-wave/inbox/content-155-p0.md`.
