"""Focused P0 tests for the KumaChappy35 audit adapter (issue #613).

Positive pins come from the read-only research checkout; source hashes are
asserted so drift fails loudly. Negative tests cover malformed/missing
input and the missing-source boundary.
"""
import hashlib
import importlib.util
import unittest
from pathlib import Path

ROOT = Path("C:/Users/alari/pikmin-randomizer/output/workflow/autofill/"
            "planning-shards/enemies-6/prepared/kumachappy35-p0-root")
ADAPTER = ROOT / "experimental/pikmin2_kumachappy35_audit.py"
RESEARCH = Path("C:/Users/alari/pikmin-randomizer/native/pikmin2-research")


def load_adapter():
    spec = importlib.util.spec_from_file_location("kumachappy35", ADAPTER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


adapter = load_adapter()

EXPECTED_STATES = {
    "KUMACHAPPY_NULL": -1, "KUMACHAPPY_Dead": 0, "KUMACHAPPY_Rebirth": 1,
    "KUMACHAPPY_Lost": 2, "KUMACHAPPY_Attack": 3, "KUMACHAPPY_Flick": 4,
    "KUMACHAPPY_Turn": 5, "KUMACHAPPY_TurnPath": 6, "KUMACHAPPY_Walk": 7,
    "KUMACHAPPY_WalkPath": 8, "KUMACHAPPY_StateCount": 9,
}
EXPECTED_ANIMS = {
    "KUMACHAPPYANIM_Attack": 0, "KUMACHAPPYANIM_Dead": 1,
    "KUMACHAPPYANIM_Flick": 2, "KUMACHAPPYANIM_Move": 3,
    "KUMACHAPPYANIM_Carry": 4, "KUMACHAPPYANIM_Lost": 5,
    "KUMACHAPPYANIM_Turn": 6, "KUMACHAPPYANIM_Eat": 7,
    "KUMACHAPPYANIM_Rebirth": 8, "KUMACHAPPYANIM_AnimCount": 9,
}


def research(rel):
    return (RESEARCH / rel).read_text(encoding="utf-8", errors="replace")


class HashTests(unittest.TestCase):
    def test_observed_source_hashes(self):
        packet = adapter.audit_source(None)
        self.assertEqual(packet["hashes"], adapter.OBSERVED_HASHES)

    def test_missing_source_raises(self):
        with self.assertRaises(ValueError):
            adapter.audit_source(Path("C:/nonexistent-research-root"))


class EnumTests(unittest.TestCase):
    def setUp(self):
        self.header = research("include/Game/Entities/KumaChappy.h")

    def test_states(self):
        self.assertEqual(adapter.parse_state_ids(self.header), EXPECTED_STATES)

    def test_anims(self):
        self.assertEqual(adapter.parse_anim_ids(self.header), EXPECTED_ANIMS)

    def test_empty_and_missing_enum(self):
        with self.assertRaises(ValueError):
            adapter.parse_state_ids("")
        with self.assertRaises(ValueError):
            adapter.parse_state_ids("int x;")
        with self.assertRaises(ValueError):
            adapter.parse_anim_ids("int x;")


class ParmTests(unittest.TestCase):
    def setUp(self):
        self.header = research("include/Game/Entities/KumaChappy.h")

    def test_defaults(self):
        parms = adapter.parse_proper_parms(self.header)
        self.assertEqual(parms["fp01"]["member"], "PoisonDamage")
        self.assertEqual(parms["fp01"]["default"], 300.0)
        self.assertEqual(parms["fp11"]["default"], 30.0)
        self.assertEqual(parms["fp11"]["max"], 500.0)
        self.assertEqual(parms["fp12"]["default"], 10.0)
        self.assertEqual(len(parms), 3)

    def test_malformed_refused(self):
        with self.assertRaises(ValueError):
            adapter.parse_proper_parms("")
        with self.assertRaises(ValueError):
            adapter.parse_proper_parms("no parms here")
        dup = ("mA(this, 'fp01', \"x\", 1.0f, 0.0f, 2.0f)\n"
               "mB(this, 'fp01', \"y\", 1.0f, 0.0f, 2.0f)")
        with self.assertRaises(ValueError):
            adapter.parse_proper_parms(dup)


class ManagerAndIdentityTests(unittest.TestCase):
    def test_manager_facts(self):
        mgr = research("src/plugProjectNishimuraU/KumaChappyMgr.cpp")
        header = research("include/Game/Entities/KumaChappy.h")
        facts = adapter.parse_manager_facts(mgr, header)
        self.assertEqual(facts["manager_name_const"], "246-KumaChappyMgr")
        self.assertEqual(facts["enemy_type_id"], "EnemyID_KumaChappy")
        self.assertEqual(facts["obj_array_member"], "mObj")

    def test_actor_refs(self):
        cpp = research("src/plugProjectNishimuraU/KumaChappy.cpp")
        refs = adapter.parse_actor_refs(cpp)
        self.assertIn("Health", refs["health_members"])
        self.assertTrue(refs["carcass_motion"])
        self.assertTrue(refs["become_carcass"])
        self.assertTrue(refs["follower_relation"])

    def test_enemyinfo_identity(self):
        info = research("src/plugProjectYamashitaU/enemyInfo.cpp")
        enumh = research("include/Game/enemyInfo.h")
        identity = adapter.parse_enemyinfo_row(info, enumh)
        self.assertEqual(identity["enum_id"], "EnemyID_KumaChappy")
        self.assertEqual(identity["numeric_id"], 35)
        self.assertEqual(identity["model_bank"], "Chappy")
        self.assertEqual(identity["drop"], "BDT_Strong")
        self.assertEqual(identity["child_count"], 0)
        self.assertIn("EFlag_UseOwnID", identity["flags"])
        self.assertIn("EFlag_CanBeSpawned", identity["flags"])

    def test_missing_row_and_doc(self):
        with self.assertRaises(ValueError):
            adapter.parse_enemyinfo_row("int x;", "")
        with self.assertRaises(ValueError):
            adapter.parse_enemyinfo_row("", "")


class AuditPacketTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.packet = adapter.audit_source(None)

    def test_shape(self):
        self.assertEqual(self.packet["schema"], "kumachappy35-p0/1")
        self.assertEqual(self.packet["source_id"], 35)
        self.assertEqual(self.packet["enum_name"], "KumaChappy")
        self.assertFalse(self.packet["generated"])
        self.assertEqual(self.packet["state_count"], 9)
        self.assertEqual(self.packet["anim_count"], 9)
        self.assertTrue(self.packet["actor"]["follower_relation"])

    def test_reused_framing_and_blockers(self):
        joined = " ".join(self.packet["reused_framing"])
        self.assertIn("pikmin2_engine_parms", joined)
        self.assertGreaterEqual(len(self.packet["blockers"]), 4)
        text = " ".join(self.packet["blockers"])
        self.assertIn("actor-birth-projectiles", text)


if __name__ == "__main__":
    unittest.main()
