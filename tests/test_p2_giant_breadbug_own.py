"""#958 Giant Breadbug (OoPanModoki 40) OWN content wiring: extractor, stager, installer.

The native side (pc_p2_breadbug_teki, variant 40) opens exactly
``p2-giantbreadbug-parms.txt``, ``p2-giantbreadbug-bank.txt`` and the
``giantbreadbug_<clip>_<ii>.mod`` poses in the private model room. These tests
pin that the root extracts and stages those files for source 40 without
disturbing the Breadbug (38) names, and that the proxy row for 40 is gone.
"""
import json
from pathlib import Path

import pytest

from experimental import pikmin2_breadbug_own_assets as assets
from experimental import pikmin2_breadbug_stage as stage
from experimental.pikmin2_family_install import ADAPTERS, IDENTITY_FAMILY, resolve_family
from randomizer.p2_proxy import load_rows
from scripts import p2_prepare_content as prepare

ISO = Path("C:/Users/alari/Downloads/PIKMIN2 for GAMECUBE.iso")

# Retail oopanmodoki/enemyparm.txt (comments stripped): same layout as PanModoki,
# Giant values.
GIANT_PARM = (
    "{\n{s003} 4 0.1\n{_eof}\n}\n"
    "{\n{fp00} 4 2000.0\n{fp27} 4 45.0\n{fp06} 4 85.0\n{fp08} 4 0.1\n{fp28} 4 2.0\n"
    "{fp10} 4 30.0\n{fp14} 4 300.0\n{fp15} 4 120.0\n{_eof}\n}\n"
    "{\n{fp00} 4 2.0\n{fp16} 4 1.0\n{fp02} 4 0.2\n{fp05} 4 5.0\n{fp03} 4 45.0\n{fp04} 4 1000.0\n"
    "{fp06} 4 100.0\n{fp14} 4 0.0\n{fp15} 4 150.0\n{ip01} 4 1\n{_eof}\n}\n"
)


def test_source_40_has_an_own_extractor_not_the_proxy():
    assert prepare.EXTRACTORS[40] == "extract_giant_breadbug"
    assert prepare.ENUM_FOR_SOURCE[40] == "OoPanModoki"
    assert 40 not in prepare.PROXY_SOURCE_IDS
    assert not any(row["source_id"] == 40 for row in load_rows())
    root = Path(prepare.__file__).resolve().parents[1]
    assert not (root / "randomizer" / "p2_proxy" / "40_OoPanModoki.json").exists()


def test_source_40_installs_through_its_own_family():
    # A separate family from the Breadbug: a family installs from ONE source
    # directory, so a seed carrying both needs both content sets staged.
    assert resolve_family(40) == "giantbreadbug"
    assert resolve_family("OoPanModoki") == "giantbreadbug"
    assert resolve_family(38) == "breadbug"
    assert IDENTITY_FAMILY[40] != "proxy"
    assert "validate" in ADAPTERS["giantbreadbug"] and "install" in ADAPTERS["giantbreadbug"]


def test_variant_names_do_not_collide_with_the_breadbug():
    small, giant = stage.VARIANTS[38], stage.VARIANTS[40]
    assert small["parms"] == stage.PARMS and small["bank"] == stage.BANK_TXT
    assert giant["parms"] == "p2-giantbreadbug-parms.txt" and giant["bank"] == "p2-giantbreadbug-bank.txt"
    assert stage.pose_name("move1", 3) == "breadbug_move1_03.mod"
    assert stage.pose_name("move1", 3, 40) == "giantbreadbug_move1_03.mod"
    assert assets.pose_name("move1", 3) == "breadbug_move1_03.mod"
    assert assets.pose_name("move1", 3, assets.OO_VARIANT) == "giantbreadbug_move1_03.mod"
    assert assets.OO_VARIANT["parm_prefix"] == "oopanmodoki/" and assets.PANMODOKI["parm_prefix"] == "panmodoki/"
    # The default extractor call still writes the 38 manifest.
    assert assets.MANIFEST == "breadbug.json" and assets.OO_VARIANT["manifest"] == "giantbreadbug.json"


