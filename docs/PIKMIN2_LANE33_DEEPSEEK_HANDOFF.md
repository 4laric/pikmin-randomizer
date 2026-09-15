# Lane 33 (Independent QA) — DeepSeek handoff (#444)

Executing agent/session: opencode (deepseek-v4-pro), DeepSeek wave lane 33.
Implementation owner: Codex through shared GitHub account `4laric` (this session
is QA; the integrator posts issue updates). Child issue: #444.

## One concrete deliverable + one missing slice

- **Deliverable (consumer):** the Snow Bulborb + Dwarf Orange Bulborb two-species
  cohort, exercised on the pinned integrated native build
  `b805d9c626e4f4558c95aef7cac311a5d9a2068f`.
- **Missing slice addressed:** "add two-species mixed scene" — reproduced the
  two-identity mixed scene (Snow `5001` + Dwarf Orange `211001` + P1 Chappy
  control `211002`) together with a frame-time measurement, and reproduced the
  first generated-session chain (bootstrap `ENEMY_P2` -> native parse/bind ->
  content stage/cache -> 5 rejection cases) via `scripts/test_p2_generated_session.py`.

No production code was changed. This lane owns QA reports only.

## Source IDs and files owned

- Snow Bulborb = `YellowKochappy` (source id 45), `native_family=Chappy`,
  generator `5001`, native module `pc_port/pc_p2_enemy.cpp` (`pc_p2_snow_*`),
  health policy 150, `behavior=P1`.
- Dwarf Orange Bulborb = `BlueKochappy` (`source_id=44`), generator `211001`
  (+ P1 Chappy control `211002`), native module `pc_port/pc_p2_dwarf_orange.cpp`
  (+ `_policy.h`, FSM `pc_p2_kochappy_fsm.cpp`), health 250, purple stun 5 s,
  `behavior=P1`. Both modules are compiled in and wired at the native baseline.
- Root files added by this slice: `tests/test_pikmin2_qa_cohort_records.py`
  (8 tests), plus this handoff.

## Ordered commits and dirty state

- Root worktree `C:/Users/alari/pikmin-randomizer/output/dsw/l33-root`, branch
  `deepseek/p2-l33`, base/head `ef1cace7fda5b4e57a0a40b08c3842733b3e7e91`.
  Commits:
  1. `lane33: QA cohort-record and matrix-guardrail tests (#444)` —
     `tests/test_pikmin2_qa_cohort_records.py`.
  2. `lane33: independent QA handoff for Snow+DwarfOrange mixed scene (#444)` —
     `docs/PIKMIN2_LANE33_DEEPSEEK_HANDOFF.md`.
- Native worktree `C:/Users/alari/pikmin-randomizer/output/dsw/native-l33`,
  branch `deepseek/p2-l33-native`, base/head
  `b805d9c626e4f4558c95aef7cac311a5d9a2068f`. **No commits, clean** — this lane
  consumed the baseline read-only; no native source was edited.

## Interfaces / hooks touched and why

None. This slice changed no shared files (no `teki.h`, `tekibteki.cpp`,
`tekimgr.cpp`, `pc_p2_preview.cpp`, CMake, etc.). The Snow/Dwarf Orange
identity/health/draw markers and the mixed-scene observer ran against the
already-integrated pin with zero native or root source edits.

## Build evidence (`output/dsw/l33-build-evidence.txt`)

```text
2026-09-14T19:35:11 lane=l33 target=pikmin_pc native=b805d9c626e4f4558c95aef7cac311a5d9a2068f dirty=no build_dir=...\native-l33-build exe=...\bin\nectar.exe sha256=8cfa1e83fb4981d36c7e64c990f69776921cda4c59606679ef94b176a5d42800 ninja_n="ninja: no work to do." seconds=151
2026-09-14T19:43:46 lane=l33 target=pc_randomizer_probe native=b805d9c626e4f4558c95aef7cac311a5d9a2068f dirty=no ... ninja_n="ninja: no work to do." seconds=2
```

- `nectar.exe` SHA-256 `8cfa1e83fb4981d36c7e64c990f69776921cda4c59606679ef94b176a5d42800`.
- `pc_randomizer_probe.exe` SHA-256 `c0dbfcf7daced3a6aef8cbfe6a176ecd1ee3287296f96d3f85827c8039f171c9`
  (the wrapper's evidence line mis-reports `nectar.exe` for the probe target;
  the probe binary is `native-l33-build/pc_randomizer_probe.exe`).
- Mixed-scene instrumented fixture `fixture.exe` SHA-256
  `bab6fdb02d2e14c45c63d4077e45ec2d94b1625e522e3ff097bba22009da3375`,
  provenance `status=built`, native head `b805d9c6`, `Release`.

## Fixture adoption evidence (current baseline)

- Centred 960x540 window: `Experimental preview window set to 960x540 windowed and centered`
  in `.../mixed-run-final/native.log` (with `PIKMIN_P2_ROOM_WINDOW=960x540` set).
