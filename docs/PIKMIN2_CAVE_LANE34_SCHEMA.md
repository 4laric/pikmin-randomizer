# Lane 34 handoff — cave slot schema and seeded logic graph

Lane 34 / owner-session opencode deepseek-v4.1-flash / parent #468 + lane issue #473.
Slice: **SCHEMA**.

## Concrete slot class / routine addressed; missing model piece

All four slot classes (segment, choke, leaf, bud), hazard tags and the per-floor
seeded table. Missing model piece addressed: there was no machine-readable
slot-class/hazard schema and no seed-deterministic table for generators 35–38 and
logic 39 to share (`pikmin2_cave_catalog` was explicitly `generated: false` with
"No seeded topology, hole selection, radial distribution or restart identity").

## Root base/head; native base/head; dirty state; ordered commits

- Root base `fba8d5eb0767950f56486bd2738598eb99a4645d` on `deepseek/p2-l34`.
- Native base `b805d9c626e4f4558c95aef7cac311a5d9a2068f` on `deepseek/p2-l34-native`;
  **no native edits** (root-only slice), worktree clean at base.
- Ordered root commits:
  1. `1717ec190124dc9d05c525a5e2b3ac80e1fd80b2` — `lane34: cave slot schema,
     seeded table, fail-closed validator, forest_1 example (#473)`
  2. the handoff commit containing this file — `lane34: lane 34 schema handoff
     (#473)`
- Working tree clean apart from untracked lane outputs outside the repo.

## Owned files; generator hooks and provider/consumer agreements

Owned (new): `experimental/pikmin2_cave_schema.py`,
`tests/test_pikmin2_cave_schema.py`, `tests/data/forest_1_floor1.json`,
`docs/PIKMIN2_CAVE_SCHEMA.md`. No existing file modified, no native hook, no
generator routine (`gameCaveInfo`, unit selection, item/gate placement,
`pc_p2_cave.*`) touched.

Provider contract for consumers (documented in `docs/PIKMIN2_CAVE_SCHEMA.md`):
`derive_floor_table(seed, cave_id, floor, *, unit_pool, unit_candidates,
tagged_treasures, gates)` returns the seed table; `requirements(table)` returns the
logic graph; `validate_floor_table(table, known_treasures=None)` is fail-closed.
Agreements assumed, not yet confirmed with a live handshake: **35** consumes
`unit_pool`/`unit_candidates` and the ordered `chokes`; **37** consumes
`treasures[].slot_id`/`leaf_hazard`; **38** consumes `buds[]` + `count`; **39**
consumes `requirements` and owns multi-floor inheritance. Seed/options value is
the same `seed` string lane 03 fixes for the AP seed.

## What is already integrated; what is actually new

Reused: the catalog's `f008` unit-pool names/unit candidates and treasure ids;
the `forest_1` floor-1 fixture was read from the disc through
`experimental.pikmin2_cave_catalog.parse` + `experimental.pikmin2_cave.unit_definition`.
New: the schema, validator, seeded derivation, requirement projection, worked
example, tests and the doc. The four-slot vocabulary did not exist anywhere in
either worktree before this commit.

## Build evidence line (native commit, exe SHA-256, ninja -n)

No native change → no build. Native worktree remains at base
`b805d9c626e4f4558c95aef7cac311a5d9a2068f`; no exe or dry run is claimed.
Recorded in `output/dsw/l34-build-evidence.txt`.

## Fixture/seed used; observed generation evidence with exact paths

Fixture: `tests/data/forest_1_floor1.json` (Hole of Beasts `forest_1.txt` sha256
`c0dccd032e576bdc9234ad04fc44b7081c6f36b52e50cb66ed48fe9e6f54cf88`; pool
`1_units_cent3_tsuchi.txt`; unit candidates `item_cap_tsuchi`, `way3_tsuchi`,
`way4_tsuchi`, `wayl_tsuchi`, `way2_tsuchi`, `way2x2_tsuchi`,
`room_cent3_4_tsuchi`; real loose treasure `juji_key_fc`; empty gate roster).
Seeds `lane34-seed-A` and `lane34-seed-B`. Evidence (private, uncommitted):
- `output/dsw/l34-out/worked_forest_1.json` — water choke + water leaf + elec leaf.
- `output/dsw/l34-out/seed-A_forest_1_f1.json` — digest `bb5c1d73…9863ac2`, 5 slots.
- `output/dsw/l34-out/seed-A_forest_1_f1_rerun.json` — byte-identical to seed-A.
- `output/dsw/l34-out/seed-B_forest_1_f1.json` — digest `38d736ae…4e02c6d1`, 8 slots.

