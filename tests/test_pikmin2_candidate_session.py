import json
import sys
from pathlib import Path
from unittest.mock import patch
import pytest
from experimental import pikmin2_candidate_session as candidate
from experimental import pikmin2_generated_session_acceptance as qa
from experimental import pikmin2_seed_bridge as bridge
from randomizer.seed import validate
from randomizer.session import Session
from randomizer.runner import NativeRun
from tests.test_pikmin2_generated_session_acceptance import pin_for


def placement():
    return {"schema": "p2-placement-v1",
            "slots": [{"uid": 401, "label": "synthetic-unit-test-slot", "stage": 1, "terrain": "ground", "radius": 300,
                       "evidence": {"xyz": True, "terrain": True, "route": True}}],
            "profiles": [{"identity": "YellowKochappy", "terrains": ["ground"],
                          "accepted_gates": ["xyz"]}]}


def test_candidate_is_scoped_and_normal_loading_stays_closed():
    original = bridge.admitted_ids
    with candidate.candidate_scope():
        manifest = qa.generate_pinned_session("candidate", placement())
        candidate.validate_candidate(manifest)
        validate(manifest)
    assert bridge.admitted_ids is original
    with pytest.raises(ValueError):
        validate(manifest)
    with pytest.raises(qa.AcceptanceBlocked):
        qa.generate_pinned_session("normal", placement())


def test_override_restored_on_error():
    original = bridge.admitted_ids
    with pytest.raises(RuntimeError), candidate.candidate_scope():
        raise RuntimeError("failure")
    assert bridge.admitted_ids is original


def test_other_id_rejected():
    with pytest.raises(qa.AcceptanceError):
        candidate.validate_candidate({"p2_layout": {"bindings": [{"source_id": 79}]}})


def test_plan_labels_candidate_without_product_admission(tmp_path):
    pin = pin_for(tmp_path)
    file = tmp_path / "placement.json"
    file.write_text(json.dumps(placement()))
    output = tmp_path / "report.json"
    argv = ["plan", "--seed", "candidate", "--placement", str(file), "--output", str(output)]
    for key, value in pin.as_dict().items():
        argv += ["--" + key.replace("_", "-"), value]
    assert candidate.main(argv) == 0
    report = json.loads(output.read_text())
    assert report["candidate_scope"] == candidate.SCOPE
    assert report["product_admission"] is False
    assert {b["source_id"] for b in report["layout"]["bindings"]} == {45}


def test_product_records_reject_candidate(tmp_path):
    prepared = tmp_path / "prepared.json"
    prepared.write_text(json.dumps({"candidate_scope": candidate.SCOPE}))
    with pytest.raises(qa.AcceptanceError, match="pre-admission"):
        qa.main(["records", "--prepared", str(prepared), "--observations", "unused",
                 "--kind", "natural", "--output", str(tmp_path / "records")])


def test_run_reconstructs_launcher_and_restores_override(tmp_path):
    pin = pin_for(tmp_path)
    with candidate.candidate_scope():
        manifest = qa.generate_pinned_session("candidate", placement())
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(manifest))
    report = tmp_path / "prepared.json"
    report.write_text(json.dumps(dict(candidate_scope=candidate.SCOPE, pin=pin.as_dict(),
        manifest=str(path), session_dir=str(tmp_path / "session"),
        content_manifest_path=str(tmp_path / "content.json"), launch=["ignored"])))
    def launch():
        assert sys.argv[1] == "run"
        assert "--content-manifest" in sys.argv
        validate(manifest)
    original = bridge.admitted_ids
    with patch("randomizer.__main__.main", launch):
        candidate.main(["run", "--prepared", str(report)])
    assert bridge.admitted_ids is original


def test_prepare_writes_reusable_candidate_runbook(tmp_path):
    import hashlib
    from experimental.pikmin2_staging import build_manifest, dump_manifest
    pin = pin_for(tmp_path)
    place = tmp_path / "placement.json"
    place.write_text(json.dumps(placement()))
    asset = tmp_path / "asset.txt"
    asset.write_text("synthetic test content")
    content = tmp_path / "content.json"
    dump_manifest(build_manifest(1, [dict(id="test", kind="config", source=str(asset),
        destination="p2-snow.txt", sha256=hashlib.sha256(asset.read_bytes()).hexdigest())],
        identities=[45]), content)
    report = tmp_path / "prepared.json"
    argv = ["prepare", "--seed", "test", "--placement", str(place),
            "--content-manifest", str(content), "--session-dir", str(tmp_path / "session"),
            "--output", str(report)]
    for key, value in pin.as_dict().items():
        argv += ["--" + key.replace("_", "-"), value]
    assert candidate.main(argv) == 0
    data = json.loads(report.read_text())
    assert data["launch"][2] == "experimental.pikmin2_candidate_session"
    assert data["content_manifest_path"] == str(content.resolve())
    assert "ENEMY_P2" in Path(data["bootstrap"]).read_text()
    with pytest.raises(ValueError):
        validate(json.loads(Path(data["manifest"]).read_text()))


def test_p2_layout_journal_reloads_after_a_previous_run(tmp_path):
    # Regression: Session journal recovery must accept the ENEMY_P2 bootstrap the
    # runner writes (schema 9 + benefit_items + p2_layout = 31 tokens), so a
    # second run of the same candidate session restarts instead of rejecting the
    # prior run's journal as an incompatible manifest.
    import hashlib
    from experimental.pikmin2_staging import build_manifest, dump_manifest
    pin = pin_for(tmp_path)
    place = tmp_path / "placement.json"
    place.write_text(json.dumps(placement()))
    asset = tmp_path / "asset.txt"
    asset.write_text("synthetic test content")
    content = tmp_path / "content.json"
    dump_manifest(build_manifest(1, [dict(id="test", kind="config", source=str(asset),
        destination="p2-snow.txt", sha256=hashlib.sha256(asset.read_bytes()).hexdigest())],
        identities=[45]), content)
    manifest = None
    with candidate.candidate_scope():
        manifest = qa.generate_pinned_session("test", placement())
    session_dir = tmp_path / "session"
    with candidate.candidate_scope():
        session = Session(manifest, session_dir)
        run = NativeRun(session)
        assert "ENEMY_P2" in run.bootstrap.read_text(encoding="ascii")
        # The native game writes its check journal into the run directory; a
        # restart must recover it without rejecting the ENEMY_P2 bootstrap.
        (run.directory / "checks.txt").write_text("0\n", encoding="ascii")
        reloaded = Session(manifest, session_dir)
    assert reloaded.data["checked"] == [session.names[0]]
