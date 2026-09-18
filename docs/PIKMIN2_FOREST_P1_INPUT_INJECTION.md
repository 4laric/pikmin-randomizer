# Forest P1 runtime input injection (#660, recovery 321e7b46)

Lane `p2-overworld-forest-runtime-input-injection`. Owner: Codex through
shared account `4laric`. Root+native tooling/runtime observation slice; no
engine/family/shared edits (reuses the #660 fixture, runner and staged-rerun
adapter read-only), no ADMIT, no ledger writes. Issues #660/#149 stay OPEN.

## Problem (from the done #751 audit)

The headed staged forest P1 run reaches the day-results screen
`ogScrResultMgr::RESULT_Active` (`src/plugPikiOgawa/ogResult.cpp:615`) and
stalls: it advances only via save-manager states 12/13/14/15
(`ogResult.cpp:624-638`) or `keyClick(KBBTN_START|KBBTN_A|KBBTN_B)`
(`ogResult.cpp:639`), and the save manager itself waits on its file-slot
selection UI (`ogSave.cpp:148/168`). Movies are not the stall. The ported
engine already exposes a sanctioned, default-off scripted-pad hook
(`pc_port/pc_p2_input_script.h`, #397): a fixture sets a virtual pad for a
player port and `ControllerMgr::updateController` uses it instead of the
physical pad. No engine change is needed.

## Injection fixture (NEW)

`native/tools/p2_forest_p1_input_injection_fixture.cpp` is a
replacement-main harness that:

- boots the REAL game-linked engine over the staged run root
  (`--experimental-pikmin2-room`), 960x540 centred window;
- runs the canonical #632 guard FIRST on every idle tick
  (`orimaDead`/`NaviDead`/`HP<=1` -> `P2_FIXTURE_CAPTAIN_DOWN` and exit 86
  BLOCKED), with a `--guard-self-test` truth table and a
  `--guard-negative-test`; parked captain via the staged arena; no blanket
  invincibility;
- injects labelled controller pulses through the scripted-pad hook:
  alternating hold/release windows, START for the first half of the pulse
  budget then A (both documented exits), each press logged as
  `P2_FOREST_INPUT_INJECTED ... injected=1` and released as
  `P2_FOREST_INPUT_CLEARED ... injected=1`;
- deliberately does NOT early-return on pause/UI-overlay states, because the
  day-results and file-slot waits ARE overlay states;
- emits no UI-advance PASS marker: advance is decided post-hoc by the
  dependency-free reader below.

## Reader (`experimental/pikmin2_forest_p1_input_injection.py`)

- Reuses the done #660 staged-rerun adapter read-only by path (never forks
  it) to stage a fresh run root with the forest P1 layout + JAudio pins.
- `read_run_log` splits the log at the first injected press and only passes
  when there is post-injection advance evidence: the save manager announcing
  itself, or a UI screen load not present in the pre-injection baseline.
  Injected markers alone never pass; captain-down / duplicate / standalone
  FAIL tokens fail; benign `FAILED to open <optional>` noise does not (no
  false positives); external `injection=1` tokens are rejected.
- `guard_record` hashes canonical `scripts/p2_fixture_captain_guard.h`
  read-only (`d2f678c9eda75e151eb534077dff9e30ad36ae4796881d971bbd09945f3c3474`),
  failing closed on drift; absent from this lane's pinned root base
  (recorded pin gap).

## Honesty

Injection is labelled everywhere and is never presented as natural input.
No boundary is claimed without an observed marker; all six arena gates stay
UNTESTED; there is no playability claim. Consumer #660/#149 stay OPEN.

## Evidence

Recorded under the lane output directory: leased private build (exe SHA-256,
`ninja: no work to do.`), fixture provenance, guard self/negative tests, the
bounded staged run log with injected markers, and the reader verdict.
