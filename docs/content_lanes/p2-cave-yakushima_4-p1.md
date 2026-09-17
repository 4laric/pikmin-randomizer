# p2-cave-yakushima_4 P1 floor-1 runtime import (#161)

Lane `shard-caves-yakushima-yakushima4-p1`, generation 3, issue #161 (parent
#531; existing content owner #137). Pins: root `36b86839`, native `a95040b6`.
The generation-2 pin-prerequisite gap is **RESOLVED** by integrating the
accepted prerequisite commits into this private worktree (see below); real
floor-1 unit staging is now observed through the accepted #129 generator.
Outcome: **P1 contract + real unit staging observed; the render/collision
boot with a live guarded squad remains open**. No ADMIT, no false PASS, issue
#161 stays OPEN.

## What is delivered (reserved files only)

- `experimental/content_lanes/p2-cave-yakushima_4_p1.py` ? floor-1 staging and
  observation contract. Consumes the pinned P0 audit packet read-only, selects
  the real floor-1 rows (`2_units_gw_l_conc.txt`, 8 enemy / 2 treasure
  definitions, 0 gates, 2 caps, treasures `baum_kuchen_s` + `chocoichigo`),
  emits the bounds-validated native entry line, probes the required provider
  files, and parses/validates the real `P2_CAVE_READY` / `P2_CAVE_NAV` boot
  markers. Unit staging is never inferred from nav lines.
- `tests/content_lanes/test_p2_cave_yakushima_4_p1.py` ? 14 focused synthetic
  tests (floor selection, pool drift, entry bounds, provider probe, blockers,
  observation positive/negative).
- `docs/content_lanes/p2-cave-yakushima_4-p1.md` ? this contract.
- `native/tools/p2_yakushima4_p1_fixture.cpp` ? engine-independent stdlib-only
  staging writer + boot checker (`-Wall -Wextra -Werror`), never linked into a
  game target.

## Prerequisite resolution (generation 3)

Accepted prerequisite commits were cherry-picked into this lane's private
worktrees only (no shared checkout edits), preserving provenance:

