"""Admit-frogs5 (#871): Wtank 25 + Armor 15 admission pins.

Rfix rigor: real native.log sha256 recomputed from disk, own-generator-token
line citations verified on disk, and pool/roster/placement/bridge sync. If
any cited log is missing locally the sha/line tests skip (like rfix); the
sync tests always run.
"""
import hashlib
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from experimental.pikmin2_enemy_roster import (
    admission_requirements,
    by_id,
    load_and_validate,
)
from randomizer.seed import (
    PLAYABLE_P2_SPECIES,
    P2_PLAYABLE_POOL,
    _default_admitted_placement,
)

WTANK_LOG = Path("C:/cop/botcamp-frogs5-25-Wtank/session/runs/6f7f48ec5786daf3784f517aaf00786f6a5423af2950f18996a010955372c3a3/native.log")
WTANK_SHA = "ba67a715fb46fb56652919464f2c5470b187e7d41254031912d8191349392ec0"
ARMOR_BLUE_LOG = Path("C:/cop/botcamp-frogs5b-15-Armor/session/runs/5994608956e0b4ce8d562b1f1d61bbcda85947a2d5996f6216fe0123483bc759/native.log")
ARMOR_BLUE_SHA = "889febb33ff5c33c0f73063f1ddbf8dd980866086f4fe04981f17ebe382dfa86"
ARMOR_RED_LOG = Path("C:/cop/botcamp-frogs5-15-Armor/session/runs/c8e08e81f2c461c3d420446ab02090a2de75647f4c5b81544dc1601c1acc9fb9/native.log")
ARMOR_RED_SHA = "51712e4b96f2d80858e49c7176cfb3638db7aa8fe520e1a9524f13bee680bab7"
ARMOR_PROD_LOG = Path("C:/cop/botcamp-admitprod-b15-15-Armor/session/runs/12176a0d9c26dd39cdb48d0bdeeb8b895151c17f51678e44cf787203e84f7991/native.log")
ARMOR_PROD_SHA = "24219d621ef8ea6c5c9240471535504c0a0096e26fc37acf06174ba9cf8bb0a9"
OWN_TOKEN = "1945764764"


def _sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_pool_contains_wtank_and_armor_with_evidence():
    by_source = {row["source_id"]: row for row in P2_PLAYABLE_POOL}
    for sid, enum in ((25, "Wtank"), (15, "Armor")):
        assert sid in by_source, sid
        assert by_source[sid]["enum_name"] == enum
        assert sid in tuple(PLAYABLE_P2_SPECIES), sid
        evidence = by_source[sid]["evidence"]
        assert evidence["run"] and evidence["log"] and evidence["installer"]
    assert len(P2_PLAYABLE_POOL) == 37  # + Gatling Groink 78 (#888), Breadbug 38 (#898)


def test_roster_admits_both_with_natural_gates_and_receipts():
    roster = load_and_validate()
    entries = by_id(roster)
    for sid in (25, 15):
        entry = entries[sid]
        assert entry.eligibility == "admitted", sid
        assert admission_requirements(entry) == [], sid
        assert (entry.delivery_receipt or "").strip(), sid


def test_placement_accepts_both():
    from randomizer.p2_placement import audit

    document = _default_admitted_placement()
    admitted = audit(document)["admitted"]
    assert admitted.get("Wtank"), "Wtank missing from placement admission"
    assert admitted.get("Armor"), "Armor missing from placement admission"


def test_bridge_playable_includes_both_and_catalog_maps():
    from experimental.pikmin2_seed_bridge import PLAYABLE_IDS
    from randomizer import p2_placement_catalog as catalog

    assert 25 in tuple(PLAYABLE_IDS) and 15 in tuple(PLAYABLE_IDS)
    document = _default_admitted_placement()
    for sid in (25, 15):
        assert catalog.binding_targets_for_sources([sid], document=document), sid


@pytest.mark.parametrize("log,sha", [
    (WTANK_LOG, WTANK_SHA),
    (ARMOR_BLUE_LOG, ARMOR_BLUE_SHA),
    (ARMOR_RED_LOG, ARMOR_RED_SHA),
    (ARMOR_PROD_LOG, ARMOR_PROD_SHA),
])
def test_cited_log_sha_matches_disk(log, sha):
    if not log.is_file():
        pytest.skip(f"missing local log {log}")
    assert _sha(log) == sha, log


def _line(log, number):
    if not log.is_file():
        pytest.skip(f"missing local log {log}")
    lines = log.read_text(encoding="utf-8", errors="replace").splitlines()
    assert 1 <= number <= len(lines), (log, number)
    return lines[number - 1]


def test_wtank_own_token_lines():
    assert f"generator={OWN_TOKEN} source_id=25" in _line(WTANK_LOG, 1060)  # BIND
    assert f"generator={OWN_TOKEN} source_id=25" in _line(WTANK_LOG, 1702)  # DEAD
    assert f"id=onion:p2:25:3 generator={OWN_TOKEN}" in _line(WTANK_LOG, 1930)  # RECEIPT
    assert f"target={OWN_TOKEN} damaged=1 killed=1 carried=1 received=1" in _line(WTANK_LOG, 1931)


def test_armor_own_token_lines():
    assert f"generator={OWN_TOKEN} source_id=15" in _line(ARMOR_BLUE_LOG, 996)  # BIND
    assert f"generator={OWN_TOKEN} source_id=15 health=200.0" in _line(ARMOR_BLUE_LOG, 1701)  # DAMAGE
    assert f"generator={OWN_TOKEN} source_id=15 health=100.0" in _line(ARMOR_BLUE_LOG, 1709)  # DAMAGE
    assert f"generator={OWN_TOKEN} source_id=15" in _line(ARMOR_BLUE_LOG, 1918)  # DEAD
    assert f"id=onion:p2:15:3 generator={OWN_TOKEN}" in _line(ARMOR_BLUE_LOG, 2401)  # RECEIPT
    assert f"target={OWN_TOKEN} damaged=1 killed=1 carried=1 received=1" in _line(ARMOR_BLUE_LOG, 2402)


def test_armor_gohome_and_product_loop_lines():
    assert f"generator={OWN_TOKEN} state=gohome" in _line(ARMOR_RED_LOG, 1700)
    assert f"generator={OWN_TOKEN} state=attack2" in _line(ARMOR_RED_LOG, 1702)
    assert f"generator={OWN_TOKEN} source_id=15" in _line(ARMOR_PROD_LOG, 1037)  # BIND
    assert f"generator={OWN_TOKEN} source_id=15" in _line(ARMOR_PROD_LOG, 1775)  # DEAD
    assert f"id=onion:p2:15:3 generator={OWN_TOKEN}" in _line(ARMOR_PROD_LOG, 2170)  # RECEIPT
