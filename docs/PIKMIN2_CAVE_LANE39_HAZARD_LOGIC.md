# PIKMIN2_CAVE_LANE39_HAZARD_LOGIC

Lane 39 / owner-session `opencode` deepseek-v4.1-flash / parent spec #468 + lane
issue #478. Slice: **AP hazard-tag config + multi-floor logic rules** for the
water/elec example, over lane 34's seeded graph.

## Concrete slot class / routine addressed; missing model piece

Addressed the AP side of all four slot classes (segment, choke, leaf, bud): derive
per-treasure, per-segment, per-floor and per-hole hazard requirements from the
seeded table; bud `type OR (bud AND pikmin_count >= N)` with Pikmin-count
tracking; cross-floor inheritance (a floor-1 choke gates every deeper floor);
stable hints. Missing model piece before this slice: lane 34 emitted a per-floor
`p2-cave-floor-table-v1` and a single-floor `requirements()` projection, but
nothing composed a whole cave, applied bud alternate keys, tracked count, or
produced AP requirements/hints. No native generator code is in scope here.

## Root base/head; native base/head; dirty state; ordered commits

- Root base `fba8d5eb0767950f56486bd2738598eb99a4645d` on `deepseek/p2-l39`.
- Native base `b805d9c626e4f4558c95aef7cac311a5d9a2068f` on
  `deepseek/p2-l39-native`; **no native edits**, worktree clean at base.
- Ordered root commits:
  1. `c14173b482c5f6a5e59e3bf3a5da53f57039dfc5` — `lane39: multi-floor AP cave
     logic over lane-34 seeded tables (#478)`.
  2. the handoff commit containing this file — `lane39: lane 39 hazard-logic
     handoff (#478)`.
- Working tree clean apart from untracked lane evidence under `output/dsw/l39-out`
  (outside the repo).

## Owned files; generator hooks and provider/consumer agreements

- New (owned): `randomizer/cave_logic.py`, `tests/test_pikmin2_cave_logic.py`,
  `tests/test_pikmin2_cave_logic_edges.py`.
- Modified (one small labelled hook): `randomizer/catalog.py` —
  `can_reach_manifest` consults `manifest['cave_requirements']` first; inert for
  every legacy location (absent key). Exact hook is 6 added lines.
- Provider contract (lane 34, `experimental.pikmin2_cave_schema`): a sequence of
  `p2-cave-floor-table-v1` mappings with `segments/chokes/leaves/buds/treasures/
  hole`, canonical slot ids and per-choke `hardness`. Lane 34 owns single-floor
  validation; `cave_logic` consumes the shape directly and does not re-implement
  it. Optional AP-side `ambient_hazards` per floor is honoured as worst-case.
- Consumer contract (lane 03 seed/options -> `catalog.can_reach_manifest`): write
  `manifest['cave_requirements'] = randomizer.cave_logic.requirements_map(graph)`
  and pass `starting_flarlic`. Requirement rows are
  `[[{'item': name} | {'capacity': n, 'color': c} | {'captain': true}], ...]`
  (AND of OR-keys).
- Reused, not rebuilt: `randomizer.catalog.field_capacity` and the Red/Yellow/Blue
  Onion item names for capability semantics; lane 34 tables for structure.
- Agreement check: the two test fixtures are also validated by lane 34's own
  `validate_floor_table` (skipped automatically until lane 34 is merged; verified
  out-of-tree against `l34-root` — see evidence). Evidence also feeds lane 34's
  real `derive_floor_table` output into `cave_logic`.

## What is already integrated; what is actually new

Already integrated: the AP access layer (`can_reach_manifest`), lane 34's schema
and seeded derivation, and the cave checkpoint/transfer native hooks (unrelated).
Actually new: the whole multi-floor logic layer — segment/leaf/hole requirement
composition, bud OR-keys with count tracking, cross-floor inheritance, worst-case
ambient handling, stable hints, the serialisable requirement map and its
fail-closed deserialiser, and the `can_reach_manifest` hook.

## Build evidence line (native commit, exe SHA-256, ninja -n)

No native change, therefore no native build. Native worktree remains at base
`b805d9c626e4f4558c95aef7cac311a5d9a2068f`, clean; no exe or dry run is claimed.
Recorded in `output/dsw/l39-build-evidence.txt`.

## Fixture/seed used; observed generation evidence with exact paths

- Injected, hand-authored lane-34-shaped fixtures: `forest_1` floor 1 (water
  choke after0, elec choke after1, water leaf seg0, elec leaf seg1, yellow bud
  seg0 count5, treasures `juji_key_fc`(water), `example_elec_treasure`(elec)) and
  floor 2 (elec choke, water leaf, `deep_demo`(water)). Tags:
  `juji_key_fc=water`, `example_elec_treasure=elec`, `deep_demo=water`.
