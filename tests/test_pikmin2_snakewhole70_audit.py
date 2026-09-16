"""Focused P0 tests for the SnakeWhole70 audit adapter (issue #376).

Positive pins come from the read-only research checkout and the canonical
roster; source hashes are asserted so drift fails loudly. Negative tests
cover malformed/missing input and the missing-source boundary.
"""
import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path("C:/Users/alari/pikmin-randomizer/output/workflow/autofill/"
            "planning-shards/enemies-1/prepared/snagret70-p0-root")
ADAPTER = ROOT / "experimental/pikmin2_snakewhole70_audit.py"
ROSTER = ROOT / "docs/PIKMIN2_ENEMY_ROSTER.json"


def load_adapter():
    spec = importlib.util.spec_from_file_location("snakewhole70", ADAPTER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


adapter = load_adapter()
ROSTER_DOC = json.loads(ROSTER.read_text(encoding="utf-8"))

EXPECTED_STATES = {
    "SNAKEWHOLE_NULL": -1, "SNAKEWHOLE_Dead": 0, "SNAKEWHOLE_Stay": 1,
    "SNAKEWHOLE_Appear1": 2, "SNAKEWHOLE_Appear2": 3,
    "SNAKEWHOLE_Disappear": 4, "SNAKEWHOLE_Wait": 5, "SNAKEWHOLE_Walk": 6,
    "SNAKEWHOLE_Home": 7, "SNAKEWHOLE_Attack": 8, "SNAKEWHOLE_Eat": 9,
    "SNAKEWHOLE_Struggle": 10, "SNAKEWHOLE_Count": 11,
}
EXPECTED_ANIMS = {
    "SNAKEWHOLEANIM_Dead": 0, "SNAKEWHOLEANIM_Appear1": 1,
    "SNAKEWHOLEANIM_Appear2": 2, "SNAKEWHOLEANIM_Dive": 3,
    "SNAKEWHOLEANIM_AttackOffset": 4, "SNAKEWHOLEANIM_HitNear": 4,
    "SNAKEWHOLEANIM_Hit": 5, "SNAKEWHOLEANIM_Far": 5,
    "SNAKEWHOLEANIM_HitFar": 6, "SNAKEWHOLEANIM_HitRight": 7,
    "SNAKEWHOLEANIM_HitLeft": 8, "SNAKEWHOLEANIM_Wait": 9,
    "SNAKEWHOLEANIM_Eat": 10, "SNAKEWHOLEANIM_Struggle": 11,
    "SNAKEWHOLEANIM_Jump": 12, "SNAKEWHOLEANIM_Carry": 13,
    "SNAKEWHOLEANIM_AnimCount": 14,
}


class HashTests(unittest.TestCase):
    def test_observed_source_hashes(self):
        packet = adapter.audit_source(None, ROSTER_DOC)
        self.assertEqual(packet["hashes"], adapter.OBSERVED_HASHES)

    def test_missing_source_raises(self):
        with self.assertRaises(ValueError):
            adapter.audit_source(Path("C:/nonexistent-research-root"), ROSTER_DOC)


class EnumTests(unittest.TestCase):
    def setUp(self):
        self.header = (adapter.RESEARCH_ROOT
                       / "include/Game/Entities/SnakeWhole.h").read_text(
                           encoding="utf-8", errors="replace")

    def test_states(self):
        self.assertEqual(adapter.parse_state_ids(self.header), EXPECTED_STATES)

    def test_anims_and_alias(self):
        anims = adapter.parse_anim_ids(self.header)
        for name, value in EXPECTED_ANIMS.items():
            if name == "SNAKEWHOLEANIM_Far":
                continue
            self.assertEqual(anims[name], value, name)
        self.assertEqual(anims["SNAKEWHOLEANIM_HitNear"],
                         anims["SNAKEWHOLEANIM_AttackOffset"])

    def test_empty_and_missing_enum(self):
        with self.assertRaises(ValueError):
            adapter.parse_state_ids("")
        with self.assertRaises(ValueError):
            adapter.parse_state_ids("int x;")
        with self.assertRaises(ValueError):
            adapter.parse_anim_ids("int x;")


class ParmTests(unittest.TestCase):
    def setUp(self):
        self.header = (adapter.RESEARCH_ROOT
                       / "include/Game/Entities/SnakeWhole.h").read_text(
                           encoding="utf-8", errors="replace")

    def test_defaults(self):
        parms = adapter.parse_proper_parms(self.header)
        self.assertEqual(parms["fp01"]["default"], 0.8)
        self.assertEqual(parms["fp01"]["max"], 1.0)
        self.assertEqual(parms["fp11"]["default"], 2.0)
        self.assertEqual(parms["fp12"]["default"], 1.0)
        self.assertEqual(parms["fp21"]["default"], 300.0)
        self.assertEqual(parms["fp21"]["member"], "PoisonDamage")

    def test_malformed_refused(self):
        with self.assertRaises(ValueError):
            adapter.parse_proper_parms("")
        with self.assertRaises(ValueError):
            adapter.parse_proper_parms("no parms here")


class ManagerAndIdentityTests(unittest.TestCase):
    def test_manager_type(self):
        mgr = (adapter.RESEARCH_ROOT
               / "src/plugProjectNishimuraU/SnakeWholeMgr.cpp").read_text(
                   encoding="utf-8", errors="replace")
        header = (adapter.RESEARCH_ROOT
                  / "include/Game/Entities/SnakeWhole.h").read_text(
                      encoding="utf-8", errors="replace")
        facts = adapter.parse_manager_facts(header + "\n" + mgr)
        self.assertEqual(facts["enemy_type_id"], "EnemyID_SnakeWhole")
        self.assertEqual(facts["obj_array_member"], "mObj")

    def test_roster_identity(self):
        entry = adapter.roster_identity(ROSTER_DOC, 70)
        self.assertEqual(entry["enum_name"], "SnakeWhole")
        self.assertEqual(entry["drop_type"], "BDT_Boss")
        self.assertEqual(entry["day_end_max"], 1)
        self.assertEqual(entry["child_count"], 0)
        self.assertTrue(entry["spawnable"])

    def test_missing_roster_id_and_doc(self):
        with self.assertRaises(ValueError):
            adapter.roster_identity(ROSTER_DOC, 9999)
        with self.assertRaises(ValueError):
            adapter.roster_identity({}, 70)
        with self.assertRaises(TypeError):
            adapter.roster_identity(None, 70)


class AuditPacketTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.packet = adapter.audit_source(None, ROSTER_DOC)

    def test_shape(self):
        self.assertEqual(self.packet["schema"], "snakewhole70-p0/1")
        self.assertEqual(self.packet["source_id"], 70)
        self.assertEqual(self.packet["enum_name"], "SnakeWhole")
        self.assertFalse(self.packet["generated"])
        self.assertEqual(self.packet["state_count"], 11)
        self.assertEqual(self.packet["anim_count"], 14)
        self.assertTrue(self.packet["joint_chain"])
        self.assertIn("mHealth", self.packet["health_accessors"])

    def test_blockers_named(self):
        joined = " ".join(self.packet["blockers"])
        for token in ("EnemyID_SnakeWhole", "mesh", "corpse", "receiver"):
            self.assertIn(token, joined)
        self.assertGreaterEqual(len(self.packet["blockers"]), 4)

    def test_reuses_existing_framing(self):
        joined = " ".join(self.packet["reused_framing"])
        self.assertIn("pikmin2_engine_parms", joined)
        self.assertIn("PIKMIN2_ENEMY_ROSTER.json", joined)


if __name__ == "__main__":
    unittest.main()
