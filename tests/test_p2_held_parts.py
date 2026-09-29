"""P1 ship-part holder slots a P2 occupant may take over (#901).

Pins the holder table against the spawn inventory and campaign sources, the
placement document's ``held_parts`` block, and the seed contract: a
transferable holder slot is bound from its own RNG stream after the ordinary
layout, so the ordinary layout is unchanged, and a protected holder is never
bound.
"""
import copy
import json
import unittest
from collections import Counter
from pathlib import Path

from experimental.pikmin2_enemy_roster import load_and_validate
from experimental.pikmin2_seed_bridge import (HELD_PART_KEY, SeedBridgeError, resolve_placement_layout,
                                              validate_layout)
from randomizer import p2_held_parts as held
from randomizer.campaign_data import CAMPAIGN_SOURCES
from randomizer.p2_placement import audit, validate_document
from randomizer.seed import PLAYABLE_P2_SPECIES, generate, validate
from randomizer.spawn_data import GENERATOR_SLOTS

ROOT = Path(__file__).resolve().parents[1]
DOCUMENT = ROOT / "docs" / "PIKMIN2_ADMITTED_PLACEMENT.json"


def _document():
    return json.loads(DOCUMENT.read_text(encoding="utf-8"))


def _without_holders(document):
    """The same document with the holder slots, block and acceptances removed."""
    stripped = copy.deepcopy(document)
    uids = {row["uid"] for row in held.P1_HELD_PART_SLOTS}
    stripped["slots"] = [slot for slot in stripped["slots"] if slot["uid"] not in uids]
    for profile in stripped["profiles"]:
        if "accepted_slot_uids" in profile:
            profile["accepted_slot_uids"] = [uid for uid in profile["accepted_slot_uids"] if uid not in uids]
    stripped.pop(HELD_PART_KEY, None)
    return stripped


def _with_flags(**flags):
    original = held.P1_HELD_PART_SLOTS
    rows = copy.deepcopy(original)
    for row in rows:
        if row["label"] in flags:
            row["held_part_transfer"] = flags[row["label"]]
    held.P1_HELD_PART_SLOTS = tuple(rows)
    try:
        return validate_document(held.apply_to_document(_without_holders(_document())))
    finally:
        held.P1_HELD_PART_SLOTS = original


class CatalogueTests(unittest.TestCase):
    def test_every_holder_is_a_protected_p1_teki_slot(self):
        rows = {uid: (stage, kind, species) for uid, stage, _, _, kind, species in GENERATOR_SLOTS}
        sources = {row["uid"]: row for row in CAMPAIGN_SOURCES}
        for row in held.P1_HELD_PART_SLOTS:
            self.assertEqual(rows[row["uid"]], (row["stage"], "teki", row["p1_teki"]), row["label"])
            self.assertTrue(sources[row["uid"]]["protected"], row["label"])
            self.assertEqual(sources[row["uid"]]["original"], row["p1_teki"], row["label"])

    def test_a_transfer_never_removes_the_last_host_of_a_species(self):
        # A holder slot bound to a P2 occupant no longer spawns its P1 teki.
        # The bestiary checks for that species must keep another host.
        hosts = Counter(row["original"] for row in CAMPAIGN_SOURCES)
        for row in held.P1_HELD_PART_SLOTS:
            if row["held_part_transfer"]:
                self.assertGreater(hosts[row["p1_teki"]], 1, row["label"])

    def test_breadbug_holder_stays_protected(self):
        # The Navel Breadbug is the only Breadbug spawn (bestiary host).
        row = held.held_part_slots_by_uid()[3406893972]
        self.assertFalse(row["held_part_transfer"])


