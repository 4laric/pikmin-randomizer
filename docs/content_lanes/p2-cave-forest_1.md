# forest_1 P0 import contract (issue #154)

P0-only source-audit packet. Lane `shard-caves-forest-forest1-p0`; owner
Codex through shared account 4laric. No playability is claimed; all six
runtime gates stay UNTESTED and issue #154 stays OPEN.

## Source and decode

- Source: `user/Mukki/mapunits/caveinfo/forest_1.txt` (shift_jis) from the
  legal US GPVE01 rev 0 image.
- Parsers reused, never forked: `experimental.pikmin2_cave_catalog.parse`
  (caveinfo framing, rosters, gates/caps) and
  `experimental.pikmin2_cave.unit_definition` (unit pools). Enemy ids come
  from the read-only decomp `enemyInfo.cpp`; treasure ids from
  `user/Abe/Pellet/us/pelletlist_us.szs` (`otakara_config.txt` +
  `item_config.txt`) via `experimental.pikmin2_pod.pellet_catalog`.
- Adapter: `experimental/content_lanes/p2-cave-forest_1.py`.

## Live result (real decode against the retail image)

```
floor_count          5              coverage 1..5              PASS
contract_mismatches  []             (pool/enemy/cargo/treasure) PASS
missing_unit_assets  []             full resource closure      PASS
```
Per-floor pools decoded: `1_units_cent3_tsuchi.txt`,
`1_units_cent2_tsuchi.txt`, `2_ABE_norhiba_blkhiba_tsuchi.txt`,
`2_ABE_mid1_nor3_tsuchi.txt`, `1_units_boss_tsuchi.txt`.

Cargo-token contract verified against the shared first-underscore rule:
`Queen_radar_a` -> Queen carrying radar_a; `Chappy_donutsichigo_s` ->
Chappy carrying donutsichigo_s; `KareOoinu_s` stays whole (its tail is
not a treasure id).

## Resource closure

Every unit referenced by the five pools resolves to an on-disc
`user/Mukki/mapunits/arc/<unit>/arc.szs` + `texts.szs` pair: the closure
check reports zero missing assets. Unit-pool and cave hashes are recorded
in the emitted packet.

## Exact P1 blockers (owner/issue refs)

- Cave generation/topology: #129 (provider #607).
- Save/day and re-entry persistence: #132 (provider #605).
- Treasure/receipt objects: #140 / #606.
- Actor/asset admission per floor roster: #130/#131 (provider #608); the
  roster includes currently unadmitted identities, which block promotion
  but not this preparatory packet.

## Limits

Weighted rows are definition inputs, not spawn instances or placements.
No seeded topology, hole selection, radial distribution or restart
identity is generated. No native build, gameplay run, shared-file edit,
ADMIT or ledger write was performed.