- Live starting Pikmin: `P2_MIXED_ARENA_SPAWN teki=3 reds=20`.
- No immediate extinction: `Extinction` absent from the log.
- Arena staged fresh into a new lane-owned output dir using the current
  `preview_pikmin2_room.overlay()` (20-red starting-squad overlay; a private
  mixed-arena observer is the replacement-main fixture, which logs the same
  window/squad/teki markers rather than relying on the env var alone).

## Six arena gates (natural vs injected)

| Gate | Status | Evidence / label |
|---|---|---|
| 1. Exact identity and spawn | **PASS** (fixture) | Natural: `P2_ENEMY_READY species=BlueKochappy source_id=44 ... health=250.0 ... purple_stun=bluekochappy_5s`, `P2_SNOW_POLICY generator=5001 health=150.0` (the READY line carries no health field). Injected: `P2_MIXED_ARENA_BIRTH id=211001/211002/5001` verify stored birth XYZ, health 250/130/150 and display name (Dwarf Orange Bulborb / Snow Bulborb). |
| 2. Autonomous movement and animation | **UNTESTED** (draw-observed bank/draw markers only; not a gameplay PASS per fan-out rules) | Natural: `P2_SNOW_BANK poses=60`, `P2_DWARF_ORANGE_BANK poses=64`, `P2_SNOW_DRAW corpse=0`, `P2_DWARF_ORANGE_DRAW corpse=0`. |
| 3. Attacks and receivers | **UNTESTED** | Not exercised by this fixture. |
| 4. Death and corpse | **UNTESTED** (incidental marker only) | `P2_DWARF_ORANGE_DRAW corpse=1` observed late in the run (Dwarf Orange killed by the free 20-red squad during observation); not a controlled death/receiver gate, Snow never died. |
| 5. Actual transport and reward | **UNTESTED** | Not exercised (lane 06 endpoint). |
| 6. Cleanup and re-entry | **UNTESTED** | Not exercised (no scene exit/re-entry). |

Natural signals are limited to the `P2_ENEMY_READY`/`P2_*_BANK`/`P2_*_DRAW`
native markers; the birth/XYZ/spawn/tick lines are the private observer's
injected instrumentation. This is a fixture-only probe: it does **not** claim a
generated seed, combat, delivery, or re-entry.

Frame-time (measured, not an agreed budget): rolling `[PC tick]` mean 8.83 ms,
p95 8.9 ms vs the native 60 fps 16.7 ms budget, on the 3-Teki engineered arena.

## Generated-session chain

`scripts/test_p2_generated_session.py` against `pc_randomizer_probe.exe` passed:
real seed bootstrap `ENEMY_P2`, native parse/bind, content stage+cache, and 5
rejection cases (unknown-id, wrong-revision, duplicate-target, bad-count,
mixed-P1/P2-layout). Admission is monkeypatched (the live roster admits nothing)
and content is synthetic, so this is product-path **wiring** proof, not a live
admission.

## QA matrix

`experimental.pikmin2_qa_matrix report` over `output/dsw/l33-out/qa-records`
pinned to root `ef1cace7…` / native `b805d9c6…`:
**PASS=2, UNTESTED=76** (BLOCKED=0, FAIL=0, N/A=0). The two fixture-boundary
PASS cells are `install × missing_assets` (generated-session probe) and
`install × frame_budget` (mixed scene). Every natural-required cell remains
UNTESTED because no natural generated-session run was possible (empty roster).

## Tests run and results

```text
py -3.12 -m pytest tests/test_pikmin2_qa_cohort_records.py tests/test_pikmin2_qa_matrix.py tests/test_pikmin2_mixed_bulborb_runtime.py -q
# 46 passed
```

- `test_pikmin2_qa_cohort_records.py` (new, 8 tests) — matrix resolution and
  manifest-import guardrails (fixture cannot satisfy natural cells; mocked
  never passes; missing provenance blocked; FAIL precedence; UNTESTED default).
- `test_pikmin2_qa_matrix.py` (22) and `test_pikmin2_mixed_bulborb_runtime.py`
  (~16) unchanged and green.

## Assumptions

- Reused prior lane-13/cohort prepared assets read-only (Dwarf Orange bank
  `output/p2-dwarf-orange-bank`, profile `output/p2-dwarf-orange-ref`, Snow
  prepared arena `output/p2-cohort-mixed-arena/4a4626c5…`) instead of
  re-extracting from the P2 ISO.
- The native 16.7 ms figure is the 60 fps target, treated as a measurement
  reference, not an agreed production density budget.
- The mixed scene is an engineered three-Teki private fixture arena (zero scatter,
  fixed XYZ); it is not a generated seed and is not reported as one.

## Remaining blockers (named provider lanes)

