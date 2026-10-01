"""Landing-validation tests (issue #703). Hermetic by design: synthetic trees
and texts only, so the suite never depends on other lanes worktrees; the
real-path verification against committed #616 runs separately and is logged,
not pytest."""
import importlib.util
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
ADAPTER_PATH = ROOT / "experimental" / "pikmin2_bomb_mgr_birth_landing.py"
_spec = importlib.util.spec_from_file_location("pikmin2_bomb_mgr_birth_landing", ADAPTER_PATH)
adapter = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(adapter)


def make_tree(tmp, files):
    base = Path(tmp) / "wt"
    for relpath, content in files.items():
        path = base / relpath
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
    return base


def getter_for(base):
    def read(relpath):
        path = Path(base) / relpath
        if not path.is_file():
            raise adapter.LandingError("missing: " + relpath)
        return path.read_bytes()
    return read


GOOD_FILES = {
    "root/docs/PIKMIN2_BOMB_MGR_BIRTH_LANDING.md": b"# landing\n",
    "root/experimental/pikmin2_bomb_mgr_birth_landing.py": b"SCHEMA = 1\n",
    "root/tests/test_pikmin2_bomb_mgr_birth_landing.py": b"import unittest\n",
    "native/pc_port/pc_p2_bomb_mgr_birth.h": b"// manager api\n",
    "native/pc_port/pc_p2_bomb_mgr_birth.cpp": b"// manager core\n",
    "native/tools/p2_bomb_mgr_birth_test.cpp": b"// fixture test\n",
}

GOOD_DOC = """P2BombPayloadPool pc_p2_bomb_payload_actor.h d9ca3b08 3aad911e
tekibteki pc_p2_teki_lifetime lifetime CMake source_id=36 #186 generalEnemyMgr
"""
GOOD_HEADER = """P2_BOMB_MGR_SOURCE_ID P2BombMgrHandle pc_p2_bomb_mgr_birth_manager
pc_p2_bomb_mgr_birth_reset pc_p2_bomb_mgr_birth_setup pc_p2_bomb_mgr_birth_carrier
pc_p2_bomb_mgr_birth_update pc_p2_bomb_mgr_birth_forget pc_p2_bomb_mgr_birth_ready
"""
GOOD_CPP = "// manager core without Section-3\n"
GOOD_BUILDER = "def expand_response(line, build):\n    # splices @file.rsp content\n"
GOOD_HOOK = "tekibteki lifetime CMake generalEnemyMgr shared hook\n"

GOOD_HANDOFF = {"schema": 1, "kind": "tooling", "lane": "x", "issue": 1,
                "generation": 1}


class PinTableTests(unittest.TestCase):
    def test_constants(self):
        self.assertEqual(adapter.SOURCE_ID, 36)
        self.assertEqual(adapter.PROVIDER_ISSUE, 616)
        self.assertEqual(len(adapter.REVIEW_PINS), 6)

    def test_pin_table_ok(self):
        ok, _ = adapter.check_pin_table(adapter.REVIEW_PINS)
        self.assertTrue(ok)

    def test_pin_table_rejects_garbage(self):
        for bad in ({}, {"a": "zz"}, {"a": "0" * 63}, {"": "0" * 64}, {"a": 0}):
            ok, _ = adapter.check_pin_table(bad)
            self.assertFalse(ok)


