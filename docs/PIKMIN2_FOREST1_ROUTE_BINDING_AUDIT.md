# Forest1 route/spawn binding audit (issue #796)

Lane `forest1-route-binding-audit`. Read-only audit of the forest1 staged-arena
spawn-slot and route-group binding, for prerequisite recovery request
`75aa5e3a0ed0ecc2ca0cd180c6fce13ccc2ddae224dd397bf2741ca196e9b62f`.
It consumes the blocked collision-obs evidence and the forest1-p1 arena
manifest read-only; no build, run, engine edit or shared-file change is made
here, and no gameplay acceptance is claimed (all six gates stay UNTESTED).

## Finding (exact defect)

**`SPAWN_ROUTE_BINDING_MISSING`** - the staged generate manifest requests 10
actors across 2 spawn lines (`spawn UjiA 6`, `spawn UjiB 4`) with **no
route/group field on any spawn line**, while the engine loads route group
`test` with 64 points. The engine births exactly one actor and it never moves
or traverses (0 movement, 0 `P2_FOREST1_TRAVERSE`) across the full ~20k-tick
observation window. The generate grammar `spawn <name> <count>` carries no
per-spawn route reference, so no spawned actor is bound to a walking route.

**Owner**: generator/actor staging line (**#129**) with criterion disposition
in **#154**. This is not a collision/locomotion engine fault: ground probes
resolve (`P2_ROOM_GROUND`), the actor grounds and contacts, but it is never
attached to a route.

## Evidence (byte-hashed; text-mode reads change the digest)

- Staged manifest `.../forest1-collision-obs-out/run-forest1-collision/
  p2-cave-generate.txt` sha256 `86691d1c59fbc4e2fc325bf3e5de49e752bc882b
  edb81f604d18068950346bdb`.
- Run log `.../forest1-collision-obs-out/run-collision2.log` sha256
  `de7812cce5a59c20650a59f0cbae7f13e8cde146988dcd59547072b525fe40b7`.
- Observed markers: 1 `P2_FOREST1_BIRTH`, 1 `P2_FOREST1_CONTACT`, 0
  `P2_FOREST1_TRAVERSE`, `live_actors=1`, `moved=0` over 20000 ticks;
  route groups `test`=64 points, `tkch`=0.

## Resume disposition for downstream #154

**NO-RESUME** for runtime re-observation on this staged arena: re-running it
would reproduce the identical 1-birth/0-traverse outcome. Resume gate: a
staged manifest whose spawns carry a route/group binding (or a generator ack
that binds them), then one fresh guarded run. `identity_spawn` and the other
five gates remain UNTESTED.

## Module and tests

- `experimental/pikmin2_forest1_route_binding_audit.py`: dependency-free
  parser + fail-closed adjudicator (`DEFECT` / `HEALTHY` / `UNDETERMINED`)
  + resume disposition. No staging, no injection.
- `tests/test_pikmin2_forest1_route_binding_audit.py`: 9 focused tests
  (real defect shape, healthy shape, partial set, missing route group,
  missing birth, malformed input, contract identity).
- Real-evidence audit output: `out/audit-real.json`.
