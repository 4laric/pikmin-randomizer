"""The committed placement document is derived from constraints (#948).

CONTRIBUTING "Placement: don't hard-code where a species may go" and "Don't
invent restrictions": accepted placements come from the species' real needs,
never from the slot an evidence run happened to use. These tests pin that:

* the committed document is byte-identical to the generator's output;
* every ordinary campaign generator is a slot (the 37 grub/aquatic/frog/
  flying/dwarf generators included), and probe evidence gates nothing;
* every playable species has more than one legal ordinary slot unless a
  cited constraint forbids it (none does today);
* arena bosses are accepted wherever their footprint fits (every measured,
  transferable arena) and on an ordinary slot when its measured radius
  covers the footprint;
* the owner's #901 rulings: Puffstool and the ship-part arenas are open,
  the Emperor arena stays protected.
"""
import json
from pathlib import Path

import pytest

from randomizer import p2_admitted_placement as generator
from randomizer import p2_placement
from randomizer.campaign_data import CAMPAIGN_SLOTS
from randomizer.p2_boss_arenas import BOSS_ENCOUNTERS, P1_BOSS_ARENAS, arena_protected
from randomizer.seed import PLAYABLE_P2_SPECIES

DOC = Path(__file__).resolve().parents[1] / "docs" / "PIKMIN2_ADMITTED_PLACEMENT.json"


@pytest.fixture(scope="module")
def committed():
    return json.loads(DOC.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def generated():
    return generator.build_admitted_document()


def _profiles(document):
    return {p["identity"]: p for p in document["profiles"]}


def _ordinary(document):
    held = {row["uid"] for row in document.get("held_parts", [])}
    return [s for s in document["slots"] if not s.get("boss_slot") and s["uid"] not in held]


def test_committed_document_matches_the_generator(committed, generated):
    assert committed == generated, "run: py -3.12 -m randomizer.p2_admitted_placement"


def test_every_campaign_generator_is_a_slot(committed):
    uids = {s["uid"] for s in committed["slots"]}
    assert {row["uid"] for row in CAMPAIGN_SLOTS} <= uids
    ordinary = _ordinary(committed)
    assert len(ordinary) == len(CAMPAIGN_SLOTS) == 72
    terrains = {s["terrain"] for s in ordinary}
    assert terrains == {"ground", "water", "mixed", "air"}


def test_probe_evidence_is_recorded_not_a_gate(committed):
    unprobed = [s for s in _ordinary(committed) if not all(s["evidence"].values())]
    assert unprobed, "the unprobed campaign generators must be present"
    accepted_somewhere = set()
    for profile in committed["profiles"]:
        accepted_somewhere.update(profile.get("accepted_slot_uids") or [])
    assert {s["uid"] for s in unprobed} <= accepted_somewhere


def test_every_playable_species_has_more_than_one_ordinary_slot(committed):
    from experimental.pikmin2_enemy_roster import load_roster
    by_source = {entry.source_id: entry.enum_name for entry in load_roster()}
    profiles = _profiles(committed)
    ordinary = {s["uid"] for s in _ordinary(committed)}
    arenas = {s["uid"] for s in committed["slots"] if s.get("boss_slot")}
    for source_id in PLAYABLE_P2_SPECIES:
        profile = profiles[by_source[source_id]]
        accepted = set(profile["accepted_slot_uids"])
        if profile["is_boss"]:
            # Real seeds: measured arenas whose clearance fits the footprint.
            assert len(accepted & arenas) > 1, (source_id, profile["identity"])
        else:
            assert len(accepted & ordinary) > 1, (source_id, profile["identity"])
            # Not a single-slot profile (the Dirigibug 58 case, #951 U4).
            assert len(accepted & ordinary) >= 49, (source_id, profile["identity"])


def test_accepted_slots_are_exactly_the_constraint_compatible_ones(committed):
    encounters = {e["id"]: e for e in committed.get("encounters", [])}
    slots = [p2_placement.normalize_slot(s) for s in committed["slots"]]
    for profile in committed["profiles"]:
        if not profile.get("accepted_gates"):
            continue
        normalized = p2_placement.normalize_profile({k: v for k, v in profile.items()
                                                     if k != "accepted_slot_uids"})
        expected = [s["uid"] for s in slots
                    if p2_placement.evaluate(s, normalized, encounters)["status"] == "legal"]
        assert profile["accepted_slot_uids"] == expected, profile["identity"]


def test_boss_placement_follows_footprint_not_a_cast_list(committed):
    profiles = _profiles(committed)
    arenas = {a["primary_uid"]: a for a in committed["arenas"]}
    for identity in ("DangoMushi", "BigTreasure"):
        footprint = BOSS_ENCOUNTERS[identity]["footprint_radius"]
        accepted = set(profiles[identity]["accepted_slot_uids"])
        for slot in committed["slots"]:
            fits = slot["radius"] >= footprint and not slot["protected"] and slot["corpse_route"]
            if slot["uid"] in arenas:
                assert (slot["uid"] in accepted) == fits, (identity, slot["label"])
            else:
                # Ordinary slots carry the unmeasured default radius (100) so
                # none fits today; the rule is data, not a cast list.
                assert (slot["uid"] in accepted) == fits, (identity, slot["label"])


def test_boss_on_a_measured_ordinary_slot_is_legal():
    """A boss profile is accepted on any slot whose radius covers its footprint."""
    document = generator.build_admitted_document()
    document = json.loads(json.dumps(document))
    ordinary = next(s for s in _ordinary(document) if s["terrain"] == "ground")
    ordinary["radius"] = 200.0  # a measured clearance
    document = generator.finalize_accepted_slots(document)
    dango = _profiles(document)["DangoMushi"]
    assert ordinary["uid"] in dango["accepted_slot_uids"]
    titan = _profiles(document)["BigTreasure"]
    assert ordinary["uid"] not in titan["accepted_slot_uids"]  # 250 > 200


def test_owner_arena_rulings(committed):
    by_id = {a["id"]: a for a in P1_BOSS_ARENAS}
    assert arena_protected(by_id["last_emperor"])
    for name in ("navel_puffstool", "hope_snagret_part", "navel_beady_long_legs",
                 "spring_cannon_beetle"):
        assert not arena_protected(by_id[name]), name
    protected = {s["uid"] for s in committed["slots"] if s.get("boss_slot") and s["protected"]}
    assert protected == {by_id["last_emperor"]["spawn_uids"][0]}


def test_generator_summary_reports_the_target_set(generated):
    summary = generator.summary(generated)
    assert summary["ordinary_slots"] == 73  # 72 campaign generators + the uf02 holder
    assert summary["slots"] == 81
