"""Isolated tests for the ElecHiba source-22 pin audit (#816).

No native build, no repo writes, no fixtures beyond pure-text samples.
Covers the happy path (wave hiba header), malformed/missing inputs
(fail-closed ValueError), and the ElecBug28-bridge applicability rule.
"""
import unittest

from experimental.pikmin2_elechiba22_pin_audit import (
    ELEC_HIBA_SYMBOLS,
    audit_record,
    classify_admission,
    delivery_bridge_applicable,
    find_symbols,
)

WAVE_HIBA_HEADER = """#pragma once
// Pikmin 2 lane-22 fixed-hazard sidecar runtime (#170, child #447).
// Opt-in, actor-local Hiba (20, fire geyser), GasHiba (21, gas pipe) and
// ElecHiba (22, electrical wire) behavior. Gated on p2-hiba-native.txt.
void pc_p2_hiba_setup();
void pc_p2_hiba_denki_hit_seen();
void pc_p2_hiba_denki_immune_seen();
bool pc_p2_hiba_denki_lethal();
"""

ELECBUG_HEADER = """#pragma once
class BTeki;
// Family-owned ground-invertebrate source behavior: Anode Beetle.
void pc_p2_elecbug_setup();
void pc_p2_elecbug_forget(BTeki*);
"""


class FindSymbolsTests(unittest.TestCase):
    def test_wave_hiba_symbols_all_present(self):
        found = find_symbols(WAVE_HIBA_HEADER, ELEC_HIBA_SYMBOLS)
        self.assertTrue(all(found.values()), found)

    def test_missing_symbol_reported_false(self):
        found = find_symbols("void unrelated();", ELEC_HIBA_SYMBOLS)
        self.assertFalse(any(found.values()))

    def test_malformed_input_rejected(self):
        for bad in (None, 0, b"bytes", ["list"]):
            with self.assertRaises(ValueError):
                find_symbols(bad, ELEC_HIBA_SYMBOLS)

    def test_empty_text_yields_all_false(self):
        found = find_symbols("", ELEC_HIBA_SYMBOLS)
        self.assertFalse(any(found.values()))


class ClassifyTests(unittest.TestCase):
    def test_fixed_hazard_sidecar(self):
        self.assertEqual(classify_admission(WAVE_HIBA_HEADER), "fixed-hazard-sidecar")

    def test_actor_family_module(self):
        self.assertEqual(classify_admission(ELECBUG_HEADER), "actor-family-module")

    def test_absent_on_empty_or_blank(self):
        self.assertEqual(classify_admission(""), "absent")
        self.assertEqual(classify_admission("   \n "), "absent")

    def test_malformed_input_rejected(self):
        for bad in (None, 42, b"bytes"):
            with self.assertRaises(ValueError):
                classify_admission(bad)

    def test_bridge_rule(self):
        self.assertFalse(delivery_bridge_applicable("fixed-hazard-sidecar"))
        self.assertTrue(delivery_bridge_applicable("actor-family-module"))
        self.assertFalse(delivery_bridge_applicable("absent"))
        with self.assertRaises(ValueError):
            delivery_bridge_applicable("unknown-kind")


class AuditRecordTests(unittest.TestCase):
    def test_record_shape_and_verdict(self):
        record = audit_record(WAVE_HIBA_HEADER, False)
        self.assertEqual(record["source_id"], 22)
        self.assertEqual(record["classification"], "fixed-hazard-sidecar")
        self.assertFalse(record["delivery_bridge_applicable"])
        self.assertFalse(record["in_maintained_main"])
        self.assertTrue(all(record["symbols_present"].values()))
        self.assertIsNotNone(record["blocker"])


if __name__ == "__main__":
    unittest.main()
