"""Focused tests for the tutorial_3 carrier-token staging contract (#826)."""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "pikmin2_tutorial3_carrier_token_staging",
    ROOT / "experimental" / "pikmin2_tutorial3_carrier_token_staging.py")
staging = importlib.util.module_from_spec(spec)
spec.loader.exec_module(staging)

SHA = "adcc816653957fbf00919c313291142cb110b5479c7790d997399e380c9b1abb"


def exact_row(enemy="Chappy", token="Chappy"):
    return {"source": {"enemy_id": enemy, "source_token": token,
                       "carried_treasure": None, "drop_mode": 0}}


def carrier_row(enemy="Carrier", token="Carrier_x", treasure="cargo_y", drop=0):
    return {"source": {"enemy_id": enemy, "source_token": token,
                       "carried_treasure": treasure, "drop_mode": drop}}


def packet_floors():
    floors = []
    for number in range(1, 9):
        rows = [carrier_row()] if number in (3, 5, 8) else [exact_row()]
        floors.append({
            "first_floor": number, "last_floor": number,
            "parameters": {"f008": "pool%d.txt" % number},
            "enemies": rows,
            "treasures": [], "caps": [], "gates": [],
        })
    return floors


PACKET = {"schema": "p2-cave-import-p0-1", "cave": "tutorial_3",
          "source_sha256": SHA, "floors": packet_floors()}


def write_packet(tmp, payload=None):
    path = Path(tmp) / "packet.json"
    path.write_text(json.dumps(payload if payload is not None else PACKET),
                    encoding="utf-8")
    return path


class CarrierStagingTests(unittest.TestCase):
    def test_known_pins_accepted(self):
        pins = staging.check_pins()
        self.assertEqual(pins["source_sha256"], SHA)

    def test_missing_pin_fail_closed(self):
        pins = dict(staging.KNOWN_PINS)
        del pins["source_sha256"]
        with self.assertRaises(staging.StagingRejected):
            staging.check_pins(pins)

    def test_unknown_pin_fail_closed(self):
        pins = dict(staging.KNOWN_PINS, source_sha256="0" * 64)
        with self.assertRaises(staging.StagingRejected):
            staging.check_pins(pins)
        with self.assertRaises(staging.StagingRejected):
            staging.check_pins(dict(staging.KNOWN_PINS, extra_pin="x"))

    def test_known_handoffs_accepted(self):
        handoffs = staging.check_handoffs()
        self.assertEqual(handoffs["p2-cave-tutorial_3-p1-source-recovery"]["root"],
                         "5c12c69916ae2cc6bb0084e4848ce5f9e9cb7c3f")
        self.assertEqual(handoffs["provider-placement-carrier-landing"]["root"],
                         "4a4e367b420fc3f3bca1e5dff4d464e78db9db61")

    def test_missing_handoff_fail_closed(self):
        handoffs = staging.check_handoffs()
        del handoffs["provider-placement-carrier-landing"]
        with self.assertRaises(staging.StagingRejected):
            staging.check_handoffs(handoffs)

    def test_unknown_handoff_root_fail_closed(self):
        handoffs = staging.check_handoffs()
        handoffs["p2-cave-tutorial_3-p1-source-recovery"]["root"] = "0" * 40
        with self.assertRaises(staging.StagingRejected):
            staging.check_handoffs(handoffs)

    def test_carrier_floors_block_with_rows(self):
        for number in (3, 5, 8):
            staged = staging.stage_floor(PACKET, number)
            self.assertEqual(staged["status"], "BLOCKED_CARRIER_TOKEN")
            self.assertEqual(len(staged["carrier_rows"]), 1)
            self.assertEqual(staged["carrier_rows"][0]["enemy_id"], "Carrier")
            self.assertEqual(staged["unit_pool"], "pool%d.txt" % number)

    def test_exact_floors_pass_through(self):
        for number in (2, 4, 6, 7):
            staged = staging.stage_floor(PACKET, number)
            self.assertEqual(staged["status"], "EXACT")
            self.assertEqual(staged["carrier_rows"], [])

    def test_floor1_refused_no_duplication(self):
        with self.assertRaises(staging.StagingRejected):
            staging.stage_floor(PACKET, 1)

    def test_drop_mode_token_counts_as_carrier(self):
        bad = json.loads(json.dumps(PACKET))
        floor = [f for f in bad["floors"] if f["first_floor"] == 2][0]
        floor["enemies"] = [carrier_row(treasure=None, drop=2)]
        with self.assertRaises(staging.StagingRejected):
            staging.stage_floor(bad, 2)

    def test_carrier_floor_without_tokens_fail_closed(self):
        bad = json.loads(json.dumps(PACKET))
        floor = [f for f in bad["floors"] if f["first_floor"] == 3][0]
        floor["enemies"] = [exact_row()]
        with self.assertRaises(staging.StagingRejected):
            staging.stage_floor(bad, 3)

    def test_packet_binds_handoffs_consumer_recovery(self):
        with tempfile.TemporaryDirectory() as tmp:
            staged = staging.build_packet(write_packet(tmp))
            body = staged["packet"]
            self.assertEqual(body["handoffs"]["provider-placement-carrier-landing"]["issue"], 657)
            self.assertEqual(body["handoffs"]["p2-cave-tutorial_3-p1-source-recovery"]["issue"], 153)
            self.assertEqual(body["downstream_consumer"]["issue"], 812)
            self.assertEqual(body["downstream_consumer"]["root_head"],
                             "2a97c0682c6bead1990f8f4cedb469623da18e06")
            self.assertEqual(body["downstream_consumer"]["native_head"],
                             "a6a63f0ddd18f3ab9d08a7e6110c464766b9bd92")
            self.assertEqual(body["recovery_request"],
                             "9002486c30bb9ab1e6dd030aa8cb82d317750911844ed2aca2c84d35e0d08372")
            self.assertEqual(sorted(int(k) for k in body["floors"]), [3, 5, 8])

    def test_consumer_check_names_real_commands(self):
        check = staging.consumer_check()
        text = json.dumps(check)
        self.assertIn("tests.content_lanes.test_p2_cave_tutorial_3_p1_later_floors", text)
        self.assertIn("p2-cave-tutorial_3_p1_later_floors.py", text)
        self.assertIn("pikmin2_tutorial3_carrier_token_staging.py", text)
        self.assertIn("9002486c30bb9ab1e6dd030aa8cb82d317750911844ed2aca2c84d35e0d08372", text)
        self.assertIn("2,4,6,7", text)

    def test_write_staging_hashes(self):
        with tempfile.TemporaryDirectory() as tmp:
            packet = write_packet(tmp)
            result = staging.write_staging(packet, Path(tmp) / "out")
            self.assertTrue(Path(result["json"]).is_file())
            sidecar = Path(result["sidecar"]).read_text(encoding="utf-8")
            self.assertIn("P2_TUTORIAL3_CARRIER_STAGING_1", sidecar)
            self.assertIn("recovery 9002486c30bb9ab1e6dd030aa8cb82d317750911844ed2aca2c84d35e0d08372",
                          sidecar)
            self.assertIn("BLOCKED_CARRIER_TOKEN", sidecar)
            self.assertIn("UNTESTEDx6", sidecar)


if __name__ == "__main__":
    unittest.main()
