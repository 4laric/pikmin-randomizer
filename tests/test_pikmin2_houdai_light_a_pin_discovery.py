"""Fail-closed tests for the Houdai_light_a pin-discovery checker (#782)."""
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(r"C:\Users\alari\pikmin-randomizer\output\workflow\autofill\planning-shards\provider-placement-catalog\prepared\houdai-lighta-pin-root")
CANON = Path(r"C:\Users\alari\pikmin-randomizer")

spec = importlib.util.spec_from_file_location(
    "houdai_pin", str(ROOT / "experimental" / "pikmin2_houdai_light_a_pin_discovery.py"))
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def fixture_inventory(token="Houdai_light_a", floors="ok", catalogs="ok"):
    inv = {"story_caves": [{"id": "tutorial_2",
                            "source": "user/Mukki/mapunits/caveinfo/tutorial_2.txt",
                            "floors": [{"first": 9, "last": 9,
                                        "unit_pool": "1_units_houdai_metal.txt",
                                        "enemy_ids": [token, "DaiodoRed"]}]}],
           "catalogs": {"us/runtime/item": {"entries": [{"name": "light_a"}]},
                        "us/runtime/otakara": {"entries": [{"name": "bolt"}]}}}
    if floors == "no-row":
        inv["story_caves"][0]["floors"] = [{"first": 8, "last": 8,
                                            "unit_pool": "x.txt", "enemy_ids": []}]
    if floors == "no-token":
        inv["story_caves"][0]["floors"][0]["enemy_ids"] = ["DaiodoRed"]
    if catalogs == "no-cargo":
        inv["catalogs"]["us/runtime/item"]["entries"] = []
    return inv


ENEMYINFO = "  EnemyID_Houdai         = 66,  // Man-at-Legs\n"


def write(tmp, name, text):
    p = tmp / name
    p.write_text(text, encoding="utf-8")
    return p


def test_found_classified(tmp_path):
    inv = write(tmp_path, "inv.json", json.dumps(fixture_inventory()))
    einfo = write(tmp_path, "enemyInfo.h", ENEMYINFO)
    packet = mod.discover(inv, einfo)
    assert packet["token"] == "Houdai_light_a"
    assert packet["classification"]["kind"] == "enemy_carried_item"
    assert packet["classification"]["enemy_id"] == 66
    assert packet["classification"]["cargo"] == "light_a"
    assert packet["downstream"] == {"issue": 747, "lane": "p2-cave-tutorial_2-p1-later-floors"}


def test_absent_floor_row_refused(tmp_path):
    inv = write(tmp_path, "inv.json", json.dumps(fixture_inventory(floors="no-row")))
    einfo = write(tmp_path, "enemyInfo.h", ENEMYINFO)
    try:
        mod.discover(inv, einfo)
    except mod.PinError as exc:
        assert "ABSENT" in str(exc)
    else:
        raise AssertionError("missing floor row must be refused")


def test_absent_token_refused(tmp_path):
    inv = write(tmp_path, "inv.json", json.dumps(fixture_inventory(floors="no-token")))
    einfo = write(tmp_path, "enemyInfo.h", ENEMYINFO)
    try:
        mod.discover(inv, einfo)
    except mod.PinError as exc:
        assert "ABSENT" in str(exc)
    else:
        raise AssertionError("missing token must be refused")


def test_unknown_cargo_refused_not_invented():
    enemies = {"Houdai": (66, 125)}
    try:
        mod.classify("Houdai_nope_x", enemies, {}, {"bolt": {}})
    except mod.PinError as exc:
        assert "refused" in str(exc).lower()
    else:
        raise AssertionError("unknown cargo must be refused, never invented")


def test_unknown_enemy_refused():
    enemies = {"Houdai": (66, 125)}
    try:
        mod.classify("Nope_light_a", enemies, {"light_a": {}}, {})
    except mod.PinError as exc:
        assert "refused" in str(exc).lower()
    else:
        raise AssertionError("unknown enemy base must be refused")


def test_malformed_json_refused(tmp_path):
    inv = write(tmp_path, "inv.json", "{not json")
    einfo = write(tmp_path, "enemyInfo.h", ENEMYINFO)
    try:
        mod.discover(inv, einfo)
    except mod.PinError as exc:
        assert "malformed" in str(exc).lower()
    else:
        raise AssertionError("malformed input must be refused")


def test_missing_input_refused(tmp_path):
    einfo = write(tmp_path, "enemyInfo.h", ENEMYINFO)
    try:
        mod.discover(tmp_path / "does-not-exist.json", einfo)
    except mod.PinError as exc:
        assert "missing" in str(exc).lower()
    else:
        raise AssertionError("missing input must be refused")


def test_live_canonical_classification():
    packet = mod.discover(CANON / "docs" / "PIKMIN2_CONTENT_INVENTORY.json",
                          CANON / "native" / "pikmin2-research" / "include" / "Game" / "enemyInfo.h")
    assert packet["classification"]["kind"] == "enemy_carried_item"
    assert packet["classification"]["enemy"] == "Houdai"
    assert packet["classification"]["enemy_id"] == 66
    assert packet["classification"]["cargo_entry"]["bmd"] == "eq_flashlight.bmd"
    assert packet["citations"]["floor_row"].endswith(":233")
    assert packet["citations"]["cargo_entry"].endswith(":5746")

