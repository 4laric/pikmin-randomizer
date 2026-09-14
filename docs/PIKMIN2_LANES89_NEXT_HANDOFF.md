# Lanes 08/09 next-wave handoff (#431, #429, parent #128)

Implementation owner: Codex through shared account `4laric`; executing agent
opencode, 2026-09-14. Private worktrees only; no maintained checkout or native
origin was modified, and no upstream GitHub writes were made.

```
Lane 08 / lane 09 / existing parents #431 (events), #429 (billboard), #128:
Concrete IDs: Armor (EnemyID 15, Cloaking Burrow-nit) event migration;
              HikariKinoko (id 48) camera-facing billboard.
Root base: 3851d4b (codex/p2-main-review); native base: f14c6851 (clean).
Root branch opencode/p2-lanes89-root-v2 @ da6d20a;
Native branch opencode/p2-lanes89-native-v2 @ b667eec9 (c2ce9216 lane08,
b667eec9 lane09).
Private build: output/tracks/p2-lanes89-next/native-build
               (Ninja, Release, MinGW gcc 16.2.0, PIKMIN_NATIVE_JAUDIO=ON).
Native exe SHA-256: F52A6435A788A032C1800DD3F086017B0E86E969DC775E3778F305272DB28C0F
No-work dry run: cmake --build . --target pikmin_pc -- -n  ->  ninja: no work to do.
Gates: A/B/C/D/E/F/G not re-run on a live arena this pass (see below).
```

## Lane 08 — Armor gameplay events (#431)

Detail: `docs/PIKMIN2_ARMOR_EVENT_CLOCK.md`.

- `pc_p2_armor.cpp` now dispatches the attack2 bite (frame 18), eat kill
  (frame 60) and flick (frame 39) from crossed `p2sampled::Clock` events instead
  of `stateTime * 30`, with per-actor generation resets on state change and
  address reuse.
- Probe `tools/test_p2_armor_events.cpp` (CTest `p2_armor_events_test`) proves
  exactly-once across frame skip, loop, pause, interruption and address reuse:
  `PASS p2_armor_events`.
- The `experimental/pikmin2_armor_behavior.validate` markers are preserved
  (`P2_ARMOR_BITE` reports the source frame, one eat per bite).

## Lane 09 — Camera-facing billboard (#429)

Detail: `docs/PIKMIN2_BILLBOARD_NATIVE.md`.

- New `Mesh::FeatureFlags::Billboard` (1<<17), no MOD layout change; strict
  MODs and all non-billboard identities are unaffected.
- `pc_port/pc_p2_billboard.h` + `Joint::render` build the flagged mesh's draw
  matrix from the active model and camera view matrices.
- Converter `billboard='native'` emits pivot-relative, unit-scale geometry and a
  joint carrying the source pivot/scale; test coverage in
  `tests/test_pikmin2_convert_billboard.py` (16 passed).
- Probe `tools/test_p2_billboard.cpp` (CTest `p2_billboard_test`):
  `PASS p2_billboard`.

## Validation actually performed

- Native production build: `[542/542] Linking CXX executable bin\nectar.exe`,
  exit 0; both new CTest probes build and pass.
- Root focused suites: billboard/clock/ground/armor/flora/material
  `98 passed, 1 skipped`; full `py -3.12 -m pytest tests -q` ->
  `2016 passed, 45 skipped, 19 failed`, where all 19 failures are the documented
  native-checkout-dependent class (the private root worktree has no `native/`).

## Remaining / requested of lane 01

1. Review and export the two native commits (lifetime/event/renderer shared
   semantics) with the root converter commit `da6d20a`.
2. Reserve one real-GL slot for the two lane gates that remain UNTESTED:
   the Armor natural `P2_ARMOR_*` run on a fresh adopted arena, and the
   HikariKinoko `billboard='native'` camera-facing visual comparison.
3. The Hikari flora tolerance remains `'static'` until that GL pass; recorded,
   not silently switched.
