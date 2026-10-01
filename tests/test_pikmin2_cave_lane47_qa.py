"""Focused tests for the lane-47 P2 cave QA report assembler.

These tests never touch the native engine, a real cave run or the GL fixtures.
They pin the marker grammar, the natural/proxy/injected labelling rules and the
fail-closed pass semantics using synthetic marker text only.
"""
import json

import pytest

from experimental import pikmin2_cave_lane47_qa as qa

GEN_OK = (
    "P2_CAVE_GEN source=engine cave=forest_1 floor=1 seed=42 segments=2 chokes=1 "
    "leaves=1 buds=1 gates=1 entrance=n0 hole=n3 salt=7 attempts=1"
)
GEN_FAILED = "P2_CAVE_GEN source=engine FAILED reason=no-solution"
ROOMS_READY = (
    "P2_CAVE_ROOMS_READY units=4 geometry=real cave=forest_1 floor=1 seed=42 "
    "salt=7 hard=2 entrance=n0 hole=n3"
)
TIMELINE_FRESH = (
    "P2_CAVE_ROOMS_TIMELINE tag=fresh_floor_no_abilities hole=0 treasure_elec=0 "
    "treasure_water=0 untagged=1"
)
TIMELINE_ELEC = (
    "P2_CAVE_ROOMS_TIMELINE tag=come_back_with_yellow hole=0 treasure_elec=1 "
    "treasure_water=0 untagged=0"
)
TIMELINE_BLUE = (
    "P2_CAVE_ROOMS_TIMELINE tag=return_with_yellow_and_blue hole=1 treasure_elec=1 "
    "treasure_water=1 untagged=0"
)
GEOMETRY_OK = (
    "P2_CAVE_GEOMETRY_READY nodes=5 real=5 proxy=0 gate_actors=1 geometry=real "
    "cave=forest_1 floor=1 seed=42 salt=7"
)
GEOMETRY_PROXY = (
    "P2_CAVE_GEOMETRY_READY nodes=3 real=0 proxy=3 gate_actors=0 geometry=proxy "
    "cave=forest_1 floor=1 seed=42 salt=7"
)
GEOMETRY_NODE = (
    "P2_CAVE_GEOMETRY_NODE id=n1 kind=segment hazard=none class=proxy "
    "model=placeholder proxy=1"
)
ITEMS_READY = (
    "P2_CAVE_ITEMS_READY items=3 tagged=2 untagged=1 geometry=real cave=forest_1 "
    "floor=1 seed=42"
)
ITEM_ACTOR = (
    "P2_CAVE_ITEM_ACTOR slot=0 item=treasure_a host=leaf_elec_0 kind=leaf tagged=1 "
    "x=1.5 y=2.0 z=3.0"
)
RECEIPT_NEW = (
    "P2_CAVE_ITEM_RECEIPT id=1 item=treasure_a host=leaf_elec_0 tagged=1 new=1 "
    "tag=fresh seed=42 result=0"
)
RECEIPT_DUP = (
    "P2_CAVE_ITEM_RECEIPT id=1 item=treasure_a host=leaf_elec_0 tagged=1 new=0 "
    "tag=fresh seed=42 result=0"
)
NATURAL_CARRY = "P2_CAVE_ITEM_NATURAL_CARRY transport=2"

LEDGER = (
    "P2_RECEIPTS_1\n"
    "42 treasure_a leaf_elec_0 encounter_1\n"
    "7 treasure_b leaf_water_0 encounter_2\n"
)

CLEAN_MARKERS = "\n".join([
    "boot",
    GEN_OK,
    ROOMS_READY,
    TIMELINE_FRESH,
    TIMELINE_ELEC,
    TIMELINE_BLUE,
    GEOMETRY_OK,
    ITEMS_READY,
    ITEM_ACTOR,
    RECEIPT_NEW,
    NATURAL_CARRY,
    "shutdown",
])

CLEAN_CHECKER = {
    "generation_pass": True,
    "evidence": "natural",
    "seed_determinism": {"pass": True},
    "reroll_invariance": {"pass": True},
    "reachability": {"pass": True},
    "failure_handling": {"pass": True},
}


def clean_report():
    return qa.check_chain(marker_logs=[CLEAN_MARKERS], checker_report=CLEAN_CHECKER,
                          receipt_ledger=LEDGER)


