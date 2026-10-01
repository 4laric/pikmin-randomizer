# PIKMIN2 forest1 generate-manifest route-binding pin-discovery (issue #801)

Lane `forest1-generate-route-binding-pindiscovery`. Read-only pin-discovery /
ownership slice for the blocked consumer `cave-forest1-collision-routes-obs`
(#773, downstream #154), following the #796 audit (handoff sha `5dd7420d`).
No build, no runtime, no engine/shared edit, no ADMIT. All six runtime gates
UNTESTED.

## Defect

`SPAWN_ROUTE_BINDING_MISSING`: the staged generate manifest requests actors
with `spawn <name> <count>` lines carrying no route/group field, while the
engine loads route group `test` (64 points). One actor births and never
moves/traverses (1 birth, 0 `P2_FOREST1_TRAVERSE`, moved=0 over ~20k ticks).
Owner: generator/actor staging line (#129); criterion disposition in #154.

## Pinned callsites (file:symbol, integrated line)

| File | Symbol | Line | Role |
|---|---|---|---|
| `native/pc_port/pc_p2_cave_generate.h` | `struct Spawn { id; count; }` | 73 | spawn record has no route/group field |
| `native/pc_port/pc_p2_cave_generate.h` | `readManifest(std::istream&, Manifest&)` spawn loop | 151 | parses `spawn <id> <count>`, no route token |
| `native/pc_port/pc_p2_cave_generate.h` | spawn emitter (`P2_CAVE_GENERATE_SPAWN`) | 217 | emits id/count only; no binding ack |
| `native/pc_port/pc_p2_cave_generate.cpp` | `kP2CaveGenerateModule` | 8 | membership stub, wired in `PC_PORT_SOURCES` |

Route loader/binding: engine-side (route manager; audit group `test` = 64
points). The generator emits spawn intents only, so no generated actor is
bound to a walking route; the binding callsite is not in the generator line.
The maintained `native/` checkout (`a95040b6`) lacks the generator sources;
the integrated line (`output/dsw/native-wave` @ `b944db03`) carries them.

## Required grammar/loader extension

- Grammar: `spawn <enemy-id> <count> <route-group>` (route required).
- Struct: add `std::string route` to `struct Spawn`.
- Parser: read the trailing route token; refuse unknown/empty groups;
  refuse legacy two-field spawn lines (fail-closed) rather than silently
  unbound.
- Loader: runner binds each spawned actor to the named route group and emits
  a `P2_CAVE_GENERATE_SPAWN route=<group>` ack.

## First executable slice

- Callsite files: `native/pc_port/pc_p2_cave_generate.h`.
- Build membership: `native/pc_port/pc_p2_cave_generate.cpp` (already wired
  in `CMakeLists.txt` `PC_PORT_SOURCES`).
- Reserve: `native/pc_port/pc_p2_cave_generate.h`,
  `native/pc_port/pc_p2_cave_generate.cpp`.
- Owner lane: #129 generator/actor staging. Provider shard:
  `provider-cave-generation`.

## Downstream #773 / #154

- Command: run the forest1 collision/traversal fixture against a
  route-bound staged manifest under a leased guarded build.
- Expected: >1 birth and >=1 `P2_FOREST1_TRAVERSE` with `moved>0`.
- Resume gate: a route-bound manifest (or generator ack) + one fresh guarded
  run. Until then: NO-RESUME (re-running reproduces 1 birth / 0 traverse).

## Adapter and tests

`experimental/pikmin2_forest1_generate_route_binding_pindiscovery.py`
implements a dependency-free spawn parser plus a fail-closed adjudicator
(`BOUND` / `SPAWN_ROUTE_BINDING_MISSING` / `MALFORMED`) and the resume
disposition. `tests/test_pikmin2_forest1_generate_route_binding_pindiscovery.py`
runs 14 focused cases (defect shape, bound shape, same-line count, malformed
and missing input, count mismatch, resume gate, callsite/packet identity).

## Boundaries

Diagnosis only, never an engine unblock. Shared/maintained native and blocked
lanes stay read-only. No ledger writes.