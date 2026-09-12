# Opt-in engineered Emergence roster (#114, #111)

`experimental.pikmin2_roster.install(content_import, run, floor, assets, imported)`
replaces only the private preview treasure/Dwarf generator records. It adds both
floor-one treasures and four Snow targets, or Atlas and seven Snow targets on
floor two. Squad, Pod, ship and existing Violet flowers are preserved.

This consumes the prepared content catalog but does not mark that source manifest
`native_ready`. Its separate `p2-roster.json` says `engineered_runtime: true`.
These are the current **standalone** engineering rooms, not the two-room assembly
or the retail random map algorithm. Floor one is denser than the complete retail
floor. Plants and source Violet placements remain outside this increment.

Actor positions choose source slots in source order. Enemy slots receive their
minimum group counts, then remaining actors up to each maximum. Multiple group
members use equally spaced angles at half the source radius. Source coordinates,
heading, radius, slot index and per-instance identity are retained alongside the
explicit ground-projected runtime position and height delta. Atlas uses its sole
source item slot. Cargo config order puts the legacy Pod-selected treasure first;
this does not change the source-slot assignment.

Before writing, the installer checks conservative clearance against the current
captain, Pod, ship, supplied marker locations and Violet flowers, pairwise actor
clearance, four neighboring ground probes, and directed connectivity from each
nearest route node back to the Pod's node. These checks do not prove complete
model footprints or native swept carry paths. Changing fixtures requires updating
the policy and these clearance anchors together.

## Interface

`p2-cargo.txt`:

```text
P2_CARGO_1
<count>
<native_generator_uint> <instance_id> <model_basename> <value> <weight> <slots>
```

Instance IDs are floor-scoped (`tutorial_1:floor1:treasure:dia_a_red:0`). Runtime
receipts prepend `treasure:`. IDs 5000 upward are encoded little-endian at generator
offset8, matching PC `_70` and host `<I` reads. This differs from scaffold source
records written big-endian. All retained record IDs are checked for collision.
Models are copied to private `courses/pikmin2room/p2cargo_<catalog>.mod` paths.
Returned `enemy_generator_ids` drives the Snow actor installer, including floor2.
Enemy labels remain `preview dwarf bulborb` for existing corpse receipt discovery.

Install rejects repeated application, shared hard-linked targets, junction paths
escaping the private run, malformed content, model hash changes and unsupported
rosters. All validation precedes mutation; a failed install still belongs in a
disposable prepared run, not a reused player profile.

## Validation

Three focused tests cover deterministic source offsets and ground projection,
capacity/no-ground failures, hard-link/outside-path rejection, clearance and
unreachable return paths. Actual local asset preparation passed for both floors:
28 and32 generator records, unique native IDs, correct two/one cargo configs,
four/seven Snow targets, twenty preserved Pikmin, and two preserved Violet
flowers on floor2. Source generator hash stayed unchanged. Reinstall rejected.
Evidence lives locally under this track's `output/roster114/result.json`.
Native collection/combat and player clearance acceptance are integration work.
