"""Focused tests for the BombOtakara93 detonation-driver discovery (#806)."""
import importlib.util
import os
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))


def _load():
    path = os.path.join(_HERE, '..', 'experimental',
                        'pikmin2_bombotakara_detonation_driver_discovery.py')
    spec = importlib.util.spec_from_file_location('deto_discovery', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


M = _load()


def _canonical():
    cur = os.path.abspath(os.path.join(_HERE, '..'))
    for _ in range(12):
        if os.path.isdir(os.path.join(cur, 'native')) and os.path.isdir(os.path.join(cur, 'output')):
            return cur
        parent = os.path.dirname(cur)
        if parent == cur:
            break
        cur = parent
    return None


ROOT = _canonical()
NATIVE_REPO = os.path.join(ROOT, 'native') if ROOT else None
OWNER_573 = os.path.join(ROOT, 'output', 'autofill-native-573', 'pc_port') if ROOT else None


class HelperTests(unittest.TestCase):
    def test_check_symbols(self):
        found, missing = M.check_symbols("alpha beta gamma", ["alpha", "delta"])
        self.assertEqual(found, ["alpha"])
        self.assertEqual(missing, ["delta"])

    def test_check_symbols_empty(self):
        found, missing = M.check_symbols("anything", [])
        self.assertEqual(found, [])
        self.assertEqual(missing, [])

    def test_git_show_absent(self):
        if NATIVE_REPO is None or not os.path.isdir(NATIVE_REPO):
            self.skipTest("native checkout absent")
        self.assertIsNone(M.git_show(NATIVE_REPO, M.NATIVE_PIN, "pc_port/no_such_file_xyz.cpp"))

    def test_git_show_present(self):
        if NATIVE_REPO is None or not os.path.isdir(NATIVE_REPO):
            self.skipTest("native checkout absent")
        blob = M.git_show(NATIVE_REPO, M.NATIVE_PIN, "pc_port/pc_p2_bombsarai_blast.h")
        self.assertIsNotNone(blob)
        self.assertIn(b"p2_bombsarai_route_blast", blob)


class PinShapeTests(unittest.TestCase):
    def test_boundaries(self):
        self.assertEqual(set(M.MAINTAINED),
                         {"shared_blast_primitive", "teki_forget_seam",
                          "payload_detonate_gate", "birth_hook_detonate"})

    def test_expectations(self):
        self.assertEqual(M.MAINTAINED["shared_blast_primitive"]["expect"], "present")
        self.assertEqual(M.MAINTAINED["teki_forget_seam"]["expect"], "present")
        self.assertEqual(M.MAINTAINED["payload_detonate_gate"]["expect"], "absent")
        self.assertEqual(M.MAINTAINED["birth_hook_detonate"]["expect"], "absent")

    def test_owners(self):
        self.assertEqual(M.OWNERS["payload_detonate_gate"]["issue"], 573)
        self.assertEqual(M.OWNERS["birth_hook_detonate"]["issue"], 616)

    def test_consumer(self):
        self.assertEqual(M.CONSUMER_LANE, "enemy-bombotakara93-payload")
        self.assertIn("run_pikmin2_fixture", M.CONSUMER_COMMAND)


class MalformedTests(unittest.TestCase):
    def test_missing_maintained_repo(self):
        with self.assertRaises(Exception):
            M.verify_maintained(os.path.join(_HERE, "no-such-native"), M.NATIVE_PIN)

    def test_missing_owner_tree(self):
        with self.assertRaises(M.DiscoveryRejected):
            M.verify_owner(os.path.join(_HERE, "no-such-owner"),
                           {"x.cpp": ["sym"]})

    def test_owner_symbol_missing(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            with open(os.path.join(tmp, "x.cpp"), "w") as fh:
                fh.write("nothing relevant here\n")
            with self.assertRaises(M.DiscoveryRejected):
                M.verify_owner(tmp, {"x.cpp": ["missing_symbol_xyz"]})

    def test_emit_refuses_overwrite(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            target = os.path.join(tmp, "bombotakara93-detonation-driver-registry.json")
            with open(target, "w") as fh:
                fh.write("{}\n")
            with self.assertRaises(M.DiscoveryRejected):
                M.emit_registry(NATIVE_REPO or tmp, tmp, tmp, tmp)


class LivePinTests(unittest.TestCase):
    def test_maintained_verdicts(self):
        if NATIVE_REPO is None or not os.path.isdir(NATIVE_REPO):
            self.skipTest("native checkout absent")
        if OWNER_573 is None or not os.path.isdir(OWNER_573):
            self.skipTest("owner-573 tree absent")
        found = M.verify_maintained(NATIVE_REPO, M.NATIVE_PIN)
        self.assertEqual(found["shared_blast_primitive"]["verdict"], "PRESENT")
        self.assertEqual(found["teki_forget_seam"]["verdict"], "PRESENT")
        self.assertEqual(found["payload_detonate_gate"]["verdict"], "ABSENT")
        self.assertEqual(found["birth_hook_detonate"]["verdict"], "ABSENT")

    def test_owner_verdicts(self):
        if OWNER_573 is None or not os.path.isdir(OWNER_573):
            self.skipTest("owner-573 tree absent")
        if NATIVE_REPO is None or not os.path.isdir(NATIVE_REPO):
            self.skipTest("native checkout absent")
        payload = M.verify_owner(OWNER_573, M.OWNERS["payload_detonate_gate"]["files"])
        self.assertIn("pc_p2_bombotakara.cpp", payload)
        birth = M.verify_owner(NATIVE_REPO + "/pc_port", {
            "pc_p2_bomb_mgr_birth.h": ["int detonate(P2BombMgrHandle"],
            "pc_p2_bomb_mgr_birth.cpp": ["P2BombMgr::detonate"]})
        self.assertIn("pc_p2_bomb_mgr_birth.cpp", birth)

    def test_registry_shape(self):
        if NATIVE_REPO is None or OWNER_573 is None:
            self.skipTest("reference trees absent")
        if not (os.path.isdir(NATIVE_REPO) and os.path.isdir(OWNER_573)):
            self.skipTest("reference trees absent")
        reg = M.build_registry(NATIVE_REPO, OWNER_573, NATIVE_REPO)
        self.assertEqual(reg["schema"], M.SCHEMA)
        self.assertEqual(set(reg["items"]),
                         {"payload_detonate_gate", "birth_hook_detonate",
                          "shared_blast_primitive", "teki_forget_seam"})
        self.assertEqual(reg["consumer"]["lane"], "enemy-bombotakara93-payload")


if __name__ == "__main__":
    unittest.main()