class VerifyFilesTests(unittest.TestCase):
    def test_positive_tmp_tree(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            base = make_tree(tmp, GOOD_FILES)
            pins = {k: adapter.sha256_bytes((base / k).read_bytes()) for k in GOOD_FILES}
            ok, _, detail = adapter.verify_files(getter_for(base), pins)
            self.assertTrue(ok)
            self.assertEqual(len(detail), 6)

    def test_missing_file_fails_closed(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            base = make_tree(tmp, GOOD_FILES)
            pins = {k: adapter.sha256_bytes((base / k).read_bytes()) for k in GOOD_FILES}
            (base / "native/tools/p2_bomb_mgr_birth_test.cpp").unlink()
            ok, why = adapter.verify_files(getter_for(base), pins)[:2]
            self.assertFalse(ok)
            self.assertIn("p2_bomb_mgr_birth_test.cpp", why)

    def test_drift_fails_closed(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            base = make_tree(tmp, GOOD_FILES)
            pins = {k: adapter.sha256_bytes((base / k).read_bytes()) for k in GOOD_FILES}
            (base / "root/docs/PIKMIN2_BOMB_MGR_BIRTH_LANDING.md").write_bytes(b"# drifted\n")
            ok, why = adapter.verify_files(getter_for(base), pins)[:2]
            self.assertFalse(ok)
            self.assertIn("drift", why)

    def test_empty_pins_rejected(self):
        ok, _ = adapter.verify_files(lambda rel: b"", {})[:2]
        self.assertFalse(ok)


class TokenTests(unittest.TestCase):
    def test_doc_tokens(self):
        ok, _ = adapter.check_tokens(GOOD_DOC, adapter.DOC_REQUIRED_TOKENS, "doc")
        self.assertTrue(ok)

    def test_doc_missing_token_fails(self):
        ok, why = adapter.check_tokens("nothing here", adapter.DOC_REQUIRED_TOKENS, "doc")
        self.assertFalse(ok)
        self.assertIn("missing", why)

    def test_empty_input_fails(self):
        ok, _ = adapter.check_tokens("", adapter.DOC_REQUIRED_TOKENS, "doc")
        self.assertFalse(ok)

    def test_header_api(self):
        ok, _ = adapter.check_tokens(GOOD_HEADER, adapter.HEADER_REQUIRED_TOKENS, "header")
        self.assertTrue(ok)

    def test_no_section3_clean(self):
        ok, _ = adapter.check_no_section3(GOOD_CPP, "core")
        self.assertTrue(ok)

    def test_no_section3_trips(self):
        bad = GOOD_CPP + "bool " + adapter.SECTION3_MARKER + "(void*);\n"
        ok, why = adapter.check_no_section3(bad, "core")
        self.assertFalse(ok)
        self.assertIn("duplication", why)

    def test_builder_tokens(self):
        ok, _ = adapter.check_tokens(GOOD_BUILDER, adapter.BUILDER_RSP_TOKENS, "builder")
        self.assertTrue(ok)

    def test_hook_tokens(self):
        ok, _ = adapter.check_tokens(GOOD_DOC + "\n" + GOOD_HOOK, adapter.HOOK_ANCHORS, "hook")
        self.assertTrue(ok)


class HandoffTests(unittest.TestCase):
    def test_positive_tmp_handoff(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "handoff.json"
            path.write_text(json.dumps(GOOD_HANDOFF), encoding="utf-8")
            ok, _, data = adapter.check_handoff(path)
            self.assertTrue(ok)
            self.assertEqual(data["lane"], "x")

    def test_missing_handoff_fails(self):
        ok, _ = adapter.check_handoff("/nonexistent/handoff.json")[:2]
        self.assertFalse(ok)

    def test_bad_schema_fails(self):
        import tempfile
        bad = dict(GOOD_HANDOFF, schema=2)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "handoff.json"
            path.write_text(json.dumps(bad), encoding="utf-8")
            ok, _ = adapter.check_handoff(path)[:2]
            self.assertFalse(ok)

    def test_wrong_kind_fails(self):
        import tempfile
        bad = dict(GOOD_HANDOFF, kind="runtime")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "handoff.json"
            path.write_text(json.dumps(bad), encoding="utf-8")
            ok, _ = adapter.check_handoff(path)[:2]
            self.assertFalse(ok)

    def test_missing_keys_fail(self):
        import tempfile
        bad = {"schema": 1, "kind": "tooling"}
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "handoff.json"
            path.write_text(json.dumps(bad), encoding="utf-8")
            ok, _ = adapter.check_handoff(path)[:2]
            self.assertFalse(ok)


class LandingTests(unittest.TestCase):
    def _refs(self, **over):
        refs = {"builder": GOOD_BUILDER, "hook666": GOOD_HOOK,
                "header616": GOOD_HEADER, "cpp616": GOOD_CPP, "doc616": GOOD_DOC}
        refs.update(over)
        return refs

    def test_positive_end_to_end(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            base = make_tree(tmp, GOOD_FILES)
            pins = {k: adapter.sha256_bytes((base / k).read_bytes()) for k in GOOD_FILES}
            refs = self._refs()
            ok, _, report = adapter.validate_landing(
                getter_for(base), lambda name: refs[name], pins)
            self.assertTrue(ok)
            self.assertTrue(report["pins"]["ok"])

    def test_drift_blocks_landing(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            base = make_tree(tmp, GOOD_FILES)
            pins = {k: adapter.sha256_bytes((base / k).read_bytes()) for k in GOOD_FILES}
            (base / "native/pc_port/pc_p2_bomb_mgr_birth.cpp").write_bytes(b"// drift\n")
            refs = self._refs()
            ok, why = adapter.validate_landing(
                getter_for(base), lambda name: refs[name], pins)[:2]
            self.assertFalse(ok)
            self.assertIn("pin", why)

    def test_section3_blocks_landing(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            base = make_tree(tmp, GOOD_FILES)
            pins = {k: adapter.sha256_bytes((base / k).read_bytes()) for k in GOOD_FILES}
            refs = self._refs(cpp616=GOOD_CPP + "bool " + adapter.SECTION3_MARKER + "(void*);\n")
            ok, why = adapter.validate_landing(
                getter_for(base), lambda name: refs[name], pins)[:2]
            self.assertFalse(ok)

    def test_missing_reference_blocks_landing(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            base = make_tree(tmp, GOOD_FILES)
            pins = {k: adapter.sha256_bytes((base / k).read_bytes()) for k in GOOD_FILES}

            def read_other(name):
                if name == "builder":
                    raise adapter.LandingError("no builder")
                return self._refs()[name]
            ok, _ = adapter.validate_landing(getter_for(base), read_other, pins)[:2]
            self.assertFalse(ok)


if __name__ == "__main__":
    unittest.main()