## Acceptance contract 1–6 results (injected vs natural)

1. **Generation invariant** — structural only, host-side: chokes join adjacent
   segments, hole is the last segment, treasures never beyond the hole, and hole
   requirement is the union of all chokes by construction. Validator enforces.
   **Not** a native generation claim.
2. **Seed determinism** — PASS, host-side. Same seed reproduces the table
   byte-for-byte (identical files + digest); different seed yields a different
   digest and slot count.
3. **Re-roll invariance** — host-side re-derivation with a fixed seed reproduces
   the table and `requirements` (test `test_reentry_same_seed_reproduces_table_and_requirements`).
   Native re-entry invariance is **not** demonstrated; named dependency: lanes
   35–38 must persist the table across engine re-entry.
4. **Reachability** — structural guard only: no treasure beyond the hole, a bud is
   never behind the hazard it provides, hard chokes are all in the hole
   requirement. Ambient-vs-alcove enforcement is 37.
5. **End-to-end loop** — not attempted; owned by lane 40.
6. **Failure handling** — validator is fail-closed (wrong schema, unknown
   class/hazard, duplicate/non-canonical slots, bad adjacency, `item_slots != 1`,
   treasure/leaf mismatch, treasure beyond hole, hole not last, own-hazard bud
   all raise `SchemaError`). Native retry-on-failure is 35; **not** demonstrated.

Injected vs natural: the schema derivation is natural host-side logic; the
`example_elec_treasure` tag and the worked example are **injected fixtures**
(`generated: false`), never a generation PASS. `juji_key_fc` is a real floor-1
treasure.

## Re-roll / restart / cross-seed result

Cross-seed shown (A vs B differ in digest and structure). Host re-derivation is
stable. Real engine re-roll/restart not run — depends on 35–38.

## Known limitations; next consumer; ONE exact reproduction command

Limitations: no native hook or persistence; `choke.unit` is a catalog name, not a
proven-traversable unit; `leaf.item_slots` is a count, not a native slot binding;
water is ambient in the engine so a water choke needs an authored corridor/gate
unit; no multi-floor table yet; purple buds carry no key hazard; provider/consumer
agreement with 35–39 is documented but not handshake-confirmed.
Next consumer: lane 35 (unit-pool partition / phased trunk growth), then 39.
Reproduction:
```
py -3.12 -m pytest tests/test_pikmin2_cave_schema.py -q
```

## Subagent usage

Three subagents were delegated per the brief, spawned in one batch:
1. `explore` **source audit** — used as-is; corrected the lane's premise: the
   native and root engine worktrees hold the **P1** decomp and only a
   `pc_p2_cave` host stub; the P2 generator lives in the read-only
   `native/pikmin2-research` checkout. Its `gameCaveInfo`/`RandMapMgr`/unit/gate
   citations directly shaped the doc's water-is-ambient and electric-gate notes.
2. `explore` **candidate inventory** — used as-is; confirmed no four-slot
   vocabulary or `P2_CAVE_*` generation marker existed, and named the catalog and
   dependency contracts to reuse.
3. `general` **fixture + test scaffolding** — mostly used, corrected. The
   `forest_1` fixture is real (verified digest) and was used verbatim. The test
   file was a strong draft; I corrected two of its implicit assumptions in the
   module (slot-index cap made `slot_id(...,99)` raise; species↔hazard mapping
   was keyed backwards) and extended it with worked-example, requirements and
   re-entry tests (14 → 17). Estimated saving 30–45 min of read-heavy work; cost
   ~15 min reviewing/fixing the mapping bug it could not see.

## Source audit reference (read-only `native/pikmin2-research`)

`RandMapMgr::create` 4-round slotting (`plugProjectNishimuraU/RandMapMgr.cpp:58`),
`MapUnitGenerator::createMemList` unit decode (`MapUnitGenerator.cpp:77`),
`RandMapUnit::setMapUnit` growth (`RandMapUnit.cpp:157`), `RandItemUnit::setItemSlot`
(`RandItemUnit.cpp:43`), `RandGateUnit::setGateDoor` (`RandGateUnit.cpp:39`),
`ItemGate`/`ItemDengekiGate` split (`itemGate.cpp:68,1077`), `FloorInfo::Parms`
`f008` (`gameCaveInfo.cpp:226`), `Pom` conversion `ip01=5` (`Pom.h:100`), ambient
water `WaterBox` (`gameMapParts.cpp:341`), hazard actors `Hiba`/`GasHiba`/`ElecHiba`
(`enemyInfo.h:79-81`).
