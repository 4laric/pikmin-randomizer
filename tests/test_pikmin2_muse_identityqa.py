"""Focused adversarial tests for the muse identityqa runner (#506).

The runner must stay fail-closed across all five adversarial classes for all
four candidates (41/57/58/78): only a fully correlated, untainted,
terrain-legal triple may yield gate1_ok True. These tests pin that contract
so placement (l52) / packaging (l53) candidates are audited, never trusted.
"""

import unittest

from experimental.pikmin2_muse_identityqa import (
    audit_assets,
    audit_log,
    audit_replay,
    run_adversarial,
)

GEN = 245001
UID = 918273


def placement_line(gen=GEN, uid=UID, terrain="ground", xyz="1", route="1"):
    return (
        "P2_PLACEMENT_SLOT generator=%d slot=%d actor=11 xyz=%s terrain=%s "
        "route=%s route_distance=12.3 x=1.000 y=0.000 z=2.000 water_depth=0.00"
        % (gen, uid, xyz, terrain, route))


def resolve_line(source=41, uid=UID):
    return ("P2_SEED_RESOLVE source_id=%d target=%d original_type=11 x=1.0 z=2.0"
            % (source, uid))


def generated_line(source=41, uid=UID, bound=1):
    return ("P2_GENERATED_PLACEMENT source_id=%d target=%d bound=%d"
            % (source, uid, bound))


BINDINGS = {
    41: "P2_HARDLANES_READY family=Fuefuki vehicle=Napkid gen=%d type=11" % GEN,
    57: "P2_KURAGE_TEKI_READY generator=%d" % GEN,
    58: "P2_BOMBSARAI_SUPPLY generator=%d" % GEN,
    78: "P2_GROINK_SPOTTED generator=%d" % GEN,
}


def good_log(source=41):
    return "\n".join([
        placement_line(), resolve_line(source), generated_line(source),
        BINDINGS[source],
    ])


class MuseIdentityqaLogTests(unittest.TestCase):
    def test_correlated_triple_passes_per_candidate(self):
        for source in (41, 57, 58, 78):
            with self.subTest(source=source):
                verdict = audit_log(good_log(source), source)
                self.assertTrue(verdict["gate1_ok"], verdict["findings"])
                self.assertEqual(verdict["slot"], UID)
                self.assertEqual(verdict["generator"], GEN)
                self.assertEqual(verdict["findings"], [])

    def test_swapped_resolve_source_fails(self):
        verdict = audit_log(
            "\n".join([placement_line(), resolve_line(57),
                       generated_line(41), BINDINGS[41]]), 41)
        self.assertFalse(verdict["gate1_ok"])
        self.assertTrue(any(f.startswith("swapped-source")
                            for f in verdict["findings"]))

    def test_swapped_binding_family_fails(self):
        verdict = audit_log(
            "\n".join([placement_line(), resolve_line(41),
                       generated_line(41), BINDINGS[57]]), 41)
        self.assertFalse(verdict["gate1_ok"])
        self.assertTrue(any(f.startswith("swapped-source")
                            for f in verdict["findings"]))

    def test_slot_disagreement_fails(self):
        verdict = audit_log(
            "\n".join([placement_line(), resolve_line(41, uid=111222),
                       generated_line(41), BINDINGS[41]]), 41)
        self.assertFalse(verdict["gate1_ok"])
        self.assertTrue(any(f.startswith("generator-slot")
                            for f in verdict["findings"]))

    def test_generator_mismatch_fails(self):
        other = BINDINGS[41].replace("gen=%d" % GEN, "gen=245002")
        verdict = audit_log(
            "\n".join([placement_line(), resolve_line(41),
                       generated_line(41), other]), 41)
        self.assertFalse(verdict["gate1_ok"])
        self.assertTrue(any(f.startswith("generator-slot")
                            for f in verdict["findings"]))

    def test_bound_zero_refused_fails(self):
        verdict = audit_log(
            "\n".join([resolve_line(41), generated_line(41, bound=0),
                       BINDINGS[41]]), 41)
        self.assertFalse(verdict["gate1_ok"])
        self.assertTrue(any("bound=0" in f for f in verdict["findings"]))

    def test_missing_resolve_fails_closed(self):
        verdict = audit_log(
            "\n".join([placement_line(), BINDINGS[41]]), 41)
        self.assertFalse(verdict["gate1_ok"])
        self.assertTrue(any("P2_SEED_RESOLVE" in f
                            for f in verdict["findings"]))

    def test_unmapped_slot_fails(self):
        verdict = audit_log(
            "\n".join([placement_line(uid=0), resolve_line(41),
                       BINDINGS[41]]), 41)
        self.assertFalse(verdict["gate1_ok"])
        self.assertTrue(any("slot=0" in f for f in verdict["findings"]))

    def test_water_terrain_fails(self):
        verdict = audit_log(
            "\n".join([placement_line(terrain="water"), resolve_line(41),
                       generated_line(41), BINDINGS[41]]), 41)
        self.assertFalse(verdict["gate1_ok"])
        self.assertTrue(any(f.startswith("unsupported-terrain")
                            for f in verdict["findings"]))

    def test_air_terrain_fails(self):
        verdict = audit_log(
            "\n".join([placement_line(terrain="air"), resolve_line(41),
                       generated_line(41), BINDINGS[41]]), 41)
        self.assertFalse(verdict["gate1_ok"])

    def test_missing_route_fails(self):
        verdict = audit_log(
            "\n".join([placement_line(route="0"), resolve_line(41),
                       generated_line(41), BINDINGS[41]]), 41)
        self.assertFalse(verdict["gate1_ok"])

    def test_mixed_terrain_allowed_only_for_kurage(self):
        mixed = placement_line(terrain="mixed")
        ok_kurage = audit_log(
            "\n".join([mixed, resolve_line(57), generated_line(57),
                       BINDINGS[57]]), 57)
        self.assertTrue(ok_kurage["gate1_ok"], ok_kurage["findings"])
        bad_fuefuki = audit_log(
            "\n".join([mixed, resolve_line(41), generated_line(41),
                       BINDINGS[41]]), 41)
        self.assertFalse(bad_fuefuki["gate1_ok"])

    def test_injected_taint_fails_and_labels(self):
        tainted = "\n".join([placement_line(), resolve_line(41),
                             generated_line(41), BINDINGS[41],
                             "P2_SEED_RESOLVE source_id=41 target=%d "
                             "injected health_zero" % UID])
        verdict = audit_log(tainted, 41)
        self.assertFalse(verdict["gate1_ok"])
        self.assertTrue(any(f.startswith("injected-taint")
                            for f in verdict["findings"]))

    def test_empty_log_absent_not_pass(self):
        verdict = audit_log("", 41)
        self.assertFalse(verdict["gate1_ok"])
        self.assertTrue(any(f.startswith("absent-markers")
                            for f in verdict["findings"]))

    def test_legacy_auto_bind_is_not_identity(self):
        proxy = "\n".join([
            "P2_KURAGE_TEKI_READY generator=201001",
            "P2_KURAGE_CORPSE_READY generator=201001 "
            "receipt=corpse:kurage:201001",
        ])
        verdict = audit_log(proxy, 57)
        self.assertFalse(verdict["gate1_ok"])


