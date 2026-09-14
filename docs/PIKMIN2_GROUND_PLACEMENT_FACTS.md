# Ground-invertebrate placement facts (lane 14 -> lane 04 #440)

Tracking: lane 14 of `docs/PIKMIN2_IMPLEMENTATION_FANOUT.md`; tracking issue
[#165](https://github.com/4laric/pikmin-randomizer/issues/165); consumer issue
[#440](https://github.com/4laric/pikmin-randomizer/issues/440); coordination
#186. Implementation owner: Codex through shared account `4laric`. This is the
lane-14 contribution named by the next-wave dispatch ("lanes 13/14/16/19 must
confirm the per-identity space/water/home/helper facts").

Root/native pins used for this analysis: root `opencode/p2-lane14-placement`
from `codex/p2-main-review` `ef1cace`; read-only decomp
`native/pikmin2-research` revision
`632af93787b9c95b63f0c13be32b161375ce3a96`; US `GPVE01` revision 0.

## What this is, and what it is not

This supplies the **per-identity terrain/space/water/home/helper facts** lane 04
needs to turn its default-deny lane-14 candidate profiles into constrained
profiles. It is **source-contract evidence**, the same level as
[the ground-invertebrate asset audit](PIKMIN2_GROUND_INVERTEBRATE_ASSETS.md): it
does **not** claim native XYZ/terrain/route evidence and it does **not** admit
any identity. Every `(slot, identity)` pair stays `denied` until the native
placement gate lands (lane 04 blocker, [sweep #437](PIKMIN2_PLACEMENT_SWEEP_437.md)).

Machine-readable companion: `docs/p2_ground_placement_facts.json`
(`schema: p2-placement-facts-v1`), validated by
`tests/test_p2_ground_placement_facts.py`.

## Facts

`footprint_radius` is the source root collision sphere (asset audit section 4);
all six fit the current default slot `radius` of 100, with Hana (75) the
binding case. `helper_budget` is what a slot's `helper_capacity` must cover.
`requires_corpse_route` is true for all six because each drops a carryable
`BDT_*` corpse.

| Identity | ID | Terrain | Water | Burrow ground | Home anchor | Helper budget | Footprint | Evidence anchors |
|---|---|---|---|---|---|---|---|---|
| Armor (Cloaking Burrow-nit) | 15 | `ground` | no | **yes** (`Appear`/`Dive`) | none | 0 | **40** | ArmorState.cpp:17-30; enemyInfo.cpp:32 |
| ElecBug (Anode Beetle) | 28 | `ground` | no | no | none | 0 (needs a 2nd beetle; not a spawned child) | 32.5 | ElecBugState.cpp:21-30; ElecBug.cpp:273-320; enemyInfo.cpp:51 |
| Imomushi (Ravenous Whiskerpillar) | 65 | `ground` | no | **yes** (`Appear`/`Dive`) | none | 0 (needs a fruit plant for berry predation) | 17.5 | ImomushiState.cpp:19-33; Imomushi.cpp:723-803; enemyInfo.cpp:34 |
| TamagoMushi (Mitite) | 68 | `ground`, `underground` | no | **yes** (`Appear`/`Hide`) | none | **10 surface / 30 cave** | 18 | tamagoMushiState.cpp:18-23; tamagoMushiMgr.cpp:77-162; generalEnemyMgr.cpp:436-443; enemyInfo.h:212 |
| Sokkuri (Skitter Leaf) | 79 | `ground`, `mixed`, `water` | **yes** (`mWaterBox`) | no | none | 0 | 25 | SokkuriState.cpp:18-26; Sokkuri.cpp:269-344; enemyInfo.cpp:109 |
| Hana (Creeping Chrysanthemum) | 84 | `ground` | no | **yes** (`Sleep`/`mBuried`) | none | 0 | **75** | Hana.h:23-46; Hana.cpp:26-175; enemyInfo.cpp:59 |

`min_water_depth` is 0 for every identity: Sokkuri is amphibious rather than
submerged-only, so it accepts water and land slots alike. No lane-14 identity has
a nest/child anchor (`child_name` is null for all six), so `requires_home` stays
false for the whole family; the only cohort identity that needs a home anchor is
lane 16's `Jigumo` (`PanHouse` child).

## Lane-04 consumption

Each `identities.<name>.profile` fragment in the JSON is a `p2-placement-v1`
profile subset (the fields `randomizer.p2_placement` accepts). Lane 14 merged
them as `randomizer.p2_placement_catalog.GROUND_INVERT_FACTS`, which
`candidate_profiles()` now reads for lane-14 identities; lane 04 still owns that
module and may adjust the merge. Lane 04 keeps owning `identity`, `cohort`,
`family_lane`, `accepted_gates` and `notes`; lane 14 does not set those. The
practical effect:

- **Sokkuri** stops matching land-only profiles and now accepts `water`/`mixed`
  slots.
- **Armor / Imomushi / TamagoMushi / Hana** require `burrow_ground` on the slot.
- **Hana** rejects any slot with `radius < 75`.
- **TamagoMushi** requires slot `helper_capacity >= 10` (30 underground).
- **ElecBug** stays a 0-helper profile; its pairing is an arena-population
  property, recorded as a note rather than a helper spawn.

Do not treat these values as a source pool. None of the six has a P1 campaign
equivalent, so lane 04's `cohort` remains `null` and the terrain constraints,
not a cohort, are the current restriction. A source-pool model for P2-only
identities is a separate lane-02/04 decision.

With the merge in place, lane 04's compatibility report now lists TamagoMushi in
`unplaceable_identities` (alongside Jigumo) because its group `helper_budget`
exceeds every slot's default `helper_capacity` of 0. That is the intended signal
for gap 1 below, not a regression.

## Open gaps this slice exposes (not solved here)

1. **Slot helper capacity is unmodelled.** `normalize_slot` defaults
   `helper_capacity` to 0 and `slots_from_campaign` never sets it, so a
   TamagoMushi profile with `helper_budget` 10 is constraint-incompatible with
   every current slot. Lane 04 must derive per-slot helper capacity from the
   source generator rows before any group identity is placeable.
2. **Cave slots are absent from the surface inventory.** TamagoMushi's 30-strong
   group and `underground` terrain have no campaign slot in the current tables.
3. **Water depth is not yet probed.** Sokkuri's `mixed`/`water` match is
   constraints-only until native terrain evidence classifies the slots.
4. **Behaviour dependencies without a field.** Imomushi's fruit plant and
   ElecBug's second beetle are recorded in `placement_note` because the schema
   has no plant/partner constraint; a dedicated field is lane 04's call.
5. **No native XYZ/terrain/route evidence.** Unchanged; still the gate that
   keeps every pair denied.

## Handoff block

```text
Lane 14 / Codex via 4laric / parent #165 + #440:
Concrete scope: per-identity terrain/space/water/home/helper facts for Armor,
  ElecBug, Imomushi, TamagoMushi, Sokkuri, Hana (ground placement constraints).
Root base/head: codex/p2-main-review ef1cace; branch opencode/p2-lane14-placement;
  native/decomp read-only 632af937 (unchanged); no native build.
Owned files: docs/PIKMIN2_GROUND_PLACEMENT_FACTS.md,
  docs/p2_ground_placement_facts.json, tests/test_p2_ground_placement_facts.py,
  randomizer/p2_placement_catalog.py (GROUND_INVERT_FACTS + candidate_profiles
  merge), tests/test_p2_placement.py (TamagoMushi unplaceable assertion).
Already in integration branch: lane-04 schema + candidate inventory (1e23df4,
  ff55584, 5d6ed8a, 6032863); what is new: the lane-14 fact fragments and their
  consumption in candidate_profiles().
Gates: A-G not claimed; source-contract placement facts only. No native
  evidence, no generated-session run, no identity admission.
Next consumer: lane 04 (#440) merges the fragments and derives slot
  helper_capacity; lane 14 continues with natural combat/reward/re-entry
  acceptance per the lane-14 next action.
```
