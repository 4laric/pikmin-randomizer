"""Focused tests for experimental/pikmin2_cave_runtime_inputs.py (#642).

Valid packages validate clean; every mismatch class is refused with an exact
reason. No engine, no assets, no display needed.
"""

import json
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "experimental"))

from pikmin2_cave_runtime_inputs import build_package, validate_package, PRESETS


PINS = {"root": "07e2126f", "native": "9688995e", "guard": "d2f678c9"}


class CaveRuntimeInputsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="cave-inputs-")
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def pkg(self, cave="forest1"):
        outdir = os.path.join(self.tmp, cave)
        build_package(outdir, cave, PINS)
        return outdir

    def rewrite(self, outdir, name, text):
        with open(os.path.join(outdir, name), "w", encoding="utf-8") as f:
            f.write(text)

    def test_forest1_valid(self):
        outdir = self.pkg("forest1")
        self.assertEqual(validate_package(outdir), [])
        provenance = json.load(open(os.path.join(outdir, "p2-cave-runtime-inputs.json"),
                                    encoding="utf-8"))
        self.assertEqual(provenance["schema"], "p2-cave-runtime-inputs-1")
        self.assertEqual(provenance["cave"], "forest1")
        self.assertEqual(provenance["entry"]["survivors"], 20)
        self.assertEqual(provenance["source_pins"], PINS)
        self.assertIn("P2_CAVE_GUARDED_BOOT_PASS", provenance["expected_markers"])

    def test_yakushima4_valid(self):
        outdir = self.pkg("yakushima4")
        self.assertEqual(validate_package(outdir), [])
        provenance = json.load(open(os.path.join(outdir, "p2-cave-runtime-inputs.json"),
                                    encoding="utf-8"))
        self.assertEqual(provenance["cave"], "yakushima4")

    def test_presets_differ(self):
        self.assertNotEqual(PRESETS["forest1"]["token"], PRESETS["yakushima4"]["token"])
        self.assertNotEqual(PRESETS["forest1"]["pool"], PRESETS["yakushima4"]["pool"])

    def test_unknown_cave_refused(self):
        with self.assertRaises(ValueError):
            build_package(os.path.join(self.tmp, "nope"), "no-such-cave", PINS)

    def test_missing_files(self):
        self.assertEqual(validate_package(os.path.join(self.tmp, "absent")),
                         ["missing-entry-file"])
        outdir = self.pkg()
        os.remove(os.path.join(outdir, "p2-cave-generate.txt"))
        self.assertEqual(validate_package(outdir), ["missing-generate-file"])
        outdir = self.pkg()
        os.remove(os.path.join(outdir, "p2-cave-runtime-inputs.json"))
        self.assertEqual(validate_package(outdir), ["missing-or-bad-provenance"])

    def test_bad_entry_header(self):
        outdir = self.pkg()
        self.rewrite(outdir, "p2-cave-entry.txt", "P2_CAVE_ENTRY_9 %s 1 1.0 20\n" % ("a" * 32))
        self.assertIn("entry-version", validate_package(outdir))
        self.rewrite(outdir, "p2-cave-entry.txt",
                     "P2_CAVE_ENTRY_1 NOTHEX 1 1.0 1\n1 1\n")
        self.assertIn("entry-token", validate_package(outdir))
        self.rewrite(outdir, "p2-cave-entry.txt",
                     "P2_CAVE_ENTRY_1 %s 5 1.0 1\n1 1\n" % ("a" * 32))
        self.assertIn("entry-floor", validate_package(outdir))
        self.rewrite(outdir, "p2-cave-entry.txt",
                     "P2_CAVE_ENTRY_1 %s 1 1.0 3\n1 1\n1 1\n" % ("a" * 32))
        self.assertIn("entry-count-mismatch", validate_package(outdir))
        self.rewrite(outdir, "p2-cave-entry.txt",
                     "P2_CAVE_ENTRY_1 %s 1 1.0 1\n9 9\n" % ("a" * 32))
        self.assertIn("entry-survivor-0", validate_package(outdir))

    def test_bad_generate_manifest(self):
        outdir = self.pkg()
        entry = open(os.path.join(outdir, "p2-cave-entry.txt"), encoding="utf-8").read()
        self.rewrite(outdir, "p2-cave-generate.txt", "P2_CAVE_GENERATE_9\n")
        self.assertIn("generate-pool", validate_package(outdir))
        self.rewrite(outdir, "p2-cave-generate.txt",
                     "P2_CAVE_GENERATE_1\npool x 1\nunit 0 x -5 5 0\nrooms 1\n"
                     "room 0 0 0 0 0 0\ndoors 0\nlinks 0\nspawns 1\nspawn Bulborb 1\nanchor hole\n")
        self.assertIn("generate-unit-0", validate_package(outdir))
        self.rewrite(outdir, "p2-cave-generate.txt",
                     "P2_CAVE_GENERATE_1\npool x 1\nunit 0 x 5 5 0\nrooms 1\n"
                     "room 0 0 0 0 0 0\ndoors 0\nlinks 0\nspawns 1\nspawn Bulborb 1\nanchor lake\n")
        self.assertIn("generate-anchor", validate_package(outdir))
        self.rewrite(outdir, "p2-cave-generate.txt",
                     "P2_CAVE_GENERATE_1\npool x 1\nunit 0 x 5 5 0\nrooms 1\n"
                     "room 0 0 0 0 0 0\ndoors 0\nlinks 0\nspawns 1\nspawn Bulborb 1\nanchor hole\nEXTRA\n")
        self.assertIn("generate-trailing-data", validate_package(outdir))
        # entry file untouched throughout
        self.assertEqual(open(os.path.join(outdir, "p2-cave-entry.txt"),
                              encoding="utf-8").read(), entry)

    def test_provenance_hash_mismatch(self):
        outdir = self.pkg()
        with open(os.path.join(outdir, "p2-cave-generate.txt"), "a", encoding="utf-8") as f:
            f.write("# tampered\n")
        problems = validate_package(outdir)
        self.assertIn("provenance-generate-hash-mismatch", problems)

    def test_bad_provenance_schema(self):
        outdir = self.pkg()
        path = os.path.join(outdir, "p2-cave-runtime-inputs.json")
        provenance = json.load(open(path, encoding="utf-8"))
        provenance["schema"] = "something-else-9"
        json.dump(provenance, open(path, "w", encoding="utf-8"))
        self.assertIn("bad-provenance-schema", validate_package(outdir))


if __name__ == "__main__":
    unittest.main()