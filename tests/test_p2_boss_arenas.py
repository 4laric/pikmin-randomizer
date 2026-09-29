"""P2 boss arenas (#899, owner ruling 2026-09-29 #3).

Pins the catalogue against the spawn inventory and the native mirror, the
placement document's arena slots, and the seed contract: arena bosses are
placed only in boss arenas (their own RNG stream, sampled per seed), and the
ordinary layout is exactly the layout of the same pool without the bosses.
"""
import copy
import json
import os
import re
import unittest
from pathlib import Path

from experimental.pikmin2_enemy_roster import load_and_validate
from experimental.pikmin2_seed_bridge import (BOSS_ARENA_KEY, SeedBridgeError, arena_boss_ids,
                                              resolve_placement_layout, validate_layout)
from randomizer import p2_boss_arenas as arenas
from randomizer.p2_placement import audit, validate_document
from randomizer.seed import PLAYABLE_P2_SPECIES, generate, validate
from randomizer.spawn_data import GENERATOR_SLOTS

ROOT = Path(__file__).resolve().parents[1]
DOCUMENT = ROOT / "docs" / "PIKMIN2_ADMITTED_PLACEMENT.json"


def _native_policy():
    candidates = []
    if os.environ.get("PIKMIN_NATIVE_ROOT"):
        candidates.append(Path(os.environ["PIKMIN_NATIVE_ROOT"]))
    candidates.append(ROOT / "native")
    for base in candidates:
        path = base / "pc_port" / "pc_p2_boss_arena_policy.h"
        if path.is_file():
            return path.read_text(encoding="utf-8")
    return None


def _document():
    return json.loads(DOCUMENT.read_text(encoding="utf-8"))


def _strip_arenas(document):
    """The same document with the arena slots and arena records removed."""
    stripped = copy.deepcopy(document)
    arena_uids = {arena["spawn_uids"][0] for arena in arenas.P1_BOSS_ARENAS}
    stripped["slots"] = [s for s in stripped["slots"] if s["uid"] not in arena_uids]
    stripped.pop("arenas", None)
    return stripped


class CatalogueTests(unittest.TestCase):
    def test_every_arena_uid_is_a_real_p1_boss_generator(self):
        rows = {uid: (stage, name, offset, kind, species)
                for uid, stage, name, offset, kind, species in GENERATOR_SLOTS}
        for arena in arenas.P1_BOSS_ARENAS:
            for uid in arena["spawn_uids"] + arena["suppress_uids"]:
                self.assertIn(uid, rows, (arena["id"], uid))
                stage, _, _, kind, _ = rows[uid]
                self.assertEqual(stage, arena["stage"], (arena["id"], uid))
                self.assertEqual(kind, arena["p1_kind"], (arena["id"], uid))
            _, _, _, _, species = rows[arena["spawn_uids"][0]]
            self.assertEqual(species, arena["p1_type"], arena["id"])

    def test_every_p1_boss_spawn_is_catalogued(self):
        # GenObjectBoss Spider/Snake/Slime/King/BoxSnake; Kogane/Pom/KingBack
        # and geysers are not bosses.
        catalogued = set(arenas.all_arena_uids())
        missing = [uid for uid, stage, _, _, kind, species in GENERATOR_SLOTS
                   if kind == "boss" and species in (0, 1, 2, 3, 7) and uid not in catalogued]
        self.assertEqual(missing, [])

    def test_hope_cannon_beetle_stays_an_ordinary_slot(self):
        self.assertNotIn(2506165730, arenas.all_arena_uids())
        slot = next(s for s in _document()["slots"] if s["uid"] == 2506165730)
        self.assertFalse(slot["boss_slot"])

    def test_native_mirror_matches(self):
        text = _native_policy()
        if text is None:
            self.skipTest("native checkout not present (set PIKMIN_NATIVE_ROOT)")
        def pairs(table):
            body = text.split(table + "[] = {", 1)[1].split("};", 1)[0]
            return sorted((int(a), int(b)) for a, b in re.findall(r"\{(\d+)u,\s*(\d+)u\}", body))
        self.assertEqual(pairs("kSuppress"), sorted(arenas.suppress_pairs()))
        self.assertEqual(pairs("kAlias"), sorted(arenas.alias_pairs()))
        body = text.split("kArenaUids[] = {", 1)[1].split("};", 1)[0]
        native_uids = [int(v) for v in re.findall(r"(\d+)u", body)]
        self.assertEqual(sorted(native_uids), sorted(arenas.all_arena_uids()))