class MuseIdentityqaAssetReplayTests(unittest.TestCase):
    def test_missing_asset_finding(self):
        findings = audit_assets({41: {"staged": True, "sha256": "aa"}},
                                {41: "aa", 57: "bb", 58: "cc", 78: "dd"})
        self.assertTrue(any("source_id=57" in f for f in findings))
        self.assertTrue(any("source_id=58" in f for f in findings))
        self.assertTrue(any("source_id=78" in f for f in findings))

    def test_hash_mismatch_finding(self):
        findings = audit_assets({41: {"staged": True, "sha256": "wrong"}},
                                {41: "aa"})
        self.assertTrue(any("disagrees" in f for f in findings))

    def test_fresh_assets_clean(self):
        manifest = {sid: {"staged": True, "sha256": "%02x" % sid}
                    for sid in (41, 57, 58, 78)}
        expected = {sid: "%02x" % sid for sid in (41, 57, 58, 78)}
        self.assertEqual(audit_assets(manifest, expected), [])

    def test_stale_replay_finding(self):
        staged = {"plan_digest": "p1", "cache_generation": 7}
        observed = {"plan_digest": "p2", "cache_generation": 6}
        findings = audit_replay(staged, observed)
        self.assertEqual(len(findings), 2)
        self.assertTrue(all(f.startswith("stale-replay") for f in findings))

    def test_fresh_replay_clean(self):
        record = {"plan_digest": "p1", "cache_generation": 7}
        self.assertEqual(audit_replay(record, dict(record)), [])

    def test_runner_matches_expectations(self):
        summary = run_adversarial([
            {"name": "clean-41", "source_id": 41, "log": good_log(41),
             "expect_ok": True},
            {"name": "swapped-41", "source_id": 41,
             "log": "\n".join([placement_line(), resolve_line(58),
                                generated_line(41), BINDINGS[41]]),
             "expect_ok": False},
            {"name": "stale-57", "source_id": 57, "log": good_log(57),
             "staged": {"plan_digest": "p1", "cache_generation": 7},
             "observed": {"plan_digest": "p1", "cache_generation": 6},
             "expect_ok": False},
        ])
        self.assertEqual(summary["passed"], 3)
        self.assertEqual(summary["failed"], 0)


if __name__ == "__main__":
    unittest.main()
