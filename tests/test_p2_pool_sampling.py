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


def trimmed_document(keep):
    """The committed document with only its first ``keep`` slots."""
    document = copy.deepcopy(committed_document())
    document["slots"] = document["slots"][:keep]
    kept = {slot["uid"] for slot in document["slots"]}
    for profile in document["profiles"]:
        if "accepted_slot_uids" in profile:
            profile["accepted_slot_uids"] = [uid for uid in profile["accepted_slot_uids"] if uid in kept]
    return document


def test_fitting_pool_keeps_the_legacy_fill():
    roster = load_and_validate()
    document = committed_document()
    fit = sorted(admitted_ids(roster))[:len(document["slots"])]
    layout = resolve_placement_layout("fit", "Player1", document, roster, species=fit)
    assert layout["density"] == DENSITY_LEGACY
    assert "unplaced" not in layout
    bound = [binding["source_id"] for binding in layout["bindings"]]
    assert set(bound) == set(fit), "every selected species appears when the selection fits"


def test_committed_pool_samples_one_species_out():
    # 37 admitted species on the 35 committed slots (Groink 78, #888;
    # Breadbug 38, #898): two species sit out of any one seed.
    roster = load_and_validate()
    pool = set(admitted_ids(roster))
    document = committed_document()
    assert len(pool) == len(document["slots"]) + 2
    layout = resolve_placement_layout("committed", "Player1", document, roster)
    bound = [binding["source_id"] for binding in layout["bindings"]]
    assert layout["density"] == DENSITY_SAMPLED
    assert len(bound) == len(set(bound)) == len(document["slots"])
    assert len(layout["unplaced"]) == 2 and set(layout["unplaced"]) == pool - set(bound)


def test_oversubscribed_pool_samples_distinct_species():
    roster = load_and_validate()
    pool = set(admitted_ids(roster))
    document = trimmed_document(20)
    layout = resolve_placement_layout("over", "Player1", document, roster)
    assert layout["density"] == DENSITY_SAMPLED
    bound = [binding["source_id"] for binding in layout["bindings"]]
    assert len(bound) == 20, "every target is still bound"
    assert len(set(bound)) == 20, "no species repeats while others are unplaced"
    assert set(layout["unplaced"]) == pool - set(bound)
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
