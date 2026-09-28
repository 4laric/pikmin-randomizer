# Floor3 source treasure haul plan (#344)

Owner: Codex using shared4laric account. Native companion: #343.

This plan selects `dia_c_green`, source treasure row1, from the frozen floor3
package. Its actual disc configuration is **150 Pokos, carry weight12, slots20**.
The model hash is checked against that package and its economy is re-read from
the disc catalog. The native instance is
`forest_1:floor3:treasure:dia_c_green:0`, scoped to engineering delivery evidence.
It is not an authorized campaign reward or a completed floor checkpoint.

The chosen spawn is source type2 slot0 in `room_north_1_hiba_tsuchi`, instance2
of the authored floor3 assembly. Local `(0,0,-25)` transforms to world
`(-85,0,-960)`. The source code's `RandItemUnit::getItemNormalSetMapNode` selects
treasure-item spawn points; this is an explicit choice from those candidates,
not a reproduction of its weighted random generation. The engineering Pod is
at `(-85,0,-280)` in the first room, 680 units from the treasure in X/Z.

Nearest source waypoints give the directed path **9→8→7→0**. A shortest-path
search uses only existing outgoing links; it never invents reverse edges.
The plan retains exact source waypoint coordinates plus treasure/Pod connectors.
It samples a 50-unit-wide strip at intervals no greater than10 units. All **267**
samples have collision floor support. This is not a swept-volume clearance test
or proof of native path selection: the runtime must still demonstrate carrying,
seam crossing, approach to the Pod and delivery.

`prepare(iso, catalog_path, units, assembly, treasure_package, output)` validates
the source floor roster, catalog/import/assembly binding, room collision, model
and recorded disc source hashes before writing a fresh `haul.json`. It retains
the source treasure row/slot, instance, geometry and economy. It does not change
geometry, source links, other treasure, actors or campaign state.

## Evidence

Actual GPVE01rev0 runs produced byte-identical plans at
`output/beasts344/first/haul.json` and `output/beasts344/repeat/haul.json`, SHA256
`fdfe3547276574a3655196e543fcf12177f1b2a750853ff726d39f21171034c6`.

Inputs relative to the private root:

- `../../output/p2-cave-catalog-batch/audit-final/catalog.json`
- `../../output/p2-mapcode0-batch/import`
- `../p2-beasts-floor3-track/output/floor3-306/final-a`
- `../p2-beasts-floor3-track/output/floor3-295/final-a`

**19 tests and 23 subtests passed** across route planning, source treasure,
assembly and collision suites. New tests exercise one-way reachability, shortest
source path, invalid route identities, lateral strip edges and failure when only
the centerline has support. Existing source tests cover changed asset/provenance
and economy constraints. No native source changed in this plan PR.

The separate native #343 runtime consumes this plan, attempts actual pellet
transport and verifies the independent Pod economy receipt, including duplicate
and reopened-credit behavior. That evidence must distinguish scripted carrier
recruitment from natural gameplay. Neither this static plan nor that engineering
receipt alone enables floor3 descent or full campaign accounting.
