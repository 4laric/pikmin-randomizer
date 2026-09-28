"""Fail-closed tests for the tutorial_2 floor-9 Houdai_light_a staging contract (#805)."""
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(r"C:\Users\alari\pikmin-randomizer\output\workflow\autofill\planning-shards\overworld-tutorial\prepared\tutorial2-floor9-staging-root")
CANON = Path(r"C:\Users\alari\pikmin-randomizer")

spec = importlib.util.spec_from_file_location(
    "floor9_staging", str(ROOT / "experimental" / "pikmin2_tutorial2_floor9_houdai_lighta_staging.py"))
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

GOOD_PINS = {"root": mod.CONSUMER["root"], "native": mod.CONSUMER["native"]}

HOUDAI = {
    "lane": "houdai-light-a-pin-discovery", "issue": 782, "generation": 2,
    "root": {"base": "x", "commits": [], "head": "c1362d51", "dirty": "", "worktree": "w"},
    "next_action": "Downstream p2-cave-tutorial_2-p1-later-floors (#747) stages floor 9 with one Houdai (id 66) carrying item light_a per the packet",
    "source_mapping": [{"description": "Houdai_light_a = Houdai id 66 carrying item light_a"}],
}
DESCEND = {
    "lane": "tutorial2-descend-policy-native", "issue": 757, "generation": 2,
    "root": {"base": "y", "commits": [], "head": "1075e1ab", "dirty": "", "worktree": "w"},
    "native": {"base": "z", "commits": [], "head": "eaabe9c8", "dirty": "", "worktree": "wn"},
    "next_action": "stage P2_CAVE_ENTRY_4 entries for floors 3-8 and observe the descend chain",
    "source_mapping": [{"description": "pc_p2_cave.cpp extends entry P2_CAVE_ENTRY_4 floors 3-8 + descend (1-7 descend, 8 terminal)"}],
    "remaining_work": ["Floor-9 cargo + persistence follow-ons"],
}


def write(tmp, name, payload, sha=None):
    p = tmp / name
    raw = payload if isinstance(payload, bytes) else json.dumps(payload).encode("utf-8")
    p.write_bytes(raw)
    return p


def test_contract_resolves_cargo_and_records_gap(tmp_path):
    h = write(tmp_path, "houdai.json", HOUDAI)
    d = write(tmp_path, "descend.json", DESCEND)
    # patch expected shas onto spec copies
    import copy
    old_h = dict(mod.HANDOFFS["houdai-light-a-pin-discovery"])
    old_d = dict(mod.HANDOFFS["tutorial2-descend-policy-native"])
    mod.HANDOFFS["houdai-light-a-pin-discovery"]["sha256"] = hashlib.sha256(h.read_bytes()).hexdigest()
    mod.HANDOFFS["tutorial2-descend-policy-native"]["sha256"] = hashlib.sha256(d.read_bytes()).hexdigest()
    try:
        packet = mod.build_contract(h, d, GOOD_PINS)
    finally:
        mod.HANDOFFS["houdai-light-a-pin-discovery"] = old_h
        mod.HANDOFFS["tutorial2-descend-policy-native"] = old_d
    assert packet["houdai"]["enemy_id"] == 66
    assert packet["houdai"]["cargo"] == "light_a"
    assert packet["houdai"]["pool"] == "1_units_houdai_metal.txt"
    assert packet["descend"]["entry"] == "P2_CAVE_ENTRY_4"
    assert packet["descend"]["floor9_admitted"] is False
    assert packet["descend"]["gap"]
    assert packet["consumer"]["issue"] == 747
    assert packet["recovery"] == "8e9f4d22"
    assert all(v == "UNTESTED" for v in packet["gates"].values())


def test_missing_handoff_refused(tmp_path):
    d = write(tmp_path, "descend.json", DESCEND)
    try:
        mod.build_contract(tmp_path / "nope.json", d, GOOD_PINS)
    except mod.PinError as exc:
        assert "missing handoff" in str(exc)
    else:
        raise AssertionError("missing handoff must be refused")


def test_tampered_handoff_refused(tmp_path):
    h = write(tmp_path, "houdai.json", {**HOUDAI, "next_action": "changed"})
    d = write(tmp_path, "descend.json", DESCEND)
    try:
        mod.build_contract(h, d, GOOD_PINS)
    except mod.PinError as exc:
        assert "hash drift" in str(exc)
    else:
        raise AssertionError("tampered handoff must be refused")


def test_malformed_handoff_refused(tmp_path):
    h = write(tmp_path, "houdai.json", b"{not json")
    d = write(tmp_path, "descend.json", DESCEND)
    import copy
    old_h = dict(mod.HANDOFFS["houdai-light-a-pin-discovery"])
    mod.HANDOFFS["houdai-light-a-pin-discovery"]["sha256"] = hashlib.sha256(h.read_bytes()).hexdigest()
    try:
        mod.build_contract(h, d, GOOD_PINS)
    except mod.PinError as exc:
        assert "malformed handoff" in str(exc)
    else:
        raise AssertionError("malformed handoff must be refused")
    finally:
        mod.HANDOFFS["houdai-light-a-pin-discovery"] = old_h


def test_unknown_consumer_pin_refused(tmp_path):
    h = write(tmp_path, "houdai.json", HOUDAI)
    d = write(tmp_path, "descend.json", DESCEND)
    old_h = dict(mod.HANDOFFS["houdai-light-a-pin-discovery"])
    old_d = dict(mod.HANDOFFS["tutorial2-descend-policy-native"])
    mod.HANDOFFS["houdai-light-a-pin-discovery"]["sha256"] = hashlib.sha256(h.read_bytes()).hexdigest()
    mod.HANDOFFS["tutorial2-descend-policy-native"]["sha256"] = hashlib.sha256(d.read_bytes()).hexdigest()
    try:
        mod.build_contract(h, d, {"root": "deadbeef", "native": GOOD_PINS["native"]})
    except mod.PinError as exc:
        assert "unknown consumer root pin" in str(exc)
    else:
        raise AssertionError("unknown consumer pin must be refused")
    finally:
        mod.HANDOFFS["houdai-light-a-pin-discovery"] = old_h
        mod.HANDOFFS["tutorial2-descend-policy-native"] = old_d


def test_missing_consumer_pins_refused():
    try:
        mod.verify_consumer_pins(None)
    except mod.PinError as exc:
        assert "missing consumer pins" in str(exc)
    else:
        raise AssertionError("missing consumer pins must be refused")


def test_live_handoffs_bind_floor9():
    packet = mod.build_contract(
        CANON / mod.HANDOFFS["houdai-light-a-pin-discovery"]["path"],
        CANON / mod.HANDOFFS["tutorial2-descend-policy-native"]["path"],
        GOOD_PINS)
    assert packet["houdai"]["enemy_id"] == 66
    assert packet["houdai"]["cargo"] == "light_a"
    assert packet["descend"]["entry_floors"] == [3, 4, 5, 6, 7, 8]
    assert packet["descend"]["descend_terminal"] == 8
    assert packet["consumer"]["root"] == "94c0261fd81a245f357bac5e7f8414a45d608cf9"
    assert packet["consumer"]["native"] == "8c66708af77b9f44c8e7493ab626c7a19f0bee79"
