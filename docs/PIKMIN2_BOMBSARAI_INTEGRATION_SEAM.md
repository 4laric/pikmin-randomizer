# Pikmin 2 Careening Dirigibug integration seam and private build (#244)

Implementation owner: Codex using shared account 4laric. Arena contract #186, terrain/clock pattern #169, converter inputs #128. Prior slices: [source audit](PIKMIN2_BOMBSARAI_AUDIT.md), [projectile lifecycle contract](PIKMIN2_BOMBSARAI_PROJECTILE_CONTRACT.md), [host adapter and blast routing](PIKMIN2_BOMBSARAI_HOST_ADAPTER.md). Ownership model per the 2026-09-13 #128 assignment and [PIKMIN2_WORKER_HANDOFF.md](PIKMIN2_WORKER_HANDOFF.md): the lane retains its mechanics, registration hooks, private builds and runtime evidence; merge/build serialization remains a repo rule (no shared binary overwrite, isolated candidates, local commits only).

## Scope

Lane-owned files, native branch `codex/p2-bombsarai-policy` (worktree `output/native-bombsarai-policy/`):

- `pc_port/pc_p2_bombsarai_map_trace.h` / `.cpp` — P1 binding of the two terrain adapter primitives via a dedicated `P2BombSaraiTraceProxy : Creature` (never actor-registered; owner collision fields never reused) and `P2BombSaraiMapBinding` (`traceMove` + `getMinY` statics with call/floor/wall counters).
- `pc_port/pc_p2_bombsarai_arena.h` / `.cpp` — registration seam: one stationary host-driven arena installed from an opt-in profile (`P2_BOMBSARAI_ARENA_1`) per #186. Pinned placement only: fixed carrier position/yaw/token, pinned capture joint (kamu_jnt1 stand-in until #128 supplies the real joint), hover and bomb parameters, and a static receiver list. Explicit supply/throw events stand in for the FSM. Debug-sphere drawing only — no converted visual assets exist, and nothing here claims visual fidelity.
- `tools/p2_bombsarai_runtime.cpp` — private real-GL fixture with flat-floor, free-trace and wall runtime probes plus a supply → Release-lob → blast → routed-hits scenario (mirrors the Groink runtime fixture structure).
- `tools/p2-bombsarai-arena.txt` — the lane's opt-in install profile (pinned placement), committed under `tools/` because the repo gitignores root-level `*.txt`; the fixture expects it in its working directory as `p2-bombsarai-arena.txt`.
- `../bombsarai-runtime-extra.cmake` (workspace `output/`, lane-side) — `CMAKE_PROJECT_INCLUDE` that appends the six lane sources to `pikmin_pc` with a deferred `target_sources`, so no shared CMakeLists edit is needed (same mechanism as the Groink lane's `output/groink-runtime-extra.cmake`).

No shared hooks, no Groink-lane edits, no converter/build/export changes, no actor registry or save-schema changes.

## Private native compile

Isolated candidate build; shared binaries/exports untouched (main checkout's `native/build-randomizer` was not used or modified).

```powershell
# PATH includes C:/msys64/mingw64/bin (MinGW GCC 16.2)
cmake -S output/native-bombsarai-policy -B output/native-bombsarai-policy/build-bombsarai-runtime `
  -G Ninja -DCMAKE_BUILD_TYPE=Release -DPIKMIN_NATIVE_JAUDIO=ON -DPIKMIN_NATIVE_OPTIMIZE=OFF `
  -DPIKMIN_RANDOMIZER_TEST_HOOKS=OFF `
  -DCMAKE_MAKE_PROGRAM=<python-scripts>/ninja.exe `
  -DCMAKE_PROJECT_INCLUDE=C:/Users/alari/pikmin-randomizer/output/bombsarai-runtime-extra.cmake
cmake --build output/native-bombsarai-policy/build-bombsarai-runtime --target pikmin_pc -j 6
```

Results: configure clean (2.6 s); build completed `[499/499]` linking `build-bombsarai-runtime/bin/nectar.exe` (6 153 048 bytes); only the known serial-LTRANS lto-wrapper note was emitted. A rebuild reports "ninja: no work to do". The runtime fixture `tools/p2_bombsarai_runtime.cpp` is compiled by the isolated fixture path only (not the game target); it was compile-checked against the frozen host with the exact `pikmin_pc` flags (defines, include set, `-include pc_port/pc_types.h`, warning profile) — exit 0, engine-header warnings only, no lane-file diagnostics.

## Fixture and probe evidence

All five standalone policy fixtures rebuilt warning-clean (`-std=gnu++17 -Wall -Wextra -Werror`, MinGW GCC 16.2) and pass: bomb lifecycle, clock, terrain adapter, hover, blast routing.

The runtime probes are implemented in the private fixture: flat-floor probe (downward trace classifies floor, center rests within one radius of the sampled ground), free-trace probe (no contact, no ground sample required), wall probe (vertical-triangle scan, wall classification plus mandatory ground sample), then clocked supply/throw/blast with routed-hit reporting (`P2_BOMBSARAI_*` markers, PASS on completion).

**Runtime probes executed, PASS**: with the staged GPVE01 rev 0 disc assets the fixture ran end-to-end against the converted room preview — `P2_BOMBSARAI_FLOOR_PROBE ... floor=1`, `P2_BOMBSARAI_WALL_PROBE_PASS`, `P2_BOMBSARAI_MAP_PROBES_PASS`, supply at tick 30 (retail `hit_start.bca` length), blast at tick 223 with three routed hits (teki 500 self-hit, navi/piki 10 with carrier token) and the airborne-immune receiver skipped. The arena profile now carries the retail numeric inputs (tekiDamage 500 overriding the 250 header default, flight height 70 overriding 90, fuse health 4.5, blast radius 90, gravity 18.6667/tick). Full commands, environment, extraction listing and verbatim markers: `docs/PIKMIN2_BOMBSARAI_RUNTIME_EVIDENCE.md`.

## Remaining runtime-acceptance gaps

1. ~~Execute `p2_bombsarai_runtime` against the room preview with user assets~~ — done, PASS (see the evidence doc); visual confirmation still shows debug markers only. One follow-up from the run: the fixture's tangent-landing probe velocities were raised to 600 units/s.
2. #128 converter inputs: the numeric inputs (bomb trace radius 15, arm-loop ticks 30, fuse health 4.5, blast radius 90, tekiDamage 500, navi/piki damage 10, gravity 18.6667/tick, hover fp01 70 override) are now taken from the retail tables. Still open: the real `kamu_jnt1` capture joint *transform* (index 14 identified in the model, transform not yet plumbed) and visual assets replacing debug spheres.
3. Carrier FSM states (Supply/Release/Fall/TakeOff…) replacing explicit harness events; Purple-forced Fall and bitter exits through the seam.
4. Multi-carrier pool behavior against the real shared Bomb manager limit, and bomb-on-bomb induction (`ip02`) routing.
5. Save/resume and cave/day transition semantics for carried/in-flight/armed bombs (audit persistence caveat).
6. Root-serialized steps before any shared integration: merge of the lane branch, combined build, and arena registration beyond the opt-in profile.
