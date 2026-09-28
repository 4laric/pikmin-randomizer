"""Fail-closed tests for the White Pikmin species pin audit (#820)."""
import importlib.util
import json
from pathlib import Path

ROOT = Path(r"C:\Users\alari\pikmin-randomizer\output\workflow\autofill\planning-shards\provider-runtime-fixtures\prepared\white-pikmin-species-pin-root")
CANON = Path(r"C:\Users\alari\pikmin-randomizer")

spec = importlib.util.spec_from_file_location(
    "species_pin", str(ROOT / "experimental" / "pikmin2_white_pikmin_species_pin_audit.py"))
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def make_tree(tmp, species=True, white_persist=False):
    (tmp / "native" / "pc_port").mkdir(parents=True)
    (tmp / "native" / "include").mkdir(parents=True)
    (tmp / "native" / "src" / "plugPikiKando").mkdir(parents=True)
    (tmp / "native" / "src" / "plugPikiColin").mkdir(parents=True)
    (tmp / "native" / "pikmin2-research" / "include" / "Game").mkdir(parents=True)
    (tmp / "native" / "pikmin2-research" / "include" / "og" / "Screen").mkdir(parents=True)
    body = "mP2White" if species else "nothing here"
    (tmp / "native" / "pc_port" / "pc_p2_species.cpp").write_text("int pc_p2_species() { %s; }\n" % body, encoding="utf-8")
    (tmp / "native" / "include" / "Piki.h").write_text("bool mP2White = false;\n", encoding="utf-8")
    (tmp / "native" / "include" / "PikiHeadItem.h").write_text("bool mP2White = false;\n", encoding="utf-8")
    (tmp / "native" / "pikmin2-research" / "include" / "Game" / "EnemyBase.h").write_text("eatWhitePikminCallBack;\n", encoding="utf-8")
    (tmp / "native" / "pikmin2-research" / "include" / "og" / "Screen" / "MapCounter.h").write_text("mShipWhitePikmin;\n", encoding="utf-8")
    for name in ("piki.cpp", "pikiheadItem.cpp", "navi.cpp", "naviState.cpp", "pikiState.cpp"):
        (tmp / "native" / "src" / "plugPikiKando" / name).write_text("mP2White = x;\n", encoding="utf-8")
    (tmp / "native" / "pc_port" / "pc_whistle_pluck.cpp").write_text("mP2White = y;\n", encoding="utf-8")
    persist = "mWhitePikiCount" if white_persist else "mRedPikiCount"
    (tmp / "native" / "src" / "plugPikiColin" / "memoryCard.cpp").write_text("%s = 1;\n" % persist, encoding="utf-8")
    (tmp / "native" / "src" / "plugPikiKando" / "pikiMgr.cpp").write_text("birth();\n", encoding="utf-8")
    return tmp


def test_found_partial(tmp_path):
    packet = mod.audit(make_tree(tmp_path))
    assert packet["verdict"] == "FOUND_PARTIAL"
    assert len(packet["found"]) == 11
    assert [a["verdict"] for a in packet["absent"]] == ["ABSENT", "ABSENT"]
    assert packet["downstream"]["issue"] == 562


def test_missing_input_refused(tmp_path):
    try:
        mod.audit(tmp_path / "nope")
    except mod.PinError as exc:
        assert "missing input" in str(exc)
    else:
        raise AssertionError("missing input must be refused")


def test_malformed_input_refused(tmp_path):
    root = make_tree(tmp_path)
    (root / "native" / "pc_port" / "pc_p2_species.cpp").write_bytes(b"\xff\xfe bad")
    try:
        mod.audit(root)
    except mod.PinError as exc:
        assert "malformed input" in str(exc)
    else:
        raise AssertionError("malformed input must be refused")


def test_unexpected_presence_refused(tmp_path):
    root = make_tree(tmp_path, white_persist=True)
    try:
        mod.audit(root)
    except mod.PinError as exc:
        assert "unexpected" in str(exc)
    else:
        raise AssertionError("broken audit assumption must be refused")


def test_absent_token_refused(tmp_path):
    root = make_tree(tmp_path, species=False)
    try:
        mod.audit(root)
    except mod.PinError as exc:
        assert "unclassifiable" in str(exc)
    else:
        raise AssertionError("missing species marker must be refused")


def test_live_canonical_audit():
    packet = mod.audit(CANON)
    assert packet["verdict"] == "FOUND_PARTIAL"
    by_file = {f["file"]: f for f in packet["found"]}
    assert by_file["native/pc_port/pc_p2_species.cpp"]["citations"][0].startswith("pc_p2_species.cpp:")
    assert any("Piki.h:33" in c for c in by_file["native/include/Piki.h"]["citations"])
    assert any("memoryCard" in a["file"] for a in packet["absent"])
    assert any("pikiMgr" in a["file"] for a in packet["absent"])

