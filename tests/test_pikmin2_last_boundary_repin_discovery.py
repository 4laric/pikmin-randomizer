"""Focused tests for the AREA LAST boundary re-pin discovery (#151).

Uses a synthetic fixture tree for grammar/negative tests plus the real
read-only research tree for one smoke pin per boundary family. No builds,
no runtime, no ADMIT.
"""
import copy
import importlib.util
import unittest
from pathlib import Path


def _load_module():
    path = (Path(__file__).resolve().parents[1] / "experimental" /
            "pikmin2_last_boundary_repin_discovery.py")
    spec = importlib.util.spec_from_file_location("last_boundary_repin", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


MOD = _load_module()

REAL_PINS = [
    ("research", "src/plugProjectKandoU/singleGameSection.cpp", 183, "init"),
    ("research", "src/plugProjectKandoU/gamePlayDataMemCard.cpp", 39, "write"),
    ("research", "src/plugProjectKandoU/onyonMgr.cpp", 403, "actOnyon"),
    ("research", "src/plugProjectKandoU/gameGeneratorCache.cpp", 557, "read"),
    ("native", "pc_port/pc_bbft.cpp", 44, "--experimental-pikmin2-room"),
]


def _fixture_tree():
    """Build a synthetic tree covering every registry pin line.

    For each registry file, filler lines are written with the recorded
    symbol placed at each recorded line, so the full registry verifies
    against fixture roots exactly like the smoke pins do.
    """
    import tempfile
    directory = Path(tempfile.mkdtemp())
    roots = {"research": directory / "research",
             "native": directory / "native"}
    by_file = {}
    for item in MOD.registry()["items"]:
        for pin in item["pins"]:
            by_file.setdefault((pin.get("root", "research"), pin["file"]),
                               []).append((pin["line"], pin["symbol"]))
    for (root_name, rel), wants in by_file.items():
        target = roots[root_name] / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        width = max(line for line, _ in wants)
        lines = ["filler %d" % i for i in range(width)]
        for line, symbol in wants:
            lines[line - 1] = symbol
        target.write_text("\n".join(lines) + "\n", encoding="utf-8")
    for root in roots.values():
        assert root.is_dir()
    return roots


class RegistryShapeTests(unittest.TestCase):
    def test_five_boundaries_exact_ids(self):
        data = MOD.registry()
        self.assertEqual(data["schema"], 1)
        self.assertEqual(data["issue"], 151)
        self.assertEqual(data["area"], "last")
        self.assertEqual([item["id"] for item in data["items"]],
                         ["overworld_boot", "day_advance", "save_serializer",
                          "receipt_ledger", "exit_reentry"])

    def test_exactly_one_consumable(self):
        data = MOD.registry()
        consumable = [item["id"] for item in data["items"]
                      if item["status"] == "consumable"]
        self.assertEqual(consumable, ["save_serializer"])

    def test_no_duplicate_pins_within_boundary(self):
        for item in MOD.registry()["items"]:
            keys = [(pin["file"], pin["line"]) for pin in item["pins"]]
            self.assertEqual(len(keys), len(set(keys)), item["id"])

    def test_owner_or_review_every_boundary(self):
        for item in MOD.registry()["items"]:
            self.assertTrue(item.get("owner") or item.get("shared_review"),
                            item["id"])

    def test_consumable_has_downstream_and_no_wall_reason(self):
        item = next(i for i in MOD.registry()["items"]
                    if i["id"] == "save_serializer")
        self.assertTrue(item["downstream"]["files"])
        self.assertTrue(item["downstream"]["acceptance"])
        self.assertIsNone(item["wall_reason"])

    def test_walls_have_reasons_and_no_downstream(self):
        for item in MOD.registry()["items"]:
            if item["status"] != "wall":
                continue
            self.assertTrue(item["wall_reason"], item["id"])
            self.assertIsNone(item["downstream"], item["id"])

    def test_no_invented_pins_all_traceable(self):
        for item in MOD.registry()["items"]:
            for pin in item["pins"]:
                self.assertTrue(pin["verified"].startswith(
                    ("fresh-", "carried-#")), (item["id"], pin))


class PinVerificationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.roots = _fixture_tree()

    def test_fixture_pins_verify(self):
        for root, path, line, symbol in REAL_PINS:
            pin = {"file": path, "line": line, "symbol": symbol, "root": root,
                   "role": "fixture check"}
            self.assertTrue(MOD.verify_pin(pin, self.roots))

    def test_wrong_symbol_rejected(self):
        pin = {"file": "src/plugProjectKandoU/singleGameSection.cpp",
               "line": 183, "symbol": "NoSuchSymbol", "role": "x"}
        with self.assertRaises(MOD.BoundaryError):
            MOD.verify_pin(pin, self.roots)

    def test_missing_key_and_bad_line_rejected(self):
        with self.assertRaises(MOD.BoundaryError):
            MOD.verify_pin({"file": "x", "line": 1, "role": "x"}, self.roots)
        with self.assertRaises(MOD.BoundaryError):
            MOD.verify_pin({"file": "x", "line": 0, "symbol": "y",
                            "role": "x"}, self.roots)

    def test_absent_file_rejected(self):
        pin = {"file": "src/plugProjectKandoU/nope.cpp", "line": 1,
               "symbol": "x", "role": "x"}
        with self.assertRaises(MOD.BoundaryError):
            MOD.verify_pin(pin, self.roots)

    def test_real_research_pins_verify_fresh(self):
        for root, path, line, symbol in REAL_PINS:
            pin = {"file": path, "line": line, "symbol": symbol, "root": root,
                   "role": "smoke"}
            self.assertTrue(MOD.verify_pin(pin))

    def test_full_registry_verifies_against_fixture_roots(self):
        data = MOD.registry()
        self.assertTrue(MOD.verify_registry(data, self.roots))

    def test_full_registry_verifies_against_real_roots(self):
        self.assertTrue(MOD.verify_registry(MOD.registry()))

    def test_rejects_duplicate_boundary(self):
        data = MOD.registry()
        data["items"].append(copy.deepcopy(data["items"][0]))
        with self.assertRaises(MOD.BoundaryError):
            MOD.verify_registry(data, self.roots)

    def test_rejects_missing_owner_and_review(self):
        data = MOD.registry()
        data["items"][1]["owner"] = None
        data["items"][1]["shared_review"] = None
        with self.assertRaises(MOD.BoundaryError):
            MOD.verify_registry(data, self.roots)

    def test_guard_hash_recorded(self):
        item = next(i for i in MOD.registry()["items"]
                    if i["id"] == "save_serializer")
        guard = next(e for e in item["evidence"]
                     if e["path"].endswith("p2_fixture_captain_guard.h"))
        self.assertEqual(
            guard["sha256"],
            "d2f678c9eda75e151eb534077dff9e30ad36ae4796881d971bbd09945f3c3474")
        self.assertEqual(
            MOD.file_digest(MOD.CANONICAL_ROOT / "scripts/p2_fixture_captain_guard.h"),
            guard["sha256"])


if __name__ == "__main__":
    raise SystemExit(unittest.main())
