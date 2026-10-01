"""Focused tests for the challenge persistence provider pin-discovery audit (#136).

Hermetic: the positive/negative matrix drives the audit through an injected
read-only content provider. One real-repo test additionally runs the audit on
the actual pinned blobs when the git object database is available, and is
skipped otherwise. All fail-closed behaviour is asserted.
"""
import hashlib
import os
import subprocess
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from experimental import pikmin2_challenge_persistence_provider_audit as audit_mod


def _sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _doc(*lines):
    return "\n".join(lines) + "\n"


CONTRACT_DOC = _doc(
    "line1",
    "line2",
    "Unsupported (no port evidence - do not claim): 1P Challenge host mode",
    "line4",
    "`treasure_count_field` semantics unproven); unlock persistence wiring",
)
CONTRACT_MOD = _doc(
    "line1",
    "            'surface_saves_132': 'Day/save persistence incl. challenge clear flags and highscores (PlayCommonData).',",
    "line3",
    "                    actors='#130/#131', saves_unlocks='#132', treasure='#140',",
)
PLAIN_DOC = _doc("surface session contract", "checkpoint write/read/validate", "no challenge terms here")


def _pins(docs):
    pins = {}
    for key, (path, text) in docs.items():
        pins[key] = {"commit": "c" * 40, "path": path, "blob": "b" * 40, "sha256": _sha(text)}
    return pins


def _show_factory(docs):
    def show(root, commit, path):
        for _key, (doc_path, text) in docs.items():
            if doc_path == path:
                return text
        raise audit_mod.AuditError("missing doc " + path)
    return show


def _blob_factory(_docs):
    def blob(root, commit, path):
        return "b" * 40
    return blob