def test_parse_markers_reads_each_kind():
    text = "\n".join([
        GEN_OK,
        ROOMS_READY,
        TIMELINE_BLUE,
        GEOMETRY_OK,
        GEOMETRY_NODE,
        "P2_CAVE_GEOMETRY_GATE id=g1 hazard=elec actor=denki model=m placed=1",
        "P2_CAVE_GEOMETRY_GATE_DENKI id=g1 actor=denki target=1 accepted=1 target_state=2",
        "P2_CAVE_GEOMETRY_DRAW nodes=5 models=3 gates=1 geometry=real",
        ITEMS_READY,
        ITEM_ACTOR,
        RECEIPT_NEW,
        "P2_CAVE_ITEM_REDELIVER duplicate_call=0 events=1 new=1",
        NATURAL_CARRY,
        "not a marker",
    ])
    parsed = qa.parse_markers(text)

    assert parsed["gen"][0]["source"] == "engine"
    assert parsed["gen"][0]["seed"] == 42
    assert parsed["gen"][0]["failed"] is False
    assert parsed["rooms_ready"][0]["units"] == 4
    assert parsed["rooms_timeline"][0]["hole"] == 1
    assert parsed["geometry_ready"][0]["geometry"] == "real"
    assert parsed["geometry_node"][0]["proxy"] == 1
    assert parsed["geometry_gate"][0]["placed"] == 1
    assert parsed["geometry_denki"][0]["accepted"] == 1
    assert parsed["geometry_draw"][0]["models"] == 3
    assert parsed["items_ready"][0]["tagged"] == 2
    assert parsed["item_actor"][0]["x"] == 1.5
    assert parsed["item_receipt"][0]["new"] == 1
    assert parsed["item_redeliver"][0]["duplicate_call"] == 0
    assert parsed["natural_carry"][0]["transport"] == 2
    assert parsed["malformed"] == []


def test_parse_markers_marks_failed_gen():
    parsed = qa.parse_markers(GEN_FAILED)
    assert parsed["gen"][0]["failed"] is True
    assert parsed["gen"][0]["source"] == "engine"
    assert parsed["gen"][0]["reason"] == "no-solution"


def test_parse_markers_tolerates_malformed_lines():
    text = "\n".join([
        GEN_OK,
        "P2_CAVE_GEN source=engine broken tokens",
        "P2_CAVE_GEOMETRY_NODE nope",
        "unrelated noise",
    ])
    parsed = qa.parse_markers(text)
    assert len(parsed["gen"]) == 1
    assert len(parsed["malformed"]) == 2
    assert all("line" in row and "reason" in row for row in parsed["malformed"])


def test_full_synthetic_clean_chain_passes():
    report = clean_report()
    assert report["schema"] == qa.SCHEMA
    assert report["pass"] is True
    assert report["failures"] == []
    assert set(report["classification"]) == set(qa.CONTRACT_ITEMS)
    assert all(value == qa.NATURAL for value in report["classification"].values())
    assert report["generation"]["pass"] is True
    assert report["live_generation"]["natural"] is True
    assert report["collection"]["pass"] is True
    assert report["timeline"]["rows"] == 3
    assert report["geometry"]["natural_real_models"] is True


def test_missing_gen_marker_fails_generation():
    report = qa.check_chain(marker_logs=["no markers here\n"], checker_report=CLEAN_CHECKER)
    assert report["generation"]["pass"] is False
    assert report["classification"]["generation_invariant"] == qa.INJECTED
    assert report["live_generation"]["present"] is False
    assert report["pass"] is False
    assert any("P2_CAVE_GEN" in failure for failure in report["failures"])


def test_failed_gen_surfaced_and_superseded_by_later_success():
    only_failed = qa.check_chain(marker_logs=[GEN_FAILED], checker_report=CLEAN_CHECKER)
    assert only_failed["generation"]["gen_markers"][0]["failed"] is True
    assert only_failed["live_generation"]["present"] is True
    assert only_failed["generation"]["pass"] is False

    with_success = qa.check_chain(marker_logs=[GEN_FAILED + "\n" + GEN_OK],
                                  checker_report=CLEAN_CHECKER)
    assert with_success["generation"]["pass"] is True


