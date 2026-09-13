# Beasts floor 3 navigation interpretation (#300)

Owner: Codex using shared 4laric account. This follows frozen PR #299/root
`ca138612bd6834e191b32422d4eef7e3bdd9e007`. It corrects the interpretation of two
audit findings and adds optional local waypoint grounding. It does not certify
native carrying, add reverse edges or relocate spawn positions.

## What the source explains

The previous package's `grounded` count measures an exact source-Y match within
0.1 units. It does not mean that unmatched candidates have no supporting floor.
All 22 block-room spawn centers have floor support. Fifteen differ by more than
0.1 units due to floor undulations; maximum absolute delta is only 1.235829 units.
All 23 north-room centers have floor support, with maximum delta 0.008578 units.

P2 `gameMapParts.cpp`, enemy birth around lines 495–503, explicitly replaces Y
with `mapMgr->getMinY`. Treasure birth around lines 538–546 additionally applies
half the pellet cylinder height. The audit therefore reports support and delta
separately from exact height match. It does not choose an actual spawn, apply a
cylinder offset or certify a spawn radius/actor footprint.

Raw waypoint links are directed. Both rooms already allow **every source
waypoint to reach every door waypoint**, despite lacking all-pairs reachability.
The missing reverse paths are block-room destination 6 and north-room destinations
3/4. They do not establish a blocked return route to a door.

`routeMgr.cpp` reads these as `mFromLinks` (lines 332–340). `makeInvertLinks`
(lines 389–419) conditionally adds inverse links only if `linkable` passes a
sampled floor-height test with a 25-unit maximum step (lines 425–449).
`pathfinder.cpp` line 553 includes them only when `PATHFLAG_TwoWayPathing` is
enabled. This implementation deliberately retains raw directed edges; reproducing
inverse-link and carry-mode semantics requires a separate engine validation.

P2 materializes non-door waypoints with `getMinY` and door waypoints with Y=0
(`gameMapParts.cpp` around lines 5140–5188). The opt-in package applies that rule
to these isolated, unrotated rooms using the existing offline ground query. In
the block room, waypoint 6 rises from Y=0 to its actual platform at Y=20.5;
waypoints 3/4/5 gain their small floor offsets. North-room waypoint Y values stay
zero. Source X/Z, radius, directed edges and spawn records remain unchanged.

Read-only research file SHA256 values, under `native/pikmin2-research/src/plugProjectKandoU`:

| File | SHA256 |
|---|---|
| gameMapParts.cpp | `267df97dceba6034a657d728e38892c273790059b29e25ee60efac26d333fd49` |
| routeMgr.cpp | `89180ee6080bf1df62f0ef6f15bf959e3aabc197e84188d54c0e0f6f42c38253` |
| pathfinder.cpp | `7e26661b59b01da7a3796c4fac6f5747dc4b20fc34dc59fafaaa3bc8f420da26` |

## Package and validation

Run from `output/p2-beasts-floor3-track`:

```powershell
python -m experimental.pikmin2_beasts_floor3 `
  --iso 'C:/Users/alari/Downloads/PIKMIN2 for GAMECUBE.iso' `
  --catalog ../../output/p2-cave-catalog-batch/audit-final/catalog.json `
  --units ../../output/p2-mapcode0-batch/import `
  --output output/floor3-300/new-package --source-navigation
python -m pytest -q tests/test_pikmin2_beasts_navigation.py tests/test_pikmin2_beasts_floor3.py tests/test_pikmin2_beasts_floor2.py tests/test_pikmin2_beasts_content.py
```

The new opt-in policy is `P2_BEASTS_FLOOR3_NAVIGATION_PACKAGE_1`.
`room.mod` embedded routes, `room.ini` and `collision.json` agree on grounded
waypoints. `source-collision.json` preserves the checked original input. Each room
manifest records both raw and door reachability, all waypoint changes, and spawn
support/delta. Existing flags still say `native_ready=false` and
`retail_generation=false`. Capped doors are not usable cave exits.

18 tests and 30 subtests passed. Actual-disc runs `output/floor3-300/first` and
`repeat` produced 15 byte-identical files. Manifest SHA256:
`1ced301bdbd664d82f06be613331b8595dad633259e8f81b8f3014344085072f`.
The separate `output/floor3-300/default` run is byte-identical to all 13 frozen
#295 `final-a` files: omission of the flag preserves the earlier package exactly.
Full hashes are local in `output/floor3-300/verification.json`.

Tests cover one-way leaves that can return, genuinely unreachable doors, absent
floor support, malformed graphs/door references, nonfinite coordinates, separate
exact-match/support classification, unchanged inputs and absence of invented
reverse edges. No native source/build/save was changed or launched. Offline
ground queries still require native collision and carrying validation in the
assembled scene; this is a source-backed engineering interpretation, not a
replacement for that evidence.
