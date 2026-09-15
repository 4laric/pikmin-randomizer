# Opt-in rendered pose interpolation (#313)

This extends #304 to noninteractive Bulblax displays only. Add a local
`p2-bulblax-interpolation.txt` containing exactly `P2_BULBLAX_INTERPOLATION_1`.
Every selected display must also have its matching retail source-clock table.
Without the marker, the existing nearest-pose path remains active.

Each display loads a private Shape through `StdSystem::getShape`; unlike
`loadShape(false)`, this does not add a mutable model to the shared shape cache.
Immutable decoded bank arrays feed that model's existing vertex and normal
storage. The draw loop allocates no interpolation buffers. Positions lerp;
normals normalize after lerping, with the nearest endpoint used for cancelling
normals. The source clock owns looping, pause and events. Samples clamp at the
ends; interpolation does not wrap the final pose to the first.

The native decoder checks chunk boundaries, vector budgets/values, baked root
identity and bounds, and requires exact same-clip indexing/material/resource
bytes across poses. This is a compatibility gate for our imported rigid banks,
not a general replacement for the MOD loader. Identical topology alone cannot
prove semantic correspondence; use poses from the same verified source bank.
Existing file/clip/total byte limits still apply. Decoded arrays and topology add
bounded CPU storage, and each of at most eight displays adds one model.

Course and root-joint bounds are rebuilt from the blended vertices. Normal
`drawshape`/`initMesh` calls rebind GX vertex arrays; `pc_gfx_set_array` advances
its array serial on every binding. No global cache/frame invalidation is used.
Private models follow the native App heap lifetime; reset drops their handles
before teardown. Repeated diagnostic setup in the same scene allocates another
private model until that scene heap is reclaimed.

`pc_p2_bulblax_visual_geometry` is a diagnostic copy of the most recently drawn
private arrays, with a bounds containment check. It returns false when the
feature is disabled or reset. The copy allocates only when explicitly queried.

Validation commands:

```text
python -m unittest tests.test_pikmin2_pose_bank tests.test_pikmin2_pose_blend tests.test_pikmin2_blend_player tests.test_pikmin2_source_clock
python -m experimental.pikmin2_bulblax_runtime build --native NATIVE --build-dir BUILD --output FRESH_BUILD --head EXACT_NATIVE_HEAD
python -m experimental.pikmin2_bulblax_runtime run --assets LOCAL_P1_ASSETS --profile PREPARED_PROFILE --retail-sources LOCAL_BULBLAX_SOURCES --exe FIXTURE_EXE --output FRESH_RUN --interpolate
```

The opt-in fixture tests two independent displays at their first, midpoint and
last poses, including a held endpoint while paused. It compares every rendered
position and normal against the shared interpolation kernel, checks cached
source positions against the original bank, and verifies reset/reload and
unchanged actors/cargo/repairs. Runtime results and visual acceptance are recorded
in #313 and local `output/interpolation313/` evidence.

This does not enable interpolation on fighting enemies, animate attachment
joints, change hitboxes, or provide skeletal interpolation. Linear vertex blends
can visibly shrink or flatten curved motion between widely spaced samples.
## Recorded acceptance

Native source: `629d94a518f9e8df9862264d2b932fb96063f865`; production target
`pikmin_pc` built successfully. Fixture02 SHA256:
`93005488b849fbe2c38d0c5ae2ea9da4dc853c75750a08534c1d844243292ec9`.

- Eight focused Python/native test methods passed, including real-bank vector
  checks, malformed input refusals and the existing clock/player regressions.
- Four default-path native runs and four opt-in native runs passed. The enabled
  modes were Queen wait1, Baby move and KingChappy move1; each had two displays.
- Three additional native runs refused a malformed marker, missing source clock
  and malformed vector padding before any interpolation-ready marker.
- Midpoint captures for all three species and Emperor endpoint captures were
  inspected: both models render with intact surfaces and no obvious interpolation
  corruption. These are static captures, not full-motion or performance sign-off.
- All runs matched the disabled control's GX warning set. Actors, cargo and
  repairs remained unchanged. The initial failed run was a fixture seek to the
  exclusive duration bound; fixture02 uses the final sampled frame instead.

Evidence is in `output/interpolation313/runtime02/result.json`,
`default-runtime/result.json`, `refusals/results.json`, and the fixture build
provenance. Retail assets, binaries and captures remain local.
