"""Focused fail-closed tests for the challenge-mode registration validator (#676).

Synthetic temp trees only; the real private tree is validated by the handoff
run. No runtime claim.
"""

import tempfile
import unittest
from pathlib import Path

from scripts.validate_p2_challenge_mode_registration import (
    EXPECTED_POST_APPLY_CMAKE_SHA256,
    RegistrationError,
    validate_registration,
)

VALID_BLOCK = """add_executable(p2_challenge_mode_fixture
    tools/p2_challenge_mode_fixture.cpp
    pc_port/pc_p2_challenge_mode.cpp)
set(P2_CHALLENGE_GUARD_INCLUDE_DIR "${CMAKE_SOURCE_DIR}/../scripts" CACHE PATH "guard")
if(NOT EXISTS "${P2_CHALLENGE_GUARD_INCLUDE_DIR}/p2_fixture_captain_guard.h")
    message(FATAL_ERROR "guard missing")
endif()
target_include_directories(p2_challenge_mode_fixture PRIVATE pc_port ${P2_CHALLENGE_GUARD_INCLUDE_DIR})
target_compile_options(p2_challenge_mode_fixture PRIVATE ${NATIVE_COMPILE_OPTIONS})
add_test(NAME p2_challenge_mode_fixture COMMAND p2_challenge_mode_fixture)
"""


def make_tree(root, cmake_text=VALID_BLOCK, module=True, fixture_guard=True,
              vendored_guard=False):
    root = Path(root)
    (root / "pc_port").mkdir(parents=True, exist_ok=True)
    (root / "tools").mkdir(parents=True, exist_ok=True)
    (root / "CMakeLists.txt").write_text(cmake_text, encoding="utf-8")
    (root / "pc_port" / "pc_p2_challenge_mode.cpp").write_text("// module\n", encoding="utf-8")
    (root / "pc_port" / "pc_p2_challenge_mode.h").write_text("#pragma once\n", encoding="utf-8")
    guard = '#include "p2_fixture_captain_guard.h"\n' if fixture_guard else ""
    (root / "tools" / "p2_challenge_mode_fixture.cpp").write_text(guard, encoding="utf-8")
    if not module:
        (root / "pc_port" / "pc_p2_challenge_mode.cpp").unlink()
    if vendored_guard:
        (root / "tools" / "p2_fixture_captain_guard.h").write_text("// vendored\n", encoding="utf-8")
    return root


class ValidatorTests(unittest.TestCase):
    def test_valid_block_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            tree = make_tree(tmp)
            facts = validate_registration(tree, expected_post_sha256=None)
            self.assertTrue(facts["ok"])
            self.assertTrue(facts["guard_adopted"])
            self.assertTrue(facts["ctest_entry"])

    def test_missing_module_tu_target_fails(self):
        bad = VALID_BLOCK.replace("    pc_port/pc_p2_challenge_mode.cpp)\n", ")\n")
        with tempfile.TemporaryDirectory() as tmp:
            tree = make_tree(tmp, cmake_text=bad)
            with self.assertRaises(RegistrationError):
                validate_registration(tree, expected_post_sha256=None)

    def test_missing_fixture_tu_target_fails(self):
        bad = VALID_BLOCK.replace("    tools/p2_challenge_mode_fixture.cpp\n", "")
        with tempfile.TemporaryDirectory() as tmp:
            tree = make_tree(tmp, cmake_text=bad)
            with self.assertRaises(RegistrationError):
                validate_registration(tree, expected_post_sha256=None)

    def test_missing_guard_validation_fails(self):
        bad = VALID_BLOCK.replace(
            'if(NOT EXISTS "${P2_CHALLENGE_GUARD_INCLUDE_DIR}/p2_fixture_captain_guard.h")\n    message(FATAL_ERROR "guard missing")\nendif()\n', "")
        with tempfile.TemporaryDirectory() as tmp:
            tree = make_tree(tmp, cmake_text=bad)
            with self.assertRaises(RegistrationError):
                validate_registration(tree, expected_post_sha256=None)

    def test_vendored_guard_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            tree = make_tree(tmp, vendored_guard=True)
            with self.assertRaises(RegistrationError):
                validate_registration(tree, expected_post_sha256=None)

    def test_missing_ctest_entry_fails(self):
        bad = VALID_BLOCK.replace(
            "add_test(NAME p2_challenge_mode_fixture COMMAND p2_challenge_mode_fixture)\n", "")
        with tempfile.TemporaryDirectory() as tmp:
            tree = make_tree(tmp, cmake_text=bad)
            with self.assertRaises(RegistrationError):
                validate_registration(tree, expected_post_sha256=None)

    def test_missing_guard_include_in_fixture_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            tree = make_tree(tmp, fixture_guard=False)
            with self.assertRaises(RegistrationError):
                validate_registration(tree, expected_post_sha256=None)

    def test_wrong_patch_hash_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            tree = make_tree(tmp)
            patch = Path(tmp) / "registration.patch"
            patch.write_text("not the real patch\n", encoding="utf-8")
            with self.assertRaises(RegistrationError):
                validate_registration(tree, patch_path=patch,
                                      expected_post_sha256=None)

    def test_post_sha_mismatch_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            tree = make_tree(tmp)
            with self.assertRaises(RegistrationError):
                validate_registration(tree,
                                      expected_post_sha256="0" * 64)

    def test_expected_packet_sha_constant(self):
        self.assertEqual(len(EXPECTED_POST_APPLY_CMAKE_SHA256), 64)


if __name__ == "__main__":
    unittest.main()