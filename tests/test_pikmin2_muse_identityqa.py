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


class MuseIdentityqaRealCandidateTests(unittest.TestCase):
    """Adversarial audit of the REAL l52/l53 candidates (#492/#493).

    Consumed as reviewed cherry-picks (placement root ``bd97334a`` + native
    ``4765885b``, packaging ``3131b76d`` + ``f82171d4``). These tests compose
    the real placement observer and the real packaging stager with this
    lane's runner over faithful native marker text, proving the pair fails
    closed where either alone would not.
    """

    REAL_BINDINGS = {
        41: "P2_HARDLANES_READY family=Fuefuki vehicle=Napkid gen=%d type=11",
        57: "P2_KURAGE_TEKI_READY generator=%d",
        58: "P2_BOMBSARAI_SUPPLY generator=%d",
        78: "P2_GROINK_SPOTTED generator=%d",
    }

    def real_log(self, source, uid=None, gen=GEN, bound=1, reason=None):
        from experimental.pikmin2_muse_placement import MUSE_ACCEPTED_SLOT
        uid = MUSE_ACCEPTED_SLOT[source] if uid is None else uid
        bind = ("P2_GENERATED_PLACEMENT source_id=%d target=%d generator=%d "
                "bound=%d" % (source, uid, gen, bound))
        if bound != 1 and reason:
            bind += " reason=%s" % reason
        return "\n".join([
            placement_line(gen=gen, uid=uid),
            resolve_line(source, uid),
            bind,
            self.REAL_BINDINGS[source] % gen,
        ])

    def test_real_accepted_triple_agrees_both_runners(self):
        from experimental.pikmin2_muse_placement import observe_identity
        for source in (41, 57, 58, 78):
            with self.subTest(source=source):
                log = self.real_log(source)
                placement = observe_identity(log, source)
                self.assertTrue(placement["correlated"], placement)
                verdict = audit_log(log, source)
                self.assertTrue(verdict["gate1_ok"], verdict["findings"])
                self.assertEqual(verdict["slot"], placement["bound_uid"])
                self.assertEqual(verdict["findings"], [])

    def test_non_accepted_slot_needs_composition(self):
        # A uid-consistent triple on a NON-accepted slot passes this
        # runner alone (it knows no allowlist) but the real placement
        # observer refuses it: the audit verdict is the pair, fail closed.
        from experimental.pikmin2_muse_placement import (
            MUSE_ACCEPTED_SLOT,
            observe_identity,
        )
        for source in (41, 57, 58, 78):
            with self.subTest(source=source):
                rogue = MUSE_ACCEPTED_SLOT[source] + 1
                log = self.real_log(source, uid=rogue)
                placement = observe_identity(log, source)
                self.assertFalse(placement["correlated"])
                self.assertEqual(placement["refusal_reason"],
                                 "slot-not-accepted")
                composed_ok = (audit_log(log, source)["gate1_ok"]
                               and placement["correlated"])
                self.assertFalse(composed_ok)

    def test_real_native_refusal_fails_both(self):
        from experimental.pikmin2_muse_placement import observe_identity
        log = self.real_log(41, bound=0, reason="slot-rejected")
        placement = observe_identity(log, 41)
        self.assertFalse(placement["bound"])
        self.assertFalse(placement["correlated"])
        verdict = audit_log(log, 41)
        self.assertFalse(verdict["gate1_ok"])
        self.assertTrue(any("bound=0" in f for f in verdict["findings"]))

    def test_binding_generator_mismatch_is_runner_leg(self):
        # Resolve+bind agree on the accepted uid, so the placement observer
        # stays correlated; the family binding names another generator, so
        # only this runner's generator leg catches it.
        from experimental.pikmin2_muse_placement import (
            MUSE_ACCEPTED_SLOT,
            observe_identity,
        )
        uid = MUSE_ACCEPTED_SLOT[41]
        log = "\n".join([
            placement_line(uid=uid),
            resolve_line(41, uid),
            "P2_GENERATED_PLACEMENT source_id=41 target=%d generator=%d "
            "bound=1" % (uid, GEN),
            self.REAL_BINDINGS[41] % 245002,
        ])
        self.assertTrue(observe_identity(log, 41)["correlated"])
        verdict = audit_log(log, 41)
        self.assertFalse(verdict["gate1_ok"])
        self.assertTrue(any(f.startswith("generator-slot")
                            for f in verdict["findings"]))

    @staticmethod
    def seed_content(root):
        import json
        from experimental import pikmin2_muse_packaging as packaging
        content = root / "content"
        manifest = {
            "schema": 1, "policy": "P2_BOMBSARAI_IMPORT_1",
            "disc_id": "GPVE01", "disc_revision": 0,
            "source_revision": "632af93787b9c95b63f0c13be32b161375ce3a96",
            "payload": {"enemy": "Bomb", "enemy_id": 36, "child_num": 2},
            "species": {"BombSarai": {"enemy_id": 58, "role": "carrier",
                                      "parameter_blocks": [{}, {"speed": 1},
                                                           {"hp": 2}],
                                      "clips": [
                                          {"name": name, "source_frames": 2,
                                           "status": "converted",
                                           "poses": [{"frame": 0}]}
                                          for name in ("wait1", "wait2",
                                                       "release1", "dead1")]}},
        }
        for source_id, enum_name in packaging.CANDIDATES.items():
            ident = content / enum_name
            ident.mkdir(parents=True)
            if source_id == 58:
                (ident / "bombsarai.json").write_text(json.dumps(manifest))
            else:
                (ident / "identity.json").write_text(json.dumps(
                    {"schema": 1, "source_id": source_id,
                     "enum_name": enum_name}))
        return content

    def test_real_staging_tamper_maps_to_finding(self):
        import tempfile
        from pathlib import Path
        from experimental import pikmin2_muse_packaging as packaging
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            content = self.seed_content(tmp)
            retail = tmp / "retail"
            (retail / "dataDir" / "stages").mkdir(parents=True)
            (retail / "dataDir" / "stages" / "base.bin").write_bytes(b"r")
            run = tmp / "run"
            layout = {"bindings": [
                {"target": "slot-fuefuki", "source_id": 41,
                 "enum_name": "Fuefuki"},
                {"target": "slot-kurage", "source_id": 57,
                 "enum_name": "Kurage"},
                {"target": "slot-bombsarai", "source_id": 58,
                 "enum_name": "BombSarai"},
                {"target": "slot-minihoudai", "source_id": 78,
                 "enum_name": "MiniHoudai"},
            ]}
            actors = {"slot-fuefuki": 41001, "slot-kurage": 57001,
                      "slot-bombsarai": 58001, "slot-minihoudai": 78001}
            receipt = packaging.stage_candidates(run, layout, content, actors,
                                                 retail_assets=retail)
            self.assertTrue(packaging.verify_staging(
                run, layout, actors)["verified"])
            # Tamper one staged sidecar: the real verifier raises, and the
            # audit maps the receipt digest pair to a stale/missing finding.
            sidecar = run / packaging.actors_filename("Fuefuki")
            with sidecar.open("ab") as stream:
                stream.write(b"tamper")
            with self.assertRaises(packaging.StagingError):
                packaging.verify_staging(run, layout, actors)
            staged = {"plan_digest": receipt["plan_digest"],
                      "cache_generation": 1}
            self.assertEqual(audit_replay(staged, dict(staged)), [])
            observed = dict(staged, plan_digest="deadbeef")
            findings = audit_replay(staged, observed)
            self.assertTrue(any(f.startswith("stale-replay")
                                for f in findings))

    def test_real_conflicting_restage_refused(self):
        import tempfile
        from pathlib import Path
        from experimental import pikmin2_muse_packaging as packaging
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            content = self.seed_content(tmp)
            run = tmp / "run"
            (run / "assets" / "dataDir" / "courses" / "pikmin2room").mkdir(
                parents=True)
            layout = {"bindings": [
                {"target": "slot-fuefuki", "source_id": 41,
                 "enum_name": "Fuefuki"},
            ]}
            packaging.stage_candidates(run, layout, content,
                                       {"slot-fuefuki": 41001})
            other = {"bindings": [
                {"target": "slot-kurage", "source_id": 57,
                 "enum_name": "Kurage"},
            ]}
            with self.assertRaises(packaging.StagingError):
                packaging.stage_candidates(run, other, content,
                                           {"slot-kurage": 57001})


if __name__ == "__main__":
    unittest.main()