- **Lane 02 (roster/admission)** and **lane 03 (seed/native bridge)**: the
  admitted roster is still empty, so no ordinary generated `ENEMY_P2`
  target-to-live-actor spawn can be reproduced yet.
- **Lane 01 (integration)** supplies the immutable combined pair plus ordinary
  generated install; **lane 05 (installation)** wires fresh/cached content into
  the generated session; **lane 06 (rewards) / lane 07 (lifetime)** gate natural
  delivery and cleanup/re-entry.

## Subagent usage

- `explore` #1 (source audit): confirmed Snow (`pc_p2_enemy`, health 150, `P2_ENEMY_READY`/`P2_SNOW_DRAW`) and Dwarf Orange (`pc_p2_dwarf_orange`, source_id 44, health 250, 5 s purple stun) are fully integrated at native `b805d9c6`, and that `pc_p2_dwarf_orange` is present. Used as-is; saved a manual grep pass and de-risked the whole slice.
- `explore` #2 (candidate inventory): located the two-species harness `experimental/pikmin2_mixed_bulborb_runtime.py`, the QA-matrix tool, the generated-session probe, and prepared assets `p2-dwarf-orange-bank`/`-ref` + the cohort-mixed Snow arena. Used as-is; directly determined the reproducible command I ran.
- `general` #3 (tests): wrote `tests/test_pikmin2_qa_cohort_records.py` (8 tests) and correctly flagged that `record_from_manifest` keys off `status`, not the runner's `passed` boolean. Used as-is (committed unchanged).

Overall the subagents saved roughly the read/discovery phase (estimated 20-30 min
of manual grepping) and produced one committed artifact; no result was discarded.

## Exact reproduction command

```powershell
# one-time: build + probe + fixture (build slots via the wrapper)
py -3.12 C:/Users/alari/pikmin-randomizer/output/deepseek-wave/build_lane.py l33
py -3.12 C:/Users/alari/pikmin-randomizer/output/deepseek-wave/build_lane.py l33 --target pc_randomizer_probe
cd C:/Users/alari/pikmin-randomizer/output/dsw/l33-root
PYTHONUTF8=1 py -3.12 scripts/test_p2_generated_session.py C:/Users/alari/pikmin-randomizer/output/dsw/native-l33-build/pc_randomizer_probe.exe
py -3.12 -m experimental.pikmin2_mixed_bulborb_runtime build --native C:/Users/alari/pikmin-randomizer/output/dsw/native-l33 --build-dir C:/Users/alari/pikmin-randomizer/output/dsw/native-l33-build --output C:/Users/alari/pikmin-randomizer/output/dsw/l33-out/mixed-fixture --head b805d9c626e4f4558c95aef7cac311a5d9a2068f
py -3.12 -m experimental.pikmin2_mixed_bulborb_runtime prepare --assets C:/Users/alari/bbft/dist/cohesion/pikmin/assets --bank C:/Users/alari/pikmin-randomizer/output/p2-dwarf-orange-bank --profile C:/Users/alari/pikmin-randomizer/output/p2-dwarf-orange-ref --snow C:/Users/alari/pikmin-randomizer/output/p2-cohort-mixed-arena/4a4626c5a6844c4884e4a40224c6caa4 --output C:/Users/alari/pikmin-randomizer/output/dsw/l33-out/mixed-arena

# the one real-GL runtime gate (gl slot + MinGW runtime DLLs on PATH):
$env:PATH='C:\msys64\mingw64\bin;'+$env:PATH
$env:PIKMIN_P2_ROOM_WINDOW='960x540'; $env:PYTHONUTF8='1'
py -3.12 C:/Users/alari/pikmin-randomizer/output/deepseek-wave/slot.py run gl l33 -- py -3.12 -m experimental.pikmin2_mixed_bulborb_runtime run --stage C:/Users/alari/pikmin-randomizer/output/dsw/l33-out/mixed-arena/79cc878179fc4fa8b08ac279fc8b25d4 --exe C:/Users/alari/pikmin-randomizer/output/dsw/l33-out/mixed-fixture/baseline/fixture.exe --output C:/Users/alari/pikmin-randomizer/output/dsw/l33-out/mixed-run-final
```

Review note: `l33-out/mixed-run` holds a failed first attempt (exit 0xC0000135, MinGW DLLs missing from PATH); the cited evidence is `mixed-run-final`. Prepend `C:/msys64/mingw64/bin` to PATH before running. The QA record `gensession-install-missing-assets.json` is `kind=synthetic` (monkeypatched admission + synthetic manifest), so that cell reports BLOCKED, not PASS.
```

Expected: `evidence.json` `passed=true` (13/13 checks), native.log shows centred
960x540 window, `P2_ENEMY_READY species=BlueKochappy source_id=44` and
`species=YellowKochappy`, `P2_MIXED_ARENA_SPAWN teki=3 reds=20`, both
`P2_*_DRAW corpse=0`, no `Extinction`.