class ChallengePersistenceProviderAuditTests(unittest.TestCase):
    def setUp(self):
        self.docs = {
            "contract_doc": ("docs/contract.md", CONTRACT_DOC),
            "contract_mod": ("experimental/contract.py", CONTRACT_MOD),
            "surface_doc": ("docs/surface.md", PLAIN_DOC),
            "cavesave_doc": ("docs/cavesave.md", PLAIN_DOC),
            "dayclock_doc": ("docs/dayclock.md", PLAIN_DOC),
        }
        self.pins = _pins(self.docs)
        self.anchors = {
            "contract_doc": {3: "Unsupported (no port evidence - do not claim)", 5: "unlock persistence wiring"},
            "contract_mod": {2: "surface_saves_132", 4: "saves_unlocks='#132'"},
        }
        self.docs_keys = ("surface_doc", "cavesave_doc", "dayclock_doc")

    def _audit(self, pins=None, anchors=None):
        return audit_mod.audit(
            "root",
            show=_show_factory(self.docs),
            blob=_blob_factory(self.docs),
            pins=pins or self.pins,
            anchors=anchors or self.anchors,
            docs=self.docs_keys,
        )

    def test_valid_audit_publishes_provider_and_slice(self):
        verdict = self._audit()
        self.assertTrue(verdict["valid"])
        self.assertEqual(verdict["schema"], audit_mod.SCHEMA)
        self.assertEqual(verdict["provider"]["key"], "challenge_persistence")
        self.assertEqual(verdict["provider"]["producer_status"], "absent")
        owner = verdict["provider"]["concrete_owner"]
        self.assertEqual(owner["lane"], "p2-challenge-persistence-wiring")
        self.assertEqual(owner["issue"], 136)
        self.assertEqual(verdict["downstream_consumer"], 561)
        self.assertEqual(set(verdict["gates"].values()), {"UNTESTED"})
        self.assertEqual(len(verdict["citations"]), 4)
        self.assertTrue(all("path" in c and "line" in c for c in verdict["citations"]))
        self.assertEqual(len(verdict["landed_contracts_checked"]), 3)

    def test_content_hash_mismatch_fails_closed(self):
        pins = _pins(self.docs)
        pins["contract_doc"]["sha256"] = "0" * 64
        with self.assertRaises(audit_mod.AuditError):
            self._audit(pins=pins)

    def test_blob_mismatch_fails_closed(self):
        def bad_blob(root, commit, path):
            return "deadbeef" * 5
        with self.assertRaises(audit_mod.AuditError):
            audit_mod.audit("root", show=_show_factory(self.docs), blob=bad_blob,
                            pins=self.pins, anchors=self.anchors, docs=self.docs_keys)

    def test_missing_contract_anchor_fails_closed(self):
        anchors = dict(self.anchors)
        anchors["contract_doc"] = {3: "Unsupported (no port evidence - do not claim)", 5: "a-token-not-present"}
        with self.assertRaises(audit_mod.AuditError):
            self._audit(anchors=anchors)

    def test_anchor_line_out_of_range_fails_closed(self):
        anchors = {"contract_doc": {999: "unlock persistence wiring"}}
        with self.assertRaises(audit_mod.AuditError):
            self._audit(anchors=anchors)

    def test_unexpected_challenge_anchor_in_132_doc_fails_closed(self):
        docs = dict(self.docs)
        docs["surface_doc"] = ("docs/surface.md", _doc("surface", "challenge clear flag persisted", "x"))
        with self.assertRaises(audit_mod.AuditError):
            audit_mod.audit("root", show=_show_factory(docs), blob=_blob_factory(docs),
                            pins=self.pins, anchors=self.anchors, docs=self.docs_keys)

    def test_missing_owner_decision_fails_closed(self):
        broken = dict(audit_mod.PROVIDER)
        broken["concrete_owner"] = {"lane": "", "issue": 0}
        original = audit_mod.PROVIDER
        audit_mod.PROVIDER = broken
        try:
            with self.assertRaises(audit_mod.AuditError):
                self._audit()
        finally:
            audit_mod.PROVIDER = original

    def test_first_slice_is_disjoint_and_bounded(self):
        spec = audit_mod.first_slice_spec()
        self.assertEqual(spec["id"], "p2-challenge-persistence-wiring-v1")
        self.assertEqual(spec["issue"], 136)
        self.assertEqual(spec["downstream_consumer"], 561)
        self.assertTrue(all(f.startswith(("experimental/", "tests/", "docs/")) for f in spec["owned_files"]))
        self.assertIn("challenge", spec["deliverable"].lower())

    def test_first_slice_overlap_detected(self):
        original = list(audit_mod.FIRST_SLICE["owned_files"])
        audit_mod.FIRST_SLICE["owned_files"] = ["experimental/content_lanes/p2-challenge-ch_mat_route_rover.py"]
        try:
            with self.assertRaises(audit_mod.AuditError):
                audit_mod.first_slice_spec()
        finally:
            audit_mod.FIRST_SLICE["owned_files"] = original

    def test_cli_reports_invalid_without_crashing(self):
        code = audit_mod.main(["--root", "root", "--json"])
        self.assertIn(code, (0, 2))


class RealPinsIntegrationTest(unittest.TestCase):
    """Runs the audit on the actual pinned blobs when the object DB is present."""

    def _repo_root(self):
        for parent in Path(__file__).resolve().parents:
            if (parent / ".git").exists():
                return parent
        return None

    def test_real_pins_audit_or_skip(self):
        root = self._repo_root()
        if root is None:
            self.skipTest("no git worktree available")
        probe = subprocess.run(
            ["git", "-C", str(root), "cat-file", "-t", audit_mod.PINS["contract_doc"]["commit"]],
            capture_output=True, text=True,
        )
        if probe.returncode != 0 or probe.stdout.strip() != "commit":
            self.skipTest("pinned framework contract commit not present")
        verdict = audit_mod.audit(str(root))
        self.assertTrue(verdict["valid"])
        self.assertEqual(verdict["provider"]["producer_status"], "absent")
        self.assertEqual(verdict["downstream_consumer"], 561)
        pins = {c["pin"] for c in verdict["citations"]}
        self.assertIn("contract_doc", pins)
        self.assertIn("contract_mod", pins)


if __name__ == "__main__":
    unittest.main()