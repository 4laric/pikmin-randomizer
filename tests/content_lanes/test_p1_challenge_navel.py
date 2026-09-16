"""Focused contract tests for the Navel P0 adapter (issue #563).

Positive pins come from the real retail source (observed values, never
invented): chal2.ini 2465 bytes with 5 timesettings, default.gen 98
records (50 tlep, 19 iket of types 5/7/8/10/12, 14 meti, 7 ssob, 5 krow,
3 ikip), plants.gen 38 tnlp records, map courses/stage2/cave.mod present.
Negative tests cover malformed/missing inputs and the missing-source
prerequisite boundary.
"""
import hashlib
import importlib.util
import unittest
from pathlib import Path

WORKTREE = Path("C:/Users/alari/pikmin-randomizer/output/autofill-root-563")
ADAPTER_PATH = WORKTREE / "experimental/content_lanes/p1-challenge-navel.py"
ASSETS = Path("C:/Users/alari/bbft/dist/cohesion/pikmin/assets")

PIN_INI = "1a16d0e61c19c1e919a9f48459b8795d52980f448ffa8739a59a6255c51837ed"
PIN_DEFAULT_GEN = "de45c8afcb6ae54d8c4b63b38e535e37e1e3b670eff6af97c0f44e50055914ba"
PIN_PLANTS_GEN = "0ce5e8423bbae1eae22f9db588f3b2b9235fbc1cb78f673710aa9831ddb8f7f9"
PIN_MAP = "da96b0a49fe12474c7fc20189cd861ef575da8a4e21271dbec3be2171f9fcb8e"


def load_adapter():
    spec = importlib.util.spec_from_file_location("p1_challenge_navel", ADAPTER_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


adapter = load_adapter()


def sha(name):
    path = ASSETS / "dataDir" / name
    with open(path, "rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


class IniTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        text = (ASSETS / "dataDir" / "stages/chal2.ini").read_bytes().decode("utf-8")
        cls.parsed = adapter.parse_stage_ini(text)

    def test_five_timesettings(self):
        self.assertEqual(self.parsed["timesettings"], 5)
        self.assertEqual(self.parsed["numsettings"], 5)

    def test_top_level_keys(self):
        self.assertEqual(self.parsed["map_file"], "courses/stage2/cave.mod")
        self.assertEqual(self.parsed["navi_start"], ["0.0", "0.0"])
        self.assertEqual(self.parsed["day_multiply"], ["1.2"])

    def test_empty_ini_fails_closed(self):
        with self.assertRaises(ValueError):
            adapter.parse_stage_ini("")
        with self.assertRaises(ValueError):
            adapter.parse_stage_ini(None)

    def test_missing_daymgr_fails_closed(self):
        with self.assertRaises(ValueError):
            adapter.parse_stage_ini("navi_start 0.0 0.0\n")

    def test_count_mismatch_fails_closed(self):
        with self.assertRaises(ValueError):
            adapter.parse_stage_ini("dayMgr {\nnumsettings 5\n}\n")


class GeneratorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        blob = (ASSETS / "dataDir" / "stages/chal2/default.gen").read_bytes()
        cls.records = adapter.decode_generators(blob)
        plants = (ASSETS / "dataDir" / "stages/chal2/plants.gen").read_bytes()
        cls.plants = adapter.decode_generators(plants)

    def test_default_gen_counts(self):
        from collections import Counter
        tags = Counter(r["tag"] for r in self.records)
        self.assertEqual(len(self.records), 98)
        self.assertEqual(dict(tags), {"tlep": 50, "iket": 19, "meti": 14,
                                      "ssob": 7, "krow": 5, "ikip": 3})

    def test_enemy_types_resolved(self):
        from collections import Counter
        kinds = Counter(r["type_byte"] for r in self.records if r["tag"] == "iket")
        self.assertEqual(dict(kinds), {5: 9, 7: 7, 10: 1, 8: 1, 12: 1})
        names = {r["teki"] for r in self.records if r["tag"] == "iket"}
        self.assertEqual(names, {"Mizigen", "Palm", "Shell", "Collec", "Hollec"})

    def test_plants_gen(self):
        self.assertEqual(len(self.plants), 38)
        self.assertTrue(all(r["tag"] == "tnlp" for r in self.plants))

    def test_bad_magic_fails_closed(self):
        with self.assertRaises(ValueError):
            adapter.decode_generators(b"NOPE" + b"\x00" * 40)
        with self.assertRaises(ValueError):
            adapter.decode_generators(b"1.0v")
        with self.assertRaises(ValueError):
            adapter.decode_generators(None)

    def test_generator_id_sharing_reported(self):
        # Generator ids are NOT unique in the retail blob: id 0 is shared by
        # 36 records (unassigned) and id 6029413 by 12 (pellet group). The
        # adapter reports ids as-is; P1 resolves sharing at import.
        from collections import Counter
        counts = Counter(r["generator"] for r in self.records)
        self.assertEqual(len(counts), 48)
        self.assertEqual(counts[0], 36)
        self.assertEqual(counts[6029413], 12)


class AuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = adapter.audit_level(str(ASSETS))

    def test_identity_and_hashes(self):
        self.assertEqual(self.report["level_key"], "challenge:navel")
        self.assertEqual(self.report["native_area_id"], 2)
        self.assertEqual(self.report["stage_info_index"], 18)
        self.assertEqual(self.report["tracks"],
                         ["Optional story destination #100",
                          "Separate timed/scored AP campaign #52"])
        self.assertEqual(self.report["hashes"]["stages/chal2.ini"], PIN_INI)
        self.assertEqual(self.report["hashes"]["stages/chal2/default.gen"],
                         PIN_DEFAULT_GEN)
        self.assertEqual(self.report["hashes"]["stages/chal2/plants.gen"],
                         PIN_PLANTS_GEN)
        self.assertFalse(self.report["generated"])

    def test_resource_closure(self):
        self.assertTrue(self.report["map_present"])
        self.assertEqual(self.report["unsupported"], [])
        self.assertEqual(self.report["enemy_types"], [5, 7, 8, 10, 12])

    def test_map_hash_observed(self):
        self.assertEqual(sha("courses/stage2/cave.mod"), PIN_MAP)


class SourceBoundaryTests(unittest.TestCase):
    def test_locate_real_source(self):
        found = adapter.locate_source([str(ASSETS)])
        self.assertTrue(found["available"])
        self.assertIsNone(found["prerequisite"])

    def test_missing_source_reports_prerequisite(self):
        found = adapter.locate_source([str(ASSETS / "nonexistent")])
        self.assertFalse(found["available"])
        self.assertIn("stages/chal2.ini", found["prerequisite"])

    def test_audit_missing_source_raises(self):
        with self.assertRaises(ValueError):
            adapter.audit_level(str(ASSETS / "nonexistent"))

    def test_audit_missing_blob_raises(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            staged = Path(tmp) / "dataDir" / "stages" / "chal2.ini"
            staged.parent.mkdir(parents=True)
            staged.write_bytes(b"dayMgr {\nnumsettings 1\ntimesetting 0 {}\n}\n")
            with self.assertRaises(ValueError):
                adapter.audit_level(tmp)


if __name__ == "__main__":
    unittest.main()