def test_parse_enemyparm_reads_the_giant_values():
    general, proper = stage.parse_enemyparm(GIANT_PARM.encode("ascii"))
    assert general["fp00"] == 2000.0 and general["fp06"] == 85.0
    assert proper["fp06"] == 100.0 and proper["fp04"] == 1000.0 and proper["ip01"] == 1
    assert proper["fp03"] == 45.0 and proper["fp16"] == 1.0


def test_staging_writes_the_giant_names_and_keeps_38_apart(tmp_path):
    bank = stage.bank_text([dict(anim_id=0, name="dead", frames=99, events=[(70, 2)], poses=[])])
    plan = dict(bank=bank, room=[], parms=GIANT_PARM.encode("ascii"), source_id=40,
                parms_name=stage.VARIANTS[40]["parms"], bank_name=stage.VARIANTS[40]["bank"])
    (tmp_path / stage.ROOM).mkdir(parents=True)
    receipt = stage.stage(tmp_path, plan)
    assert receipt["parms"] == "p2-giantbreadbug-parms.txt"
    assert (tmp_path / "p2-giantbreadbug-parms.txt").read_bytes() == plan["parms"]
    assert (tmp_path / "p2-giantbreadbug-bank.txt").read_bytes() == bank
    assert not (tmp_path / stage.PARMS).exists() and not (tmp_path / stage.BANK_TXT).exists()
    assert stage.parse_bank(bank)["clips"][0]["events"] == [(70, 2)]


def test_plan_needs_a_manifest_and_picks_the_variant(tmp_path):
    assert stage.plan(tmp_path) is None
    (tmp_path / "giantbreadbug.json").write_text(json.dumps(dict(schema=1, enemy_id=38, clips=[])), encoding="utf-8")
    with pytest.raises(stage.BreadbugStageError):
        stage.plan(tmp_path)  # manifest says 38 but the file is the giant's
    with pytest.raises(stage.BreadbugStageError):
        stage.plan(tmp_path, 99)


@pytest.mark.skipif(not ISO.is_file(), reason="needs the owner's GPVE01 ISO")
def test_iso_extract_and_stage_what_native_opens(tmp_path):
    target = prepare.extract_giant_breadbug(ISO, tmp_path / "content")
    assert target.name == "OoPanModoki"
    manifest = json.loads((target / "giantbreadbug.json").read_text(encoding="utf-8"))
    assert manifest["enemy_id"] == 40 and manifest["enum_name"] == "OoPanModoki"
    assert [Path(c["file"]).stem for c in manifest["clips"]] == list(stage.CLIPS)
    assert all(c["status"] == "converted" for c in manifest["clips"])
    assert not (target / "breadbug.json").exists()
    run = tmp_path / "run"
    (run / stage.ROOM).mkdir(parents=True)
    ADAPTERS["giantbreadbug"]["validate"](target)
    receipt = ADAPTERS["giantbreadbug"]["install"](target, run, [(2903640892, "OoPanModoki")])
    assert receipt["source_id"] == 40 and receipt["species"] == "OoPanModoki"
    parms = run / "p2-giantbreadbug-parms.txt"
    general, proper = stage.parse_enemyparm(parms.read_bytes())
    assert general["fp00"] == 2000.0 and proper["fp06"] == 100.0 and proper["fp04"] == 1000.0 and proper["ip01"] == 1
    parsed = stage.parse_bank((run / "p2-giantbreadbug-bank.txt").read_bytes())
    staged = sorted(p.name for p in (run / stage.ROOM).iterdir())
    expected = sorted(stage.pose_name(c["name"], i, 40) for c in parsed["clips"].values() for i in range(len(c["poses"])))
    assert staged == expected and len(staged) == receipt["breadbug"]["poses"] > 0
    # The Giant's Dead clip carries KEYEVENT_2 (boundEffect) at frame 70.
    assert (70, 2) in parsed["clips"][0]["events"]
    # Pulled loop (type1 5..10) and the carcass hold (type5 10) have poses.
    assert 5 in parsed["clips"][3]["poses"] and 10 in parsed["clips"][7]["poses"]
    # A wrong-identity source is refused by the validator.
    with pytest.raises(Exception):
        ADAPTERS["breadbug"]["validate"](target)
