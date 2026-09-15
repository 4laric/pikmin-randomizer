import importlib.util
import os
from pathlib import Path

import pytest

DEFAULT_NATIVE_ROOT = "C:/Users/alari/pikmin-randomizer/output/dsw/native-l31"

FULL_LOG_LINES = [
    "P2_WATERWRAITH_ENCOUNTER_WINDOW size=960x540",
    "P2_WATERWRAITH_ENCOUNTER_READY",
    "P2_WATERWRAITH_ENCOUNTER_STAGE_A crushes=18 damage=0.0",
    "P2_WATERWRAITH_ENCOUNTER_PURPLE_SETUP",
    "P2_WATERWRAITH_BODY_ZERO tick=62 bodyHealth=0.0",
    "P2_WATERWRAITH_CORPSE pos=0.000,40.000,229.667 registered=1 standin=number_pellet",
    "P2_WATERWRAITH_FINISHED tick=64 bodyHealth=0.0",
    "P2_WATERWRAITH_CARRY_SETUP",
    "P2_WATERWRAITH_POD_RECEIPT generator=0 deliveries=1",
    "P2_WATERWRAITH_ENCOUNTER_DELIVERED deliveries=1",
    "P2_WATERWRAITH_ENCOUNTER_DEATH_REENTRY ready=1 attached=1",
    ("P2_WATERWRAITH_ENCOUNTER_PASS stuns=1 hits=63 crushes=18 damage=3300.0 "
     "zeroed=1 child_removed=1 body_zeroed=1 treasure=1 kill=1 delivered=1"),
    "PASS WATERWRAITH_ENCOUNTER_RUNTIME",
]

FULL_LOG = "\n".join(FULL_LOG_LINES) + "\n"

# A valid BLOCKED outcome: the corpse stand-in was born view-less, so there is
# no Pod receipt/delivery; the teardown/re-entry and capture still complete.
BLOCKED_LOG_LINES = [
    "P2_WATERWRAITH_ENCOUNTER_WINDOW size=960x540",
    "P2_WATERWRAITH_ENCOUNTER_READY",
    "P2_WATERWRAITH_ENCOUNTER_STAGE_A crushes=18 damage=0.0",
    "P2_WATERWRAITH_ENCOUNTER_PURPLE_SETUP",
    "P2_WATERWRAITH_BODY_ZERO tick=62 bodyHealth=0.0",
    "P2_WATERWRAITH_CORPSE pos=0.000,40.000,237.667 registered=0 standin=number_pellet",
    "P2_WATERWRAITH_FINISHED tick=64 bodyHealth=0.0",
    "P2_WATERWRAITH_CARRY_SETUP",
    "P2_WATERWRAITH_CARRY_BLOCKED registered=0 reason=viewless_number_pellet_mPelletView_null",
    "P2_WATERWRAITH_ENCOUNTER_DEATH_REENTRY ready=1 attached=1",
    ("P2_WATERWRAITH_ENCOUNTER_PASS stuns=1 hits=63 crushes=18 damage=3300.0 "
     "zeroed=1 child_removed=1 body_zeroed=1 treasure=1 kill=1 delivered=0"),
    "BLOCKED WATERWRAITH_ENCOUNTER_RUNTIME carry=viewless_number_pellet",
]
BLOCKED_LOG = "\n".join(BLOCKED_LOG_LINES) + "\n"


def _verifier_module():
    root = Path(os.environ.get("PIKMIN_NATIVE_ROOT", DEFAULT_NATIVE_ROOT))
    source = root / "tools" / "p2_waterwraith_encounter_runtime_run.py"
    spec = importlib.util.spec_from_file_location(
        "p2_waterwraith_encounter_runtime_run", source)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _log_without(removed):
    return "\n".join(line for line in FULL_LOG_LINES if line != removed) + "\n"


def test_valid_log_passes():
    verify_log = _verifier_module().verify_log
    assert verify_log(FULL_LOG) == []


def test_blocked_log_passes():
    verify_log = _verifier_module().verify_log
    assert verify_log(BLOCKED_LOG) == []


@pytest.mark.parametrize("removed", [
    "P2_WATERWRAITH_BODY_ZERO tick=62 bodyHealth=0.0",
    "P2_WATERWRAITH_CORPSE pos=0.000,40.000,229.667 registered=1 standin=number_pellet",
    "P2_WATERWRAITH_FINISHED tick=64 bodyHealth=0.0",
    "P2_WATERWRAITH_CARRY_SETUP",
    "P2_WATERWRAITH_POD_RECEIPT generator=0 deliveries=1",
    "P2_WATERWRAITH_ENCOUNTER_DELIVERED deliveries=1",
    "P2_WATERWRAITH_ENCOUNTER_DEATH_REENTRY ready=1 attached=1",
    "PASS WATERWRAITH_ENCOUNTER_RUNTIME",
])
def test_removed_marker_is_detected(removed):
    verify_log = _verifier_module().verify_log
    assert verify_log(_log_without(removed)) != []


def test_zero_crush_stage_a_is_detected():
    verify_log = _verifier_module().verify_log
    mutated = list(FULL_LOG_LINES)
    for index, line in enumerate(mutated):
        if line.startswith("P2_WATERWRAITH_ENCOUNTER_STAGE_A "):
            mutated[index] = "P2_WATERWRAITH_ENCOUNTER_STAGE_A crushes=0 damage=0.0"
    assert verify_log("\n".join(mutated) + "\n") != []
