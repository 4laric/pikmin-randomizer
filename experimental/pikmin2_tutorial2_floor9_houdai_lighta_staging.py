"""tutorial_2 floor-9 Houdai_light_a staging contract (issue #805).

Binds two DONE handoffs to the consumer closure for
p2-cave-tutorial_2-p1-later-floors (#747):
  * houdai-light-a-pin-discovery (#782, handoff sha 7fa6df04): Houdai_light_a
    is the compound token <enemy Houdai id 66> + <item light_a>, on floor 9,
    unit pool 1_units_houdai_metal.txt.
  * tutorial2-descend-policy-native (#757, handoff sha 3cacd9ac): entry
    P2_CAVE_ENTRY_4 admits floors 3-8; descend runs 1-7 with floor 8 terminal.

Root-only, read-only: it never edits producer/shared trees and stages nothing.
It fails closed (PinError) on any missing/unknown pin or handoff, and records
the one remaining engine prerequisite it cannot resolve (floor-9 descend
terminal extension) rather than inventing it. All six runtime gates UNTESTED.
"""
import hashlib
import json
import sys
from pathlib import Path

TOKEN = "Houdai_light_a"
FLOOR = 9
ENEMY = "Houdai"
ENEMY_ID = 66
CARGO = "light_a"
CARGO_ARCHIVE = "light_a.szs"
CARGO_BMD = "eq_flashlight.bmd"
POOL = "1_units_houdai_metal.txt"

RECOVERY = "8e9f4d22"

CONSUMER = {
    "lane": "p2-cave-tutorial_2-p1-later-floors",
    "issue": 747,
    "root": "94c0261fd81a245f357bac5e7f8414a45d608cf9",
    "native": "8c66708af77b9f44c8e7493ab626c7a19f0bee79",
    "checks": [
        "py -3.12 -m unittest tests.content_lanes.test_p2_cave_tutorial_2_p1_later_floors",
        ("py -3.12 experimental/content_lanes/p2-cave-tutorial_2_p1_later_floors.py "
         "--packet <tutorial_2-p0-packet.json> --output <private_dir> --floors 9 --runtime-inputs"),
        "guarded headed run of native/tools/p2_tutorial2_p1_later_floors_fixture.cpp floor 9 via scripts/run_pikmin2_fixture.py",
    ],
    "expected": ("floor-9 staging plan resolves the Houdai_light_a cargo (Houdai id 66 + "
                 "item light_a, pool 1_units_houdai_metal.txt) and the guarded floor-9 "
                 "boot reaches P2_TUTORIAL2_LATER_PASS; cargo no longer refused as unknown_cargo"),
}

HANDOFFS = {
    "houdai-light-a-pin-discovery": {
        "path": ("output/workflow/delivery/1d75823a6322eb01855feb48dd0004bd0ace44be6299af6602a46e0931b8e9e9/handoff.json"),
        "sha256": "7fa6df04dc8a28b380844582494aa4937818a6bebb32b32b3e6ab36c0cc993df",
        "issue": 782,
        "expect_lane": "houdai-light-a-pin-discovery",
    },
    "tutorial2-descend-policy-native": {
        "path": "output/workflow/autofill/prerequisites/tutorial2-descend-policy-native/out/handoff.json",
        "sha256": "3cacd9ac4cb778db1147e37ad71d257cd797d37f23bc6154b6bdebe2739f0128",
        "issue": 757,
        "expect_lane": "tutorial2-descend-policy-native",
    },
}

DESCEND_POLICY = {
    "entry": "P2_CAVE_ENTRY_4",
    "entry_floors": [3, 4, 5, 6, 7, 8],
    "descend_from": [1, 2, 3, 4, 5, 6, 7],
    "descend_terminal": 8,
    "callsite": "native/pc_port/pc_p2_cave.cpp",
    "handoff_lane": "tutorial2-descend-policy-native",
    "handoff_sha256": "3cacd9ac4cb778db1147e37ad71d257cd797d37f23bc6154b6bdebe2739f0128",
}

REMAINING_PREREQUISITE = (
    "Floor-9 descend admission: the accepted descend policy is terminal at floor 8 "
    "(entry floors 3-8, descend 1-7). Reaching floor 9 needs a bounded engine "
    "follow-on extending native/pc_port/pc_p2_cave.cpp entry/descend to floor 9 "
    "under the canonical lease build + #632 guard before the floor-9 guarded run "
    "can be observed. This contract does not stage or perform that change."
)


class PinError(Exception):
    """Fail-closed refusal: missing/unknown pin, tampered handoff or bad input."""


def repo_root_from_here() -> Path:
    here = Path(__file__).resolve()
    for parent in (here.parent,) + tuple(here.parents):
        if (parent / "output" / "workflow" / "registry.sqlite3").exists():
            return parent
    raise PinError("cannot locate canonical root from %s" % here)


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_handoff(path: Path, expected_sha: str) -> dict:
    if not isinstance(path, Path):
        path = Path(path)
    if not path.is_file():
        raise PinError("missing handoff refused: %s" % path)
    got = _digest(path)
    if got != expected_sha:
        raise PinError("handoff hash drift refused: %s (%s != %s)" % (path, got, expected_sha))
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PinError("malformed handoff refused: %s (%s)" % (path, exc))
    if not isinstance(data, dict):
        raise PinError("malformed handoff refused: not an object: %s" % path)
    return data


