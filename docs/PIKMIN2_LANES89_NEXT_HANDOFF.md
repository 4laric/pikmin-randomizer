# Lanes 08/09 next-wave handoff (#431, #429, parent #128)

Implementation owner: Codex through shared account `4laric`; executing agent
opencode, 2026-09-14. Private worktrees only; no maintained checkout or native
origin was modified, and no upstream GitHub writes were made.

```
Lane 08 / lane 09 / existing parents #431 (events), #429 (billboard), #128:
Concrete IDs: Armor (EnemyID 15, Cloaking Burrow-nit) event migration;
              HikariKinoko (id 48) camera-facing billboard.
Root base: 3851d4b (codex/p2-main-review); native base: f14c6851 (clean).
Root branch: opencode/p2-lanes89-root-v2 (pushed to origin).
Native branch: opencode/p2-lanes89-native-v2 @ 8c9a6cb (c2ce9216 lane08,
  b667eec9, e6d55224, d5aa3afb, 8c9a6cb lane09).
Private build: output/tracks/p2-lanes89-next/native-build
               (Ninja, Release, MinGW gcc 16.2.0, PIKMIN_NATIVE_JAUDIO=ON).
Native exe SHA-256: F35DE2B45B9B319E22CE08D98A5502C79A85FB60788C9F15BB996C9244C45A0E
No-work dry run: cmake --build . --target pikmin_pc -- -n  ->  ninja: no work to do.
Lane 08 arena gate: PASS (real-GL, slot committed/released in #186).
Lane 09 visual gate: PASS (replacement-main GL fixture).
```

## Lane 08 - Armor gameplay events (#431)

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
- **Runtime PASS**: fresh overlay arena, 960x540, `P2_ARMOR_BITE frame=18` x4
  (exact source event frame) each followed by `P2_ARMOR_EAT`, no extinction.
  Run `output/tracks/p2-lanes89-next/armor-runtime-01/0c7c1e01016b480eae910ef2f97cd392`;
  native.log SHA-256 `FC58AE5B309F6221760D507BACDED60B85A631A6E594425EBBA0BB1B63C231CE`.

## Lane 09 - Camera-facing billboard (#429)

Detail: `docs/PIKMIN2_BILLBOARD_NATIVE.md`.

- New `Mesh::FeatureFlags::Billboard` (1<<17), no MOD layout change; strict MODs
  and all non-billboard identities are unaffected.
- Renderer hook is in the real PC backends
  (`OGLGraphics`/`DGXGraphics::drawSingleMatpoly`), not the dead `Joint::render`.
  `billboardFromJoint` keys off the active GPU matrix so both port composition
  conventions are handled.
- Converter `billboard='native'` emits pivot-relative, unit-scale geometry and a
  joint carrying the source pivot/scale; 16 tests in
  `tests/test_pikmin2_convert_billboard.py`.
- Probe `tools/test_p2_billboard.cpp` (CTest `p2_billboard_test`):
  `PASS p2_billboard`.
- **Real-source conversion PASS**: all six sampled HikariKinoko poses convert
  with `billboard='native'`; pivot/scale match the audited `(-4,46,0)`/`0.8`.
- **Real-GL PASS** (`experimental/pikmin2_hikari_billboard_fixture.py`):
  `PASS HIKARI_BILLBOARD draws=2 max_offdiagonal=0.000000 visible=2364`.
  Run `output/tracks/p2-lanes89-next/hikari-gl-run-02`, native.log SHA-256
  `95EE2D4487DED8DE6070EAA6A6961E2CB0EC115EDB3402AA7F7BB14B89EA401E`.
- `experimental/pikmin2_flora_assets.TOLERANCES['HikariKinoko']` now defaults to
  `billboard='native'`, so the ordinary flora extraction emits the camera-facing
  bank.

## Validation actually performed

- Native production build: `[542/542] Linking CXX executable bin\nectar.exe`,
  exit 0; all three CTest probes build and pass.
- Lane 08 real-GL arena PASS and lane 09 real-GL fixture PASS (above).
- Root focused suites: flora/billboard/clock/ground/armor/behavior
  `127 passed, 1 skipped`; full `py -3.12 -m pytest tests -q` ->
  `2016 passed, 45 skipped, 19 failed`, where all 19 failures are the documented
  native-checkout-dependent class (the private root worktree has no `native/`).

## Remaining / requested of lane 01

1. Review and export the native lane series (`8c9a6cb`) with the root converter
   and flora-default commits.
2. Run a full flora-install arena now that the default Hikari bank is native, and
   the mixed-scene/perf gate for the admitted cohort.
3. Optional: handle a rotated billboard joint in the converter (bake `R^-1` out
   of the local frame); Hikari's sampled poses do not need it.
