"""Tests for the enemies-1 missing audit (issue #653). Hermetic: synthetic
decomp trees and inventories under tmp_path only. Real-source validation
runs through the adapter main() and is logged, not pytest.
"""
import importlib.util
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
ADAPTER_PATH = ROOT / "experimental" / "pikmin2_enemies1_missing_audit.py"
_spec = importlib.util.spec_from_file_location(
    "pikmin2_enemies1_missing_audit", ADAPTER_PATH)
adapter = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(adapter)

HEADER = """\
enum EEnemyTypeID {
EnemyID_Tobi = 14,
EnemyID_ElecHiba = 22,
EnemyID_PanModokiNest = 39,
EnemyID_Clover = 47,
EnemyID_Tukushi = 80,
EnemyID_Chiyogami = 89,
};
"""
INFO = """\
{"Tobi", EnemyTypeID::EnemyID_Tobi, -1, 1, (EFlag_CanBeSpawned)},
{"ElecHiba", EnemyTypeID::EnemyID_ElecHiba, -1, 2, (EFlag_HasNoInfo)},
{"Clover", EnemyTypeID::EnemyID_Clover, -1, 1, (EFlag_CanBeSpawned)},
{"Tukushi", EnemyTypeID::EnemyID_Tukushi, -1, 1, (EFlag_CanBeSpawned)},
{"Chiyogami", EnemyTypeID::EnemyID_Chiyogami, -1, 1, (EFlag_HasNoInfo)},
"""
INVENTORY = {"story_caves": [{"floors": [{"enemy_ids": ["Tobi", "Clover"]}]}]}


def make_decomp(tmp, header=HEADER, info=INFO, files=("src/plugProjectNishimuraU/Tobi.cpp",
                                                      "include/Game/Entities/Tobi.h")):
    decomp = Path(tmp) / "decomp"
    (decomp / "include/Game").mkdir(parents=True)
    (decomp / "src/plugProjectYamashitaU").mkdir(parents=True)
    (decomp / "include/Game/enemyInfo.h").write_text(header, encoding="utf-8")
    (decomp / "src/plugProjectYamashitaU/enemyInfo.cpp").write_text(info, encoding="utf-8")
    for name in files:
        path = decomp / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("// synthetic\n", encoding="utf-8")
    return decomp


class ParseTests(unittest.TestCase):
    def test_enum_ids(self):
        ids = adapter.parse_enum_ids(HEADER)
        self.assertEqual({ids["Tobi"], ids["ElecHiba"], ids["Clover"]}, {14, 22, 47})

    def test_enum_empty_rejected(self):
        with self.assertRaises(ValueError):
            adapter.parse_enum_ids("no enums here\n")

    def test_info_row_found(self):
        self.assertEqual(adapter.info_row_line(INFO, "Tobi"), 1)

    def test_info_row_absent(self):
        self.assertIsNone(adapter.info_row_line(INFO, "PanModokiNest"))

    def test_inventory_hits(self):
        hits = adapter.inventory_hits(INVENTORY, "Tobi")
        self.assertTrue(hits)
        self.assertFalse(adapter.inventory_hits(INVENTORY, "ElecHiba"))


class AuditTests(unittest.TestCase):
    def test_tobi_row(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            decomp = make_decomp(tmp)
            row = adapter.audit_identity(14, HEADER, INFO, decomp, INVENTORY)
        self.assertEqual(row["internal"], "Tobi")
        self.assertTrue(row["anchors"]["info_row"].endswith(":1"))
        self.assertEqual(row["inventory_hits"], 1)
        self.assertTrue(all(v == "UNTESTED" for v in row["gates"].values()))

    def test_alias_row_without_info_row(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            decomp = make_decomp(tmp, files=())
            row = adapter.audit_identity(39, HEADER, INFO, decomp, {"x": ["PanModokiNest"]})
        self.assertIsNone(row["anchors"]["info_row"])
        self.assertIn("PanHouse83", row["anchors"]["remap"])

    def test_enum_drift_rejected(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            decomp = make_decomp(tmp)
            with self.assertRaises(ValueError):
                adapter.audit_identity(14, HEADER.replace("Tobi = 14", "Tobi = 15"),
                                       INFO, decomp, INVENTORY)

    def test_missing_info_row_rejected(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            decomp = make_decomp(tmp)
            with self.assertRaises(ValueError):
                adapter.audit_identity(14, HEADER, "{}", decomp, INVENTORY)

    def test_unexpected_alias_row_rejected(self):
        import tempfile
        bad_info = INFO + '{"PanModokiNest", 0},\n'
        with tempfile.TemporaryDirectory() as tmp:
            decomp = make_decomp(tmp, files=())
            with self.assertRaises(ValueError):
                adapter.audit_identity(39, HEADER, bad_info, decomp, {})

    def test_missing_entity_rejected(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            decomp = make_decomp(tmp, files=())
            with self.assertRaises(ValueError):
                adapter.audit_identity(14, HEADER, INFO, decomp, INVENTORY)


class PacketTests(unittest.TestCase):
    def good_packet(self):
        rows = []
        for sid in adapter.SOURCE_IDS:
            rows.append({"source_id": sid, "internal": "X", "gates": {
                g: "UNTESTED" for g in ("identity_spawn", "movement_animation",
                                        "attacks_receivers", "death_corpse",
                                        "transport_reward", "cleanup_reentry")},
                "inventory_paths": []})
        return {"schema": adapter.SCHEMA, "rows": rows}

    def test_valid_packet(self):
        adapter.check_packet(self.good_packet(), {"a": 1})

    def test_bad_schema_rejected(self):
        packet = self.good_packet()
        packet["schema"] = "nope"
        with self.assertRaises(ValueError):
            adapter.check_packet(packet, {})

    def test_wrong_id_set_rejected(self):
        packet = self.good_packet()
        packet["rows"] = packet["rows"][:5]
        with self.assertRaises(ValueError):
            adapter.check_packet(packet, {})

    def test_non_untested_gate_rejected(self):
        packet = self.good_packet()
        packet["rows"][0]["gates"]["identity_spawn"] = "PASS"
        with self.assertRaises(ValueError):
            adapter.check_packet(packet, {})

    def test_run_end_to_end(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            files = ("src/plugProjectNishimuraU/Tobi.cpp",
                     "include/Game/Entities/Tobi.h",
                     "src/plugProjectNishimuraU/ElecHiba.cpp",
                     "include/Game/Entities/ElecHiba.h",
                     "src/plugProjectNishimuraU/Hana.cpp",
                     "src/plugProjectMorimuraU/pelplant.cpp",
                     "include/Game/Entities/Hana.h",
                     "include/Game/Entities/Pelplant.h")
            decomp = make_decomp(tmp, files=files)
            inv = {"hits": ["Tobi", "ElecHiba", "Clover", "Tukushi",
                            "Chiyogami", "PanModokiNest"]}
            inv_path = Path(tmp) / "inv.json"
            inv_path.write_text(json.dumps(inv), encoding="utf-8")
            out = Path(tmp) / "out"
            result = adapter.run(decomp, inv_path, out)
            self.assertEqual(len(result["rows"]), 6)
            self.assertTrue((out / "packet.json").is_file())
            self.assertTrue((out / "run.log").is_file())

    def test_run_missing_header_rejected(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            decomp = Path(tmp) / "empty"
            decomp.mkdir()
            inv_path = Path(tmp) / "inv.json"
            inv_path.write_text("{}", encoding="utf-8")
            with self.assertRaises(ValueError):
                adapter.run(decomp, inv_path, Path(tmp) / "out")


if __name__ == "__main__":
    unittest.main()