def test_injected_checker_evidence_never_natural():
    checker = dict(CLEAN_CHECKER, evidence="injected")
    report = qa.check_chain(marker_logs=[GEN_OK], checker_report=checker)
    assert report["generation"]["checker_evidence"] == "injected"
    assert report["generation"]["pass"] is False
    assert report["classification"]["generation_invariant"] == qa.INJECTED


def test_proxy_geometry_labelled():
    report = qa.check_chain(marker_logs=[GEOMETRY_PROXY + "\n" + GEOMETRY_NODE])
    assert report["geometry"]["geometry"] == "proxy"
    assert report["geometry"]["nodes_proxy"] == 3
    assert report["geometry"]["natural_real_models"] is False
    assert report["geometry"]["proxy_nodes"] == ["n1"]


def test_geometry_real_models_is_natural():
    report = qa.check_chain(marker_logs=[GEOMETRY_OK])
    assert report["geometry"]["nodes_real"] == 5
    assert report["geometry"]["natural_real_models"] is True
    assert report["geometry"]["proxy_nodes"] == []


def test_collection_requires_new_and_natural_carry():
    missing = qa.check_chain(marker_logs=[ITEM_ACTOR + "\n" + RECEIPT_DUP])
    assert missing["collection"]["receipts_new"] == 0
    assert missing["collection"]["receipts_duplicate"] == 1
    assert missing["collection"]["natural_carry"] == 0
    assert missing["collection"]["pass"] is False

    complete = qa.check_chain(
        marker_logs=[ITEM_ACTOR + "\n" + RECEIPT_NEW + "\n" + NATURAL_CARRY])
    assert complete["collection"]["receipts_new"] == 1
    assert complete["collection"]["natural_carry"] == 2
    assert complete["collection"]["pass"] is True


def test_collection_without_receipts_is_proxy_not_injected():
    report = qa.check_chain(marker_logs=[ITEM_ACTOR])
    assert report["collection"]["pass"] is False
    assert report["classification"]["end_to_end_loop"] == qa.PROXY

    injected = qa.check_chain(marker_logs=["nothing\n"])
    assert injected["classification"]["end_to_end_loop"] == qa.INJECTED


def test_timeline_derivation():
    fresh_only = qa.check_chain(marker_logs=[TIMELINE_FRESH])
    assert fresh_only["timeline"] == {
        "rows": 1,
        "hole_closed_fresh": True,
        "hole_open_with_blue": False,
        "elec_open_with_yellow": False,
        "staged_grants": 0,
        "natural_grants": 0,
        "abilities_staged": False,
    }
    full = qa.check_chain(
        marker_logs=[TIMELINE_FRESH + "\n" + TIMELINE_ELEC + "\n" + TIMELINE_BLUE])
    assert full["timeline"]["hole_closed_fresh"] is True
    assert full["timeline"]["elec_open_with_yellow"] is True
    assert full["timeline"]["hole_open_with_blue"] is True
    assert full["timeline"]["rows"] == 3


def test_ledger_parse():
    rows = qa.parse_receipt_ledger(LEDGER + "\nstray\n")
    assert rows == [
        {"seed": "42", "treasure": "treasure_a", "host": "leaf_elec_0", "encounter": "encounter_1"},
        {"seed": "7", "treasure": "treasure_b", "host": "leaf_water_0", "encounter": "encounter_2"},
    ]
    assert qa.parse_receipt_ledger("") == []
    assert qa.check_chain(marker_logs=[], receipt_ledger=LEDGER)["collection"]["ledger_rows"] == 2


def test_missing_checker_keys_are_none():
    checker = {"generation_pass": True, "evidence": "natural"}
    report = qa.check_chain(marker_logs=[CLEAN_MARKERS], checker_report=checker)
    assert report["classification"]["seed_determinism"] is None
    assert report["classification"]["reroll_invariance"] is None
    assert report["classification"]["reachability"] == qa.NATURAL  # derived from gen pass
    assert report["classification"]["failure_handling"] is None
    assert not any("seed_determinism" in failure for failure in report["failures"])

    no_checker = qa.check_chain(marker_logs=[CLEAN_MARKERS])
    assert no_checker["classification"]["reachability"] is None
    assert no_checker["classification"]["generation_invariant"] == qa.INJECTED
    assert no_checker["pass"] is False


