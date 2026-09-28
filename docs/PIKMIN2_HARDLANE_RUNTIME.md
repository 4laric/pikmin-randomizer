# Hard-lane runtime validation (#244 / #446)

Runtime validation of the reconciled hard-lane batch on the maintained-line
native source that this candidate mirrors.

Implementation owner: Codex via shared account `4laric`. Executing session:
opencode (deepseek-v4.1-flash), 2026-09-13.

Source native branch `opencode/p2-longlegs-fsm`:
- base `f9e139d8` (`codex/pikmin2-room-preview`, maintained line)
- head `5853bce4` (adds the lane-25/26/27 policy modules and a 960x540 fixture
  default; `tools/p2_bombsarai_runtime.cpp` now calls `pc_window_center()`)

## 1. Production room host loads the seam

- Binary: `output/native-lane26/build-fsm/bin/nectar.exe`, SHA-256
  `83b319a15a619d351a830f5ba847e6bcdb98efa3e35284d5c3e41806fd2b0cef`.
- Run: `output/p2-lane27-bombsarai-run` (`nectar.exe --experimental-pikmin2-room`,
  960×540, 35 s capture).
- Markers:
  - `[PC Port] Experimental preview window set to 960x540 windowed and centered`
  - `P2_BOMBSARAI_ARENA_READY pinned=1 fsm=1 no_ai=1 no_visual_assets=1 receivers=4 pool=2 events=0`
  - `P2_HARDLANES_READY family=BombSarai arena=1`
  - `P2_BOMBSARAI_ARENA_DRAW debug_markers_only no_visual_assets=1`

This proves the reconciled hard-lane seam registers and runs inside the standard
maintained-line executable with the mandatory centred 960×540 window.

## 2. Replacement-main behavior fixture passes three scenarios

- Fixture source `tools/p2_bombsarai_runtime.cpp` built by
  `scripts/build_pikmin2_fixture.py` against `output/native-lane26-build-abs`
  (absolute-compiler Ninja/Release/MinGW, JAudio ON) at native head `5853bce4`;
  provenance status `built`.
- Fixture executable SHA-256
  `75272228c5d0fba60c141857be3be8ea7c07aa7595d8701bfa8d2620650afdc2`;
  exit 0; window log `SDL2 Window & OpenGL Context initialized successfully (960x540)`.
- Run: `output/p2-lane27-bombsarai-run/capture-fixture-960/native.log`,
  SHA-256 `905FEE42DE1D937E47461108D7D5A94C8CA18159433720F00242A610F0B4E2F9`.
- Results:

| Scenario | Throw | Blast | carrier_dead | Result |
|---|---|---|---|---|
| approach | `Release` tick 46 | ticks=105 traces=10 floors=1 hits=3 | 0 | `P2_BOMBSARAI_SCENARIO_PASS` |
| purple | `Fall` tick 55 | ticks=118 traces=18 floors=0 hits=3 | 0 | `P2_BOMBSARAI_SCENARIO_PASS` |
| death | `Death` tick 45 | ticks=101 traces=6 floors=1 hits=3 | 1 | `P2_BOMBSARAI_SCENARIO_PASS` |

Blast hits route to receiver ids 501 (teki, 500 self), 502 (navi, 10), 503
(piki, 10).

## Limits

- The behavior run is the lane's replacement-main harness, not an ordinary
  spawned BombSarai in a normal encounter. Ordinary actor registration remains
  lane 27 work.
- `no_visual_assets=1`: the BombSarai visual bank/`kamu_jnt1` is still #128-gated.
- The room-host run emits setup/registration markers only; the scenario markers
  come from the fixture above.

## Fixture baseline adoption

| Field | Value |
|---|---|
| Root/native revision | native `opencode/p2-longlegs-fsm` @ `5853bce4` (base `f9e139d8`) |
| Private builds | `output/native-lane26-build-abs` (`pikmin_pc`), fixture via `build_pikmin2_fixture.py` |
| Window | 960×540; log line `...initialized successfully (960x540)`; fixture calls `pc_window_center()` |
| Squad | BombSarai arena profile (custom runner; no overlay squad needed for the pinned carrier harness) |
| Executables | `nectar.exe` `83b319a1…`; `fixture.exe` `75272228…` |
| Result | 3/3 scenarios PASS; hard-lane seam registered in the standard binary |
