# p2-cave-yakushima_2 import contract (P0, issue #159)

Lane `p2-cave-yakushima_2`, phase P0 (source audit and additive import
contract). Implementation owner: Codex through shared account `4laric`;
executing contributor Muse Spark 1.3 through OpenCode. Parent coverage issue
#109; coordination #531. This document specifies the validated import
contract; the machine-readable packet is produced by
`experimental/content_lanes/p2-cave-yakushima_2.py` and tested by
`tests/content_lanes/test_p2_cave_yakushima_2.py` (11/11 pass).

## Source identity

- Source ID `yakushima_2` (p2-cave), retail story cave, US GPVE01 rev 0.
- Definition: `user/Mukki/mapunits/caveinfo/yakushima_2.txt`,
  recorded sha256
  `5a071801508a55ee5d21f5a9e5ff28c085c105a8a9af3eae1467c725c406db15`
  (catalog evidence pin; the disc was unavailable to this turn, so no bytes
  were re-extracted).
- Enemy catalog pin `305f82601d5d31ac47f491adf4f9dbfbb891dbb` (recorded).
- Baseline inputs: lane-plan entry (`docs/PIKMIN_CONTENT_IMPORT_LANES.json`),
  inventory entry (`docs/PIKMIN2_CONTENT_INVENTORY.json`, id `yakushima_2`),
  decoded catalog entry with hash map and unit-pool closure (retail catalog
  evidence). All three agree; any drift fails the adapter closed.

## Floor coverage (6/6, contiguous)

| Floor | Unit pool (pool sha256, recorded) | Main roster | Treasures |
|---|---|---|---|
| 1 | `1_units_hit6x6_yakushima_toy.txt` (`0d0b5b43…41de`) | KumaKochappy x3 | bane_red |
| 2 | `1_units_large_toy.txt` (`a0cf3857…fec2`) | BlackPom, UjiA x2, UjiB, PanModoki x2, Armor, Chiyogami | g_futa_kyusyu, cookie_m_l |
| 3 | `3_units_small2_small_mid_toy.txt` (`2e11490e…1506`) | Mar, PanModoki, ElecBug x3, ElecHiba | tatebue, castanets |
| 4 | `2_units_hit47_hit67_toy.txt` (`a12d767b…3ef8`) | KumaChappy_g_futa_sikoku, KumaKochappy x2, PanModoki | chocowhite_l, sensya |
| 5 | `2_units_sara_sara2_toy.txt` (`347a5bb9…9db2`) | Fkabuto, KumaKochappy x4 | compact, bell_blue |
| 6 | `1_units_opan_toy.txt` (`a5151ca4…782c`) | OoPanModoki_fue_b, PanModoki, Egg, ElecBug x2, ElecHiba | dia_b_green, medama_yaki, donutsichigo |

Parameters (`f000`–`f017`, incl. timers `f006`/`f016`, pool `f008`, light
`f009`, flooring `f00A`) are preserved verbatim per floor in the packet. No
gates on any floor. Cap blocks on floors 3 and 5 (below) carry version-1
definitions.

## Explicit extra rosters (floor-audit questions, not silent inclusions)

- Cap/ambush-only tokens: `$1Egg`, `$1ElecBug`, `$1RandPom`, `YellowPom`
  (floors 3/5 caps; `BlackPom` and `Egg` also appear as caps alongside main
  roster membership).
- Cargo tokens: `KumaChappy_g_futa_sikoku`, `OoPanModoki_fue_b`
  (carried-treasure binding resolved by the existing importer).
- Drop tokens: `$1ElecBug`, `$1Egg`, `$1RandPom` (drop mode 1,
  `pikmin_or_leader` semantics per the existing importer).

## Resource closure

Each of the 6 pools resolves to a decoded unit list (e.g. floor 6
`room_opan_toy`, 12x12 cells) with arc/texts asset references checked by the
catalog build. Unit internals stay catalog-owned; this packet records pool
names and unit names only.

## What is NOT claimed

No placements are emitted (weights are definition inputs). No seeded
topology, hole selection, spawn instances, runtime behavior, collection,
persistence or playability is claimed. Full content acceptance and all
runtime dependencies stay OPEN.

## Native/framework blockers (exact)

1. P1 runtime waits on validated generator/actor/mode contracts: cave
   generation lanes 34–51 / #468 / #129; actor/assets/species lanes
   (#128, #130, #131, #140–146 and family owners for Kuma variants,
   BlackPom/YellowPom/RandPom, Uji pair, PanModoki pair, Armor, Chiyogami,
   Mar, ElecBug/ElecHiba, Fkabuto, Egg); surface/saves #132.
2. Cap/ambush/drop/cargo tokens above need floor-audit resolution with the
   owning family lanes before any promotion.
3. Localized display-name mapping stays open; stable source IDs are
   authoritative.

## Validation evidence (this turn)

- `tests/content_lanes/test_p2_cave_yakushima_2.py`: 11/11 pass (real
  sources validate; drifted/truncated/corrupt/missing inputs rejected).
- `scripts/check_content_import_lanes.py` plan suite: 15/15 pass (untouched).
- Packet `packet.json` sha256
  `27658f927ba6e1b9c78fd94f9c629f9121cbdaae05777199354a3fc7c2e04d16`
  in the lane output directory.