def test_main_exit_codes(tmp_path):
    log = tmp_path / "run.log"
    log.write_text(CLEAN_MARKERS, encoding="utf-8")
    checker = tmp_path / "checker.json"
    checker.write_text(json.dumps(CLEAN_CHECKER), encoding="utf-8")
    ledger = tmp_path / "receipts.txt"
    ledger.write_text(LEDGER, encoding="utf-8")
    out = tmp_path / "report.json"

    code = qa.main(["--live-log", str(log), "--checker", str(checker),
                    "--receipts", str(ledger), "--out", str(out)])
    assert code == 0
    written = json.loads(out.read_text(encoding="utf-8"))
    assert written["pass"] is True

    empty = tmp_path / "empty.log"
    empty.write_text("no markers\n", encoding="utf-8")
    code = qa.main(["--live-log", str(empty), "--checker", str(checker),
                    "--out", str(out)])
    assert code == 1
    assert json.loads(out.read_text(encoding="utf-8"))["pass"] is False


NESTED_CHECKER = {
    "schema": "p2-cave-spike-report/1",
    "cave": "forest_1",
    "floor": 1,
    "seed": 468001,
    "generation_invariant": {
        "name": "generation_invariant",
        "pass": True,
        "generation_pass": True,
        "model_pass": True,
        "evidence": "natural",
        "layouts": [{"layout_source": "engine", "pass": True, "retry_required": False}],
    },
    "reroll_invariance": {"name": "reroll_invariance", "pass": True},
    "end_to_end_loop": {"name": "end_to_end_loop", "pass": True},
    "seed_determinism": {"name": "seed_determinism", "pass": True},
    "pass": True,
}

NEGATIVE_REPORT = {
    "schema": "p2-cave-spike-report/1",
    "generation_invariant": {
        "pass": False,
        "generation_pass": False,
        "model_pass": False,
        "evidence": "injected",
        "layouts": [{"layout_source": "engine", "pass": False, "retry_required": True,
                     "findings": ["missing leaf leaf_water_0"]}],
    },
    "pass": False,
}


def test_lane40_nested_report_file_shape_is_understood():
    report = qa.check_chain(marker_logs=[CLEAN_MARKERS], checker_report=NESTED_CHECKER,
                            receipt_ledger=LEDGER)
    assert report["generation"]["checker_pass"] is True
    assert report["generation"]["checker_evidence"] == "natural"
    assert report["generation"]["pass"] is True
    assert report["classification"]["seed_determinism"] == qa.NATURAL
    assert report["classification"]["reroll_invariance"] == qa.NATURAL
    assert report["classification"]["reachability"] == qa.NATURAL
    assert report["pass"] is True


def test_failure_handling_derived_from_negative_control():
    report = qa.check_chain(marker_logs=[CLEAN_MARKERS], checker_report=NESTED_CHECKER,
                            receipt_ledger=LEDGER, failure_report=NEGATIVE_REPORT)
    assert report["classification"]["failure_handling"] == qa.NATURAL
    assert report["pass"] is True

    benign = dict(NEGATIVE_REPORT)
    benign["generation_invariant"] = dict(NEGATIVE_REPORT["generation_invariant"],
                                          layouts=[{"pass": False, "retry_required": False}])
    no_retry = qa.check_chain(marker_logs=[CLEAN_MARKERS], checker_report=NESTED_CHECKER,
                              receipt_ledger=LEDGER, failure_report=benign)
    assert no_retry["classification"]["failure_handling"] == qa.INJECTED
    assert no_retry["pass"] is False


def test_staged_ability_grants_downgrade_end_to_end_loop():
    log = CLEAN_MARKERS + "\n" + "P2_CAVE_ROOMS_GRANT species=yellow natural_acquire=0 staged=1"
    report = qa.check_chain(marker_logs=[log], checker_report=NESTED_CHECKER,
                            receipt_ledger=LEDGER)
    assert report["timeline"]["abilities_staged"] is True
    assert report["timeline"]["staged_grants"] == 1
    assert report["collection"]["pass"] is True
    assert report["classification"]["end_to_end_loop"] == qa.PROXY
    assert report["pass"] is False
    assert any("end_to_end_loop" in failure for failure in report["failures"])


def test_report_is_deterministic():
    first = clean_report()
    second = clean_report()
    assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)
    assert first == second
