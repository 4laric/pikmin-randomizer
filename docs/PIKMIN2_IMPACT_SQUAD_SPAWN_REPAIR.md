# Pikmin 2 impact squad-spawn repair (#745)

Consumer-repair for stopped consumer `p1-challenge-impact-runtime-acceptance`
(#565, gen 4): the integrated #739 fix emits `PARK_ALIVE` but the squad never
spawns (zero SQUAD/BOOT/PASS in 300 s while the engine renders).

## Diagnosis

The #739 `gateDiag` throttle `(frames % 300)` never fires at ~1 FPS headed
throughput, so the post-PARK stall is unattributed: the log shows
`PARK_ALIVE pikis=1` and then nothing. No gate state (movie/pause/ui/navi)
is recorded.

## Repair (behavior-preserving)

`native/tools/p2_challenge_guarded_boot_fixture.cpp`: `gateDiag` now uses an
observed-based throttle — print on first sighting of an `observed` value,
every 120th repeat, capped at 600 prints — and attributes the holding gate
(`managers`, `navi`, `movie`, `pause`, `ui`) with the full gate state
(`observed`, `alive`, `frames`, `movie`, `pause`, `ui`, `navi`) on each line.
No engine behavior changes; only diagnostic emission.

## Evidence

- `native/tools/p2_impact_squad_spawn_probe.cpp`: standalone throttle-contract
  probe (`PROBE_PASS checks=5`).
- `scripts/build_p2_impact_squad_spawn.py`: leased build/run harness; headed
  chal0 boot classified by `experimental/pikmin2_impact_squad_spawn_repair.py`.
- `tests/test_pikmin2_impact_squad_spawn_repair.py`: fail-closed classifier
  tests (spawned / frozen-attributed / frozen-unattributed / blocked).

Acceptance: headed chal0 run spawns squad (SQUAD + BOOT + PASS, exit 0).
Gates UNTESTED except observed spawn/boot. No ADMIT.
