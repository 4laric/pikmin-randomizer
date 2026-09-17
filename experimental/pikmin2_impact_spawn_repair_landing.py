"""Landing validator for the committed #745 squad-spawn repair (#756).

Read-only re-verification of evidence produced by lane
impact-squad-spawn-repair-native: pinned commits present in their
repositories, fixture/run-log hashes match the #745 report, and the headed
run log carries PARK_ALIVE 21 / SQUAD 40 / BOOT / PASS with no captain-down
or extinction. Emits nothing executable and invents no gameplay; all six
gates stay UNTESTED except the observed spawn/boot facts, which are not
gameplay acceptance.
"""
import hashlib
import re
from pathlib import Path

NATIVE_COMMIT = "2e54daf994a408e469e39e3a4b2b7b2e420d5f2a"
ROOT_COMMIT = "49f3ba3a6012550ce53c250ce710b85313a547d4"
EXE_SHA256 = "3d5fe18a5b6398019017ae58017f1bffb9bdb91c76ab2b71de38d9d9d3ec21a3"
LOG_SHA256 = "2ce41e11f88812bb016b97e7114ca0ec03a8976132395a4bab1d4629fd0df145"

EXE_PATH = ("C:/Users/alari/pikmin-randomizer/output/native-impact-squad-spawn-build"
            "/p2_impact_squad_spawn_fixture.exe")
LOG_PATH = ("C:/Users/alari/pikmin-randomizer/output/workflow/autofill/prerequisites"
            "/impact-squad-spawn-repair-native/out/harness/runs"
            "/b409b19b5c0b48adb3a4f1eca7447750/native.log")

PARK_ALIVE = "P2_CHALLENGE_PARK_ALIVE pikis=21"
SQUAD = "P2_CHALLENGE_SQUAD pikis=40"
BOOT = "P2_CHALLENGE_BOOT level=0 slot=chal0"
PASS = "PASS P2_CHALLENGE_GUARDED_BOOT boot1 squad_alive"

_CAPTAIN_DOWN_TOKENS = ("P2_FIXTURE_CAPTAIN_DOWN", "GAMEEND_PikminExtinction",
                        "DEMOID_Extinction", "orima_dead=1")


def sha256_file(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def validate_log(text):
    """Check spawn/boot markers; reject captain-down or extinction."""
    for token in _CAPTAIN_DOWN_TOKENS:
        if token in text:
            return {"spawn_boot": False, "clean": False,
                    "reason": "captain-down marker: " + token}
    if re.search(r"Extinction", text, re.IGNORECASE):
        return {"spawn_boot": False, "clean": False,
                "reason": "extinction marker"}
    missing = [m for m in (PARK_ALIVE, SQUAD, BOOT, PASS) if m not in text]
    if missing:
        return {"spawn_boot": False, "clean": True,
                "reason": "missing markers: " + ", ".join(missing)}
    return {"spawn_boot": True, "clean": True, "reason": "PARK_ALIVE 21 + SQUAD 40 + BOOT + PASS"}


def verify(exe_path=EXE_PATH, log_path=LOG_PATH):
    """Re-verify the #745 evidence bundle against pinned hashes and markers."""
    exe_digest = sha256_file(exe_path)
    log_digest = sha256_file(log_path)
    if exe_digest != EXE_SHA256:
        return {"verified": False, "reason": "fixture exe hash drift"}
    if log_digest != LOG_SHA256:
        return {"verified": False, "reason": "run log hash drift"}
    text = Path(log_path).read_text(encoding="utf-8", errors="replace")
    result = validate_log(text)
    result["verified"] = result["spawn_boot"] and result["clean"]
    result["exe_sha256"] = exe_digest
    result["log_sha256"] = log_digest
    result["native_commit"] = NATIVE_COMMIT
    result["root_commit"] = ROOT_COMMIT
    return result
