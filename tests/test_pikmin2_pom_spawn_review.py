"""Tests for the Candypop-bud natural-spawn adjudicator (#448, shard enemies-1).

Synthetic logs plus an optional read-only decomp check; no engine run, no
retail assets. Proves the proxy-vehicle verdict, the natural-observed path,
base-Pom rejection, missing-marker reporting and malformed input handling.
"""
import importlib.util
import unittest
from pathlib import Path

_RETAIL = Path("C:/Users/alari/pikmin-randomizer/native/pikmin2-research")


def _load():
    path = (Path(__file__).resolve().parents[1] / "experimental"
            / "pikmin2_pom_spawn_review.py")
    spec = importlib.util.spec_from_file_location("pom_spawn_review", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


R = _load()

PROXY = "P2_POM_BIND generator=353003 species=RedPom source_id=4 host=teki type=3"
NATURAL = "\n".join([
    "P2_POM_BIND generator=353003 species=RedPom source_id=4 host=pom",
    "P2_POM_DRAW generator=353003 source_id=4 bank=pom pose=wait",
    "P2_SEED_RESOLVE source_id=4",
    "P2_GENERATED_PLACEMENT source_id=4 target=353003 generator=353003 bound=1",
])


class AdjudicationTests(unittest.TestCase):
    def test_proxy_vehicle_bind_requires_spawned_actor(self):
        result = R.adjudicate(PROXY)
        self.assertEqual(result["verdict"], "spawned_actor_required")
        self.assertEqual(result["gate1"], "UNTESTED")
        self.assertTrue(any("proxy-vehicle" in r for r in result["reasons"]))
        self.assertEqual(result["provider"]["id"], "pom-actor-manager")

    def test_natural_triple_observed(self):
        result = R.adjudicate(NATURAL)
        self.assertEqual(result["verdict"], "natural_spawn_observed")
        self.assertEqual(result["gate1"], "PASS-candidate")
        self.assertIsNone(result["provider"])

    def test_natural_requires_matching_source_id(self):
        # Placement bound to a different source id must not satisfy source 4.
        text = NATURAL.replace("P2_SEED_RESOLVE source_id=4",
                               "P2_SEED_RESOLVE source_id=8")
        self.assertEqual(R.adjudicate(text)["verdict"], "spawned_actor_required")

    def test_natural_requires_bound_one(self):
        text = NATURAL.replace("bound=1", "bound=0")
        self.assertEqual(R.adjudicate(text)["verdict"], "spawned_actor_required")

    def test_natural_requires_draw_marker(self):
        text = "\n".join(l for l in NATURAL.splitlines() if "P2_POM_DRAW" not in l)
        self.assertEqual(R.adjudicate(text)["verdict"], "spawned_actor_required")

    def test_base_pom_bind_is_flagged(self):
        text = "P2_POM_BIND generator=99 species=Pom source_id=82 host=teki type=3"
        result = R.adjudicate(text)
        self.assertEqual(result["verdict"], "spawned_actor_required")
        self.assertTrue(any("base-Pom (82)" in r for r in result["reasons"]))

    def test_missing_markers_are_listed(self):
        result = R.adjudicate(PROXY)
        joined = " ".join(result["reasons"])
        self.assertIn("P2_SEED_RESOLVE source_id=4", joined)
        self.assertIn("P2_GENERATED_PLACEMENT source_id=4 bound=1", joined)
        self.assertIn("P2_POM_DRAW source_id=4", joined)

    def test_no_binds_is_reported(self):
        result = R.adjudicate("no markers here\n")
        self.assertEqual(result["verdict"], "spawned_actor_required")
        self.assertTrue(any("no P2_POM_BIND" in r for r in result["reasons"]))

    def test_multiple_proxy_binds_counted(self):
        text = PROXY + "\nP2_POM_BIND generator=353007 species=RandPom source_id=8 host=teki type=3"
        result = R.adjudicate(text)
        self.assertTrue(any("2 proxy-vehicle bind" in r for r in result["reasons"]))
        self.assertEqual(len(R.proxy_vehicle_binds(result["binds"])), 2)


class MalformedInputTests(unittest.TestCase):
    def test_parse_binds_rejects_non_text(self):
        for bad in (None, 5, ["x"]):
            with self.assertRaises(ValueError):
                R.parse_binds(bad)

    def test_adjudicate_rejects_empty_and_non_text(self):
        for bad in ("", "   ", None, 7):
            with self.assertRaises(ValueError):
                R.adjudicate(bad)

    def test_proxy_vehicle_binds_rejects_non_list(self):
        for bad in (None, "x", 3):
            with self.assertRaises(ValueError):
                R.proxy_vehicle_binds(bad)

    def test_parse_placement_triple_rejects_non_text(self):
        for bad in (None, 3, b"x"):
            with self.assertRaises(ValueError):
                R.parse_placement_triple(bad)

    def test_hash_helper_rejects_non_text(self):
        with self.assertRaises(ValueError):
            R.sha256_text(b"bytes")
        self.assertEqual(len(R.sha256_text("x")), 64)

    def test_malformed_bind_line_ignored(self):
        self.assertEqual(R.parse_binds("P2_POM_BIND generator=abc"), [])


class SourceFactTests(unittest.TestCase):
    def test_source_facts_confirmed_or_skipped(self):
        h = _RETAIL / "include/Game/enemyInfo.h"
        c = _RETAIL / "src/plugProjectYamashitaU/enemyInfo.cpp"
        if not (h.is_file() and c.is_file()):
            self.skipTest("decomp source unavailable")
        facts = R.check_source_facts(h, c)
        self.assertTrue(R.validate_source_facts(facts))

    def test_missing_source_is_unavailable(self):
        facts = R.check_source_facts("C:/nonexistent/enemyInfo.h",
                                     "C:/nonexistent/enemyInfo.cpp")
        self.assertFalse(facts["available"])
        with self.assertRaises(ValueError):
            R.validate_source_facts(facts)

    def test_false_fact_rejected(self):
        with self.assertRaises(ValueError):
            R.validate_source_facts({"available": True, "parent_resolution": False})


if __name__ == "__main__":
    unittest.main()