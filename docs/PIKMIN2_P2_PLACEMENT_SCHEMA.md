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

## Slot record

Required: `uid`, `label`, `stage`, `terrain`, `radius`.
Optional: `water_depth`, `flight_space`, `burrow_ground`, `home`,
`helper_capacity`, `projectile_corridor`, `corpse_route`, `protected`,
`boss_slot`, `first_day`, `respawn_days`, `source_identity`, `evidence`.

`terrain` is one of `ground`, `water`, `air`, `underground`, `mixed`.
`evidence` carries the accepted native placement facts and defaults to
`{xyz: false, terrain: false, route: false}`.

## Profile record

Required: `identity`, `terrains`.
Optional: `family_lane`, `footprint_radius`, `min_water_depth`,
`requires_flight_space`, `requires_burrow_ground`, `requires_home`,
`helper_budget`, `requires_projectile_corridor`, `requires_corpse_route`,
`is_boss`, `encounter_descriptor`, `accepted_gates`, `allow_protected`,
`requires_renewable_slot`, `min_first_day`, `notes`.

`accepted_gates` defaults to empty. An empty list denies every slot for that
identity: eligibility is denied until placement evidence exists.

## Default-deny rules

A pair is `legal` only when every rule passes; any failure yields `denied` with
machine-readable reasons.

1. The profile has at least one accepted placement gate.
2. The slot carries accepted native `xyz`, `terrain` and `route` evidence.
3. Protected slots are refused unless `allow_protected`.
4. Bosses, and boss slots, require an `encounter_descriptor`; there is no
   universal replacement permission.
5. Terrain, water depth, flight space, burrow ground, home/nest anchor,
   projectile corridor and corpse return route must all be satisfied.
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

## Current status and limitations

- Schema, normalization, strict validation, evaluation and audit are
  implemented and tested (`tests/test_p2_placement.py`).
- No retail P2 identity is admitted here yet: candidate profiles still need
  lane 02 identity keys and family-supplied terrain/space/helper facts plus
  accepted native XYZ/terrain/route evidence.
- A `legal` decision is a placement constraint result, not a gameplay or
  six-gate acceptance.
