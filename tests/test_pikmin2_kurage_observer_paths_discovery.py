"""Focused designation tests: disjointness, pins, scope, fail-closed (#753)."""
import json
import unittest
from pathlib import Path

import experimental.pikmin2_kurage_observer_paths_discovery as paths


class DisjointTests(unittest.TestCase):
    def test_zero_overlap_with_owner(self):
        self.assertTrue(paths.check_disjoint())
        self.assertEqual(
            sorted(set(paths.DESIGNATED_PATHS) & set(paths.OWNER_PATHS)), [])

    def test_owner_paths_exact(self):
        self.assertEqual(list(paths.OWNER_PATHS), [
            "experimental/pikmin2_muse_kurage.py",
            "tests/test_pikmin2_muse_kurage.py",
            "docs/PIKMIN2_MUSE_KURAGE_HANDOFF.md",
            "native/tools/p2_muse_kurage_fixture.cpp",
        ])

    def test_empty_designation_fails_closed(self):
        with self.assertRaises(paths.AmbiguousOwnershipError):
            paths.check_disjoint([], paths.OWNER_PATHS)

    def test_overlap_fails_closed(self):
        with self.assertRaises(paths.AmbiguousOwnershipError):
            paths.check_disjoint(
                ["experimental/pikmin2_muse_kurage.py"], paths.OWNER_PATHS)


class VerdictTests(unittest.TestCase):
    def test_verdict_structure(self):
        verdict = paths.compatibility_verdict()
        self.assertTrue(verdict["compatible"])
        self.assertEqual(verdict["owner_issue"], 498)
        self.assertEqual(verdict["source_id"], 57)
        self.assertEqual(len(verdict["designated_paths"]), 4)
        self.assertTrue(all(row["file"] and row["role"]
                            for row in verdict["consumer_pins"]))

    def test_taken_path_fails_closed(self):
        with self.assertRaises(paths.AmbiguousOwnershipError):
            paths.compatibility_verdict(
                taken=["tests/test_pikmin2_kurage57_observer.py"])


class ScopeTests(unittest.TestCase):
    def test_scope_shape(self):
        scope = paths.observer_scope()
        self.assertEqual(scope["owned_files"],
                         list(paths.DESIGNATED_PATHS))
        self.assertEqual(len(scope["acceptance"]), 3)
        self.assertIn("498", scope["scope"])

    def test_cli_roundtrip(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "designation.json"
            self.assertEqual(paths.main(["--out", str(target)]), 0)
            payload = json.loads(target.read_text(encoding="utf-8"))
            self.assertTrue(payload["verdict"]["compatible"])
            self.assertEqual(payload["observer_scope"]["owned_files"],
                             list(paths.DESIGNATED_PATHS))


if __name__ == "__main__":
    unittest.main()