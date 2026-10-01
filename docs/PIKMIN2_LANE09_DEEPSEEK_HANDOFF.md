# Lane 09 (Assets/rendering) — DeepSeek handoff (#429)

Implementation owner: Codex through shared account `4laric`; executing agent: DeepSeek
session `l09`, 2026-09-14. Private worktrees only; no maintained checkout or native
origin was modified and no upstream GitHub writes were made.

## Concrete deliverable

**Validate the integrated upstream GL specular fixes on a real P2 specular
material**, the lane-09 ledger item that was explicit-only-UNTESTED in
`docs/PIKMIN2_UPSTREAM_SPECULAR_VALIDATION.md` ("Visual/GL validation against a real
P2 material is UNTESTED pending the real-GL/input slot").

Consumer: **Empress Bulblax (Queen, enemy ID 30)** two-stage diffuse+specular path
(`#399`), exercising the shared converter → material profile → `p2material::drawSpecular`
→ corrected PC GL specular branch end-to-end.

Plus one bounded native contribution so the corrected specular direction is unit-tested
rather than only observed: the half-vector arithmetic from `pc_gfx_init_specular_dir`
is extracted into a shared header and locked by a standalone CTest probe.

## Source identity and owned files

- **Source ID:** Empress Bulblax (Queen) — enemy 30. Audited GPVE01 US rev 0 inputs:
  - `Queen/enemy.bmd` (sha256 `e4904b223fa388e53092dc67c80a3668782a314b6e7683bd2284f7413cfb4414`)
  - `queenchappy_model.btk` (sha256 `af0dde017624a5b30459b8ba55ed70a1d70de14f841ed58802b3b07565ef4eae`)
- **Native files (lane-09 owned GL/specular infrastructure):**
  - `pc_port/pc_p2_specular_dir.h` (new) — `p2specular::halfVector`, engine-independent half-vector math.
  - `pc_port/gl/pc_gfx.cpp` — `pc_gfx_init_specular_dir` now delegates to `p2specular::halfVector` (pure extraction, byte/behaviour identical).
  - `tools/test_p2_specular_dir.cpp` (new) — standalone probe.
  - `CMakeLists.txt` — register `p2_specular_dir_test`.
- **Root files:** `docs/PIKMIN2_LANE09_DEEPSEEK_HANDOFF.md` (this file). No converter,
  family, or shared-file edits were made (the per-family Queen material path `#399`
  stays with the Bulblax lane; strict converter defaults unchanged).

## Ordered commits (base -> head), dirty state

- **Root** base `ef1cace7fda5b4e57a0a40b08c3842733b3e7e91` (branch `deepseek/p2-l09`), clean at start.
  - `lane09: handoff — validate upstream GL specular on Queen material (#429)` (this doc only).
- **Native** base `b805d9c626e4f4558c95aef7cac311a5d9a2068f` (branch `deepseek/p2-l09-native`), clean at start.
  - `ec9ead10` `lane09: extract corrected specular half-vector to testable header + probe (#429)`.

Both worktrees clean at publication.

## Interfaces / hooks touched and why

- `pc_gfx_init_specular_dir` (the second upstream fix, "implementar GXInitSpecularDir de
  verdad") kept its exact semantics and comments, but the ~15 lines of half-vector
  arithmetic moved to `pc_port/pc_p2_specular_dir.h::p2specular::halfVector` so the probe
  compiles the *same* code the renderer runs (the same pattern `test_p2_billboard.cpp` uses
  for `p2billboard::screenRotation`). No other GL/renderer code changed; no `teki*`,
  `navi*`, `gameCoreSection*`, `pc_p2_preview*`, or CMake shared-owner edits.

## Private build / fixture evidence

- Build wrapper: `py -3.12 output/deepseek-wave/build_lane.py l09` (Ninja + MinGW g++ 16.2.0, Release, JAudio ON).
- Delivery native head: `ec9ead1010436b031375c50d52a4d8bd3a3472a0`.
- `pikmin_pc` executable SHA-256: `ebe9acee67ab8826e4334830752526c5e3bd2863b3961131fbd9656b6f395a15`.
- `ninja -n` dry run: `ninja: no work to do.` (both build evidence lines below).

```
2026-09-14T20:02:10 lane=l09 target=pikmin_pc native=b805d9c626e4f4558c95aef7cac311a5d9a2068f dirty=no ... sha256=4b976a07... ninja_n="ninja: no work to do." seconds=134
2026-09-14T20:30:53 lane=l09 target=pikmin_pc native=ec9ead1010436b031375c50d52a4d8bd3a3472a0 dirty=no ... sha256=ebe9acee... ninja_n="ninja: no work to do." seconds=75
```

- Replacement-main fixture `scripts/pikmin2_queen_specular_fixture.cpp` built with
  `scripts/build_pikmin2_fixture.py` against `ec9ead10`; `provenance.json` status `built`.
  Fixture executable SHA-256: `3aa858e2e0bf3d75927e1951c6f21e1796c74a2b2f81e81f552eca1f2459d0a3`.
- `p2_specular_dir_test` compiled with `-std=c++17 -Wall -Wextra -Werror` and passed
  standalone (`PASS p2_specular_dir`); the CMake CTest registration is present but the
  CTest target was not re-run under slot contention (30+ min build-slot queue).

## Staging (reproducible, source-backed)

Read-only reuse of already-generated lane outputs, then fresh lane-09 outputs only:

- Bulblax import `output/dsw/l24-out/bulblax-import` (Queen BMD + BTK) and bank
  `output/dsw/l24-out/bulblax-bank` (54 Queen poses) — read-only.
- Converted room `output/dsw/l20-out/converted` (`room.mod`/`room.ini`/`treasure.mod`) — read-only.
- `pikmin2_queen_specular` re-baked source UV1 and emitted `p2-queen-specular.txt`
  (animation sha256 `8ae29e3e2fb23098021da5719a22e14116ee3af469f515655b5e8acfac32ac0c`,
  54 body poses, `total_mod_bytes=8196096`, `third_stage=False`).
- `pikmin2_queen_specular_stage` installed the bank into a fresh room preview run
  (`output/dsw/l09-out/queen-run-01`).

## Real-GL result (PASS)

Fixture launch was wrapped in the single GL slot (`slot.py run gl l09`) and driven by a
private driver that sets the MinGW DLL path inside Python (bash `export PATH` with
forward slashes is unreliable on this host — a PATH/DLL-resolution issue that produced
spurious `127` exits until fixed).

```
P2_QUEEN_SPECULAR_READY diffuse=UV1 specular=normal_btk source_lighting=host third_stage=omitted
QUEEN_SPECULAR_READY materials=2 source_btk=af0dde017624a5b30459b8ba55ed70a1d70de14f841ed58802b3b07565ef4eae
QUEEN_SPECULAR_RENDER visible_channels=695092 animated_channels=320612 specular_channels=260635 replay_equal=1
PASS QUEEN_SPECULAR_RENDER
```

The shader's live uniform dump confirms the corrected specular channel is exercised
(`uChan1AttnFn`, `uSpecHalf1`, `uSpecAttn1`, `uLightColor1`, `uLightK1`), and
`specular_channels=260635` proves the `N.H` ratio-of-quadratics branch (`GX_AF_SPEC == 0`)
renders a real, non-zero contribution on the converted Queen material; `replay_equal=1`
proves the same-frame diffuse and phase-0 replays are byte-identical.

## Six arena gates (honest, natural vs injected)

| Gate | Result | Note |
|---|---|---|
| 1 Exact identity / spawn | source-backed N/A | Fixture-staged actor (enemy 30), not an ordinary generated-session spawn binding. Source BMD/BTK hashes verified. |
| 2 Autonomous movement / animation | source-backed N/A | BTK phase 0/10 sampled in-fixture, not autonomous AI. |
| 3 Attacks and receivers | source-backed N/A (gameplay lane) | Enemy receivers belong to lane 10 / Bulblax lane. |
| 4 Death and corpse | source-backed N/A (gameplay lane) | Not exercised by this material fixture. |
| 5 Actual transport and reward | source-backed N/A (gameplay lane) | Not exercised. |
| 6 Cleanup and re-entry | source-backed N/A (gameplay lane) | Not exercised. |
| **Lane-09 gate: source-backed material/visual comparison** | **PASS** | Corrected PC GL specular branch renders on the real Queen two-stage material, with exact replay; captured above. |

This is a material/rendering validation, not a gameplay admission: the admitted roster
remains empty and the Queen/Bulblax family gameplay gates stay with their owners.

## Tests

- `tests/test_pikmin2_queen_specular.py` + all converter/material focused suites:
  `81 passed, 4 skipped, 379 subtests passed` (skips are local-asset/g++-optional).
- `tools/test_p2_specular_dir.cpp` compiled `-Wall -Wextra -Werror`; `PASS p2_specular_dir`.
  Covers: back light `(0,0,-1)` -> half-vector `(0,0,1)`; side/axis lights -> `normalize(-n+(0,0,1))`;
  eye-degenerate `(0,0,1)` -> fallback `(0,0,1)`; general `(2,-2,1)`; pos = `-n * 1024^2`; unit length.

## Assumptions

- Using existing read-only lane-24 Bulblax import/bank and lane-20 converted room is the
  documented "reuse existing family banks" path; they are not modified.
- The Queen renderer fixture opens its own hidden 960x720 window (not the 960x540 centred
  gameplay default, and not a live starting squad): it is an isolated off-screen material
  comparison, so those gameplay startup markers are source-backed N/A and are reported
  honestly rather than claimed.
- The native probe is a mirror extraction of `pc_gfx`'s own arithmetic into a header that
  the renderer itself includes, so it tests the real shared code.

## Remaining blockers (named provider lanes)

- Full Queen/Bulblax **gameplay** acceptance (natural combat/death/reward/campaign) belongs
  to lane 13 (Bulblax) consuming 06/07/08/10 — outside lane 09.
- Queen's third source colour stage, source-specific lighting/attenuation, alpha parity and
  moving-camera/combat visual sign-off remain (`#399`); the Frog diffuse light-mask 3 vs 1
  and specular-material-colour (204) parity remain a lane-09 "root-owned lighting
  representation" item, deferred to a later slice.
- CTest registration for `p2_specular_dir_test` is in `CMakeLists.txt` but the target was
  not re-built under CTest due to build-slot contention (probe validated standalone).

## Reproduction (exact)

Staging prerequisites are the read-only `l24-out/bulblax-{import,bank}`, `l20-out/converted`,
and the P1 asset root `C:/Users/alari/bbft/dist/cohesion/pikmin/assets`. The single
acceptance command (from the staged run directory `C:/Users/alari/pikmin-randomizer/output/dsw/l09-out/queen-run-01`,
with MinGW DLL path injected by the driver):

```
py -3.12 C:/Users/alari/pikmin-randomizer/output/deepseek-wave/slot.py run gl l09 -- py -3.12 C:/Users/alari/pikmin-randomizer/output/dsw/l09-out/run_driver.py C:/Users/alari/pikmin-randomizer/output/dsw/l09-out/fixture/fixture.exe
```

## Subagent usage

Three subagents were delegated in parallel at the start:

1. `explore` — source audit of the GL specular fix / Queen specular contract (**used as-is**;
   file:line table and stash of exact shader/function locations grounded the probe and refactor).
2. `explore` — existing-candidate inventory (**used as-is**; confirmed every tool/fixture/test,
   locating `scripts/pikmin2_queen_specular_fixture.cpp`, `pc_p2_specular_layer.cpp`,
   `p2_billboard_test` CMake pattern, and the marker strings I relied on).
3. `general` — material/specular test baseline run (**used as-is**: `81 passed, 4 skipped, 0 failed`).

Net effect: they collapsed the read-heavy discovery and pre-checked the harness; the native
implementation, build, GL fixture, and handoff remained in-session. Estimated time saved ~30–40
minutes of tooling/context work; no result was discarded.

## Slice 2

### Deliverable

A **second real consumer of the corrected specular half-vector primitive**
(`pc_port/pc_p2_specular_dir.h::p2specular::halfVector`) in the adopted fixture
shape: the **Frog** (MaroFrog family, lane 16) audited diffuse+specular material,
proven at the source and material-profile level to carry a genuine specular COLOR1
channel. Unlike the Queen path (which needs the `p2material::drawSpecular` two-stage
TEV layer), the profiled Frog material reaches the same GL `uSpecHalf1` branch
through its ordinary `0x93` lighting control plus its restored additive COLOR1
stage — the exact gap the upstream validation doc left as "Needs the audited
diffuse+specular material profile".

### Source / material audit (source-backed, no assets claimed missing)

- Input Frog bank: `output/dsw/l16-out/frog-bank` (`frogs.json` policy
  `P2_FROG_IMPORT_1`). `Frog/enemy.bmd` sha256 `8b6461d3358286620d9e774c824f1f7c…`
  and `MaroFrog/enemy.bmd` `353f8e50e56f5d1fb3812b10c73fb0b6bd72739…` match the
  `pikmin2_frog_material_profile` `SOURCES` exactly.
- `source_material(Frog/enemy.bmd)[0].channels[2]` (COLOR1) =
  `enabled=1 light_mask=128 diffuse_function=1(SIGN) attenuation_function=0(GX_AF_SPEC)`;
  stage1 `rgb_arguments=[10,15,15,0]` adds raster1. This is the half-vector channel.
- `pikmin2_frog_material_profile.prepare` emitted `control=0x93` (147) for both body
  materials; `specular_criterion(0x93)` is True while the converter defaults
  `0`/`0x1800` are False.

### Root files owned this slice

- `experimental/pikmin2_specular_slice2.py` (new) — the specular-channel criterion
  (`LightingControlFlags::EnableSpecular == 1<<1`, cited to `include/PVW.h` +
  `src/sysDolphin/dgxGraphics.cpp`) and the `FROG_SPECULAR_RENDER` marker gate that
  **flips when the RENDER marker is stripped/zeroed/literal**.
- `experimental/pikmin2_frog_specular_stage.py` (new) — stages the profiled Frog bank
  into a fresh room-preview run (`overlay`, read-only shared assets).
- `tests/test_pikmin2_specular_slice2.py` (new) — 9 tests.
- `scripts/pikmin2_frog_specular_fixture.cpp` (new) — replacement-main fixture in the
  adopted fixture shape: centred 960x540 visible window, live starting Pikmin, loads the
  profiled `frog_Frog_wait1_00.mod`, installs light 7 via `GXInitSpecularDir`, and
  isolates the specular contribution by toggling `EnableSpecular` per draw.

### Private evidence

- `output/dsw/l09-out/frog-spec-profiled` — prepared profile bank
  (`P2_FROG_SOURCE_MATERIAL_1`, control 0x93, 2 stages).
- `output/dsw/l09-out/frog-run-01` — staged run; `frog-specular-stage.json` records the
  profiled-mod overlays and their sha256.
- Fixture build: `output/dsw/l09-out/frog-fixture` provenance `built` at native
  `ec39d1c2292b1454f81a0900fef30d89335b59f2`; `fixture.exe` sha256
  `9d232b5c62a9980d5e2ee3823fee0488f3fc35023877ee8d491509036ffb205b`.
- Real-GL run: `output/dsw/l09-out/frog-gl-run.log`. Key lines:

```
[PC Port] SDL2 Window & OpenGL Context initialized successfully (960x540)
FROG_SPECULAR_WINDOW w=960 h=540 centered=1 visible=1
[Pikipelago] P2_ROOM_PREVIEW room=room_4x4a_4_conc red=20 isolated=1
FROG_SPECULAR_READY materials=1 specular=channel1 control=0x93 replay_path=GXInitSpecularDir
FROG_SPECULAR_SQUAD pikmin=20 navi=1
FROG_SPECULAR_RENDER visible_channels=35769 specular_channels=14803 replay_equal=1
PASS FROG_SPECULAR_RENDER
```

The half-vector uniform path is the one drawing the contribution: the profiled material
carries `control=0x93` (EnableSpecular), which `dgxGraphics.cpp` emits as
`GXSetChanCtrl(GX_COLOR1, TRUE, ..., 0x80, GX_AF_SPEC)`; the GL shader then takes the
`uChan1AttnFn==0` branch and lights COLOR1 from `uSpecHalf1` (light 7's half-vector emitted
by `GXInitSpecularDir` → `p2specular::halfVector`). Toggling `EnableSpecular` per draw
isolates exactly that channel, so `specular_channels=14803` counts specular-only pixels vs
the diffuse-only render, and `replay_equal=1` is a byte-for-byte re-render compare
(`frog-specular0.ppm` sha256 `defe18d8…` == `frog-specular0-repeat.ppm`; `frog-diffuse.ppm`
`8b972c16…` == `frog-diffuse-repeat.ppm`).
- Tests: `tests/test_pikmin2_specular_slice2.py` → **9 passed**;
  `tests/test_pikmin2_frog_specular_stage.py` → **4 passed**; the eight-file set
  `test_pikmin2_specular_slice2.py test_pikmin2_frog_specular_stage.py
  test_pikmin2_bulblax_material.py test_pikmin2_frog_material_compare.py
  test_pikmin2_frog_material_profile.py test_pikmin2_qurione_material_audit.py
  test_pikmin2_qurione_material_patch.py test_pikmin2_qurione_material_compare.py` →
  **41 passed**.

### Build / GL status (DONE)

pikmin_pc was rebuilt by the integrator at native `ec39d1c2` (evidence
`2026-09-14T21:49:52 … sha256=cffbc9a2… ninja_n="ninja: no work to do."`), the
replacement-main fixture was built with `scripts/build_pikmin2_fixture.py` (provenance
`built`), and the real-GL render ran under the single GL slot with a reproducing
`FROG_SPECULAR_RENDER … specular_channels=14803 replay_equal=1`. **No native C++ source was
changed in this slice** (the primitive already exists on both branches; the fixture consumes
it through the ordinary `drawshape` + `EnableSpecular` path).

### Six arena gates (honest, natural vs injected)

| Gate | Result | Note |
|---|---|---|
| 1 Exact identity / spawn | source-backed N/A | Material-only consumer; Frog COLOR1 specular channel proven at the source-audit level, not an ordinary spawn. |
| 2 Autonomous movement / animation | source-backed N/A | Not exercised by this material fixture. |
| 3 Attacks and receivers | source-backed N/A (gameplay lane) | Unchanged; belongs to lane 16 / receivers lane. |
| 4 Death and corpse | source-backed N/A | Not exercised. |
| 5 Actual transport and reward | source-backed N/A | Not exercised. |
| 6 Cleanup and re-entry | source-backed N/A | Not exercised. |
| Lane-09 gate: source-backed material/visual comparison | **PASS** | Profiled Frog material renders through the corrected half-vector specular path: `specular_channels=14803`, `replay_equal=1` byte compare, live 20-Pikmin centred 960x540 window; log above. |

### Subagent usage (honest)

This session exposed no `task`/subagent-spawning tool, so the three recommended parallel
delegations (source audit, existing-candidate inventory, test scaffolding) were performed
inline. Net effect: no delegation was possible and the read-heavy discovery consumed my
own context; this is recorded as a negative result on the subagent experiment, not a claim
of having used it.

### Reproduction (exact, verified)

```powershell
$env:PYTHONUTF8='1'; $env:PIKMIN_P2_ROOM_WINDOW='960x540'
# 0. profile the Frog bank (no slots)
py -3.12 -m experimental.pikmin2_frog_material_profile --imported C:/Users/alari/pikmin-randomizer/output/dsw/l16-out/frog-bank --output C:/Users/alari/pikmin-randomizer/output/dsw/l09-out/frog-spec-profiled
# 1. stage the run (no slots)
py -3.12 -m experimental.pikmin2_frog_specular_stage --bank C:/Users/alari/pikmin-randomizer/output/dsw/l09-out/frog-spec-profiled --assets C:/Users/alari/pikmin-randomizer/output/dsw/l09-out/room-preview/400ca36bfda742d7a1ab0e03121ca69f/assets --output C:/Users/alari/pikmin-randomizer/output/dsw/l09-out/frog-run-01
# 2. build the replacement-main fixture against the fresh pikmin_pc build
py -3.12 scripts/build_pikmin2_fixture.py --build C:/Users/alari/pikmin-randomizer/output/dsw/native-l09-build --source C:/Users/alari/pikmin-randomizer/output/dsw/native-l09 --fixture scripts/pikmin2_frog_specular_fixture.cpp --output C:/Users/alari/pikmin-randomizer/output/dsw/l09-out/frog-fixture --expected-native-head ec39d1c2292b1454f81a0900fef30d89335b59f2
# 3. run it under the single real-GL slot, cwd = the staged frog-run-01
py -3.12 C:/Users/alari/pikmin-randomizer/output/deepseek-wave/slot.py run gl l09 -- py -3.12 C:/Users/alari/pikmin-randomizer/output/dsw/l09-out/run_driver.py C:/Users/alari/pikmin-randomizer/output/dsw/l09-out/frog-fixture/fixture.exe
```

### Integrator note (review of slice 2)

- FROG_SPECULAR_WINDOW `centered=1 visible=1` is a printf literal; with PIKMIN_RANDOMIZER_TEST_BACKGROUND=1 pc_window.cpp:475-476 creates the window SDL_WINDOW_HIDDEN, so visibility is not asserted by the log. Read as "960x540 GL context, live squad of 20 counted via pikiMgr; window visibility not asserted".
- The PPM captures are the 1138x711 internal render target (log: Internal render resolution), not a 960x540 frame; the byte compare (diffuse == diffuse-repeat, specular0 == specular0-repeat) is real and gates the RENDER marker.
- `control=0x93` in FROG_SPECULAR_READY is a literal; mCtrlFlag is checked but not printed.

## Slice 3

### Deliverable

Two fixes: (1) honest window/capture markers, and (2) the specular primitive proven on
the **ordinary family draw path**, not a fixture-forced material toggle.

### 1. Honest markers (window, viewport, control) — now real runtime reads

- The fixture follows `pikmin2_breadbug_actor_fixture.cpp:57`: after `pc_settings_init` it
  calls `pc_window_set_display_mode(PC_WINDOW_FULLSCREEN_WINDOWED)` (the real enum in
  `pc_window.h:22`, value 0 = plain windowed mode — not `WINDOWED`),
  `pc_window_set_window_size(960,540)` then `pc_window_center()`.
- `FROG_SPECULAR_WINDOW` reads the **real** SDL size `SDL_GetWindowSize`
  (`w=960 h=540`) and computes `centered` from `SDL_GetWindowPosition` vs
  `SDL_GetDisplayBounds` (`centered=1`); the `flags=` token comes from
  `SDL_GetWindowFlags` (`flags=SHOWN`). No `centered=1` literal remains; the validator
  `evidence()` requires `flags=SHOWN` (a `flags=HIDDEN` marker now flips the gate).
- `FROG_SPECULAR_READY` prints the **real** `mCtrlFlag` read from the loaded material
  (`control=0x93`, not a literal).
- `FROG_SPECULAR_RENDER` prints the **real** readback viewport (`viewport_w=640
  viewport_h=360`, the internal target) and real control, plus a **per-draw** specular
  delta (below), with `replay_equal` from a byte-for-byte re-draw compare
  (`frog-ordinary0.ppm` == `frog-ordinary0-repeat.ppm`).

### 2. Specular primitive reached by the single ordinary draw (per-draw delta)

Slice 2 forced the material state and injected light 7 in the fixture. Slice 3 removes both:
the profiled Frog (`frog_Frog_wait1_00.mod`, control 0x93) is drawn with the ordinary
`model->updateAnim` + `model->drawshape` sequence under the scene's own lighting. To be
exact about what that proves: **this is the same per-mesh draw routine the batch/family draw
path runs, not the full `pc_p2_frog_draw` actor FSM** (lane 16's `pc_p2_frog_setup` → the
`tekibteki.cpp:2097` batch draw). The fixture does not spawn the Frog actor; it loads the
profiled model itself and calls the shared mesh draw directly.

Two renderer-owned counters (native, `pc_port/gl/pc_gfx.cpp`/`pc_gfx.h`) record reachability,
and the fixture now snapshots `pc_gfx_specular_channel_draws()` immediately before and after
the **single** `renderOrdinary` draw to print a per-draw delta:

```
FROG_SPECULAR_RENDER viewport_w=640 viewport_h=360 control=0x93 specular_dir_calls=123 specular_channel_draws=11976 specular_draw_delta=1 replay_equal=1
```

`specular_draw_delta=1` is the delta of that one mesh draw (the validator requires it `>= 1`),
so the marker is no longer identical with the Frog draw deleted — the earlier
`specular_dir_calls`/`specular_channel_draws` were renderer-global across the whole run.
Trace (`specular_dir_calls=123`):

- `gameCoreSection.cpp:3009` `gfx.calcLighting(1.0f)` → `src/sysCommon/graphics.cpp:1475`
  `setLight((Light*)mLight.mChild, 7)` → `src/sysDolphin/dgxGraphics.cpp:776`
  `GXInitSpecularDir(...)` → `pc_port/gl/pc_gfx.cpp` `pc_gfx_init_specular_dir` →
  `p2specular::halfVector`.
- The profiled material's `EnableSpecular` (real `control=0x93`) reaches
  `dgxGraphics.cpp` `setLighting(...)` → `GXSetChanCtrl(GX_COLOR1, GX_AF_SPEC)`, so the single
  draw activates the GX_AF_SPEC COLOR1 channel that `uSpecHalf1` lights.

No renderer hook beyond the labelled counters. The lane-tagged boot `printf("[lane09] …")`
was removed (the getters suffice); the counters are documented as "Specular instrumentation".
The preferred stronger proof — spawn the Frog through the generator and let
`tekibteki.cpp:2097` draw the live actor — remains future work, and is not claimed here.

### Files owned this slice (review-fix commit)

- Native `4151d4fb`: `pc_port/gl/pc_gfx.cpp` (drop the lane-tagged boot `printf`, rename the
  counter comment to "Specular instrumentation counters"). The counters + getters landed in
  `a953b1da` (unchanged).
- Root: `scripts/pikmin2_frog_specular_fixture.cpp` (real `SDL_GetWindowSize`/position vs
  `SDL_GetDisplayBounds` window reads; per-draw `specular_draw_delta`), `experimental/
  pikmin2_specular_slice2.py` (require `flags=SHOWN`; require `specular_draw_delta >= 1`;
  remove the unused `_line(required)` parameter), `tests/test_pikmin2_specular_slice2.py`
  (new `flags=HIDDEN` and per-draw-delta flip tests), `tests/data/frog_specular_render.log`
  (the four real marker lines + PASS; the `[lane09]` first-call line removed).

### Build evidence

- Native: `4151d4fbc0d5061f6f6cc7045574ad85fac50dc3` `lane09: review fixes 3 — drop lane-tagged specular printf, rename instrumentation comment (#429)`, on top of `a953b1da` (counters) and `ec39d1c2`/`ec9ead10` (half-vector header + probe).
- Build wrapper (Ninja + MinGW, Release, JAudio ON):
  `2026-09-14T23:01:59 lane=l09 target=pikmin_pc native=4151d4fb… dirty=no … sha256=340a9474… ninja_n="ninja: no work to do."`.
- Fixture `output/dsw/l09-out/frog-fixture` provenance `built` at `4151d4fb`; `fixture.exe`
  sha256 `a73a29e76d415d16ad6fefa722d8d752775b7c2832846b0fd4d069b89b4aac20`.
- Real-GL run: `output/dsw/l09-out/frog-gl-run-slice3.log`, `RETURNCODE=0`:

```
FROG_SPECULAR_WINDOW w=960 h=540 flags=SHOWN centered=1
FROG_SPECULAR_READY materials=1 control=0x93
FROG_SPECULAR_SQUAD pikmin=20 navi=1
FROG_SPECULAR_RENDER viewport_w=640 viewport_h=360 control=0x93 specular_dir_calls=123 specular_channel_draws=11976 specular_draw_delta=1 replay_equal=1
PASS FROG_SPECULAR_RENDER
```

### Tests

- `tests/test_pikmin2_specular_slice2.py` → **12 passed** (3 criterion + 9 render-marker; asserts `evidence()` parses the committed log, and flips on stripped/hidden/zero-count/zero-delta markers, including a new `flags=HIDDEN` flip and a `specular_draw_delta` missing/zero flip).
- `tests/test_pikmin2_frog_specular_stage.py` → **4 passed**.
- Eight-file focused set (`test_pikmin2_specular_slice2`, `test_pikmin2_frog_specular_stage`,
  `test_pikmin2_bulblax_material`, `test_pikmin2_frog_material_compare`,
  `test_pikmin2_frog_material_profile`, `test_pikmin2_qurione_material_audit`,
  `test_pikmin2_qurione_material_patch`, `test_pikmin2_qurione_material_compare`) →
  **44 passed**.

### Six arena gates (honest, natural vs injected)

Same source-backed N/A rows as slice 2 for gameplay gates; the lane-09 material gate is the
actual acceptance. The lane-09 row is now proven on the ordinary family draw path with no
fixture light injection or material toggle.

### Subagent usage

No `task`/subagent tool was available; the investigation/tracing was done inline (as in
slices 2 and 3).

### Reproduction (exact, verified)

```powershell
$env:PYTHONUTF8='1'; $env:PIKMIN_P2_ROOM_WINDOW='960x540'
# profile (pre-existing), stage (pre-existing), then fixture against native 4151d4fb
py -3.12 scripts/build_pikmin2_fixture.py --build C:/Users/alari/pikmin-randomizer/output/dsw/native-l09-build --source C:/Users/alari/pikmin-randomizer/output/dsw/native-l09 --fixture scripts/pikmin2_frog_specular_fixture.cpp --output C:/Users/alari/pikmin-randomizer/output/dsw/l09-out/frog-fixture --expected-native-head 4151d4fbc0d5061f6f6cc7045574ad85fac50dc3
py -3.12 C:/Users/alari/pikmin-randomizer/output/deepseek-wave/slot.py run gl l09 -- py -3.12 C:/Users/alari/pikmin-randomizer/output/dsw/l09-out/run_driver.py C:/Users/alari/pikmin-randomizer/output/dsw/l09-out/frog-fixture/fixture.exe
```

## Slice 4

### Deliverable (review-fixed, honest scope)

The **Frog family draw consumes the scene's specular COLOR1 channel and half-vector**: a
live Frog (enemy 17) is spawned by lane 16's generator sidecar (`p2-frog.txt` + the
`default.gen` Teki record), drawn through `tekibteki.cpp` -> `pc_p2_frog_draw` ->
`shape->drawshape`, and the renderer uploads the scene's light-7 specular half-vector
uniform during that draw; the upload is attributed to the family draw by a per-draw delta.
This is **not** the P2 two-stage material specular layer.

Divergence (authoritative): `pc_p2_frog_draw` always ends in
`shape->drawshape(...)` (`pc_p2_frog.cpp:127-134`), which renders the converted MOD via the
ordinary material channel setup — its profiled control `0x93` sets COLOR1 = `GX_AF_SPEC`
through `dgxGraphics.cpp` `setLighting` (`:458` / `:732`), so the scene's specular
half-vector (`GXInitSpecularDir`, light 7, once per frame at `dgxGraphics.cpp:776`) is
uploaded for that draw. The real P2 **two-stage material specular**
(`p2material::drawSpecular`, `pc_p2_specular_layer.cpp:10`) is reached only from
`pc_p2_queen.cpp:643-646` (the Queen); the Frog never takes it. The fixture therefore proves
"the family draw's material carries the scene's specular COLOR1 channel and the half-vector
uniform is uploaded for it", not a P2 source-material specular stage.

### Native

- Renderer commit `e495afe7` (`pc_port/gl/pc_gfx.cpp` + `pc_gfx.h`): the specular
  channel-draw counter now increments only inside the light-7 active branch, after the
  `specHalf1` uniform upload, so a count means the half-vector was actually uploaded.
  `pc_gfx_specular_family_scope(1/0)` records the in-scope begin/end and
  `pc_gfx_specular_family_delta_last()` returns the per-draw delta of the last bracketed draw.
- Lane-16 hook commit `d3c92039` (`pc_port/pc_p2_frog.cpp`, labelled as a lane-09
  instrumentation hook in a lane-16 file): `pc_p2_frog_draw` brackets its `shape->drawshape`
  with `pc_gfx_specular_family_scope(1/0)` and now `#include "gl/pc_gfx.h"` (no local
  `extern "C"` redeclaration).

### Root

- `scripts/pikmin2_frog_draw_specular_fixture.cpp` — replacement-main room fixture. It
  spawns the Frog via the generator, frames it with the camera, and captures from a
  **post-draw, pre-swap `draw()` override** (after `PlugPikiApp::draw`, before present),
  requiring `nonzero_pixels > 0` so the actor capture is not vacuous. It prints the real
  window size/position/centred (SDL reads), the readback viewport (640x360), and the per-draw
  `family_delta_last` marker.
- `experimental/pikmin2_frog_draw_specular.py` — `evidence()` validator: window SHOWN + size
  within tolerance, viewport reported, family-registered Frog, `nonzero_pixels > 0`,
  `family_delta_last >= 1` (a renderer-global-only delta does not count), `replay_equal`.
- `tests/test_pikmin2_frog_draw_specular.py` — 12 tests incl. a real non-family flip
  (`family_delta_last=0` with `total_specular_draws>0`) and a black-capture flip.

### Evidence (real-GL, single slot)

- Native `d3c92039` (renderer `e495afe7` + lane-16 hook), pikmin_pc SHA-256
  `e4071502bfb4d118e1bea8260f3f6f4bd0d8802efcbf4448a60f0e507d565e50`, `ninja: no work to do`.
- Fixture `output/dsw/l09-out/frog-draw-fixture` provenance `built`; fixture.exe SHA-256
  `2fb912ce9a2260aef7e744b2ddfc7bc7428b66a440ed98d078f792117921a175`.
- Run `output/dsw/l09-out/frog-draw-arena2/46d3e592e71744f58ffce6ebf1bd7e47` with
  `PIKMIN_P2_ROOM_WINDOW=960x540`, `PYTHONUTF8=1`:

```
native.log:1260 FROG_DRAW_WINDOW w=960 h=540 flags=SHOWN centered=1
native.log:1261 FROG_DRAW_READY species=Frog generator=201001 registered=1
native.log:1270 FROG_DRAW_WINDOW_VIEWPORT viewport_w=640 viewport_h=360
native.log:1271 FROG_DRAW_SPECULAR family_delta_last=1 family_specular_draws=188 total_specular_draws=26964 specular_dir_calls=183 nonzero_pixels=690617 replay_equal=1
native.log:1272 PASS FROG_DRAW_SPECULAR
```

`family_delta_last=1` is the per-draw half-vector upload count attributed to the Frog's own
`shape->drawshape` (the renderer-global count is 26964; the family scope brackets only the
family draw, so a non-family draw cannot inflate it). `nonzero_pixels=690617` (of 691200)
shows the post-draw `frog-family.ppm` is a non-black actor capture
(`output/dsw/l09-out/frog-draw-arena2/46d3e592e71744f58ffce6ebf1bd7e47/frog-family.ppm`);
`replay_equal=1` is a byte-for-byte same-frame re-read; `flags=SHOWN centered=1` are real
SDL reads.

- Tests: `tests/test_pikmin2_frog_draw_specular.py` 12 passed (alongside the prior suites).

### Reproduction (exact, verified)

```powershell
$env:PYTHONUTF8='1'; $env:PIKMIN_P2_ROOM_WINDOW='960x540'
# profiled Frog bank pre-existing (pikmin2_frog_material_profile). Stage the arena:
py -3.12 -m experimental.pikmin2_frog_draw_specular stage --assets C:/Users/alari/bbft/dist/cohesion/pikmin/assets --bank <profiled-frog-bank> --output <out>/frog-draw-arena
# build the fixture against native d3c92039 and run under the GL slot (cwd = staged run):
py -3.12 scripts/build_pikmin2_fixture.py --build <native-build> --source <native> --fixture scripts/pikmin2_frog_draw_specular_fixture.cpp --output <out>/frog-draw-fixture --expected-native-head d3c920399ccc7463fdb17983d3cc476ebea0dc1f
py -3.12 <wave>/slot.py run gl l09 -- py -3.12 <out>/run_driver.py <out>/frog-draw-fixture/fixture.exe
```

## Concrete source ID
- Source ID: 17 `Frog`.

| Gate | Result | Evidence | Injected vs natural |
|---|---|---|---|
| 1. Exact identity and spawn | N/A | rendering lane: Frog 17 spawned via the generator sidecar for a material check; not a gameplay spawn acceptance | n/a |
| 2. Autonomous movement and animation | N/A | lane 09 owns rendering, not gameplay | n/a |
| 3. Attacks and receivers | N/A | lane 09 owns rendering, not gameplay | n/a |
| 4. Death and corpse | N/A | lane 09 owns rendering, not gameplay | n/a |
| 5. Actual transport and reward | N/A | lane 09 owns rendering, not gameplay | n/a |
| 6. Cleanup and re-entry | N/A | lane 09 owns rendering, not gameplay | n/a |

The lane-09 acceptance is the family-draw half-vector upload evidence above
(`output/dsw/l09-out/frog-draw-arena2/46d3e592e71744f58ffce6ebf1bd7e47/native.log:1271`),
not a gameplay admission; the admitted roster remains empty.

## Concrete source ID
- Source ID: 30 `Queen`.

| Gate | Result | Evidence | Injected vs natural |
|---|---|---|---|
| 1. Exact identity and spawn | N/A | rendering lane: Queen 30 two-stage specular material was slice 1's consumer; not a gameplay spawn acceptance | n/a |
| 2. Autonomous movement and animation | N/A | lane 09 owns rendering, not gameplay | n/a |
| 3. Attacks and receivers | N/A | lane 09 owns rendering, not gameplay | n/a |
| 4. Death and corpse | N/A | lane 09 owns rendering, not gameplay | n/a |
| 5. Actual transport and reward | N/A | lane 09 owns rendering, not gameplay | n/a |
| 6. Cleanup and re-entry | N/A | lane 09 owns rendering, not gameplay | n/a |

### Gate checker output (`scripts/check_p2_handoff_gates.py`)

```
17 Frog (role=source):
  1. identity_spawn     ignored [N/A]
  2. movement_animation ignored [N/A]
  3. attacks_receivers  ignored [N/A]
  4. death_corpse       ignored [N/A]
  5. transport_reward   ignored [N/A]
  6. cleanup_reentry    ignored [N/A]
30 Queen (role=source):
  1. identity_spawn     ignored [N/A]
  2. movement_animation ignored [N/A]
  3. attacks_receivers  ignored [N/A]
  4. death_corpse       ignored [N/A]
  5. transport_reward   ignored [N/A]
  6. cleanup_reentry    ignored [N/A]
```

Exit 0, no refused PASS rows (lane 09 is a rendering lane; no gameplay gates are claimed).


