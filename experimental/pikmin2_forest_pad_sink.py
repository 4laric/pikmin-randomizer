"""Forest controller PAD sink contract (issue #794).

Lane forest-controller-pad-sink-native. Records the exact test-only sink
contract: a static setter writing sControllerPad button bits so
ControllerMgr::keyDown observes injected A/START presses, with fail-closed
negatives (baseline clear, no bleed, clear-after-write). Stdlib only.

The sink lives in native/src/sysDolphin/controllerMgr.cpp (+ decl in
native/include/Controller.h) and is called exclusively by the guarded
fixture; production code never references it. Downstream consumer #660.
"""

import re

SCHEMA = "p2-forest-pad-sink-v1"
ISSUE = 794
CONSUMER = {"lane": "p2-overworld-forest-runtime-input-injection", "issue": 660}
SINK_SYMBOL = "ControllerMgr::testSinkPadButtons"
KEYDOWN_SYMBOL = "ControllerMgr::keyDown"
BUTTON_A = 0x0100
BUTTON_START = 0x1000
MARKERS = (
    "P2_FOREST_PAD_SINK_BASELINE_CLEAR",
    "P2_FOREST_PAD_SINK_OBSERVED button=A",
    "P2_FOREST_PAD_SINK_OBSERVED button=START",
)
PASS_MARKER = "PASS P2_FOREST_PAD_SINK_RUN markers=3"
CAPTAIN_DOWN = "P2_FIXTURE_CAPTAIN_DOWN"
GUARD_SHA256 = "d2f678c9eda75e151eb534077dff9e30ad36ae4796881d971bbd09945f3c3474"
OWNED_NATIVE = (
    "native/src/sysDolphin/controllerMgr.cpp",
    "native/include/Controller.h",
    "native/tools/p2_forest_pad_sink_fixture.cpp",
)

_HEX64 = re.compile(r"^[0-9a-f]{64}$")


def check_run_log(text):
    """Return (ok, detail) for a pad-sink fixture run log; fail-closed."""
    if not isinstance(text, str):
        raise TypeError("run log must be text")
    if CAPTAIN_DOWN in text:
        return False, "captain-down interruption present"
    if PASS_MARKER not in text:
        return False, "run PASS marker absent"
    missing = [m for m in MARKERS if m not in text]
    if missing:
        return False, "missing markers: %s" % "; ".join(missing)
    if "FAIL P2_FOREST_PAD_SINK" in text:
        return False, "fixture failure present"
    return True, "run PASS with sink observations"


def sink_declared(header_text, impl_text):
    """True when the sink decl + def are present and production is clean."""
    if not isinstance(header_text, str) or not isinstance(impl_text, str):
        raise TypeError("source texts required")
    decl = "testSinkPadButtons" in header_text
    defined = "ControllerMgr::testSinkPadButtons" in impl_text
    return bool(decl and defined)


def production_clean(tree_texts):
    """True when no production TU references the sink (fixture-only use)."""
    hits = []
    for path, text in tree_texts.items():
        if "testSinkPadButtons" in text and "p2_forest_pad_sink_fixture" not in path:
            if "controllerMgr.cpp" in path or "Controller.h" in path:
                continue
            hits.append(path)
    return not hits
