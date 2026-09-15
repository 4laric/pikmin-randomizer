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