class DocumentTests(unittest.TestCase):
    def setUp(self):
        self.document = validate_document(_document())

    def test_boss_slots_are_exactly_the_arena_primaries(self):
        boss_slots = sorted(s["uid"] for s in self.document["slots"] if s["boss_slot"])
        primaries = sorted(a["primary_uid"] for a in self.document["arenas"])
        self.assertEqual(boss_slots, primaries)

    def test_protected_arenas_are_denied(self):
        report = audit(self.document)
        protected = {a["primary_uid"] for a in self.document["arenas"] if a["protected_drop"]}
        self.assertTrue(protected)
        for identity, uids in report["admitted"].items():
            self.assertFalse(protected & set(uids), identity)

    def test_non_boss_identities_never_accept_an_arena(self):
        report = audit(self.document)
        boss_slots = {s["uid"] for s in self.document["slots"] if s["boss_slot"]}
        for identity, uids in report["admitted"].items():
            if identity in arenas.BOSS_ENCOUNTERS:
                self.assertTrue(set(uids) <= boss_slots, identity)
            else:
                self.assertFalse(set(uids) & boss_slots, identity)

    def test_non_boss_acceptance_is_unchanged_by_the_arenas(self):
        report = audit(self.document)
        stripped = audit(_strip_arenas(_document()))
        ordinary = {k: v for k, v in report["admitted"].items() if k not in arenas.BOSS_ENCOUNTERS}
        before = {k: v for k, v in stripped["admitted"].items() if k not in arenas.BOSS_ENCOUNTERS}
        self.assertEqual(ordinary, before)
        # Without arena slots an arena boss is accepted nowhere.
        for identity in arenas.BOSS_ENCOUNTERS:
            self.assertNotIn(identity, stripped["admitted"])

    def test_crawbster_has_at_least_two_eligible_arenas(self):
        report = audit(self.document)
        self.assertGreaterEqual(len(report["admitted"].get("DangoMushi", [])), 2)

    def test_arena_bosses(self):
        # The pool's arena boss has a profile; the other lane bosses (30, 73,
        # 66) carry descriptors and get their profile with pool admission.
        roster = load_and_validate()
        self.assertEqual(arena_boss_ids(self.document, roster), {94})
        descriptors = {e["identity"] for e in self.document["encounters"]}
        self.assertEqual(descriptors, set(arenas.BOSS_ENCOUNTERS))

    def test_rebuild_is_idempotent(self):
        rebuilt = arenas.apply_to_document(_document(), arenas.ARENA_MEASUREMENTS)
        self.assertEqual(rebuilt, _document())


class SeedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.roster = load_and_validate()
        cls.document = _document()
        cls.spawn_by_arena = {a["id"]: {str(a["spawn_uids"][0])} for a in arenas.P1_BOSS_ARENAS}
        cls.all_arena = {str(u) for u in arenas.all_arena_uids()}

    def layout(self, seed, species=None, document=None):
        return resolve_placement_layout(seed, "Player1", document or self.document, self.roster,
                                        species=species)

    def test_crawbster_only_in_boss_arenas(self):
        used = set()
        for i in range(40):
            layout = self.layout(f"arena-{i}", species=sorted(PLAYABLE_P2_SPECIES))
            block = layout[BOSS_ARENA_KEY]
            for binding in layout["bindings"]:
                if binding["source_id"] == 94:
                    self.assertIn(binding["target"], self.all_arena)
                else:
                    self.assertNotIn(binding["target"], self.all_arena)
            self.assertEqual(len(block["placed"]), 1)
            row = block["placed"][0]
            self.assertEqual(row["source_id"], 94)
            self.assertEqual(set(row["targets"]), self.spawn_by_arena[row["arena"]])
            used.add(row["arena"])
            validate_layout(layout, self.roster)
        # Sampled per seed: both eligible arenas are used across seeds.
        self.assertGreaterEqual(len(used), 2)

    def test_ordinary_layout_equals_the_pool_without_bosses(self):
        pool = sorted(PLAYABLE_P2_SPECIES)
        without = [s for s in pool if s not in (30, 73, 94, 66)]
        for i in range(10):
            with_boss = self.layout(f"eq-{i}", species=pool)
            ordinary = dict(with_boss)
            ordinary.pop(BOSS_ARENA_KEY)
            ordinary["bindings"] = [b for b in with_boss["bindings"] if b["source_id"] != 94]
            self.assertEqual(ordinary, self.layout(f"eq-{i}", species=without))

    def test_boss_free_pool_is_byte_identical_without_the_arenas(self):
        without = [s for s in sorted(PLAYABLE_P2_SPECIES) if s != 94]
        stripped = _strip_arenas(self.document)
        for i in range(10):
            new = self.layout(f"id-{i}", species=without)
            self.assertNotIn(BOSS_ARENA_KEY, new)
            self.assertEqual(json.dumps(new, sort_keys=True),
                             json.dumps(self.layout(f"id-{i}", species=without, document=stripped),
                                        sort_keys=True))

    def test_boss_only_pool(self):
        layout = self.layout("solo-boss", species=[94])
        self.assertTrue(all(b["source_id"] == 94 for b in layout["bindings"]))
        self.assertEqual(len(layout[BOSS_ARENA_KEY]["placed"]), 1)

    def test_tampered_arena_block_is_rejected(self):
        layout = self.layout("tamper", species=sorted(PLAYABLE_P2_SPECIES))
        bad = copy.deepcopy(layout)
        bad[BOSS_ARENA_KEY]["placed"][0]["source_id"] = 2
        with self.assertRaises(SeedBridgeError):
            validate_layout(bad, self.roster)

    def test_playable_seed_generation(self):
        manifest = generate("arena-playable", "solo", "Player1", starting_area="forest",
                            p2_enemies=True, p2_species="playable")
        validate(manifest)
        placed = manifest["p2_layout"][BOSS_ARENA_KEY]["placed"]
        self.assertEqual([row["source_id"] for row in placed], [94])
        self.assertLessEqual(len(manifest["p2_layout"]["bindings"]), 64)


if __name__ == "__main__":
    unittest.main()
