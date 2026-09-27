"""Pin the capability of the 2 slots shared by the admitted and proxy docs (#871).

Placement-cap promoted the proxy tier's 2 Hope singletons into
docs/PIKMIN2_ADMITTED_PLACEMENT.json with terrain/route evidence true, while
the proxy sibling still said false / proxy_only: true. The native
P2_PLACEMENT_SLOT probe samples terrain and the nearest waypoint at the slot
XYZ (not per species or tier), and two probes agree on terrain=ground route=1
(pk1 proxy run and the six-gate rev8 run). These tests keep both documents,
and the validator, in agreement so the pair cannot drift apart again.
No game, no ISO, no native build.
"""

import copy
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from randomizer import p2_placement as placement

SHARED = {1849273021: "hope_0-29_4189", 2049888785: "hope_0-29_3592"}
PROBED = {"xyz": True, "terrain": True, "route": True}
MECHANICAL = {"xyz": True, "terrain": False, "route": False}
# Physical slot facts that must be identical in both documents.
SLOT_FACTS = ("label", "stage", "terrain", "radius", "water_depth", "flight_space",
              "burrow_ground", "home", "helper_capacity", "projectile_corridor",
              "corpse_route", "protected", "boss_slot", "first_day", "respawn_days",
              "source_identity", "cohort", "evidence")


def _load(name):
    return json.loads((ROOT / "docs" / name).read_text(encoding="utf-8"))


def _slots(document):
    return {slot["uid"]: slot for slot in document["slots"]}


def test_shared_uid_set_is_exactly_the_overlap():
    admitted = set(_slots(_load("PIKMIN2_ADMITTED_PLACEMENT.json")))
    proxy = set(_slots(_load("PIKMIN2_PROXY_PLACEMENT.json")))
    assert admitted & proxy == set(SHARED)
    assert set(placement.PROXY_SHARED_UIDS) == set(SHARED)
    assert placement.PROXY_SHARED_UIDS <= placement.PROXY_SINGLETON_UIDS


def test_shared_slots_agree_across_documents():
    admitted = _slots(placement.validate_document(_load("PIKMIN2_ADMITTED_PLACEMENT.json")))
    proxy = _slots(placement.validate_proxy_document(_load("PIKMIN2_PROXY_PLACEMENT.json")))
    for uid, label in SHARED.items():
        a, p = admitted[uid], proxy[uid]
        assert a["label"] == p["label"] == label
        assert a["terrain"] == "ground"
        assert a["evidence"] == PROBED
        for key in SLOT_FACTS:
            assert a[key] == p[key], (uid, key)
        assert p["proxy_only"] is False
        assert p["pack"] is False
        assert p["evidence_level"] == placement.PROXY_SHARED_EVIDENCE_LEVEL


def test_proxy_exclusive_packs_stay_mechanical_only():
    proxy = placement.validate_proxy_document(_load("PIKMIN2_PROXY_PLACEMENT.json"))
    packs = [slot for slot in proxy["slots"] if slot["uid"] not in SHARED]
    assert len(packs) == 14
    for slot in packs:
        assert slot["pack"] is True
        assert slot["proxy_only"] is True
        assert slot["evidence"] == MECHANICAL


def _shared_raw(document, uid):
    return next(slot for slot in document["slots"] if slot["uid"] == uid)


@pytest.mark.parametrize("uid", sorted(SHARED))
@pytest.mark.parametrize("mutation", [
    ("evidence", "terrain", False),
    ("evidence", "route", False),
    ("proxy_only", None, True),
    ("evidence_level", None, placement.PROXY_EVIDENCE_LEVEL),
])
def test_validator_rejects_drift_on_shared_slots(uid, mutation):
    document = copy.deepcopy(_load("PIKMIN2_PROXY_PLACEMENT.json"))
    slot = _shared_raw(document, uid)
    key, sub, value = mutation
    if sub is None:
        slot[key] = value
    else:
        slot[key][sub] = value
    with pytest.raises(ValueError):
        placement.validate_proxy_document(document)


def test_validator_rejects_probed_evidence_on_packs():
    # Promoting a pack without native evidence must still fail closed.
    document = copy.deepcopy(_load("PIKMIN2_PROXY_PLACEMENT.json"))
    pack = next(slot for slot in document["slots"] if slot["pack"] is True)
    pack["evidence"] = dict(PROBED)
    pack["proxy_only"] = False
    with pytest.raises(ValueError):
        placement.validate_proxy_document(document)