def _verify_handoff(name: str, data: dict, spec: dict) -> None:
    if data.get("lane") != spec["expect_lane"]:
        raise PinError("handoff lane mismatch for %s: %r" % (name, data.get("lane")))
    if data.get("issue") != spec["issue"]:
        raise PinError("handoff issue mismatch for %s: %r" % (name, data.get("issue")))
    if not isinstance(data.get("root"), dict) or not data["root"].get("head"):
        raise PinError("handoff %s missing root head pin" % name)


def classify_houdai_handoff(data: dict) -> dict:
    """Extract the floor-9 Houdai_light_a binding from the #782 handoff."""
    nxt = str(data.get("next_action", ""))
    text = nxt + " " + json.dumps(data.get("source_mapping", []))
    if "Houdai" not in text or "light_a" not in text:
        raise PinError("houdai handoff does not bind Houdai/light_a; refusing")
    if "floor 9" not in text and "floor-9" not in text:
        raise PinError("houdai handoff does not name floor 9; refusing")
    return {
        "token": TOKEN,
        "floor": FLOOR,
        "enemy": ENEMY,
        "enemy_id": ENEMY_ID,
        "cargo": CARGO,
        "archive": CARGO_ARCHIVE,
        "bmd": CARGO_BMD,
        "pool": POOL,
        "handoff_lane": "houdai-light-a-pin-discovery",
        "handoff_sha256": HANDOFFS["houdai-light-a-pin-discovery"]["sha256"],
    }


def classify_descend_handoff(data: dict) -> dict:
    """Extract the accepted descend policy and the floor-9 gap from #757."""
    text = json.dumps(data.get("source_mapping", [])) + " " + json.dumps(data.get("remaining_work", []))
    if "P2_CAVE_ENTRY_4" not in text or "descend" not in text:
        raise PinError("descend handoff does not carry the ENTRY_4 descend policy; refusing")
    policy = dict(DESCEND_POLICY)
    policy["floor9_admitted"] = FLOOR in policy["entry_floors"] or policy["descend_terminal"] >= FLOOR
    policy["gap"] = REMAINING_PREREQUISITE if not policy["floor9_admitted"] else ""
    return policy


def verify_consumer_pins(pins: dict) -> dict:
    if not isinstance(pins, dict):
        raise PinError("missing consumer pins refused")
    for key in ("root", "native"):
        if pins.get(key) != CONSUMER[key]:
            raise PinError("unknown consumer %s pin refused: %r (expected %s)"
                           % (key, pins.get(key), CONSUMER[key]))
    if pins.get("lane") not in (None, CONSUMER["lane"]):
        raise PinError("unknown consumer lane refused: %r" % pins.get("lane"))
    return dict(CONSUMER)


def build_contract(houdai_path, descend_path, consumer_pins) -> dict:
    h_spec = HANDOFFS["houdai-light-a-pin-discovery"]
    d_spec = HANDOFFS["tutorial2-descend-policy-native"]
    h_data = load_handoff(Path(houdai_path), h_spec["sha256"])
    d_data = load_handoff(Path(descend_path), d_spec["sha256"])
    _verify_handoff("houdai", h_data, h_spec)
    _verify_handoff("descend", d_data, d_spec)
    houdai = classify_houdai_handoff(h_data)
    descend = classify_descend_handoff(d_data)
    consumer = verify_consumer_pins(consumer_pins)
    return {
        "schema": "p2-tutorial2-floor9-houdai-lighta-staging/1",
        "issue": 805,
        "recovery": RECOVERY,
        "floor": FLOOR,
        "houdai": houdai,
        "descend": descend,
        "consumer": consumer,
        "handoffs": {k: {"path": v["path"], "sha256": v["sha256"]} for k, v in HANDOFFS.items()},
        "remaining_prerequisites": [REMAINING_PREREQUISITE],
        "gates": {g: "UNTESTED" for g in (
            "identity_spawn", "movement_animation", "attacks_receivers",
            "death_corpse", "transport_reward", "cleanup_reentry")},
        "evidence": {
            "houdai_handoff": h_spec["sha256"],
            "descend_handoff": d_spec["sha256"],
            "consumer_root": CONSUMER["root"],
            "consumer_native": CONSUMER["native"],
        },
    }


def main(argv=None) -> int:
    root = repo_root_from_here()
    args = list(sys.argv[1:] if argv is None else argv)
    houdai_path = Path(args[0]) if len(args) >= 1 else root / HANDOFFS["houdai-light-a-pin-discovery"]["path"]
    descend_path = Path(args[1]) if len(args) >= 2 else root / HANDOFFS["tutorial2-descend-policy-native"]["path"]
    pins = {"root": CONSUMER["root"], "native": CONSUMER["native"]}
    try:
        packet = build_contract(houdai_path, descend_path, pins)
    except PinError as exc:
        print("REFUSED: %s" % exc)
        return 1
    print(json.dumps(packet, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
