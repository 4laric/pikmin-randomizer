# Beasts final-floor source packages (#318)

Implementation owner: Codex using shared account 4laric. Parent #154.
This batch prepares the final three room candidates and cargo models for floors
4/5, and preserves source-definition coverage for all five floors. It does not
install actors, select retail placements or certify a complete playable cave.

| Floor | Source pool | Main roster | Other source content | Exit |
|---|---|---|---|---|
| 1 | `1_units_cent3_tsuchi.txt` | UjiB minimum 4; three distinct UjiA rows minimum 2 each; Clover target 4, Tukushi target 2, KareOoinu_s target 2 | Loose `juji_key_fc` | Descend 2 |
| 2 | `1_units_cent2_tsuchi.txt` | BlackPom minimum 2; HikariKinoko target 6, KareOoinu_s target 2 | Cap Egg minimum 2; no treasure | Descend 3 |
| 3 | `2_ABE_norhiba_blkhiba_tsuchi.txt` | Hiba minimum 7 at placement type 1 and another 7 at type 8; HikariKinoko target 8 | Loose `donutswhite`, `dia_c_green` | Descend 4 |
| 4 | `2_ABE_mid1_nor3_tsuchi.txt` | Chappy minimum 1 carrying `donutsichigo_s`; BlackPom minimum 1; Hiba minimum 4; HikariKinoko target 6 | Loose `dia_b_blue`; cap TamagoMushi minimum 1 and Egg minimum 2 | Descend 5 |
| 5 | `1_units_boss_tsuchi.txt` | Queen minimum 1 carrying `radar_a`; HikariKinoko target 8 | No loose treasure | Geyser present, clogged flag set |

These counts are generation inputs, not guaranteed spawned instances. All five
definitions have empty gate lists. Source rows remain distinct; definition IDs
include floor definition, main/cap category and row index. Cargo has an explicit
owner definition or `loose` delivery. These IDs must not become receipt IDs until
generation selects actual instances. The package preserves full source parameters
and rows alongside the summary, including cap helpers and carried-treasure tokens.

| Imported cargo | Ownership | Catalog | Pokos | Weight / slots |
|---|---|---|---|---|
| `dia_b_blue` | Floor 4 loose row | Treasure | 140 | 1 / 3 |
| `donutsichigo_s` | Floor 4 Chappy row | Treasure | 280 | 20 / 30 |
| `radar_a` | Floor 5 Queen row | Equipment | 200 | 35 / 45 |

`radar_a` is in `item_config.txt`, not `otakara_config.txt`. Both catalogs are
read and hashed; an identity appearing in both is rejected. Importing its model
and carry values does not install its equipment effect or a boss reward.

The rooms `room_mid1_6_tsuchi`, `room_north3_1_tsuchi` and `room_boss_1_tsuchi`
have respectively 44, 15 and 14 source spawn centers. All **73** have floor
support. The report separately records whether source Y matches that floor;
support is not equated with an exact height match. Each isolated room has capped
exits and its original route graph/spawn coordinates. No route repairs, connected
floor assembly, carry reachability or native traversal are claimed by this batch.

## Reproduce and evidence

From private root `output/p2-cave-lane`:

```powershell
python -m experimental.pikmin2_beasts_final_floors `
  --iso 'C:/Users/alari/Downloads/PIKMIN2 for GAMECUBE.iso' `
  --catalog ../../output/p2-cave-catalog-batch/audit-final/catalog.json `
  --units ../../output/p2-mapcode0-batch/import `
  --output output/beasts318/new-package
```

The importer checks GPVE01 revision 0, binds the unit import to the catalog hash,
rechecks every catalog/import source hash against the disc, checks all room input
hashes and source pool definitions, and converts the three actual BMD models.
The output directory must be fresh. Source files, models, outputs and saves stay
local; only importer/tests/docs are committed.

Two actual-disc runs in `output/beasts318/final-a` and `final-b` produced **19
byte-identical files**. Manifest SHA256:
`e793a4d912120f6fce16c5128d19e65f76129cd6d5106912c98f05a01db6b87f`.
`output/beasts318/verification.json` records every output hash. The initial probe
stopped before creating output because it searched only the treasure catalog;
the equipment-catalog fix precedes both successful packages.

**15 tests and 28 subtests passed** across final-floor, catalog and collision
tests. Tests cover roster/pool/exit drift, repeated source-row identity, carried
cargo ownership, equipment classification/collision, catalog/import conflicts and
changed disc bytes. No native executable or shared source changed in this track.

## Remaining path to a full cave

Floor 3 has a native geometry survey (#315); explicit native checkpoint entry is
being implemented separately in #317. Floors 4/5 still need connected geometry,
selected placements and native entry/exit lifecycle. Every floor still needs its
complete roster and natural treasure hauling checked in the cave, including
floor-4 carried cargo and floor-5 boss death, equipment effect and geyser access.

Queen's family lane has a separate sampled actor candidate in #256, including
the `f_01` variant. That candidate's evidence does not certify integration into
this room or the boss-cargo lifecycle. Hiba belongs to #170; plants/Candypops to
#171; cap helpers to the relevant family lanes. Retain those implementation owners
and integrate reviewed candidates rather than replacing them with visual proxies.
The full-cave milestone also requires retreat, extinction, re-entry, reload and
surface accounting. #154 remains open.
