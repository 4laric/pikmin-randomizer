"""#898 Breadbug (PanModoki 38) OWN content wiring: extractor, stager, installer.

The native side (pc_p2_breadbug_teki / pc_p2_breadbug_fsm) opens exactly
``p2-breadbug-parms.txt``, ``p2-breadbug-bank.txt`` and the
``breadbug_<clip>_<ii>.mod`` poses in the private model room. These tests pin
that the root extracts and stages those files for source 38 and that the
generic proxy path no longer declares 38.
"""
import json
from pathlib import Path

import pytest

from experimental import pikmin2_breadbug_stage as stage
from experimental.pikmin2_family_install import ADAPTERS, IDENTITY_FAMILY, resolve_family
from randomizer.p2_proxy import load_rows
from scripts import p2_prepare_content as prepare

ISO = Path("C:/Users/alari/Downloads/PIKMIN2 for GAMECUBE.iso")

RETAIL_PARM = (
    "{\n{s003} 4 0.1\n{_eof}\n}\n"
    "{\n{fp00} 4 1100.0\n{fp27} 4 45.0\n{fp06} 4 60.0\n{fp08} 4 0.1\n{fp28} 4 3.0\n"
    "{fp10} 4 15.0\n{fp14} 4 500.0\n{fp15} 4 120.0\n{_eof}\n}\n"
    "{\n{fp00} 4 1.0\n{fp16} 4 2.0\n{fp02} 4 0.2\n{fp05} 4 5.0\n{fp03} 4 35.0\n{fp04} 4 1000.0\n"
    "{fp06} 4 200.0\n{fp14} 4 0.0\n{fp15} 4 150.0\n{ip01} 4 11\n{_eof}\n}\n"
)


def test_source_38_has_an_own_extractor_not_the_proxy():
    assert prepare.EXTRACTORS[38] == "extract_breadbug"
    assert prepare.ENUM_FOR_SOURCE[38] == "PanModoki"
    assert 38 not in prepare.PROXY_SOURCE_IDS
    assert not any(row["source_id"] == 38 for row in load_rows())
    root = Path(prepare.__file__).resolve().parents[1]
    assert not (root / "randomizer" / "p2_proxy" / "38_PanModoki.json").exists()


def test_source_38_installs_through_the_breadbug_adapter():
    assert resolve_family(38) == "breadbug"
    assert resolve_family("PanModoki") == "breadbug"
    assert IDENTITY_FAMILY[38] != "proxy"
    assert "breadbug" in ADAPTERS and "validate" in ADAPTERS["breadbug"]


def test_parse_enemyparm_reads_general_and_proper_blocks():
    general, proper = stage.parse_enemyparm(RETAIL_PARM.encode("ascii"))
    # The proper block also has fp00 (nest scale) and fp14 (wait time): the
    # general block is the one with fp27, never the proper one.
    assert general["fp00"] == 1100.0 and general["fp06"] == 60.0
    assert proper["fp06"] == 200.0 and proper["fp04"] == 1000.0 and proper["ip01"] == 11
    with pytest.raises(stage.BreadbugStageError):
        stage.parse_enemyparm(b"{\n{s003} 4 0.1\n{_eof}\n}\n")


def test_bank_round_trip_and_native_bounds():
    clips = [dict(anim_id=i, name=name, frames=49, events=[(10, 0), (39, 1)] if name == "move2" else [],
                  poses=[0, 24, 48]) for i, name in enumerate(stage.CLIPS)]
    text = stage.bank_text(clips)
    parsed = stage.parse_bank(text)
    assert set(parsed["clips"]) == set(range(9))
    assert parsed["clips"][2]["events"] == [(10, 0), (39, 1)]
    assert text.startswith(b"P2_BREADBUG_BANK_1 9\n") and text.endswith(b"END\n")
    bad = [dict(clips[0], poses=[5, 5])]
    with pytest.raises(stage.BreadbugStageError):
        stage.bank_text(bad)
    with pytest.raises(stage.BreadbugStageError):
        stage.parse_bank(b"P2_BREADBUG_BANK_1 1\nclip 9 x 49 0 0\nEND\n")


