# forest_1 P1 floor-1 staging plan (lane shard-caves-forest-forest1-p1, #154)

Parent #586 (planning fanout); planning shard #594; content integration #531.
Implementation owner: Codex through shared GitHub account `4laric`.
BOUNDED P1 slice: forest_1 floor 1 only. Full P2 acceptance stays open; no ADMIT.

## What this slice delivers

A deterministic, placement-free floor-1 STAGING PLAN derived from the DONE
forest_1 P0 packet (`shard-caves-forest-forest1-p0`), plus an
engine-independent native fixture that validates the plan's invariants.

- `experimental/content_lanes/p2-cave-forest_1_p1.py` consumes the P0 packet
  read-only (`load_packet` strict schema/cave/floor-coverage checks), extracts
  the floor-1 decode (`staging_plan`) and emits
  `p2-forest1-floor1.json` (handoff) and `p2-forest1-floor1.txt`
  (line-oriented sidecar). `validate_plan` enforces: no `generated` claim, no
  invented `placements`, a present unit pool + sha, unique units, well-formed
  enemy rows (a minimum or target count, non-negative ints, source-token
  names) and optional unit-asset closure.
- `native/tools/p2_forest1_p1_fixture.cpp` is additive and engine-independent
  (no engine headers, never linked into a game target). It parses the sidecar
  and re-checks the same invariants, emitting
  `P2_FOREST1_P1_PLAN` and `PASS P2_FOREST1_P1_STAGING_PLAN`.

## Round trip

```
py -3.12 experimental/content_lanes/p2-cave-forest_1_p1.py \
  --packet <P0 packet.json> --output <private out>
g++ -std=c++17 tools/p2_forest1_p1_fixture.cpp -o p2_forest1_p1_fixture.exe
p2_forest1_p1_fixture.exe <private out>/p2-forest1-floor1.txt
```

## Honest scope and remaining blockers

- This validates the STAGING PLAN. It does not boot the game, spawn actors,
  or prove real collision/routes/unit staging; no runtime floor-1 boot has
  been observed in this slice. The four arena gates remain UNTESTED.
- Missing runtime prerequisite: a cave replacement-main runtime fixture built
  through the leased private build (`scripts/build_pikmin2_fixture.py`) that
  boots forest_1 floor 1 with the current preview overlay and observes
  960x540 centred startup, live squad and active gameplay, adopting captain
  safety #632 (`scripts/p2_fixture_captain_guard.h`: orimaDead/NaviDead/
  HP<=1 before pause/movie returns or observation ticks, `CAPTAIN_DOWN` +
  BLOCKED exit, parked captain, negative guard test).
- Provider blockers stay with their owners: #129 (caves), #128 (assets),
  #131 (species), #132 (saves), #140/#144/#145/#146. Unadmitted floor roster
  members block promotion, not this preparatory plan.
- Floors 2-5, persistence, retreat/extinction/reload and natural collection
  remain OPEN.

## Gen-4 update (consumed prerequisites, conformance gate)

- Consumed accepted #129 consumer landing into the private native worktree
  (cherry-pick `21caef9a` -> `1a0904ac`: `pc_p2_cave_generate.h`/`.cpp`,
  `pc_p2_cave.cpp` hook, CMake line). It defines the `p2-cave-generate.txt`
  sidecar contract the runtime fixture will feed.
- New `check_generate_against_floor_one(packet, sidecar)`: strict-conformance
  gate between any candidate generate sidecar and the pinned floor-1 decode.
  Problems fail closed (unknown unit/spawn, below-minimum counts, pool
  mismatch, malformed sidecar); notes label every STAGED choice (room
  topology, unit dimensions, anchor kind, target deviations).
- Honest gap confirmed: a faithful passing sidecar still needs the unit-blob
  decode (dimensions/doors for `1_units_cent3_tsuchi.txt`, pinned hash
  `5082b1e2...`, absent from every reachable checkout) plus staged room
  topology and anchor kind. The runtime floor-1 boot remains BLOCKED on the
  replacement-main fixture + leased build + captain guard #632.

## Gen-5 update (sidecar generation + provider harness consumed)

- Reviewed integrated `cave-generate-provider` (#129, native e44b5d70): its
  header is the same module the consumer landing ports; its root-side proving
  harness `experimental/pikmin2_cave_generate_proving.py` defines
  `manifest_from_packet(packet, floor, unit_defs)` + marker verification.
- Added the consumer-side mirror to this adapter: `generate_sidecar`,
  `render_generate_sidecar` and `write_generate_sidecar`. Pool and spawn
  counts come from the P0 floor-1 decode; unit geometry comes from
  `unit_defs`; rooms (one per unit, +x spaced, turn=i%4) and anchor kind are
  explicitly STAGED harness shaping.
- Round-trip is tested: generated sidecar parses under the strict reader and
  passes `check_generate_against_floor_one` (18 tests pass).
- Remaining gap (unchanged, now singular): the pinned unit blob
  `1_units_cent3_tsuchi.txt` (sha 5082b1e2...) must be decoded with the
  shared `unit_definition` parser to supply real `unit_defs`. Absent from all
  reachable checkouts, so no sidecar is generated for the real floor. Runtime
  floor-1 boot additionally needs the replacement-main fixture under lease,
  #632 captain guard and an observed 960x540 boot.
