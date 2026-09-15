# Lane 35 — unit-pool partition and phased trunk/choke generation (#474)

Lane 35 / owner-session DeepSeek l35 / parent #468 + lane issue #474. Wave
contract: `output/deepseek-wave/_cave_fanout.md`.

## Concrete slot class / routine addressed; missing model piece

Addressed: **unit-pool partition** into the frozen segment/choke/leaf classes and
**phased trunk growth** (grow segment A -> forced choke -> grow segment B from the
choke's far door -> place the hole in B) with deterministic per-seed tables,
rerolling geometry, and retry-on-failure.

Missing model piece filled: the wave previously had no partition and no by-
construction must-pass choke. This lane defines and validates both, in a root
model (`experimental/pikmin2_cave_growth.py`) and an engine-free native policy
(`pc_port/pc_p2_cave_growth.h`).

## Bases, heads, dirty state, ordered commits

- Root base `fba8d5eb0767950f56486bd2738598eb99a4645d`; head
  `d68dc3e105ecfc3d84c8d0230f1b70744706e706`; dirty: no.
  1. `d68dc3e1` lane35: seeded cave unit-pool partition + phased trunk growth model + tests (#474)
- Native base `b805d9c626e4f4558c95aef7cac311a5d9a2068f`; head
  `40a0cfaf3d9ac7bf0fe8ae2e2afc1e00f47d6227`; dirty: no.
  1. `e39ab40f` lane35: engine-free unit-pool partition + phased trunk growth policy + test (#474)
  2. `40a0cfaf` lane35: unconditional native checks; use choke hazards in path proof (#474)

## Owned files; generator hooks and provider/consumer agreements

New, lane-owned:
- `experimental/pikmin2_cave_growth.py` — partition + seeded table + phased growth + path proof + CLI.
- `tests/test_pikmin2_cave_growth.py` — 11 focused tests.
- Native `pc_port/pc_p2_cave_growth.h` — header-only engine-free mirror of the same policy.
- Native `tools/p2_cave_growth_test.cpp` + one CMake block (labelled lane-35 hook).
- This handoff.

Reused, not forked: `pikmin2_cave_catalog` (`catalog.json`, `unit_pools[f008]`,
unit `kind`/doors), `pikmin2_cave.unit_definition`, `pikmin2_selected_units` water
decoding. No shared generator routine was edited; no second generator path was added.

Provider/consumer agreements:
- **Provider (lane 34 schema):** the ordered per-floor choke hazard list and per-
  unit hazard classification. `build_table(..., chokes=[...])` consumes an
  authoritative list; `partition_pool(..., hazards)` consumes a name->hazard map.
- **Consumer (lanes 36/37):** the leaf/choke classes and the far-door frontier of
  the forced choke; leaf alcove authoring (36) and gate/item placement (37) attach
  to the emitted `choke`/`leaf` slots, not to segments.
- **Consumer (lane 39 logic):** the seeded table (`chokes`, hole host segment) is
  the stable graph; geometry is not logic.
- **Consumer (native generator, unported):** `p2_cave_grow`/`p2_cave_choke_on_every_path`.

## What is already integrated; what is actually new

- Already integrated: retail cave definition/inventory tooling and unit decoding;
  the native port's cave **runtime** (entry/checkpoint/transfer) only.
- New: the partition, the seeded structural table, the phased growth, and the
  articulation proof. The native port has **no** cave map generator (`src`/`include`
  contain no `RandMap*`/`MapUnit*` code; only the read-only decomp at
  `C:/Users/alari/pikmin-randomizer/native/pikmin2-research` has it), so native
  integration of this policy into a live generator is future work.

## Build evidence

`output/dsw/l35-build-evidence.txt` line 2:
`2026-09-15T13:05:51 lane=l35 target=p2_cave_growth_test
native=40a0cfaf3d9ac7bf0fe8ae2e2afc1e00f47d6227 dirty=no
exe=.../native-l35-build/p2_cave_growth_test.exe
sha256=acdf06a77521baa74e3d95638ab7eb1eb917f33267d9258e76f68a33fd98e584
ninja_n="ninja: no work to do."`

The native test is a non-GL unit test; it was executed directly (exit 0):
`PASS p2 cave growth: partition, forced choke on every path, multi-choke chain,
reroll, bypass and no-room failure rejection`.

## Fixture/seed and observed generation evidence

- Catalog regenerated from the local disc (GPVE01 rev0) + research source:
  `output/dsw/l35-out/catalog/catalog.json` (14 caves / 105 floors / 96 pools);
  dependencies `output/dsw/l35-out/dependencies/dependencies.json`. `forest_1`
  floors 1-4 map to pools `1_units_cent3_tsuchi.txt`, `1_units_cent2_tsuchi.txt`,
  `2_ABE_norhiba_blkhiba_tsuchi.txt`, `2_ABE_mid1_nor3_tsuchi.txt`; floor 5 is the
  boss-only `1_units_boss_tsuchi.txt`.
- Hazard source of truth `output/dsw/l35-out/forest1_pools.json`: all 14 forest_1
  units decode `waterbox.txt` empty (Hole of Beasts is dry). The water choke is
  therefore a **provider-injected** hazard on the real 2-door corridor
  `wayl_tsuchi` (`output/dsw/l35-out/forest1_hazards.json`); it is not a natural
  retail water unit and is labelled injected.
- Primary generation log `output/dsw/l35-out/primary_growth.log` (seed 20260915,
  forest_1 floor 1) shows the forced water choke `n4=wayl_tsuchi` between segment A
  (`room_cent3_4_tsuchi,way3,way4,way3`) and segment B (`room_cent3_4_tsuchi,
  way2`) with `choke=n4 on_every_path=true` and `P2_CAVE_GROWTH PASS choke_count=1`.
- Summary `output/dsw/l35-out/evidence_summary.txt`.

## Acceptance contract results (model scope; injected vs natural)

1. Generation invariant — **PASS (model, by construction + BFS articulation check)**;
   choke is on every path for floors 1-4. Not engine generation.
2. Seed determinism — **PASS (model)**: same seed -> identical table; 16 seeds ->
   4 distinct choke tables. **PASS, model**.
3. Re-roll invariance — **PASS (model)**: geometry differs across 8 salts while the
   table and the choke hazard are fixed.
4. Reachability — **PASS (model)**: the hole is reachable only through the seeded
   choke(s); a bypass edge makes the checker fail (native negative test).
5. End-to-end loop — **not in scope**, owned by lane 40.
6. Failure handling — **PASS (model)**: floor 5's boss-only pool has no segment,
   returns `status=failed` after the retry budget rather than an ungated layout; a
   native no-room pool is rejected. Label: model, not engine.

Evidence class: **model generation, `generated:"model"`, `native_validated:false`**.
The water choke hazard is **injected**. No claim of a live engine-generated cave.

## Re-roll / restart / cross-seed result

- Cross-seed: seeds 0-15 produce tables `{('elec',),('elec','water'),('water',),
  ('water','elec')}` (4 distinct); same seed repeats exactly.
- Re-roll: salts 0-7 differ in unit identity/rotation while `table` is unchanged.
- Cross-floor: floors 1-4 grow; floor 5 fails cleanly. Restart/live re-entry is a
  remaining dependency (no native generator).

## Known limitations; next consumer; reproduction

Limitations: no live engine generator to drive; forest_1 has no natural water
unit, so the choke hazard is injected; door geometry is a direction/rotation model,
not collision-validated offsets; item/gate and leaf authoring are out of scope
(36/37). The retail source has **no whole-floor regeneration** (only local
`RandMapChecker` rejection over 500 attempts), so the "engine already retries"
assumption in #468 is **not** established by the decomp and the retry loop here is
new behavior that native integration must add.

Next consumer: the native generator port (or lane 40's spike) should call
`p2_cave_grow` with lane-34's choke list and feed the emitted slots to lanes 36/37;
lane 39 reads the same table.

ONE exact reproduction command:

```powershell
py -3.12 -m experimental.pikmin2_cave_growth --catalog "C:/Users/alari/pikmin-randomizer/output/dsw/l35-out/catalog/catalog.json" --cave forest_1 --floor 1 --seed 20260915 --chokes water --hazards "C:/Users/alari/pikmin-randomizer/output/dsw/l35-out/forest1_hazards.json" --output "C:/Users/alari/pikmin-randomizer/output/dsw/l35-out/forest1-water-choke" --verify-salts 8
```

## Subagent usage

Three subagents were spawned, staggered, per the brief:
- `explore` #1 (P2 generator source audit): returned the exact `UnitKind`
  (Cap/Room/Corridor), door-matching/offset rules, hole-as-spawn-type, water as a
  per-unit collision volume, and the absence of any choke/regen concept. **Used
  as-is**; it directly shaped the design (no hole unit kind, no engine retry).
- `explore` #2 (existing-candidate inventory): confirmed no native cave generator
  exists and listed the reusable primitives. **Used as-is**; prevented a second
  generator path and redirected the slice to the model + engine-free native policy.
- `general` #3 (data extraction): regenerated the real catalog/dependencies and
  decoded forest_1's units (all water=false). **Used as-is**; its finding that the
  floor is dry forced the honest injected-label on the water choke.

Estimated saving: roughly 60-90 minutes of reading and asset decoding moved off the
critical path. Cost: the `general` run's catalog regeneration is I/O heavy, and one
subagent audit conclusion (unit kinds) had to be reconciled against the model
before use, not trusted blind.
