"""Focused schema/citation/order tests for the reviewed source-79 transport evidence.

Issue #844. These tests pin the roster/evidence documents to the reviewed
immutable gen-5 enabled-session run of lane `rd-p2-sokkuri-receipt`:

* `docs/PIKMIN2_ENEMY_ROSTER_EVIDENCE.json` entry 79 `transport_reward` is
  `PASS` and its `delivery_receipt` cites the exact gen-5 exactly-once Onion
  receipt (`onion:p2:79:0` run1 `new=1` then run2 duplicate `new=0`).
* Cleanup/re-entry stays UNTESTED in the reviewed evidence; this lane credits
  transport only.
* Recording the roster evidence is not P2_PLAYABLE_POOL admission.

The tests are read-only: they never mutate the committed roster or evidence.
"""
import json
import re
from pathlib import Path

from experimental.pikmin2_enemy_roster import EVIDENCE_PATH, GATE_IDS
from randomizer.seed import P2_PLAYABLE_POOL, PLAYABLE_P2_SPECIES

ROOT = Path(__file__).resolve().parents[1]
RECEIPT_DOC = ROOT / "docs" / "PIKMIN2_SOKKURI79_RECEIPT.md"

GEN5_RUN1 = (
    "output/reduced/rd-p2-sokkuri-receipt/campaign-g5-01/runs/run1/"
    "ee61caf5c5344b428df4eac95592b112/capture/native.log"
)
GEN5_RUN2 = (
    "output/reduced/rd-p2-sokkuri-receipt/campaign-g5-01/runs/run2/"
    "9cc6e022732a41beaf6f7b7df6753234/capture/native.log"
)


def _evidence():
    return json.loads(EVIDENCE_PATH.read_text(encoding="utf-8"))


def _entry79():
    return _evidence()["entries"]["79"]


def _notes79():
    return "\n".join(_entry79()["notes"])


def test_evidence_schema_and_source79_fields():
    payload = _evidence()
    assert payload["schema"] == "p2-enemy-roster-1-evidence"
    assert isinstance(payload["entries"], dict) and payload["entries"]
    entry = payload["entries"]["79"]
    for field in ("native_module", "owner_lane", "eligibility", "source", "notes", "gates", "delivery_receipt"):
        assert field in entry, field
    assert entry["native_module"] == "pc_p2_sokkuri"
    assert set(entry["gates"]) == set(GATE_IDS)


def test_source79_transport_reward_pass_with_gen5_receipt_citation():
    entry = _entry79()
    assert entry["gates"]["transport_reward"] == "PASS"
    assert GEN5_RUN1 + ":1271" in entry["delivery_receipt"]


def test_source79_exactly_once_pair_cited_in_order():
    notes = _notes79()
    assert GEN5_RUN1 + ":1271" in notes
    assert GEN5_RUN2 + ":1265" in notes
    # exactly-once: the grant (new=1) is cited before the duplicate (new=0).
    assert notes.index("new=1") < notes.index("new=0")
    assert "566.31" in notes  # natural free-Pikmin haul, not injected


def test_source79_cleanup_reentry_stays_untested_in_reviewed_evidence():
    notes = _notes79()
    assert "cleanup_reentry remains UNTESTED" in notes
    assert "re-bind is not scene re-entry" in notes


def test_source79_gate_keys_preserve_canonical_order():
    raw = EVIDENCE_PATH.read_text(encoding="utf-8")
    block = raw[raw.index('"79": {'):raw.index('"82": {')]
    positions = [block.index('"%s":' % gate) for gate in GATE_IDS]
    assert positions == sorted(positions)


def test_other_species_and_gates_are_preserved():
    entries = _evidence()["entries"]
    assert entries["0"]["gates"]["identity_spawn"] == "UNTESTED"
    assert entries["9"]["eligibility"] == "admitted"
    assert entries["84"]["gates"]["cleanup_reentry"] == "UNTESTED"
    assert entries["79"]["gates"]["identity_spawn"] == "PASS"
    assert entries["79"]["gates"]["death_corpse"] == "PASS"


def test_roster_evidence_is_not_playable_pool_admission():
    assert 79 not in PLAYABLE_P2_SPECIES
    assert all(row["source_id"] != 79 for row in P2_PLAYABLE_POOL)
    assert "not P2_PLAYABLE_POOL admission" in _notes79()


def test_source79_receipt_doc_leaves_gate6_untested():
    doc = RECEIPT_DOC.read_text(encoding="utf-8")
    row6 = [line for line in doc.splitlines() if line.strip().startswith("| 6.")]
    assert row6, "gate 6 row missing from the reviewed receipt doc"
    assert re.search(r"\bUNTESTED\b", row6[0])
