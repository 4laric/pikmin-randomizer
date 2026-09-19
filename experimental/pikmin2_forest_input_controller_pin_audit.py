#!/usr/bin/env python3
"""Forest result/save-screen controller accessor pin registry (lane forest-input-controller-pin-fresh).

Read-only pin-discovery for recovery a2085549 (consumer
p2-overworld-forest-runtime-input-injection #660, gen 3 blocked). Pins the
section/controller accessor callsite chain the ogScrResultMgr/ogSaveMgr screens
poll, the input-bit accessor, and the owning line for any accessor change - or
the precise no-accessor/existing-owner finding. Stdlib only. Fail-closed.
"""

import argparse
import json
import sys

SCHEMA = "p2-forest-input-controller-pins-1"

CHAIN = [
    {"step": "screens receive the controller",
     "symbol": "NewPikiGameSetupSection::update",
     "file": "src/plugPikiColin/newPikiGame.cpp", "line": 2092,
     "detail": "mController->update(); the setup section's Controller (new Controller(1) at :776)"},
    {"step": "mode state update",
     "symbol": "mCurrentModeState->update", "file": "src/plugPikiColin/newPikiGame.cpp",
     "line": 2102, "detail": "farms result/save polling to the active ModeState"},
    {"step": "result window poll",
     "symbol": "ogScrResultMgr::update", "file": "src/plugPikiColin/newPikiGame.cpp",
     "line": 1393, "detail": "resultWindow->update(mParentSection->mController)"},
    {"step": "challenge window poll",
     "symbol": "challengeWindow->update", "file": "src/plugPikiColin/newPikiGame.cpp",
     "line": 1384, "detail": "challengeWindow->update(mParentSection->mController)"},
    {"step": "section controller member",
     "symbol": "BaseGameSection::mController", "file": "include/Section.h", "line": 119,
     "detail": "Controller* mController; active controller (created new Controller(1), player 1)"},
    {"step": "mode state parent",
     "symbol": "ModeState::mParentSection", "file": "include/Section.h", "line": 148,
     "detail": "BaseGameSection* mParentSection"},
    {"step": "result active wait",
     "symbol": "ogScrResultMgr::update RESULT_Active", "file": "src/plugPikiOgawa/ogResult.cpp",
     "line": 629, "detail": "mSaveMgr->update(input); exits only on ogSave states 12/13/14/15"},
    {"step": "keyClick fallback",
     "symbol": "input->keyClick", "file": "src/plugPikiOgawa/ogResult.cpp", "line": 653,
     "detail": "keyClick(KBBTN_START | KBBTN_A | KBBTN_B) (canonical pin d01b89a7 cites :639)"},
    {"step": "input bit accessor",
     "symbol": "Controller::keyClick", "file": "include/Controller.h", "line": 65,
     "detail": "reads mInputPressed; keyDown reads mCurrentInput (Controller.h)"},
    {"step": "controller self-update",
     "symbol": "Controller::update", "file": "src/sysCommon/controller.cpp", "line": 70,
     "detail": "gsys->mControllerMgr.updateController(this)"},
    {"step": "updateCont derives edges",
     "symbol": "Controller::updateCont", "file": "src/sysCommon/controller.cpp", "line": 44,
     "detail": "mInputPressed = mCurrentInput & ~mPrevInput"},
    {"step": "scripted-pad hook",
     "symbol": "ControllerMgr::updateController (pc_p2_input_script_override branch)",
     "file": "src/sysDolphin/controllerMgr.cpp", "line": None,
     "detail": "calls controller->updateCont(scripted) - sets mCurrentInput AND mInputPressed"},
    {"step": "hook definition",
     "symbol": "pc_p2_input_script_set/override", "file": "pc_port/pc_p2_input_script.h",
     "line": 13, "detail": "#397 additive default-off scripted pad (shared hook, #186)"},
]

FINDING = {
    "verdict": "NO_MISSING_ACCESSOR",
    "premise": "#660 gen3 claimed the scripted-pad override 'only reaches Controller::mCurrentInput'.",
    "source_evidence": "At the #660 native pin and native-wave, the override branch in "
                       "ControllerMgr::updateController calls controller->updateCont(scripted); "
                       "updateCont (src/sysCommon/controller.cpp:44) sets mInputPressed from "
                       "mCurrentInput & ~mPrevInput. keyClick reads mInputPressed. The hook already "
                       "reaches the exact bit keyClick reads; no new accessor is required.",
    "remaining_unknown": "Runtime identity/timing only: which Controller instance the result "
                         "screen polls during the overlay, its mPlayerNum vs the scripted port, and "
                         "press-window alignment across the per-tick Controller::update() (system.cpp:352, "
                         "app->idle() at :358).",
    "owner_line_for_accessor_change": {
        "files": ["native/src/sysDolphin/controllerMgr.cpp", "native/include/Controller.h"],
        "owner_lane": "forest-controller-pad-sink-native (#794, test-only sink)",
        "shared_review": "4laric/pikmin-randomizer#186 (scripted-pad hook #397 semantics)",
    },
    "first_bounded_staging_slice": {
        "lane": "p2-overworld-forest-runtime-input-injection",
        "consumer": "#660",
        "files": ["native/tools/p2_forest_p1_input_injection_fixture.cpp",
                  "experimental/pikmin2_forest_p1_input_injection.py"],
        "pins": {"native": "f511aba6b56df238de23012ce2ce7240f04f203f",
                 "root": "8092d0974381781937ee5d325bbcbe4e3e4dc4c4"},
        "deliverable": "Read-only instrumented trace: at each result/save poll, log the polled "
                       "Controller pointer identity, mPlayerNum, mCurrentInput, mInputPressed and the "
                       "script active state, plus press-window timing; no engine edits. Fail closed if "
                       "the trace cannot establish the polled controller/port identity.",
    },
}

REGISTRY = {
    "schema": SCHEMA,
    "lane": "forest-input-controller-pin-fresh",
    "issue": 804,
    "recovery": "a20855498ab0c30e2aac13f32e58c69f3316d28e2b7ad3f7e528a32acc44dac3",
    "consumer": "p2-overworld-forest-runtime-input-injection (#660, gen 3 blocked)",
    "destination_pins": {
        "root": "f2803e423b9f30ee6fcaf79004be02b2770a5a98",
        "native": "b944db033a3eef7aabb135372c4656d04e47bd7d",
    },
    "chain": CHAIN,
    "finding": FINDING,
}


def registry():
    return json.loads(json.dumps(REGISTRY))


def check_step(name):
    """Fail-closed lookup of one chain step by symbol."""
    for step in CHAIN:
        if step["symbol"] == name:
            return {"symbol": name, "file": step["file"], "line": step["line"], "problems": []}
    return {"symbol": name, "verdict": "REFUSED", "problems": ["unknown-symbol:" + str(name)]}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("pins")
    check = sub.add_parser("check")
    check.add_argument("--symbol", required=True)
    args = parser.parse_args(argv)
    if args.command == "pins":
        print(json.dumps(registry(), indent=1, sort_keys=True))
        return 0
    result = check_step(args.symbol)
    print(json.dumps(result, indent=1, sort_keys=True))
    return 0 if not result["problems"] else 1


if __name__ == "__main__":
    raise SystemExit(main())