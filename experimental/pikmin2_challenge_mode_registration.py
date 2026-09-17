"""Registration-packet generator for the #651 host-mode guarded fixture (#661).

Drafts the maintained CMake/CTest registration change for
``native/tools/p2_challenge_mode_fixture.cpp`` as a review-ready patch with
file:line anchors, guard/harness references and validation commands. The patch
is dry-applied against a private worktree only; this module never edits the
maintained/shared native checkout and runs no builds.
"""
import hashlib
import re
from pathlib import Path

NATIVE_CMAKE = "CMakeLists.txt"
FIXTURE = "tools/p2_challenge_mode_fixture.cpp"
HOST_MODULE = "pc_port/pc_p2_challenge_mode.cpp"
HOST_HEADER = "pc_port/pc_p2_challenge_mode.h"
GUARD_HEADER = "scripts/p2_fixture_captain_guard.h"
GUARD_SHA256 = "d2f678c9eda75e151eb534077dff9e30ad36ae4796881d971bbd09945f3c3474"

ANCHOR_AFTER = "add_test(NAME pc_menu_repeat_test COMMAND pc_menu_repeat_test)"
ANCHOR_NEXT = "# Host software DSP test (not linked into main game)"

PATCH = """--- a/CMakeLists.txt
+++ b/CMakeLists.txt
@@ -606,6 +606,19 @@
 target_compile_options(pc_menu_repeat_test PRIVATE ${NATIVE_COMPILE_OPTIONS})
 add_test(NAME pc_menu_repeat_test COMMAND pc_menu_repeat_test)
 
+# P2 Challenge host-mode guarded fixture (#651). These host-mode files are new
+# additions carried by the #651 lane; registering them in the maintained build
+# touches shared CMake/CTest and therefore requires #186 review before merge.
+# The fixture consumes the canonical #632 captain guard header, which lives in
+# the repository-level scripts/ directory (outside the native include tree).
+add_executable(p2_challenge_mode_fixture
+    tools/p2_challenge_mode_fixture.cpp
+    pc_port/pc_p2_challenge_mode.cpp)
+target_include_directories(p2_challenge_mode_fixture PRIVATE
+    pc_port
+    ${CMAKE_SOURCE_DIR}/../scripts)
+target_compile_options(p2_challenge_mode_fixture PRIVATE ${NATIVE_COMPILE_OPTIONS})
+add_test(NAME p2_challenge_mode_fixture COMMAND p2_challenge_mode_fixture)
+
 # Host software DSP test (not linked into main game)
 add_executable(pc_dsp_host_test
     pc_port/audio/pc_dsp_host_test.cpp
"""

VALIDATION = [
    "git -C <private-native> apply --check output/workflow/autofill/prerequisites/hostmode-registration/patch/registration.patch",
    "git -C <private-native> apply output/workflow/autofill/prerequisites/hostmode-registration/patch/registration.patch",
    "cmake --build <private-build> --target p2_challenge_mode_fixture -j 6",
    "ctest --test-dir <private-build> -R p2_challenge_mode_fixture --output-on-failure",
]


class RegistrationError(ValueError):
    pass


def anchors(cmake_text):
    """Return the exact insertion anchors; fail closed when absent."""
    if ANCHOR_AFTER not in cmake_text:
        raise RegistrationError("Anchor absent: " + ANCHOR_AFTER)
    if ANCHOR_NEXT not in cmake_text:
        raise RegistrationError("Anchor absent: " + ANCHOR_NEXT)
    lines = cmake_text.splitlines()
    at = lines.index(ANCHOR_AFTER) + 1
    nxt = lines.index(ANCHOR_NEXT) + 1
    between = lines[at:nxt - 1]
    if not 0 <= nxt - at <= 2 or any(part.strip() for part in between):
        raise RegistrationError("Anchors are not adjacent")
    return {"insert_after_line": at, "next_line": nxt,
            "after": ANCHOR_AFTER, "next": ANCHOR_NEXT}


def assert_guard(path, expected=GUARD_SHA256):
    """Fail closed unless the canonical #632 guard header hash matches."""
    actual = hashlib.sha256(Path(path).read_bytes()).hexdigest()
    if actual != expected:
        raise RegistrationError("Guard hash mismatch: " + actual)
    return actual


def packet(cmake_text, guard_path, source_pins):
    """Assemble the machine-readable registration packet."""
    where = anchors(cmake_text)
    guard = assert_guard(guard_path)
    return {
        "schema": 1,
        "issue": 661,
        "fixture": FIXTURE,
        "host_module": HOST_MODULE,
        "host_header": HOST_HEADER,
        "guard_header": GUARD_HEADER,
        "guard_sha256": guard,
        "anchor": where,
        "patch": PATCH,
        "patch_sha256": hashlib.sha256(PATCH.encode()).hexdigest(),
        "validation": VALIDATION,
        "source_pins": source_pins,
        "review_owner": "#186 shared build review",
        "downstream": ["#651 challenge-host-mode lane", "#656 host-mode build harness",
                       "P1 challenge stage lanes via #651"],
    }
