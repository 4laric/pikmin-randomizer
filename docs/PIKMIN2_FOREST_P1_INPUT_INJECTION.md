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

## Generation-3 runtime result (honest: NO advance observed)

Delivered and verified: leased private build
(`output/forest-input-injection-build`, exe
`9696b26fe0920c860b634bbdcc837d8985f242c41017c1afa3c3940249d79ea1`,
`ninja: no work to do.`); private fixture link (native head `f511aba6`,
fixture exe `65177ee943ee7b67ff2b1f066bb234b29af8c1da6128c24a815a1b3c2011c92`,
provenance `built`); guard self-test `rows=7` exit 0 and negative exit 86
BLOCKED; bounded staged run via `scripts/run_pikmin2_fixture.py`
(960x540 centred window observed, engine fact observed, no captain-down).

**Result: the stall did not break.** In the run log
(`run-injection-03/native.log`) every one of the 44 UI screen-bundle loads
completed BEFORE the first labelled press (last `eng_blo` line 1035; first
injected press line 1044). 395 labelled START/A pulses then produced zero
new screens, no `SAVE Mgr START`, and no state change.

Concrete, source-anchored diagnosis: the sanctioned scripted-pad override
writes `Controller::mCurrentInput` through
`ControllerMgr::updateController`, but `ControllerMgr::keyDown` reads
`sControllerPad` directly (`src/sysDolphin/controllerMgr.cpp`). Any UI code
that polls `gsys->mControllerMgr.keyDown(...)` therefore never sees the
injected pad. The exact next step (owner-reviewable) is to confirm which
controller object the `ogScrResultMgr`/`ogSaveMgr` screens poll and extend
the injection to that path — either by routing the override through
`ControllerMgr::keyDown` or by driving the section controller the screens
actually read.

All six arena gates remain UNTESTED; no boundary is claimed; injection is
labelled and never presented as natural play; consumer #660/#149 stay OPEN.