class DocumentTests(unittest.TestCase):
    def setUp(self):
        self.document = validate_document(_document())

    def test_block_matches_the_table(self):
        block = {row["uid"]: row for row in self.document[HELD_PART_KEY]}
        for row in held.P1_HELD_PART_SLOTS:
            self.assertEqual(block[row["uid"]]["held_part_transfer"], row["held_part_transfer"])
            slot = next(s for s in self.document["slots"] if s["uid"] == row["uid"])
            self.assertEqual(slot["protected"], not row["held_part_transfer"])
            self.assertFalse(slot["boss_slot"])

    def test_admission_follows_the_flag(self):
        admitted = audit(self.document)["admitted"]
        for row in held.P1_HELD_PART_SLOTS:
            hosts = [identity for identity, uids in admitted.items() if row["uid"] in uids]
            if row["held_part_transfer"]:
                self.assertTrue(hosts, row["label"])
            else:
                self.assertEqual(hosts, [], row["label"])

    def test_rebuild_is_idempotent(self):
        self.assertEqual(held.apply_to_document(_document()), _document())

    def test_validation_rejects_a_flag_the_slot_disagrees_with(self):
        bad = _document()
        row = next(r for r in bad[HELD_PART_KEY] if r["uid"] == 613834665)
        row["held_part_transfer"] = not row["held_part_transfer"]
        with self.assertRaises(Exception):
            validate_document(bad)


class SeedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.roster = load_and_validate()

    def test_playable_seed_binds_the_transferable_holder(self):
        manifest = generate("held-part", p2_enemies=True, p2_species="playable")
        validate(manifest)
        layout = manifest["p2_layout"]
        placed = layout[HELD_PART_KEY]["placed"]
        self.assertEqual([row["target"] for row in placed], ["613834665"])
        self.assertEqual(placed[0]["part"], "uf02")
        by_target = {b["target"]: b["source_id"] for b in layout["bindings"]}
        self.assertEqual(by_target["613834665"], placed[0]["source_id"])
        self.assertIn(placed[0]["source_id"], PLAYABLE_P2_SPECIES)
        self.assertNotIn("3406893972", by_target)  # Breadbug stays protected

    def test_ordinary_layout_is_unchanged(self):
        document = _document()
        for seed in ("held-a", "held-b", "held-c"):
            with_holders = resolve_placement_layout(seed, "Player1", document, self.roster)
            without = resolve_placement_layout(seed, "Player1", _without_holders(document), self.roster)
            placed = {row["target"] for row in with_holders.get(HELD_PART_KEY, {}).get("placed", [])}
            ordinary = [b for b in with_holders["bindings"] if b["target"] not in placed]
            self.assertEqual(ordinary, without["bindings"], seed)
            self.assertEqual({k: v for k, v in with_holders.items() if k not in ("bindings", HELD_PART_KEY)},
                             {k: v for k, v in without.items() if k != "bindings"}, seed)

    def test_holder_prefers_an_unplaced_species(self):
        document = _document()
        by_enum = {entry.enum_name: entry.source_id for entry in self.roster}
        admitted = audit(document)["admitted"]
        hosts = {by_enum[identity] for identity, uids in admitted.items() if 613834665 in uids}
        for seed in ("held-a", "held-b", "held-c", "held-d"):
            layout = resolve_placement_layout(seed, "Player1", document, self.roster)
            row = layout[HELD_PART_KEY]["placed"][0]
            if set(layout.get("unplaced", [])) & hosts:
                self.assertIn(row["source_id"], layout["unplaced"], seed)

    def test_protected_holder_is_never_bound(self):
        document = _with_flags(spring_puffy_blowhog_uf02=False)
        layout = resolve_placement_layout("held-a", "Player1", document, self.roster)
        self.assertNotIn(HELD_PART_KEY, layout)
        self.assertNotIn("613834665", {b["target"] for b in layout["bindings"]})

    def test_bounded_density_leaves_holders_vanilla(self):
        layout = resolve_placement_layout("held-a", "Player1", _document(), self.roster,
                                          species=[23], density="bounded-coverage-v1")
        self.assertNotIn(HELD_PART_KEY, layout)

    def test_validate_layout_rejects_a_mismatched_block(self):
        layout = resolve_placement_layout("held-a", "Player1", _document(), self.roster)
        bad = copy.deepcopy(layout)
        bad[HELD_PART_KEY]["placed"][0]["source_id"] = -1
        with self.assertRaises(SeedBridgeError):
            validate_layout(bad, self.roster)
        validate_layout(layout, self.roster)


if __name__ == "__main__":
    unittest.main()
