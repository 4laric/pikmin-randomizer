"""Negative/contract tests for the muse Fuefuki gate-1 observer (#497).

The observer must stay fail-closed until the placement (l52/#492) and
packaging (l53/#493) candidates land: only a fully correlated triple — same
seed uid in placement slot and source-41 resolve, same generator file id in
placement and Fuefuki binding, mapped slot, ground terrain, route evidence —
may yield gate1_ok True.
"""

import unittest

from experimental.pikmin2_muse_fuefuki import parse

GEN = 245001
UID = 918273

PLACEMENT = (
    "P2_PLACEMENT_SLOT generator=%d slot=%d actor=11 xyz=1 terrain=ground "
    "route=1 route_distance=12.3 x=1.000 y=0.000 z=2.000 water_depth=0.00"
    % (GEN, UID)
)
SEED = "P2_SEED_RESOLVE source_id=41 target=%d original_type=11 x=1.0 z=2.0" % UID
BIND = (
    "P2_HARDLANES_READY family=Fuefuki vehicle=Napkid gen=%d type=11 "
    "follow_locomotion=actteki_volatile_approx" % GEN
)


class MuseFuefukiObserverTests(unittest.TestCase):
    def test_correlated_triple_passes(self):
        verdict = parse("\n".join([PLACEMENT, SEED, BIND]))
        self.assertTrue(verdict["gate1_ok"])
        self.assertTrue(verdict["same_generator"])
        self.assertEqual(verdict["generator"], GEN)
        self.assertEqual(verdict["seed_uid"], UID)

    def test_teki_marker_counts_as_binding(self):
        teki = "P2_FUEFUKI_TEKI_DEAD generator=%d" % GEN
        verdict = parse("\n".join([PLACEMENT, SEED, teki]))
        self.assertTrue(verdict["gate1_ok"])

    def test_binding_file_id_mismatch_fails(self):
        other_bind = BIND.replace("gen=%d" % GEN, "gen=245002")
        verdict = parse("\n".join([PLACEMENT, SEED, other_bind]))
        self.assertFalse(verdict["gate1_ok"])

    def test_seed_uid_mismatch_fails(self):
        other_seed = SEED.replace("target=%d" % UID, "target=111222")
        verdict = parse("\n".join([PLACEMENT, other_seed, BIND]))
        self.assertFalse(verdict["gate1_ok"])

    def test_missing_placement_fails(self):
        self.assertFalse(parse("\n".join([SEED, BIND]))["gate1_ok"])

    def test_missing_seed_resolve_fails(self):
        # Staged Napkid proxy markers without any seed leg (legacy l28
        # teki-receipt shape) must never read as a generated identity.
        proxy = "\n".join(
            [
                "P2_HARDLANES_READY family=Fuefuki vehicle=Napkid gen=%d type=11" % GEN,
                "P2_FUEFUKI_TEKI_DEAD generator=%d" % GEN,
            ]
        )
        verdict = parse(proxy)
        self.assertFalse(verdict["gate1_ok"])
        self.assertEqual(verdict["seed_resolve_41_targets"], [])

    def test_wrong_source_id_fails(self):
        other = SEED.replace("source_id=41", "source_id=57")
        verdict = parse("\n".join([PLACEMENT, other, BIND]))
        self.assertFalse(verdict["gate1_ok"])
        self.assertTrue(verdict["seed_resolve_other_source"])

    def test_missing_binding_fails(self):
        self.assertFalse(parse("\n".join([PLACEMENT, SEED]))["gate1_ok"])

    def test_unmapped_slot_fails_closed(self):
        unmapped = PLACEMENT.replace("slot=%d" % UID, "slot=0")
        verdict = parse("\n".join([unmapped, SEED, BIND]))
        self.assertFalse(verdict["gate1_ok"])

    def test_water_terrain_fails_closed(self):
        water = PLACEMENT.replace("terrain=ground", "terrain=water")
        verdict = parse("\n".join([water, SEED, BIND]))
        self.assertFalse(verdict["gate1_ok"])

    def test_missing_route_fails_closed(self):
        off_route = PLACEMENT.replace("route=1", "route=0")
        verdict = parse("\n".join([off_route, SEED, BIND]))
        self.assertFalse(verdict["gate1_ok"])

    def test_empty_log_fails(self):
        verdict = parse("")
        self.assertFalse(verdict["gate1_ok"])
        self.assertEqual(verdict["generator"], -1)


if __name__ == "__main__":
    unittest.main()