def test_staging_needs_a_private_room(tmp_path):
    plan = dict(bank=stage.bank_text([dict(anim_id=0, name="dead", frames=99, events=[], poses=[])]),
                room=[], parms=RETAIL_PARM.encode("ascii"))
    with pytest.raises(stage.BreadbugStageError):
        stage.stage(tmp_path, plan)
    (tmp_path / stage.ROOM).mkdir(parents=True)
    receipt = stage.stage(tmp_path, plan)
    assert (tmp_path / stage.PARMS).read_bytes() == plan["parms"]
    assert (tmp_path / stage.BANK_TXT).read_bytes() == plan["bank"]
    assert receipt["poses"] == 0
    # Idempotent for identical inputs, refuses a different existing file.
    stage.stage(tmp_path, plan)
    with pytest.raises(stage.BreadbugStageError):
        stage.stage(tmp_path, dict(plan, parms=b"{\n}\n"))


def _tree(tmp_path, nest=None):
    import hashlib
    clips = [dict(file=f"{name}.bca", events=[], source_frames=10, status="unsupported", poses=[])
             for name in stage.CLIPS]
    manifest = dict(schema=1, enemy_id=38, clips=clips)
    if nest is not None:
        (tmp_path / nest["file"]).write_bytes(nest.pop("data"))
        manifest["nest"] = nest
    (tmp_path / "breadbug.json").write_text(json.dumps(manifest), encoding="utf-8")
    (tmp_path / "enemyparm.txt").write_bytes(RETAIL_PARM.encode("ascii"))
    return hashlib


def test_plan_stages_the_lair_model_when_present(tmp_path):
    hashlib = _tree(tmp_path, dict(file="breadbug_nest.mod", data=b"nest-bytes", scale=1.0))
    plan = stage.plan(tmp_path, 38)
    assert ("breadbug_nest.mod", b"nest-bytes") in plan["room"]


def test_plan_without_lair_still_stages_and_rejects_bad_lair(tmp_path):
    _tree(tmp_path)
    assert all(name != "breadbug_nest.mod" for name, _ in stage.plan(tmp_path, 38)["room"])
    bad = tmp_path / "bad"
    bad.mkdir()
    _tree(bad, dict(file="breadbug_nest.mod", data=b"x", sha256="0" * 64))
    with pytest.raises(stage.BreadbugStageError):
        stage.plan(bad, 38)
    wrong = tmp_path / "wrong"
    wrong.mkdir()
    _tree(wrong, dict(file="other_nest.mod", data=b"x"))
    with pytest.raises(stage.BreadbugStageError):
        stage.plan(wrong, 38)


@pytest.mark.skipif(not ISO.is_file(), reason="needs the owner's GPVE01 ISO")
def test_iso_extract_and_stage_what_native_opens(tmp_path):
    target = prepare.extract_breadbug(ISO, tmp_path / "content")
    manifest = json.loads((target / "breadbug.json").read_text(encoding="utf-8"))
    assert [Path(c["file"]).stem for c in manifest["clips"]] == list(stage.CLIPS)
    assert all(c["status"] == "converted" for c in manifest["clips"])
    run = tmp_path / "run"
    (run / stage.ROOM).mkdir(parents=True)
    ADAPTERS["breadbug"]["validate"](target)
    receipt = ADAPTERS["breadbug"]["install"](target, run, [(1945764764, "PanModoki")])
    assert receipt["source_id"] == 38
    general, proper = stage.parse_enemyparm((run / stage.PARMS).read_bytes())
    assert general["fp00"] == 1100.0 and proper["fp06"] == 200.0 and proper["fp04"] == 1000.0
    parsed = stage.parse_bank((run / stage.BANK_TXT).read_bytes())
    staged = sorted(p.name for p in (run / stage.ROOM).iterdir())
    expected = sorted([stage.pose_name(c["name"], i) for c in parsed["clips"].values() for i in range(len(c["poses"]))]
                      + [stage.nest_name(38)])
    assert staged == expected and len(staged) == receipt["breadbug"]["poses"] > 0
    # #1022 lair: the PanHouse model at the proper-parm nest scale.
    assert manifest["nest"]["file"] == "breadbug_nest.mod" and manifest["nest"]["scale"] == 1.0
    assert manifest["nest"]["source"] == "enemy/data/PanHouse/model.szs"
    # Pulled loop (type1 5..10) and the carcass hold (type5 10) have poses.
    assert 5 in parsed["clips"][3]["poses"] and 10 in parsed["clips"][7]["poses"]
