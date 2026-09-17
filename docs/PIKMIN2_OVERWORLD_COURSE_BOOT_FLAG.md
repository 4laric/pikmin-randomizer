# Overworld course boot flag P1 runtime (issue #767)

Private candidate implementing the shared overworld course boot flag as a
new additive module, proved with a leased private build plus a game-linked
guarded fixture run under captain safety #632.

## Module (owned, additive)

- `native/pc_port/pc_p2_overworld_course.h` / `.cpp`: course selection over
  exactly `tutorial | forest | yakushima | last` (indices 0-3),
  `pc_pikipelago_overworld_course()` accessor,
  `pc_pikipelago_overworld_course_id()`, and
  `pc_pikipelago_overworld_course_register()` for the shared stage-table
  path. Fail-closed: unknown or repeated selection exits 2, mirroring the
  `--experimental-challenge-level` argv style. No behavior change when
  unselected.

## Fixture (owned)

- `native/tools/p2_overworld_boot_flag_fixture.cpp`: replacement-main
  harness. Parses `--experimental-overworld-course <id>`, registers,
  boots the preview room (960x540), observes 30 guarded ticks.
  Markers: `P2_OVERWORLD_COURSE_FLAG`, `P2_OVERWORLD_COURSE_REGISTERED`,
  `P2_OVERWORLD_BOOT_FLAG_WINDOW`, `P2_OVERWORLD_COURSE_OBSERVED`,
  `PASS OVERWORLD_BOOT_FLAG`; `P2_FIXTURE_CAPTAIN_DOWN` + exit 86 on any
  captain-down signal. `--allow-unguarded` and missing/unknown course
  exit 2 (unguarded runs refused).

## Adapter (owned)

- `experimental/pikmin2_overworld_course_boot_flag.py`: course-record
  validation, utf-8/utf-16 run-log reader, honest six-gate evaluator
  (PASS only on observed markers; BLOCKED only on CAPTAIN_DOWN or
  nonzero exit; else UNTESTED).
- `tests/test_pikmin2_overworld_course_boot_flag.py`: focused tests.

## Captain safety #632

Guard predicate vendored verbatim semantics from
`scripts/p2_fixture_captain_guard.h` sha256
`d2f678c9eda75e151eb534077dff9e30ad36ae4796881d971bbd09945f3c3474`
(orimaDead / deadState / HP<=1 checked before every observed tick).
Captain parked by the preview-room spawn; no blanket invincibility.

## Serialized follow-on (NOT in this slice)

`pc_bbft_init` argv wiring plus `pc_bbft.h` declaration and CMake
membership land only after staged scope `challenge-pc-bbft-followon`
(#755), via #186 review + integrator. This slice never edits
`native/pc_port/pc_bbft.cpp`, `native/pc_port/pc_bbft.h` or
`native/CMakeLists.txt`. No ADMIT, no ledger writes.

## Run evidence

Recorded in the lane out dir: native commits, exe SHA-256, log SHA-256,
ninja -n dry run, guard hash. Six gates start UNTESTED; only observed
markers are claimed.
