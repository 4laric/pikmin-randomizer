"""Focused tests for the kusachi content-wiring bridge (#688)."""
import importlib.util
import unittest
from pathlib import Path

MODULE = (Path(__file__).resolve().parents[1] / "experimental"
          / "pikmin2_kusachi_content_wiring.py")
_spec = importlib.util.spec_from_file_location("kusachi_content_wiring", MODULE)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

staged_identity = _mod.staged_identity
verify_source_bytes = _mod.verify_source_bytes
decode_layout = _mod.decode_layout
arena_binding = _mod.arena_binding
actor_rows = _mod.actor_rows
starting_squad = _mod.starting_squad
boot_params = _mod.boot_params
wiring_packet = _mod.wiring_packet
MissingInput = _mod.MissingInput
HashMismatch = _mod.HashMismatch
LayoutDecodeError = _mod.LayoutDecodeError
BOOT_MARKERS = _mod.BOOT_MARKERS
SOURCE_SHA256 = _mod.SOURCE_SHA256


def mini_caveinfo():
    return ("{ {c000} 4 1 {_eof} } 1\n"
            "{ {f000} 4 0 {f001} 4 0 {f008} -1 kusachi_pool.txt "
            "{f009} -1 test_light.ini {f015} 4 1 {_eof} }\n"
            "{ 2 Alpha 21 1 Beta 4 6 }\n"
            "{ 1 gem_one 12 }\n{ 0 }\n{ 1 0 Egg 11 1 }")


ENEMIES = {"Alpha", "Beta", "Egg"}
TREASURES = {"gem_one"}


class IdentityTests(unittest.TestCase):
    def test_staged_identity_pinned(self):
        ident = staged_identity()
        self.assertEqual(ident["cave_id"], "ch_NARI_01kusachi")
        self.assertEqual(ident["source_sha256"], SOURCE_SHA256)
        self.assertEqual(ident["floors"], 1)
        self.assertEqual(ident["ui_index"], 3)
        self.assertEqual(ident["roster"][0], [0, 0, 50])
        self.assertEqual(ident["floor_seconds"], [180.0])
        self.assertEqual((ident["bitter_sprays"], ident["spicy_sprays"]), (1, 2))

    def test_source_hash_gate(self):
        with self.assertRaises(HashMismatch):
            verify_source_bytes(b"not the source")


class DecodeTests(unittest.TestCase):
    def test_synthetic_decode_and_coverage(self):
        decoded = decode_layout(mini_caveinfo(), ENEMIES, TREASURES)
        self.assertEqual(decoded["floor_count"], 1)
        arena = arena_binding(decoded)
        self.assertEqual(arena["unit_pool"], "kusachi_pool.txt")
        self.assertEqual(arena["light"], "test_light.ini")
        rows = actor_rows(decoded)
        kinds = sorted({r["kind"] for r in rows})
        # The mini gate block is empty (count 0), so no gate kind appears.
        self.assertEqual(kinds, ["cap", "enemy", "treasure"])
        self.assertTrue(all("source_weight" in r["record"] or "gate_id" in r["record"]
                            or r["record"].get("empty") is not None or "token" in r["record"]
                            for r in rows))

    def test_malformed_decode_fails_closed(self):
        for text in ("", "{ unbalanced",
                     mini_caveinfo().replace("{c000} 4 1", "{c000} 4 2"),
                     mini_caveinfo().replace("kusachi_pool.txt", "../evil.txt")):
            with self.subTest(text=text[:30]), self.assertRaises((ValueError, LayoutDecodeError)):
                arena_binding(decode_layout(text, ENEMIES, TREASURES))

    def test_unknown_reference_rejected(self):
        with self.assertRaises(LayoutDecodeError):
            decode_layout(mini_caveinfo(), {"Other"}, TREASURES)


class BootParamTests(unittest.TestCase):
    def setUp(self):
        self.decoded = decode_layout(mini_caveinfo(), ENEMIES, TREASURES)

    def test_squad_wiring(self):
        squad = starting_squad()
        self.assertEqual(squad["roster"][0], [0, 0, 50])
        self.assertEqual(squad["ui_index"], 3)

    def test_boot_params_shape(self):
        params = boot_params(self.decoded)
        self.assertEqual(params["cave_id"], "ch_NARI_01kusachi")
        self.assertEqual(params["ui_index"], 3)
        self.assertEqual(params["selection"]["mechanism"],
                         "host-mode StageEntry table keyed by ui_index")
        self.assertIn("harness", params)
        self.assertEqual(list(params["markers"]), list(BOOT_MARKERS))
        self.assertEqual(len(BOOT_MARKERS), 5)

    def test_boot_params_carry_no_placements(self):
        blob = repr(boot_params(self.decoded))
        for banned in ("spawn_position", "coordinates", "x=", "z="):
            self.assertNotIn(banned, blob)

    def test_packet_shape(self):
        packet = wiring_packet(boot_params(self.decoded))
        self.assertEqual(packet["schema"], 1)
        self.assertEqual(packet["source_sha256"], SOURCE_SHA256)
        self.assertFalse(packet["generated"])
        self.assertEqual(packet["semantic_resolution"], "open")
        self.assertTrue(packet["blockers"] and packet["limitations"])


if __name__ == "__main__":
    unittest.main()
