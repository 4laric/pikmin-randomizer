"""Tests for the pikidemo.h extern-C guard check (#776). Hermetic synthetic
headers, except one read-only live check against the repaired worktree file.
"""
import unittest
from pathlib import Path

from experimental.pikmin2_pikidemo_externc_guard_check import (
    GuardError,
    check_definition,
    check_header,
    check_pair,
)

GOOD = """\
#ifndef X_H
#define X_H
BEGIN_SCOPE_EXTERN_C
void Jac_DemoSceneInit(void);
#ifdef PIKI_PC_PORT
void Jac_NoteDemoSkipped(void);
#endif
END_SCOPE_EXTERN_C
#endif
"""

BEFORE_FIX = """\
BEGIN_SCOPE_EXTERN_C
void Jac_DemoSceneInit(void);
END_SCOPE_EXTERN_C
#ifdef PIKI_PC_PORT
void Jac_NoteDemoSkipped(void);
#endif
"""

DUP = GOOD.replace("#endif\nEND_SCOPE", "#endif\nvoid Jac_NoteDemoSkipped(void);\nEND_SCOPE")

C_DEF = """\
#include "pikidemo.h"
void Jac_NoteDemoSkipped(void) { demo_was_skipped = TRUE; }
"""


class GuardCheckTests(unittest.TestCase):
    def test_guarded_decl_passes(self):
        result = check_header(GOOD)
        self.assertTrue(result["guarded"])
        self.assertEqual(result["decl_line"], 6)

    def test_unguarded_decl_fails_with_exact_defect(self):
        with self.assertRaisesRegex(GuardError, "outside extern-C guards"):
            check_header(BEFORE_FIX)

    def test_missing_decl_fails(self):
        with self.assertRaisesRegex(GuardError, "missing"):
            check_header("BEGIN_SCOPE_EXTERN_C\nEND_SCOPE_EXTERN_C\n")

    def test_duplicate_decl_rejected(self):
        with self.assertRaisesRegex(GuardError, "2 times"):
            check_header(DUP)

    def test_unbalanced_guards_rejected(self):
        with self.assertRaisesRegex(GuardError, "unbalanced"):
            check_header("void Jac_NoteDemoSkipped(void);\n")
        with self.assertRaisesRegex(GuardError, "missing or empty"):
            check_header("   ")

    def test_definition_present(self):
        result = check_definition(C_DEF)
        self.assertTrue(result["defined"])

    def test_definition_missing(self):
        with self.assertRaisesRegex(GuardError, "definition missing"):
            check_definition("void Other(void) {}\n")

    def test_pair_agrees(self):
        result = check_pair(GOOD, C_DEF)
        self.assertTrue(result["guarded"] and result["defined"])

    def test_live_repaired_header(self):
        path = Path("C:/Users/alari/pikmin-randomizer/output/workflow/autofill/"
                    "prerequisites/jaudio-pikidemo-externc-guard-repair-native/"
                    "include/jaudio/pikidemo.h")
        if not path.is_file():
            self.skipTest("private native worktree absent")
        result = check_header(path.read_text(encoding="utf-8", errors="replace"))
        self.assertTrue(result["guarded"])


if __name__ == "__main__":
    unittest.main()