- native: `21caef9a` (cave generator consumer landing, #129) -> `7188454c`.
  Ports the accepted `e44b5d70` `pc_p2_cave_generate.h/.cpp` byte-identical and
  wires the reviewed `pc_p2_cave.cpp` hook + CMake line on baseline `a95040b6`.
- root: `ad4a34e5` (P0 adapter) and `60b8caad` (consumer landing doc).

The provider presence probe from the Python adapter now reports
`native_provider_files_present: true`, so the staging path is executable.

## Original gap this resolves

The generation-2 lane was blocked because the pins lacked:

| Required at pin | State |
|---|---|
| `pc_port/pc_p2_cave_generate.h` / `.cpp` (#129 native provider) | **absent** from native `a95040b6` |
| `experimental/content_lanes/p2-cave-yakushima_4.py` (P0 adapter) | **absent** from root `36b86839` (committed only on `codex/shard-caves-yakushima-y4p0`) |
| native per-floor unit-staging consumer | **absent**: `pc_p2_cave.cpp` consumes a floor entry and emits `P2_CAVE_NAV`, but does not stage cave-decode units |

The #129 provider module exists on the divergent `output/dsw/native-wave` line
(`pc_p2_cave_generate.h`), which is not an ancestor of this lane's native pin.
Consequently no real floor-1 **unit staging** boot can be produced on the
assigned pins without a cross-line integration that is outside the four
reserved files. This is recorded as the exact blocker instead of simulating it.

## Honest status

- Floor selection, entry-manifest emission, provider probe and boot-observation
  validation are implemented and tested (14/14).
- `collision_routes` are only claimed once a real `P2_CAVE_READY floor=1` plus
  a `P2_CAVE_NAV` walk-inside sample exist; none was produced this turn
  (BLOCKED at staging), so the acceptance runtime items are UNTESTED.
- Higher floors, persistence and full-campaign resume remain out of scope;
  #128/#131/#140 and unadmitted encounter species remain OPEN.
- Captain-safety (#632) adoption is recorded for the future run: the fixture
  guard must be present before any observation tick; no protected-invincibility
  claim is made here.

## Exact next dependency

Re-provision this lane on an integrated pin that contains both the #129
`pc_p2_cave_generate` module and the #161 P0 adapter (the P0 adapter commit is
`ad4a34e5` on `codex/shard-caves-yakushima-y4p0`), or authorize a scoped
cross-line integration. Then a leased private engine build with the captain
guard can observe the floor-1 boot and complete the runtime acceptance items.


## Generation 7: guarded runtime fixture integrated (prerequisite #642)

The blocked guarded-boot gap is resolved at the tooling level by integrating the
accepted prerequisite `cave-guarded-runtime-fixture` (#642) into this lane's
private worktrees: native `tools/p2_cave_guarded_boot_fixture.cpp` (real
game-linked replacement-main fixture with the #632 captain guard) and root
`experimental/pikmin2_cave_runtime_inputs.py` + builder/tests/doc.

Verified this turn on lean pins root `a95c9517` / native `555981f0`:

- Private leased build green (`pikmin_pc` exit 0, fixture TU compiled, linked
  82 objects); exe sha256 `a9d82b1f87d0609caf72be6a23dd725d5379296b8c03044851dd6874d201005b`.
- Captain guard (#632) adopted and verified: `--guard-self-test` exit 0
  (`P2_CAVE_GUARDED_SELFTEST_PASS rows=7`); `FORCE_CAPTAIN_DOWN=1` negative run
  exits 86 with `P2_FIXTURE_CAPTAIN_DOWN ... outcome=BLOCKED` and no PASS.
  Canonical header `scripts/p2_fixture_captain_guard.h` sha256
  `d2f678c9...09945f3c3474`, vendored verbatim.
- Input package built with the REAL P0-derived sidecar (not the preset
  placeholder) and validated `INPUTS_PASS`.
- Headed guarded run reached the 960x540 centred window
  (`P2_CAVE_GUARDED_WINDOW size=960x540 ... centered=1`) and GL 3.3, loaded the
  preview generators (default 80, plants 30), then aborted in
  `pc_p2_preview.cpp:128` with `P2 preview: duplicate treasure` BEFORE the cave
  entry could activate. No `P2_CAVE_READY`, no `P2_CAVE_GENERATE_PASS`; all six
  gates UNTESTED.

## Remaining concrete gap (arena data, owner outside this lane)

The preview abort fires because the generic chal0/practice arena exposes more
than one `pr05` treasure and no `p2-cargo.txt` config disambiguates. A headed
cave boot therefore needs a private arena overlay with exactly one `pr05` (or a
valid `p2-cargo.txt`), which is arena/fixture-data provisioning owned by the
fixture-baseline / provider-runtime-fixtures lanes, not by this lane's four
reserved files. Until then the guarded boot cannot reach the cave entry on a
legal arena.


## Generation 8: arena overlay provider integrated; headed boot stalls pre-stage

Integrated the accepted `runtime-fixtures-cave-arena-overlay-pr05` (#654)
provider (commit `722d7951`): the arena overlay input grammar, presence
checker and 26 tests (all pass in my tree) are now available read-only-plus;
no shared files were edited.

Diagnosed the real stall root cause: the raw assets `chal0/default.gen`
carries TWO pr05 rows (both generator_id 0), so the provider prune
(lowest-id keep) fails closed. A positional keep (first row, deterministic,
labelled) stages a single-pr05 overlay (`ecc37c92`, 79 records) into a
private junction overlay tree; input package validates `INPUTS_PASS`.

Two bounded headed guarded runs (150s and 280s) reached the 960x540 centred
window and GL 3.3 with linked shaders, and the duplicate-treasure abort is
GONE ? but the boot stalls silently after texture-filtering init, before any
stage load. No DVD errors, no P2_CAVE_READY, no P2_CAVE_GENERATE_PASS. This is
an engine-internal pre-stage stall outside my four reserved files and outside
every integrated provider. All six gates stay UNTESTED. The exact remaining
gap is a diagnosed engine boot stall, plus the authored yakushima_4 room
graph for a genuine collision claim.


## Generation 10: generic boot blocker CLEARED; real floor-1 guarded boot PASS

Adopted the canonical runner `scripts/run_pikmin2_cave_fixture.py` (#671) and
regenerated this lane's arena with the current 20-Pikmin squad while preserving
the real P0-derived cave sidecar. The generic pre-stage stall was a fixture
construction defect (directory junctions to ordinary files made `consFont.bti`
unreadable), not an engine defect.

Real runtime evidence on the UNCHANGED private executable
`a9d82b1f87d0609caf72be6a23dd725d5379296b8c03044851dd6874d201005b`:

- Positive (`out/laneresult-1`): exit 0, 2.25s, `baseline_smoke_only:false`.
  `P2_CAVE_GUARDED_WINDOW size=960x540 centered=1`; `P2_CAVE_READY floor=1
  survivors=20`; the full real `P2_CAVE_GENERATE_*` staging from the actual
  unit pool `2_units_gw_l_conc.txt` and roster (BlackMan, FireChappy, Tank,
  Hiba x5, Zenmai 9; baum_kuchen_s, chocoichigo); `P2_CAVE_GENERATE_PASS
  rooms=8 spawns=10 links=36 anchor=hole`; `P2_CAVE_GUARDED_ENTRY_READY
  floor=1 observed=1`; `P2_CAVE_GUARDED_BOOT_PASS floor=1 squad_alive=20`;
  `PASS CAVE_GUARDED_BOOT`.
- Negative (`out/lane-negative-1`, `FORCE_CAPTAIN_DOWN=1`): raw exit 86,
  `P2_FIXTURE_CAPTAIN_DOWN`, no boot PASS.
- Arena `2f6fd495...`, entry `28127be7...`, sidecar `aa8f9986...`; guard
  header `d2f678c9...` vendored verbatim.

This clears the generic cave-boot dependency only. It does NOT establish
yakushima_4 authored geometry or collision, higher floors or persistence: no
`P2_CAVE_NAV` route samples were produced, and the staged room graph is the
real unit pool placed at identity, not the authored yakushima_4 room layout.
Those remain the actual outstanding requirements.


## Generation 11: authored yakushima_4 floor-1 geometry integrated (#682)

Integrated the accepted `yakushima4-authored-geometry-native` prerequisite
into private worktrees: native authored room/door/link tables baked into
`pc_p2_cave.cpp` (purely additive) plus the guarded probe fixture
`tools/p2_yakushima4_authored_geometry_fixture.cpp`, and root
`scripts/build_p2_yakushima4_authored_geometry.py`.

Leased harness chain on these pins (native `096f3082`): configure/build
green, fixture provenance `built` (exe sha256
`acb7c34347ea99746814891765550e2d8a2f30186e0783ab778e73de0071d093`),
guard self-test (table matches real decode) and `negcap` negative (exit 86,
`CAPTAIN_DOWN`) pass, and the live run emits the full authored topology:
`P2_YAKUSHIMA4_AUTHORED valid=1 rooms=8 doors=19 links=36` plus all 36
`P2_CAVE_NAV authored=1` route samples with real distances and enemy flags,
diffed against an independent real re-decode of
`user/Mukki/mapunits/caveinfo/yakushima_4.txt` + `2_units_gw_l_conc.txt`
(caveinfo sha256 `3e3fc04e...` matches the P0 pin).

This is a table-level route observation, not a windowed boot: the run emits
41 marker lines and performs no GL/window, squad or collision traversal.
Combined with the generation-10 windowed guarded boot (960x540, live 20,
unit staging), the slice now holds real floor-1 boot, unit staging, and
authored route topology ? but still no physical collision traversal on a
built yakushima_4 map and no `P2_CAVE_NAV` walk-inside samples. Higher
floors, persistence and admission remain open.
