# Damagumo arena runtime assembly (#798)

Lane `shard-enemies-3-damagumo56-arena-assembly`, issue #798, parent #586.
Recovery assembly for the stranded gen-9 gap in
`shard-enemies-3-damagumo56-observer` (#173): no staged Damagumo arena and no
built preview-room executable existed to run the #173 guarded game path.

## Pins (read-only inputs)

- native build pin `45534ee3d5193b776339a8b464f004d4d24eae5d` (guarded room app +
  fixture + engine)
- `damagumo-family.json` `f9ec5030890d72fba0c890b41407aa8788b6fac53223dd62f231a3259f68ef94`
  and `damagumo-slot-312004.json` `61019a39bf255442e49cd5d03db6f16581ab5370ab401a346341f8d077c4e37c`
  (canonical LF) from `damagumo-converter-artifact-landing` (#685)
- `Demon/enemy.bmd` `8fc0ac7fd6c7585113cf10da12ecd7faccf807896d2d642ab0f80019fff2a961`
- `longlegs_Damagumo_bind_00.mod` `c5642cc97a292210b1556465125685963c8403134b438398c9739a9f64827dc2`
  (104640 bytes) from `damagumo-bind-mod-conversion-native` (#727)
- guard #632 `scripts/p2_fixture_captain_guard.h`
  `d2f678c9eda75e151eb534077dff9e30ad36ae4796881d971bbd09945f3c3474`

## Delivered (owned files)

- `experimental/pikmin2_damagumo_arena_assembly.py` - fail-closed staging
  adapter: canonical-LF hash verification of the four pinned artifacts,
  family/slot structural validation, slot-312004 roster (Damagumo + ordinary
  P1 control at generator 312004/312005), bind-mod + mesh + actors-config
  installation into a private run, receipt with exact hashes, and a reload
  verifier. No engine/family/shared edits, no ADMIT, no ledger writes.
- `tests/test_pikmin2_damagumo_arena_assembly.py` - 8 focused tests
  (CRLF/LF canonicalization, hash drift, missing input, malformed JSON, wrong
  slot, missing anchor, actor grammar/rejection).

Engine facts confirmed read-only: `pc_p2_long_legs.cpp` already resolves the
`Damagumo` species and loads
`assets/dataDir/courses/pikmin2room/longlegs_Damagumo_bind_00.mod`; the host
reads `p2-long-legs-actors.txt` (`P2_LONG_LEGS_ACTORS_1`) and requires every
wanted generator present in the scene.

## Remaining gap (blocked)

The runtime acceptance (`scripts/run_pikmin2_fixture.py` consumer check with
`prerequisite_resolved=true`) needs (a) the canonical stock game asset root
whose `dataDir/stages/chal0/default.gen` carries the stock `iket` enemy
template the shared `generator()` overlay requires - the assets roots reachable
in this worktree carry a previously overridden `chal0` (`r9=ikip`), so the
shared arena overlay refuses; and (b) a leased private preview-room build at
native `45534ee3` splicing `p2_muse_damagumo_room_app.cpp` under #632 plus a
leased GL run. Neither the stock assets nor the leased GL slot were available
to this lane, so the consumer check could not run and no gameplay gate is
claimed. Gates 1-4/6 UNTESTED, gate 5 source-backed N/A.

Exact owner action: provide the canonical stock asset root (or the missing
`chal0/default.gen` enemy template) to the private arena overlay, then run the
leased preview-room build + guarded GL path.

## Captain safety (#632)

No runtime run was executed by this lane, so no observed ticks: the guard is
adopted by reference (hash above) in the pinned room app; the assembly itself
runs no engine.
