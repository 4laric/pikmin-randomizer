"""Per-seed P2 pool sampling when the pool outgrows its placement slots (#893).

Owner decision (2026-09-28): when the P2 pool holds more species than there
are eligible placement targets, each seed samples the pool. Every target gets
a distinct species and the rest are recorded as ``unplaced`` (sampled-v1). A
pool that fits keeps the legacy fill byte-for-byte, and an explicitly requested
density still fails closed.

The committed accepted-placement document is trimmed to fewer slots so the
real admitted pool (35 species) becomes oversubscribed without changing the
roster.
"""
import copy
import json
from pathlib import Path

import pytest

from experimental.pikmin2_enemy_roster import load_and_validate
from experimental.pikmin2_seed_bridge import (
    DENSITY_BOUNDED,
    DENSITY_LEGACY,
    DENSITY_SAMPLED,
    SeedBridgeError,
    admitted_ids,
    resolve_placement_layout,
    validate_layout,
)

ROOT = Path(__file__).resolve().parents[1]
ADMITTED_PLACEMENT_DOC = ROOT / "docs/PIKMIN2_ADMITTED_PLACEMENT.json"


def committed_document():
    return json.loads(ADMITTED_PLACEMENT_DOC.read_text(encoding="utf-8"))


def ordinary_slots(document):
    """Placement slots outside the boss arenas (#899) and the #901 holder slots."""
    held = {row["uid"] for row in document.get("held_parts", [])}
    return [slot for slot in document["slots"] if not slot.get("boss_slot") and slot["uid"] not in held]


def ordinary_bound(layout):
    """Bound source ids outside the boss arenas (#899) and holder slots (#901)."""
    arena = {target for row in layout.get("boss_arenas", {}).get("placed", []) for target in row["targets"]}
    arena |= {row["target"] for row in layout.get("held_parts", {}).get("placed", [])}
    return [binding["source_id"] for binding in layout["bindings"] if binding["target"] not in arena]


def arena_bosses(layout):
    return {row["source_id"] for row in layout.get("boss_arenas", {}).get("placed", [])}


def trimmed_document(keep):
    """The committed document with only its first ``keep`` ordinary slots
    (the boss arenas, #899, are kept)."""
    document = copy.deepcopy(committed_document())
    document["slots"] = ordinary_slots(document)[:keep] + [
        slot for slot in document["slots"] if slot.get("boss_slot")]
    kept = {slot["uid"] for slot in document["slots"]}
    for profile in document["profiles"]:
        if "accepted_slot_uids" in profile:
            profile["accepted_slot_uids"] = [uid for uid in profile["accepted_slot_uids"] if uid in kept]
    return document


def test_fitting_pool_keeps_the_legacy_fill():
    roster = load_and_validate()
    document = committed_document()
    # #244: Dirigibug 58 accepts a single ordinary slot (1787125272) that many
    # species share, so a seed-shuffled legacy fill can leave it without a
    # unique target; keep the fitting selection to species with room.
    fit = [source_id for source_id in sorted(admitted_ids(roster)) if source_id != 58][:len(ordinary_slots(document))]
    layout = resolve_placement_layout("fit", "Player1", document, roster, species=fit)
    assert layout["density"] == DENSITY_LEGACY
    assert "unplaced" not in layout
    bound = [binding["source_id"] for binding in layout["bindings"]]
    assert set(bound) == set(fit), "every selected species appears when the selection fits"


def test_committed_pool_fits_the_constraint_derived_targets():
    # 42 admitted species (Kurage 57 #960, Groink 78 #888, Demon 32 #215, Titan Dweevil 73
    # #246, Breadbug 38 #898, Antenna Beetle 41 #245, Dirigibug 58 #244). The
    # Crawbster 94 and the Titan 73 live in boss arenas for real seeds
    # (#899). Since #948 the ordinary target set is every campaign generator
    # (72 slots), so the 39 ordinary species all fit: nothing is sampled out,
    # the legacy fill binds every target and no species is dropped for lack
    # of a slot. (Sampling, #893, still applies to a trimmed document below.)
    roster = load_and_validate()
    pool = set(admitted_ids(roster))
    document = committed_document()
    assert len(pool) == 42
    assert len(ordinary_slots(document)) == 72
    layout = resolve_placement_layout("committed", "Player1", document, roster)
    bound = ordinary_bound(layout)
    assert layout["density"] == DENSITY_LEGACY
    assert arena_bosses(layout) == {73, 94}
    assert "unplaced" not in layout
    assert set(bound) == pool - arena_bosses(layout)
    assert len(bound) == len(ordinary_slots(document))


def test_oversubscribed_pool_samples_distinct_species():
    roster = load_and_validate()
    pool = set(admitted_ids(roster))
    document = trimmed_document(20)
    layout = resolve_placement_layout("over", "Player1", document, roster)
    assert layout["density"] == DENSITY_SAMPLED
    bound = ordinary_bound(layout)
    assert len(bound) == 20, "every target is still bound"
    assert len(set(bound)) == 20, "no species repeats while others are unplaced"
    assert set(layout["unplaced"]) == pool - set(bound) - arena_bosses(layout)
    assert layout["unplaced"] == sorted(layout["unplaced"])
    validate_layout(layout, roster, admitted=sorted(pool))


def test_sampling_is_deterministic_and_varies_by_seed():
    roster = load_and_validate()
    document = trimmed_document(20)
    first = resolve_placement_layout("same", "Player1", document, roster)
    again = resolve_placement_layout("same", "Player1", document, roster)
    assert first == again
    subsets = {tuple(sorted(binding["source_id"] for binding in
                            resolve_placement_layout(f"seed-{i}", "Player1", document, roster)["bindings"]))
               for i in range(8)}
    assert len(subsets) > 1, "different seeds sample different subsets"


@pytest.mark.parametrize("density", [DENSITY_LEGACY, DENSITY_BOUNDED])
def test_explicit_density_still_fails_closed_when_oversubscribed(density):
    with pytest.raises(SeedBridgeError, match="no unique accepted placement target"):
        resolve_placement_layout("over", "Player1", trimmed_document(20), load_and_validate(), density=density)


def test_species_subset_that_fits_is_unchanged():
    roster = load_and_validate()
    subset = sorted(admitted_ids(roster))[:10]
    layout = resolve_placement_layout("subset", "Player1", trimmed_document(20), roster, species=subset)
    assert layout["density"] == DENSITY_LEGACY
    assert {binding["source_id"] for binding in layout["bindings"]} == set(subset)


def test_generated_seed_round_trips_with_an_unplaced_list(monkeypatch):
    import randomizer.seed as seed_module

    monkeypatch.setattr(seed_module, "_default_admitted_placement", lambda: trimmed_document(20))
    manifest = seed_module.generate("round-trip", "solo", "Player1", p2_enemies=True, p2_species="playable")
    layout = manifest["p2_layout"]
    assert layout["density"] == DENSITY_SAMPLED and layout["unplaced"]
    seed_module.validate(manifest)
