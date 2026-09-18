# Forest result/save-screen controller accessor pin-discovery (#804, consumer #660)

Lane `forest-input-controller-pin-fresh`, issue #804 (OPEN), recovery request
`a20855498ab0c30e2aac13f32e58c69f3316d28e2b7ad3f7e528a32acc44dac3`, downstream
consumer `p2-overworld-forest-runtime-input-injection` (#660, gen 3 blocked).
Diagnosis only: read-only audit, no engine/shared/native/CMake/manifest edits,
no edits to the pad-sink owner files, no builds, no launches, no ADMIT. All six
runtime gates UNTESTED.

## Pinned callsite chain (the screens' poll path)

1. `NewPikiGameSetupSection::update` — `src/plugPikiColin/newPikiGame.cpp:2092`
   `mController->update();` (the setup section `Controller`, `new Controller(1)`
   at `:776`, so `mPlayerNum == 1`).
2. `mCurrentModeState->update` — `newPikiGame.cpp:2102` farms polling to the mode
   state.
3. Result poll — `newPikiGame.cpp:1393`
   `resultWindow->update(mParentSection->mController)`.
4. Challenge poll — `newPikiGame.cpp:1384`
   `challengeWindow->update(mParentSection->mController)`.
5. `BaseGameSection::mController` — `include/Section.h:119` (`Controller*`).
6. `ModeState::mParentSection` — `include/Section.h:148` (`BaseGameSection*`).
7. `ogScrResultMgr::update` `RESULT_Active` — `src/plugPikiOgawa/ogResult.cpp:629`
   (`mSaveMgr->update(input)`).
8. `input->keyClick(KBBTN_START | KBBTN_A | KBBTN_B)` — `ogResult.cpp:653`
   (canonical pin `d01b89a7` cites `:639`).
9. `Controller::keyClick` — `include/Controller.h:65`: reads `mInputPressed`
   (`keyDown` at `:64` reads `mCurrentInput`).
10. `Controller::update` — `src/sysCommon/controller.cpp:70`
    (`gsys->mControllerMgr.updateController(this)`).
11. `Controller::updateCont` — `controller.cpp:44`:
    `mInputPressed = mCurrentInput & ~mPrevInput`.
12. Scripted-pad hook — `ControllerMgr::updateController`
    (`src/sysDolphin/controllerMgr.cpp`, `pc_p2_input_script_override` branch)
    calls `controller->updateCont(scripted)`; hook defined at
    `pc_port/pc_p2_input_script.h:13` (#397, additive default-off, #186).

## Finding: NO_MISSING_ACCESSOR

The #660 gen-3 premise that the scripted-pad override "only reaches
`Controller::mCurrentInput`" is contradicted by source at both the #660 native
pin (`f511aba6`) and native-wave: the override branch calls
`controller->updateCont(scripted)`, and `updateCont` sets **`mInputPressed`**,
which is exactly the bit `keyClick` reads. So no new engine accessor is required,
and inventing one would be an unjustified engine change.

The unresolved item is runtime identity/timing only: which `Controller` instance
the result screen polls during the overlay, whether its `mPlayerNum` matches the
scripted port, and press-window alignment across the per-tick
`Controller::update()` (`system.cpp:352`, `app->idle()` at `:358`).

Owner line for any accessor change, if the trace shows one is genuinely needed:
`native/src/sysDolphin/controllerMgr.cpp` + `native/include/Controller.h` (owned
by the #794 test-only-sink lane) with #186 review for the #397 hook semantics.

## First bounded executable staging slice (fail-closed)

Owner lane `p2-overworld-forest-runtime-input-injection` (#660), consuming this
packet; files are that lane's own
`native/tools/p2_forest_p1_input_injection_fixture.cpp` and
`experimental/pikmin2_forest_p1_input_injection.py` at pins native `f511aba6`,
root `8092d097`. Deliverable: a read-only instrumented trace that, at each
result/save poll, logs the polled `Controller` pointer identity, `mPlayerNum`,
`mCurrentInput`, `mInputPressed` and script-active state, plus press-window
timing. No engine edits. Fail closed if the trace cannot establish the polled
controller/port identity. Downstream consumer #660; recovery `a2085549`.

## Tooling

`experimental/pikmin2_forest_input_controller_pin_audit.py` exposes the registry
(`pins`) and a fail-closed symbol checker (`check --symbol`). 6 focused tests
green. Destination pins recorded: root `f2803e42`, native `b944db03`.