- Natural host-side generation (lane 34's own `derive_floor_table`, seeds
  `lane39-seed-A` / `lane39-seed-B`, pool `1_units_cent3_tsuchi.txt`): fed into
  `load_cave`. Same seed reproduces the requirement fingerprint; different seed
  changes it.
- Paths (private, uncommitted): `output/dsw/l39-out/l39-tables-seedA.json`,
  `output/dsw/l39-out/l39-logic-evidence.json`, `output/dsw/l39-out/pytest-l39.txt`.
  Deep-treasure hint from seed A:
  `Floor 2 deep_demo: Blue Onion AND Yellow Onion AND Yellow Onion or yellow
  candypop (5)` (cross-floor inheritance plus a bud OR-key).

## Acceptance contract 1-6 results (subset in scope), injected vs natural

1. **Generation invariant** — not in scope (no native generator in this lane).
   Logic invariant only: the hole requirement is the union of every floor choke by
   construction, and treasures are never placed beyond the hole (lane 34 enforced).
2. **Seed determinism** — PASS at the logic level. Same seed -> same tables ->
   identical `requirement_fingerprint`; different seed -> different fingerprint.
   **Not** a native generation claim.
3. **Re-roll invariance** — PASS at the logic level. Adding/changing a `geometry`
   field on a table does not change any hint or the fingerprint; lane 34 same-seed
   re-derivation reproduces. Native re-entry invariance is not demonstrated;
   named dependency: lanes 35-38 must persist the table across engine re-entry.
4. **Reachability** — partial, logic level. Requirements are derived only from the
   table's chokes/leaves plus configured ambient worst-case; the hole is gated by
   exactly its chokes. No live floor was traversed.
5. **End-to-end loop** — not attempted; owned by lane 40.
6. **Failure handling** — not attempted here; lane 34 validation and lane 35
   retry own it. `cave_logic` fails closed on inconsistent tables/tags/serialised
   rows.

Injected vs natural: the hand-authored fixtures and the two hazard tags are
**injected**; the seed-A/seed-B evidence uses lane 34's **natural host-side**
seeded derivation. No engine-generated cave is claimed anywhere.

## Re-roll / restart / cross-seed result (or named remaining dependency)

Cross-seed: seed A and seed B requirement fingerprints differ. Same-seed
re-derivation reproduces. Re-roll/restart: not run — blocked on the lane 35 native
generator, which does not exist in this build.

## Known limitations; next consumer; ONE exact reproduction command

Limitations:

- No P2 cave treasure locations exist in the current AP catalog, so the
  `cave_requirements` hook is exercised only by tests/manifests that carry the
  key; the seed/options layer (03) must populate it and lane 40 must add the
  locations.
- Bud OR-keys are credited only within the same floor; cross-floor candypop
  conversion is deliberately not credited (conservative direction).
- `poison` maps to `White Onion`, which has no AP item yet, so poison gating is
  modelled but not currently obtainable; leaf/ambient hardness uses lane 34's
  default hazard table while per-choke hardness comes from the table.
- `cave_logic` does not re-implement lane 34's full validator; it only indexes
  what it reads and fails closed on inconsistencies.
- Untagged random treasures are not in the seeded table, so they remain
  worst-case/none; path-dependent requirements stay out of scope by design.

Next consumer: the seed/options layer writes `manifest['cave_requirements']`;
lane 40 (spike/QA) tags two treasures and drives the loop through
`can_reach_manifest`.

Reproduction:

```
py -3.12 -m pytest tests/test_pikmin2_cave_logic.py tests/test_pikmin2_cave_logic_edges.py -q
```

## Subagent usage

Three subagents, spawned in one batch initially, per the brief:

1. `explore` **source audit** — used as-is. Corrected the lane's premise: the
   engine cave generator lives only in the read-only `native/pikmin2-research`
   checkout; `native-l39` holds only `pc_p2_cave.*` host hooks. Its citations
   (`RandMapMgr::create`, `RandGateUnit`, `Pom` ip01=5, ambient `WaterBox`) shaped
   the hardness/ambient and count-tracking rules.
2. `explore` **candidate inventory** — used as-is. Confirmed no segment/choke/
   leaf/bud or hazard-tag logic existed and named the AP access-rule entry points
   and `field_capacity`/Onion item names to reuse.
3. `general` **tests and harness** — corrected and adapted. Its adversarial suite
   found a real defect (treasure ids were unique only within a floor, so a
   cross-floor collision silently dropped a requirement row) and a fail-open path
   in the serialised-literal parser. I fixed both in `cave_logic.py`, then had to
   re-point the suite at lane 34's real table shape after I discovered lane 34's
   handoff had landed. Its cases were carried into
   `tests/test_pikmin2_cave_logic_edges.py` verbatim where the API allowed.

Estimated saving: roughly 30-45 minutes of read-heavy audit/inventory and a
genuine bug catch; cost ~20 minutes fixing the API shape it could not see and
re-pointing its tests.
