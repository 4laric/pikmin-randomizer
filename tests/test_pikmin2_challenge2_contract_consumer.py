"""Focused tests for the challenge-2 contract consumer (#137).

All fixtures are synthetic stage-table texts and synthetic inventories
exercising the partition boundary (exact seven keys), the contract
delegation, readiness rules and first-slice determinism. No value here is
claimed as retail fact; the real decode evidence lives in
docs/PIKMIN2_CHALLENGE2_CONTRACT_CONSUMER.md.
"""
import importlib.util
import json
import unittest
from pathlib import Path
import tempfile

ADAPTER = (Path(__file__).resolve().parents[1] / "experimental"
           / "pikmin2_challenge2_contract_consumer.py")

KEYS = ("ch_ABEM_LeafChappy", "ch_MAT_conc_cave", "ch_MAT_flier",
        "ch_MAT_limited_time", "ch_MAT_t_hunter_hana", "ch_MUKI_bigfoot",
        "ch_MUKI_metal")

REAL_ROWS = [("ch_ABEM_LeafChappy", 2, 30, 400.0, 1, 1, [85.0, 100.0], 17, 11),
             ("ch_MAT_conc_cave", 3, 2, 500.0, 0, 0, [70.0, 100.0, 50.0], 2, 0),
             ("ch_MAT_flier", 1, 50, 500.0, 1, 1, [160.0], 28, 0),
             ("ch_MAT_limited_time", 1, 40, 160.0, 3, 4, [130.0], 11, 0),
             ("ch_MAT_t_hunter_hana", 1, 80, 400.0, 0, 0, [145.0], 14, 0),
             ("ch_MUKI_bigfoot", 1, 50, 0.0, 0, 2, [200.0], 7, 0),
             ("ch_MUKI_metal", 2, 50, 0.0, 1, 1, [130.0, 100.0], 1, 0)]


