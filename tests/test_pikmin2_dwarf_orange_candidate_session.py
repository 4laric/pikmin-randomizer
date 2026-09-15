import json
import sys
from unittest.mock import patch
import pytest
from experimental import pikmin2_candidate_session as candidate
from experimental import pikmin2_generated_session_acceptance as qa
from experimental import pikmin2_seed_bridge as bridge
from randomizer.seed import validate
from tests.test_pikmin2_generated_session_acceptance import pin_for


def placement44():
    return {"schema": "p2-placement-v1",
            "slots": [{"uid": 401, "label": "synthetic-unit-test-slot", "stage": 1, "terrain": "ground", "radius": 300,
                       "evidence": {"xyz": True, "terrain": True, "route": True}}],
            "profiles": [{"identity": "BlueKochappy", "terrains": ["ground"],
                          "accepted_gates": ["xyz"]}]}


def test_dwarf_orange_candidate_scope_patches_admission():
    original = bridge.admitted_ids
    source = None
    with candidate.candidate_scope(44):
        from experimental import pikmin2_seed_bridge as current
        source = current.admitted_ids(None)
    assert source == [44]
    assert bridge.admitted_ids is original


def test_dwarf_orange_rejects_other_sources():
    with pytest.raises(qa.AcceptanceError, match='source 44'):
        candidate.validate_candidate(
            {'p2_layout': {'bindings': [{'source_id': 45}]}}, source=44)
    with pytest.raises(qa.AcceptanceError, match='source 45'):
        candidate.validate_candidate(
            {'p2_layout': {'bindings': [{'source_id': 44}]}}, source=45)


def test_dwarf_orange_scope_name():
    assert candidate.scope_name(44) == 'private-dwarf-orange-candidate-v1'
    assert candidate.scope_name(45) == 'private-snow-candidate-v1'


def test_dwarf_orange_plan_labels_candidate_without_product_admission(tmp_path):
    pin = pin_for(tmp_path)
    file = tmp_path / "placement.json"
    file.write_text(json.dumps(placement44()))
    output = tmp_path / "report.json"
    argv = ["plan", "--source", "44", "--seed", "candidate",
            "--placement", str(file), "--output", str(output)]
    for key, value in pin.as_dict().items():
        argv += ["--" + key.replace("_", "-"), value]
    assert candidate.main(argv) == 0
    report = json.loads(output.read_text())
    assert report["candidate_scope"] == "private-dwarf-orange-candidate-v1"
    assert report["product_admission"] is False
    assert {b["source_id"] for b in report["layout"]["bindings"]} == {44}


def test_dwarf_orange_run_reconstructs_launcher_and_restores_override(tmp_path):
    pin = pin_for(tmp_path)
    with candidate.candidate_scope(44):
        manifest = qa.generate_pinned_session("candidate", placement44())
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(manifest))
    report = tmp_path / "prepared.json"
    report.write_text(json.dumps(dict(candidate_scope="private-dwarf-orange-candidate-v1",
        pin=pin.as_dict(), manifest=str(path), session_dir=str(tmp_path / "session"),
        content_manifest_path=str(tmp_path / "content.json"), launch=["ignored"])))
    def launch():
        assert sys.argv[1] == "run"
        assert "--content-manifest" in sys.argv
        validate(manifest)
    original = bridge.admitted_ids
    with patch("randomizer.__main__.main", launch):
        candidate.main(["run", "--source", "44", "--prepared", str(report)])
    assert bridge.admitted_ids is original