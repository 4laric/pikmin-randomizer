"""Fail-closed validator for the challenge-mode registration landing (#676).

Read-only checker over a PRIVATE native tree: proves the #661 registration
patch was applied so that the #651 module TU (``pc_p2_challenge_mode.cpp``)
joins a CMake target together with the guarded fixture, the canonical guard
include directory is validated (no vendored copy), and a CTest entry exists.

It never edits the maintained/shared tree and never claims a runtime result.
Stdlib only.
"""

import hashlib
import re
from pathlib import Path

EXPECTED_PATCH_SHA256 = (
    "3c2cf41c4ce9183aadc8b7740e77642c323a745342c43a2ae30878ffc1f8989c")
# The #661 packet's post-apply hash (ec901b40...) predates the pinned #651/#186
# review correction that replaced the hardcoded ${CMAKE_SOURCE_DIR}/../scripts
# include with the validated P2_CHALLENGE_GUARD_INCLUDE_DIR cache PATH. This is
# the post-apply hash of the CORRECTED private landing.
EXPECTED_POST_APPLY_CMAKE_SHA256 = (
    "2f0a67f73479b3541332285aeaef84df0380448bfc55d45cb73939a82193315f")
TARGET = "p2_challenge_mode_fixture"
FIXTURE_TU = "tools/p2_challenge_mode_fixture.cpp"
MODULE_TU = "pc_port/pc_p2_challenge_mode.cpp"
GUARD_HEADER = "p2_fixture_captain_guard.h"


class RegistrationError(ValueError):
    pass


def _read(path):
    p = Path(path)
    if not p.is_file():
        raise RegistrationError("Missing file: %s" % p)
    return p.read_text(encoding="utf-8", errors="replace")


def target_block(cmake_text, target=TARGET):
    """Return the text of the ``add_executable(<target> ...)`` block."""
    match = re.search(
        r"add_executable\(\s*" + re.escape(target) + r"\b(.*?)\)", cmake_text, re.S)
    if not match:
        raise RegistrationError("No add_executable block for target %s" % target)
    return match.group(1)


def validate_registration(native_tree, cmake_rel="CMakeLists.txt",
                          patch_path=None,
                          expected_patch_sha256=EXPECTED_PATCH_SHA256,
                          expected_post_sha256=EXPECTED_POST_APPLY_CMAKE_SHA256):
    """Validate the private registration; return a facts dict, else raise."""
    tree = Path(native_tree)
    facts = {"native_tree": str(tree), "target": TARGET}

    if patch_path is not None:
        patch_bytes = Path(patch_path).read_bytes()
        digest = hashlib.sha256(patch_bytes).hexdigest()
        if digest != expected_patch_sha256:
            raise RegistrationError(
                "Registration patch hash %s != expected %s" % (digest, expected_patch_sha256))
        facts["patch_sha256"] = digest

    cmake_path = tree / cmake_rel
    cmake_text = _read(cmake_path)
    facts["cmake_sha256"] = hashlib.sha256(
        cmake_path.read_bytes()).hexdigest()
    if (expected_post_sha256 is not None
            and facts["cmake_sha256"] != expected_post_sha256):
        raise RegistrationError(
            "Post-apply CMakeLists.txt sha %s != packet %s"
            % (facts["cmake_sha256"], expected_post_sha256))

    block = target_block(cmake_text)
    if FIXTURE_TU not in block:
        raise RegistrationError(
            "Target %s does not link the #651 fixture %s" % (TARGET, FIXTURE_TU))
    if MODULE_TU not in block:
        raise RegistrationError(
            "Target %s does not link the module TU %s" % (TARGET, MODULE_TU))
    if not (tree / FIXTURE_TU).is_file() or not (tree / MODULE_TU).is_file():
        raise RegistrationError("Fixture/module sources absent from the native tree")

    # Guard include dir must be a validated cache PATH, never vendored.
    if "P2_CHALLENGE_GUARD_INCLUDE_DIR" not in cmake_text:
        raise RegistrationError("Guard include cache variable missing")
    if not re.search(
            r"if\(NOT EXISTS \"\$\{P2_CHALLENGE_GUARD_INCLUDE_DIR\}/"
            + re.escape(GUARD_HEADER) + r"\"\)", cmake_text):
        raise RegistrationError("Guard header existence validation missing (vendoring risk)")
    if "FATAL_ERROR" not in cmake_text:
        raise RegistrationError("Guard include validation is not fail-closed")
    if (tree / "tools" / GUARD_HEADER).is_file():
        raise RegistrationError(
            "Vendored guard copy found under tools/ (must use the canonical scripts dir)")

    # CTest entry present for the target.
    if not re.search(
            r"add_test\(NAME\s+" + re.escape(TARGET) + r"\s+COMMAND\s+"
            + re.escape(TARGET), cmake_text):
        raise RegistrationError("Missing CTest entry for %s" % TARGET)
    facts["ctest_entry"] = True

    # The fixture must adopt the canonical guard include (not a private guard).
    fixture_text = _read(tree / FIXTURE_TU)
    if GUARD_HEADER not in fixture_text:
        raise RegistrationError("Fixture does not include the #632 captain guard")
    facts["guard_adopted"] = True
    facts["ok"] = True
    return facts


def main(argv=None):
    import argparse
    import json
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--native", required=True)
    parser.add_argument("--patch", default=None)
    args = parser.parse_args(argv)
    try:
        print(json.dumps(validate_registration(args.native, patch_path=args.patch),
                         indent=2))
        return 0
    except RegistrationError as error:
        print(json.dumps({"ok": False, "error": str(error)}, indent=2))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())