# P2 placement and encounter compatibility schema (lane 04)

Tracking: lane 04 of `docs/PIKMIN2_IMPLEMENTATION_FANOUT.md` (dispatch #435);
child issue #440; coordination #186; audit #434. Implementation owner: Codex via
shared account `4laric`. Executing agent/session: opencode (deepseek-v4.1-flash).

This defines the machine-readable side of the production randomizer bridge that
decides whether a candidate P2 identity may occupy a source spawn slot. It is a
schema plus audit tool; it does not choose a seed, serialize a layout, or
implement family behavior.

## Ownership boundary

- Lane 02 owns the canonical roster and the identity keys.
- Lane 04 owns the placement/encounter constraints and this audit.
- Lane 03 owns seed serialization and the native manifest binding; it consumes
  the `legal`/`denied` decisions here.
- Lane 05 owns asset staging; it consumes the admitted identities.
- Family lanes supply the terrain/space/helper facts that become profiles.

The schema is `p2-placement-v1`. Lanes 02/03/05 must agree on it before coding
consumers; a profile is lane 04's contribution, the identity list is lane 02's.
Encounter descriptors use the companion schema `p2-encounter-v1`.

## Slot record

Required: `uid`, `label`, `stage`, `terrain`, `radius`.
Optional: `water_depth`, `flight_space`, `burrow_ground`, `home`,
`helper_capacity`, `projectile_corridor`, `corpse_route`, `protected`,
`boss_slot`, `first_day`, `respawn_days`, `source_identity`, `cohort`,
`evidence`.

`terrain` is one of `ground`, `water`, `air`, `underground`, `mixed`.
`evidence` carries the accepted native placement facts and defaults to
`{xyz: false, terrain: false, route: false}`. `cohort` is an optional
placement-compatibility class (e.g. `ground`, `dwarf`, `grub`, `frog`,
`aquatic`, `flying`); a profile with a cohort may only occupy a slot with the
same cohort, or any slot when either side leaves `cohort` null.

## Profile record

Required: `identity`, `terrains`.
Optional: `family_lane`, `footprint_radius`, `min_water_depth`,
`requires_flight_space`, `requires_burrow_ground`, `requires_home`,
`helper_budget`, `requires_projectile_corridor`, `requires_corpse_route`,
`is_boss`, `encounter_descriptor`, `accepted_gates`, `allow_protected`,
`requires_renewable_slot`, `min_first_day`, `cohort`, `notes`.

`accepted_gates` defaults to empty. An empty list denies every slot for that
identity: eligibility is denied until placement evidence exists.

## Encounter descriptor record

A placement document may carry an optional `encounters` list of descriptor
records (schema `p2-encounter-v1`). A boss profile must reference one by id via
its `encounter_descriptor` field; a descriptor without a matching boss profile is
allowed but unused.

Required: `id`, `identity`, `terrains`, `footprint_radius`, `helper_budget`,
`arena_slots`, `phases`, `protected_drops`, `required_gates`.
Optional: `notes`.

- `id` is the unique descriptor key; `identity` is the boss identity it describes.
- `terrains` is a non-empty subset of the slot terrain classes.
- `footprint_radius` is the arena footprint compared against the slot `radius`.
- `helper_budget` is the helper count compared against slot `helper_capacity`.
- `arena_slots` is `{min, max}` (non-negative ints, `min <= max`); a legal slot
  must satisfy `min <= 1 <= max`, i.e. host exactly one boss arena.
- `phases` is a positive integer. `protected_drops` and `required_gates` are lists
  of strings. `required_gates` are requirements, not native proof.

Document validation rejects duplicate descriptor ids, unknown descriptor fields,
unknown `arena_slots` fields and boss profiles that reference a missing id.

## Default-deny rules

A pair is `legal` only when every rule passes; any failure yields `denied` with
machine-readable reasons.

1. The profile has at least one accepted placement gate.
2. The slot carries accepted native `xyz`, `terrain` and `route` evidence.
3. Protected slots are refused unless `allow_protected`.
4. Bosses, and boss slots, require an `encounter_descriptor`; there is no
   universal replacement permission. When descriptor records are supplied, a boss
   pair is legal only if the referenced descriptor exists, its `identity` matches
   the profile identity, its `terrains`/`footprint_radius`/`helper_budget` fit the
   slot and `arena_slots.min <= 1 <= arena_slots.max`.
5. Terrain, water depth, flight space, burrow ground, home/nest anchor,
   projectile corridor, corpse return route and placement cohort must all be
   satisfied.
6. Helper budget must fit the slot's `helper_capacity`; footprint must fit
   `radius`.
7. Renewable/scheduled requirements and `min_first_day` must hold.

## Audit output

`randomizer.p2_placement.audit()` returns a deterministic report: evaluated
counts, every `(slot, identity)` decision, admitted/denied slot lists per
identity, a denied-reason histogram, unplaced identities and boss slots.

```
py -3.12 -m randomizer.p2_placement --document placement.json --summary
```

`randomizer.p2_placement.slot_from_spawn_row()` adapts existing P1 spawn rows
(`randomizer.spawn_data`) into default-deny slot records so the audit can run
against the current slot table before native evidence lands.

## Compatibility report

`randomizer.p2_placement.compatibility_report()` separates hard incompatibilities
from evidence gaps. It runs the same constraint checks as `evaluate` but ignores
the admission/evidence defaults, so a slot that no constraint rejects counts as
*compatible* while the pair is still *denied* for missing gates and native
evidence:

- `identity_compatibility`: per identity, compatible/incompatible slot counts and
  uids and the top constraint violations (`top_reasons`, default 3).
- `slot_compatibility`: per slot, how many candidate identities could ever fit.
- `unplaceable_identities`: candidate identities with no constraint-compatible
  slot anywhere, i.e. a real placement gap rather than an evidence gap.

## Concrete candidate inventory (lane 04)

`randomizer.p2_placement_catalog` turns the real slot tables into a validated
`p2-placement-v1` document for the initial candidate cohort (fan-out lanes 13,
14, 16 and 19):

- `slots_from_campaign()` reads the 72 production `CAMPAIGN_SLOTS` generators,
  classifies terrain from `cohort`, copies the source `protected` flag and marks
  `evidence.xyz` when an extracted position exists.
- `slots_from_adult_group()` reads `ADULT_SLOTS`/`GROUP_SLOTS` (ground adults and
  dwarf/grub groups) with `radius` decoded from `radius_hex`.
- `slots_from_generators()` reads the 690 raw teki/boss generators. These are
  excluded from `all_slots()` by default because they have no extracted XYZ or
  terrain; pass `include_generators=True` only for inventory inspection.
- `candidate_profiles()` emits default-deny profiles for the P2 source ids owned
  by lanes 13/14/16/19, keyed on the lane-02 roster enum names. A candidate with a
  P1 catalog equivalent inherits that production `cohort`.
- `boss_encounters()` / `boss_profiles()` provide the two aquatic bosses
  (`UmiMushi`, `UmiMushiBlind`) via `p2-encounter-v1` descriptors. They stay out
  of the default document because the campaign table exposes no boss arena slot;
  `build_document(include_bosses=True)` only makes sense with caller-supplied boss
  slots. Inspect the descriptors with `--boss-descriptors`.

```
py -3.12 -m randomizer.p2_placement_catalog --summary
py -3.12 -m randomizer.p2_placement_catalog \
    --document output/lane04/p2_placement_document.json \
    --report output/lane04/p2_placement_compatibility.json
```

At the current source revision the 72 known-terrain slots yield: 33 `ground`,
10 `grub`, 6 `dwarf`, 7 `frog`, 10 `aquatic` and 6 `flying`. Ground-terrain
candidates without a P1 equivalent match all 49 walkable slots (the three ground
classes); candidates with an equivalent are restricted to their own cohort.

Homes and routes come from the lane-02 roster: every cohort identity drops a
carryable corpse, so all profiles set `requires_corpse_route`, and `Jigumo`
(Hermit Crawmad) additionally sets `requires_home` because its roster child is
`PanHouse`. Submerged slots expose a corpse route (Blue Pikmin carry through
water) but no campaign slot exposes a nest anchor, so `Jigumo` is reported as
`unplaceable` — a concrete placement gap, not an evidence gap.

## Coverage report

`randomizer.p2_placement.coverage_report()` returns a deterministic,
machine-readable summary of the same default-deny evaluation:

- `identity_coverage`: per identity, the admitted slot count and uids, whether it
  is a boss and whether it has a valid (existing, identity-matching) descriptor,
  and the top denial reasons with counts (`top_reasons`, default 3).
- `slot_coverage`: per slot, the admitted identity count and the admitted
  identity list, plus label and boss-slot flag.
- `unresolved_bosses`: sorted boss profile identities with no valid descriptor
  (missing, unreferenced or identity-mismatched); this is a schema gap, not a
  native-evidence claim.

## Current status and limitations

- Schema, normalization, strict validation, encounter-descriptor validation,
  evaluation, audit, coverage and compatibility reporting are implemented and
  tested (`tests/test_p2_placement.py`).
- The lane-04 candidate inventory classifies concrete slots and rejects foreign
  cohorts, but no retail P2 identity is admitted: every candidate profile ships
  `accepted_gates: []` and every slot leaves `evidence.terrain`/`evidence.route`
  false. Terrain is derived from the campaign cohort, not a native terrain probe.
- Candidate profiles are a lane-04 constraint seed. Family lanes still own and
  must confirm the per-identity terrain/space/helper facts; lane 02 keys the
  identity list; lanes 03/05 consume the admitted identities. New P2 species with
  no P1 equivalent (`Sokkuri`, `Armor`, `ElecBug`, `FireChappy`, ...) currently
  carry `cohort: null`, so they match every walkable slot until a source pool or
  terrain evidence constrains them.
- `UmiMushi`/`UmiMushiBlind` are bosses: they need an encounter descriptor and
  remain in `BOSS_COHORT`, outside the non-boss document.
- A `legal` decision is a placement constraint result, not a gameplay or
  six-gate acceptance. Constraint-compatible is not accepted.