def load_adapter():
    spec = importlib.util.spec_from_file_location("challenge2_consumer", ADAPTER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def render_table(rows):
    """Render a synthetic stages.txt: [(key, floors, pop, time, bitter, spicy,
    timers, ui, treasure)]. Roster puts pop in Red/Leaf, rest zero."""
    lines = [str(len(rows))]
    for key, floors, pop, time, bitter, spicy, timers, ui, treasure in rows:
        roster = [pop if (c, h) == (1, 0) else 0 for c in range(7) for h in range(3)]
        lines += ["4", key + ".txt"] + [str(v) for v in roster]
        lines += [str(time), str(bitter), str(spicy), str(floors), str(treasure), str(ui)]
        lines += [str(v) for v in timers]
    return "\n".join(lines) + "\n"


def synth_inventory(rows):
    stages = [{"cave_id": r[0], "cave_path": "user/Mukki/mapunits/caveinfo/" + r[0] + ".txt",
               "floors": r[1],
               "pikmin_by_native_color_and_maturity": [[r[2] if c == 1 else 0, 0, 0] for c in range(7)],
               "legacy_time": r[3], "bitter_sprays": r[4], "spicy_sprays": r[5],
               "treasure_count_field": r[8], "ui_index": r[7], "floor_seconds": list(r[6]),
               "issue": 137} for r in rows]
    return {"challenge": {"stages": stages}}


class StubContract:
    """Stand-in contract recording delegation without disc reads."""
    def __init__(self, parsed):
        self._parsed = parsed
        self.calls = []

    def parse_stage_table(self, text):
        self.calls.append("parse")
        if text == "BROKEN":
            raise ValueError("synthetic malformed input")
        return self._parsed

    def cross_check_inventory(self, stages, inventory):
        self.calls.append("cross")
        return []

    def framework_providers(self):
        self.calls.append("providers")
        return {"existing": {"x": "y"}, "missing": {"challenge_host_mode": "z"}}


class ConsumerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = load_adapter()

    def test_partition_constants(self):
        self.assertEqual(self.mod.PARTITION_KEYS, KEYS)
        self.assertEqual(self.mod.ISSUE, 137)

    def test_decode_keeps_exactly_seven(self):
        stub = StubContract([{"cave_id": k} for k in KEYS] + [{"cave_id": "ch_OTHER"}])
        rows = self.mod.decode_partition("anything", stub)
        self.assertEqual(sorted(s["cave_id"] for s in rows), sorted(KEYS))
        self.assertIn("parse", stub.calls)

    def test_missing_partition_key_rejected(self):
        stub = StubContract([{"cave_id": k} for k in KEYS if k != "ch_MAT_flier"])
        with self.assertRaises(self.mod.ConsumerError):
            self.mod.decode_partition("anything", stub)

    def test_malformed_input_propagates(self):
        stub = StubContract([])
        with self.assertRaises(ValueError):
            self.mod.decode_partition("BROKEN", stub)

    def test_cross_check_reports_partition_drift(self):
        class Drifty(StubContract):
            def cross_check_inventory(self, stages, inventory):
                return [{"cave_id": "ch_MAT_flier", "reason": "x"},
                        {"cave_id": "ch_OTHER", "reason": "y"}]
        out = self.mod.cross_check([], {}, Drifty([]))
        self.assertEqual(out, [{"cave_id": "ch_MAT_flier", "reason": "x"}])

    def test_readiness_rules(self):
        stub = StubContract([])
        good = {"cave_id": "k", "floors": 1,
                "roster": [[0, 0, 0], [1, 0, 0], [0, 0, 0], [0, 0, 0],
                           [0, 0, 0], [0, 0, 0], [0, 0, 0]],
                "floor_seconds": [90.0], "bitter_sprays": 1, "spicy_sprays": 1}
        table = self.mod.readiness_map([good], stub)
        self.assertTrue(table[0]["ready"])
        self.assertEqual(table[0]["unsupported_semantics"], ["challenge_host_mode"])
        empty = dict(good, roster=[[0, 0, 0]] * 7)
        self.assertIn("empty starting squad",
                      self.mod.readiness_map([empty], stub)[0]["blockers"])
        bad_timer = dict(good, floor_seconds=[-5.0])
        self.assertIn("non-positive floor timer",
                      self.mod.readiness_map([bad_timer], stub)[0]["blockers"])
        bad_count = dict(good, floor_seconds=[90.0, 90.0])
        self.assertIn("timer/floor count mismatch",
                      self.mod.readiness_map([bad_count], stub)[0]["blockers"])
        bad_spray = dict(good, bitter_sprays=-1)
        self.assertIn("bad bitter_sprays",
                      self.mod.readiness_map([bad_spray], stub)[0]["blockers"])

    def test_first_slice_deterministic(self):
        rows = [{"cave_id": "b", "floors": 2, "floor_seconds": [10.0, 10.0], "ui_index": 1},
                {"cave_id": "a", "floors": 1, "floor_seconds": [100.0], "ui_index": 9},
                {"cave_id": "c", "floors": 1, "floor_seconds": [100.0], "ui_index": 2}]
        pick = self.mod.first_slice(rows)
        self.assertEqual(pick["cave_id"], "c")
        self.assertIn("host_mode", pick["owners"])
        with self.assertRaises(self.mod.ConsumerError):
            self.mod.first_slice([])

    def test_load_contract_missing_file(self):
        with self.assertRaises(self.mod.ConsumerError):
            self.mod.load_contract("/nonexistent/contract.py")

    def test_load_contract_missing_api(self):
        with tempfile.TemporaryDirectory() as tmp:
            stub = Path(tmp) / "stub_contract.py"
            stub.write_text("X = 1\n", encoding="utf-8")
            with self.assertRaises(self.mod.ConsumerError):
                self.mod.load_contract(str(stub))

    def test_end_to_end_packet(self):
        text = render_table(REAL_ROWS)
        inv = synth_inventory(REAL_ROWS)
        real = self.mod.load_contract()
        packet = self.mod.build_packet(text, inv, real)
        self.assertEqual(len(packet["stages"]), 7)
        self.assertEqual(packet["first_slice"]["cave_id"], "ch_MAT_limited_time")
        self.assertEqual(len(packet["packet_sha256"]), 64)
        self.assertFalse(packet["generated"])
        self.assertEqual(packet["placements"], [])

    def test_cli_writes_packet(self):
        with tempfile.TemporaryDirectory() as tmp:
            stage_file = Path(tmp) / "stages.txt"
            stage_file.write_text(render_table(REAL_ROWS), encoding="utf-8")
            inv_file = Path(tmp) / "inv.json"
            inv_file.write_text(json.dumps(synth_inventory(REAL_ROWS)), encoding="utf-8")
            out = Path(tmp) / "packet.json"
            self.mod.main(["--stages-text", str(stage_file), "--inventory", str(inv_file),
                           "--output", str(out)])
            packet = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(packet["first_slice"]["timer_total"], 130.0)

    def test_cli_missing_output_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            stage_file = Path(tmp) / "stages.txt"
            stage_file.write_text(render_table(REAL_ROWS), encoding="utf-8")
            inv_file = Path(tmp) / "inv.json"
            inv_file.write_text(json.dumps(synth_inventory(REAL_ROWS)), encoding="utf-8")
            with self.assertRaises(self.mod.ConsumerError):
                self.mod.main(["--stages-text", str(stage_file),
                               "--inventory", str(inv_file),
                               "--output", str(Path(tmp) / "absent" / "packet.json")])


if __name__ == "__main__":
    unittest.main()