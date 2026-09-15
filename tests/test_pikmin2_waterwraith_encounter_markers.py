import importlib.util
import os
from pathlib import Path

import pytest

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
     ("P2_WATERWRAITH_ENCOUNTER_PASS stuns=1 hits=55 crushes=18 damage=3300.0 "
      "zeroed=1 child_removed=1 body_zeroed=1 treasure=1 kill=1 delivered=1"),
    "PASS WATERWRAITH_ENCOUNTER_RUNTIME",
]

FULL_LOG = "\n".join(FULL_LOG_LINES) + "\n"

# A valid BLOCKED outcome: natural carry did not complete, so no Pod receipt
# fires; carrier evidence is logged and teardown/re-entry still complete.
BLOCKED_LOG_LINES = [
    "P2_WATERWRAITH_ENCOUNTER_WINDOW size=960x540",
    "P2_WATERWRAITH_ENCOUNTER_READY",
    "P2_WATERWRAITH_ENCOUNTER_STAGE_A crushes=18 damage=0.0",
    "P2_WATERWRAITH_ENCOUNTER_PURPLE_SETUP",
    "P2_WATERWRAITH_BODY_ZERO tick=62 bodyHealth=0.0",
    "P2_WATERWRAITH_CORPSE pos=0.000,-0.000,229.667 registered=1 standin=number_pellet",
    "P2_WATERWRAITH_FINISHED tick=64 bodyHealth=0.0",
    "P2_WATERWRAITH_CARRY_SETUP",
    "P2_WATERWRAITH_CARRY_UNRESOLVED frame=2400 max_carriers=0 deliveries=0",
    "P2_WATERWRAITH_ENCOUNTER_DEATH_REENTRY ready=1 attached=1",
     ("P2_WATERWRAITH_ENCOUNTER_PASS stuns=1 hits=55 crushes=18 damage=3300.0 "
      "zeroed=1 child_removed=1 body_zeroed=1 treasure=1 kill=1 delivered=0"),
    "BLOCKED WATERWRAITH_ENCOUNTER_RUNTIME carry=no_natural_carry",
]
BLOCKED_LOG = "\n".join(BLOCKED_LOG_LINES) + "\n"


def _verifier_module():
    env_root = os.environ.get("PIKMIN_NATIVE_ROOT")
    if env_root:
        root = Path(env_root)
    else:
        engine = Path(__file__).resolve().parents[1] / "engine"
        if engine.is_dir():
            root = engine
        else:
            pytest.skip("PIKMIN_NATIVE_ROOT not set; set it to the native worktree")
    source = root / "tools" / "p2_waterwraith_encounter_runtime_run.py"
    spec = importlib.util.spec_from_file_location(
        "p2_waterwraith_encounter_runtime_run", source)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if "P2_WATERWRAITH_CARRY_SETUP" not in source.read_text(encoding="utf-8"):
        pytest.skip("exported engine verifier lacks the carry markers; set PIKMIN_NATIVE_ROOT")
    return module


def _log_without(removed):
    for lines in (FULL_LOG_LINES, BLOCKED_LOG_LINES):
        if removed in lines:
            return "\n".join(line for line in lines if line != removed) + "\n"
    return "\n".join(FULL_LOG_LINES) + "\n"


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
    "P2_WATERWRAITH_CARRY_UNRESOLVED frame=2400 max_carriers=0 deliveries=0",
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


# `verify_log` only regex-checks the markers listed in its own rules; it has no
# rule for P2_WATERWRAITH_SQUAD_FREE / P2_WATERWRAITH_SQUAD_ASSIST, so those
# markers are optional (their absence never flips the result).
def test_free_assist_markers_are_optional():
    verify_log = _verifier_module().verify_log
    for marker in ("P2_WATERWRAITH_SQUAD_FREE count=8",
                   "P2_WATERWRAITH_SQUAD_ASSIST carriers=20 assisted=1"):
        assert verify_log(_log_without(marker)) == []


# An ASSISTED receipt still satisfies the delivered path: the runtime PASS check
# is a plain substring test ("PASS WATERWRAITH_ENCOUNTER_RUNTIME" in text), so
# the " ASSISTED" suffix on the final line still matches.
def test_assisted_delivery_is_valid():
    verify_log = _verifier_module().verify_log
    assisted_lines = FULL_LOG_LINES[:-1] + [
        "P2_WATERWRAITH_SQUAD_ASSIST carriers=20 assisted=1",
        "PASS WATERWRAITH_ENCOUNTER_RUNTIME ASSISTED",
    ]
    assert verify_log("\n".join(assisted_lines) + "\n") == []
