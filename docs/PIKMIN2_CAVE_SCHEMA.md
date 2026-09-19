# P2 cave slot schema and seeded logic graph (lane 34 / #473 / #468)

`experimental.pikmin2_cave_schema` is the host-side contract for the frozen #468
model: four slot classes, hazard tags and the per-floor seeded structural table.
It is the interface lanes 35–38 realize in the engine and lane 39 reads for
logic. It generates no geometry and edits no native code.

```powershell
py -3.12 -m experimental.pikmin2_cave_schema --worked --output <dir>\worked_forest_1.json
py -3.12 -m experimental.pikmin2_cave_schema --seed <ap-seed> --cave forest_1 --floor 1 ^
  --pool 1_units_cent3_tsuchi.txt --unit way2_tsuchi --unit way3_tsuchi ^
  --tag juji_key_fc=water --tag example_elec_treasure=elec --output <dir>\forest_1_f1.json
```

## Slot classes

- **segment** — hazard-free trunk unit. Shape/size/untagged spawns reroll freely.
  `{slot_id, index}`.
- **choke** — forced must-pass unit/gate joining segment `i` to `i+1`. Carries
  `{hazard, kind, hardness, unit}`. `kind`/`hardness` are `hard` or `soft`; the
  same hazard may be hard (a water pool or electric gate) or soft (a geyser) per
  placement, so hardness is a per-choke field, not a global property.
- **leaf** — single-door dead end with exactly one item spawn slot. Carries
  `{segment, hazard, item_slots}`; the validator enforces `item_slots == 1`.
- **bud** — seeded candypop slot in a segment. Carries `{segment, species, count}`.
  `count` is the conversion count (5 vanilla). Purple carries no hazard key.

Hazards: `water` (hard, alternate key blue, captains wade but cannot carry),
`elec` (hard, yellow), `fire` (soft, red), `poison` (soft, white). The engine
decomp treats water as an ambient `WaterBox`/`SeaMgr` volume and fire/poison/
electric geysers as `Hiba`/`GasHiba`/`ElecHiba` actors; a water *choke* therefore
has to be authored as a water corridor/gate unit rather than the ambient volume.
See `HoleSourceAudit` rows in the lane handoff.

## Seeded table

Per AP seed and floor, `derive_floor_table(seed, cave_id, floor, *, unit_pool,
unit_candidates, tagged_treasures, gates)` returns a table keyed by `schema`,
`seed`, `cave_id`, `floor`, `unit_pool`, `segments`, `chokes`, `leaves`, `buds`,
`treasures`, `hole`, `generated`, `geometry_rerolls`. Slot ids are canonical:
`{cave_id}:f{floor}:{class}:{index}`.

The seed is hashed with a namespace plus `cave_id`/`floor` into a
`random.Random`, so identical inputs reproduce the table byte-for-byte and a
different seed produces a different structure. Geometry is deliberately absent:
shape, size and untagged spawns are the engine's to reroll.

## Logic projection

`requirements(table)` returns the graph lane 39 consumes:

```python
{"treasures": {treasure_id: {"segment": k, "leaf_hazard": h, "chokes": [slot_id, ...]}},
 "hole": {"segment": last, "chokes": [all chokes]}}
```

A path to segment `k` requires every choke with `after_segment < k`; a tagged
treasure adds its leaf hazard; the hole requires every choke on the floor, and
therefore so does every deeper floor. A bud before a choke turns that choke's
requirement into `hazard OR (bud_species AND pikmin_count >= count)`. Never seed a
bud behind the hazard it provides — `validate_floor_table` rejects it.

## Fail-closed validator

`validate_floor_table(table, known_treasures=None)` raises `SchemaError` on:
wrong `schema`; unknown slot class/hazard; duplicate or non-canonical slot ids;
non-contiguous segment/choke/leaf/bud ordering; a choke that does not join
adjacent existing segments; a leaf with `item_slots != 1`; a treasure whose leaf
slot is missing or whose `leaf_hazard` disagrees with the leaf; a treasure beyond
the hole; a hole that is not the last segment; a bud gated by its own hazard; and,
when supplied, a treasure not in `known_treasures`.

## Worked example and evidence

`worked_example()` is the fan-out's first-step table: `forest_1` floor 1 with one
water choke, a water leaf and an electric leaf. `juji_key_fc` is the real
floor-1 loose treasure (fixture `tests/data/forest_1_floor1.json`, disc sha256
`c0dccd…cf88`); `example_elec_treasure` is an injected tag standing in for an AP
hazard tag. `generated: false` marks it a schema fixture, not engine generation.

Lane-34 evidence (private, not committed): `output/dsw/l34-out/worked_forest_1.json`,
`seed-A_forest_1_f1.json` (digest `bb5c1d…3ac2`), byte-identical
`seed-A_forest_1_f1_rerun.json`, and `seed-B_forest_1_f1.json` (digest
`38d736…c6d1`, a different 8-slot structure).

## Scope

Owned here: schema module, validator, docs and tests. Not here: native generator
routines (35), alcove unit assets (36), tagged placement (37), bud placement (38),
AP logic and multi-floor inheritance (39), spike/QA (40). Physical unit
traversability, native slot binding and native retry remain open.
