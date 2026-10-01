"""Focused tests for the save-dayclock dependency-ready publisher (#132).

The adapter is loaded from its file path (no package init is owned by this
lane). The positive test verifies the REAL done-lane outputs
(`provider-save-dayclock-anchor-audit` inventory, doc, adapter, tests, plus
the research tree); negative tests prove fail-closed boundaries for
tampered, truncated, corrupted or missing inputs. Nothing here builds, runs
the game, or claims gameplay.
"""

import copy
import importlib.util
import json
import unittest
from pathlib import Path


def _root():
    for parent in Path(__file__).resolve().parents:
        if (parent / "output" / "workflow" / "registry.sqlite3").is_file():
            return parent
    raise AssertionError("Canonical workspace root not found")


ROOT = _root()
AUDIT_OUT = (ROOT / "output" / "workflow" / "autofill" / "planning-shards"
             / "provider-save-progression" / "prepared" / "save-anchor-audit")
AUDIT_ROOT = (ROOT / "output" / "workflow" / "autofill" / "planning-shards"
              / "provider-save-progression" / "prepared" / "save-anchor-audit-root")
INVENTORY = AUDIT_OUT / "out" / "inventory.json"
AUDIT_FILES = {
    "inventory": AUDIT_OUT / "out" / "inventory.json",
    "doc": AUDIT_ROOT / "docs" / "PIKMIN2_SAVE_DAYCLOCK_ANCHOR_AUDIT.md",
    "adapter": AUDIT_ROOT / "experimental" / "pikmin2_save_dayclock_anchor_audit.py",
    "tests": AUDIT_ROOT / "tests" / "test_pikmin2_save_dayclock_anchor_audit.py",
}
RESEARCH = ROOT / "native" / "pikmin2-research"

# Pinned lane record, matching the canonical registry
# (provider-save-dayclock-anchor-audit, issue 132, commit 4fff74c7).
LANE_RECORD = {
    "lane": "provider-save-dayclock-anchor-audit",
    "issue": 132,
    "commits": ["4fff74c7ed656c42e24c46b8d9294fc97367b417"],
    "head": "4fff74c7ed656c42e24c46b8d9294fc97367b417",
}


def _load_adapter():
    path = (ROOT / "output" / "workflow" / "autofill" / "planning-shards"
            / "caves-tutorial" / "prepared"
            / "save-dayclock-dependency-ready-root" / "experimental"
            / "pikmin2_save_dayclock_dependency_ready.py")
    spec = importlib.util.spec_from_file_location("save_dayclock_ready", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


ADAPTER = _load_adapter()


class SaveDayclockReadyTests(unittest.TestCase):
    def test_real_audit_outputs_verify(self):
        result = ADAPTER.build(INVENTORY, dict(LANE_RECORD), RESEARCH,
                               {k: str(v) for k, v in AUDIT_FILES.items()})
        self.assertEqual(result["provider"]["commit"], "4fff74c7ed656c42e24c46b8d9294fc97367b417")
        self.assertEqual(sorted(result["anchor_groups"]),
                         ["day_clock", "debt_equipment", "louie_president",
                          "save_migration", "sprout_regeneration", "sunset_loss"])
        self.assertEqual([c["lane"] for c in result["downstream_consumers"]],
                         ["p2-cave-tutorial_2", "p2-cave-tutorial_3"])
        self.assertEqual(result["generated"], False)
        self.assertEqual(result["placements"], [])
        self.assertTrue(result["unevaluated_save_semantics"])
        self.assertEqual(len(result["research_source_pins"]), 2)
        for label, entry in result["audit_files"].items():
            self.assertRegex(entry["sha256"], r"[0-9a-f]{64}")

    def test_incomplete_verdict_rejected(self):
        inventory = json.loads(INVENTORY.read_text(encoding="utf-8"))
        inventory["verdict"] = "partial"
        with self.assertRaises(ValueError):
            ADAPTER.build(self._write(inventory), dict(LANE_RECORD), RESEARCH,
                          self._files())

    def test_missing_group_rejected(self):
        inventory = json.loads(INVENTORY.read_text(encoding="utf-8"))
        inventory["groups"].pop("debt_equipment")
        with self.assertRaises(ValueError):
            ADAPTER.build(self._write(inventory), dict(LANE_RECORD), RESEARCH,
                          self._files())

    def test_empty_group_rejected(self):
        inventory = json.loads(INVENTORY.read_text(encoding="utf-8"))
        inventory["groups"]["sunset_loss"] = []
        with self.assertRaises(ValueError):
            ADAPTER.build(self._write(inventory), dict(LANE_RECORD), RESEARCH,
                          self._files())

    def test_wrong_sources_rejected(self):
        inventory = json.loads(INVENTORY.read_text(encoding="utf-8"))
        inventory["sources"] = {"other.cpp": {}}
        with self.assertRaises(ValueError):
            ADAPTER.build(self._write(inventory), dict(LANE_RECORD), RESEARCH,
                          self._files())

    def test_wrong_commit_rejected(self):
        record = dict(LANE_RECORD, commits=["00000000"], head="00000000")
        with self.assertRaises(ValueError):
            ADAPTER.build(INVENTORY, record, RESEARCH, self._files())

    def test_missing_audit_file_rejected(self):
        files = self._files()
        files["doc"] = str(INVENTORY.parent / "absent.md")
        with self.assertRaises(ValueError):
            ADAPTER.build(INVENTORY, dict(LANE_RECORD), RESEARCH, files)

    def test_missing_inputs_rejected(self):
        with self.assertRaises(ValueError):
            ADAPTER.load_json(INVENTORY.parent / "absent.json")
        with self.assertRaises(ValueError):
            ADAPTER.sha256_file(INVENTORY.parent / "absent.json")
        with self.assertRaises(ValueError):
            ADAPTER.check_hash("not-a-hash", "test")
        with self.assertRaises(ValueError):
            ADAPTER.check_hash("0" * 64, "test")

    def test_cli_writes_record(self):
        import tempfile
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            record = root / "lane.json"
            record.write_text(json.dumps(LANE_RECORD), encoding="utf-8")
            out = root / "dependency-ready.json"
            audit = []
            for label, path in AUDIT_FILES.items():
                audit += ["--audit-file", "%s=%s" % (label, path)]
            ADAPTER.main(["--inventory", str(INVENTORY),
                          "--lane-record", str(record),
                          "--research-root", str(RESEARCH)]
                         + audit + ["--output", str(out)])
            packet = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(packet["schema"], 1)

    def _write(self, inventory):
        import tempfile
        directory = tempfile.mkdtemp()
        path = Path(directory) / "inventory.json"
        path.write_text(json.dumps(inventory), encoding="utf-8")
        self.addCleanup(__import__("shutil").rmtree, directory, True)
        return path

    def _files(self):
        return {k: str(v) for k, v in AUDIT_FILES.items()}


if __name__ == "__main__":
    unittest.main()