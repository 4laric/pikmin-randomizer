"""Floor-1 descend-chain handoff emitter for the #747 persistence round-trip (#817).

Reads the DONE floor-1 lane handoff (4cb92a8a) and the #757 descend-policy
handoff (3cacd9ac) read-only, verifies their SHA-256 pins, and emits the
machine-readable descend-chain packet: floor-1 origin entries, ENTRY policies,
hole/geyser anchor and the 20-squad baseline, with file:line citations.

Fail-closed: missing inputs, malformed JSON, hash mismatch or unknown pins
raise HandoffError. No engine, no builds, no launches, no ADMIT.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path

LANE = "tutorial2-floor1-descend-handoff"
ISSUE = 817
DOWNSTREAM_LANE = "p2-cave-tutorial_2-p1-later-floors"
DOWNSTREAM_ISSUE = 747

FLOOR1_HANDOFF_SHA256 = "4cb92a8a98972c14ef8e8d84a0f04727b2803c49e4254b605566657a5b6f2735"
POLICY_HANDOFF_SHA256 = "3cacd9ac4cb778db1147e37ad71d257cd797d37f23bc6154b6bdebe2739f0128"
FLOOR1_ROOT_PIN = "ebb643bb"
FLOOR1_LANE_HEAD = "9fd930894c40fb6b6e8b9b4889a2583f40448519"
POLICY_ROOT_HEAD = "1075e1ab65e211d17a8e683d921be24738ee9b60"
POLICY_NATIVE_HEAD = "eaabe9c816478b35b95e7fe8efe4de9a87096537"

CITATIONS = {
    "origin_adapter": "experimental/content_lanes/p2-cave-tutorial_2_p1.py@ebb643bb:219 (squad [[1,1]]*20), :224 (anchor hole), :72-94 (pool/tokens/treasure), :40 (source sha)",
    "origin_outputs": "handoff 4cb92a8a source_mapping (P2_CAVE_READY floor=1/20, squad_alive=20, pool 3_MAT_mid1_mid2_uzu1_snow.txt)",
    "entry_policy": "native/pc_port/pc_p2_cave.cpp@eaabe9c8:58 (P2_CAVE_ENTRY_4), :59/:64 (floors 3-8, 32-hex token), :69-72 (descend 1-7, 8 terminal)",
    "entry_registry": "experimental/pikmin2_tutorial2_descend_policy.py@1075e1ab:18-20 (ENTRY_4, FLOORS 3-8), :54-68 (descend flags, PASS)",
}

ORIGIN = {
    "stage": "tutorial_2 floor 1",
    "unit_pool": "3_MAT_mid1_mid2_uzu1_snow.txt",
    "enemies": {"YellowKochappy": 4, "YellowChappy": 2, "Demon": 2, "GasHiba": 2},
    "treasures": 2,
    "squad_baseline": 20,
    "anchor": "hole",
}

POLICY = {
    "entry_version": "P2_CAVE_ENTRY_4",
    "admitted_floors": [3, 4, 5, 6, 7, 8],
    "descend_floors": [1, 2, 3, 4, 5, 6, 7],
    "terminal_floor": 8,
    "token_contract": "32-hex",
}


class HandoffError(ValueError):
    """A handoff input violates the emitter contract."""


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_verified_handoff(path, expected_sha256):
    """Load a source handoff, failing closed on missing/malformed/pin mismatch."""
    if not path:
        raise HandoffError("handoff path required")
    candidate = Path(path)
    if not candidate.is_file():
        raise HandoffError("handoff missing: %s" % path)
    try:
        data = json.loads(candidate.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError) as exc:
        raise HandoffError("handoff malformed: %s (%s)" % (path, exc))
    if not isinstance(data, dict) or data.get("schema") != 1:
        raise HandoffError("handoff schema must be 1: %s" % path)
    actual = sha256_file(candidate)
    if actual != expected_sha256:
        raise HandoffError("unknown pin for %s: %s" % (path, actual))
    return data


def emit(floor1_handoff_path, policy_handoff_path):
    """Build the descend-chain packet from the two verified source handoffs."""
    floor1 = load_verified_handoff(floor1_handoff_path, FLOOR1_HANDOFF_SHA256)
    policy = load_verified_handoff(policy_handoff_path, POLICY_HANDOFF_SHA256)
    if floor1.get("lane") != "p2-cave-tutorial_2-p1-runtime":
        raise HandoffError("unexpected floor-1 producer: %r" % floor1.get("lane"))
    if policy.get("lane") != "tutorial2-descend-policy-native":
        raise HandoffError("unexpected policy producer: %r" % policy.get("lane"))
    packet = {
        "schema": 1,
        "lane": LANE,
        "issue": ISSUE,
        "downstream": {"lane": DOWNSTREAM_LANE, "issue": DOWNSTREAM_ISSUE,
                       "re_run_check": "persistence round-trip re-run over floors 1-8 with this packet pinned"},
        "sources": {
            "floor1": {"lane": floor1["lane"], "generation": floor1.get("generation"),
                       "root_head": FLOOR1_LANE_HEAD, "brief_pin": FLOOR1_ROOT_PIN,
                       "handoff_sha256": FLOOR1_HANDOFF_SHA256},
            "policy": {"lane": policy["lane"], "generation": policy.get("generation"),
                       "root_head": POLICY_ROOT_HEAD, "native_head": POLICY_NATIVE_HEAD,
                       "handoff_sha256": POLICY_HANDOFF_SHA256},
        },
        "origin": copy.deepcopy(ORIGIN),
        "policy": copy.deepcopy(POLICY),
        "citations": copy.deepcopy(CITATIONS),
        "gates": "all six UNTESTED",
        "admit": False,
    }
    packet["packet_sha256"] = hashlib.sha256(
        json.dumps(packet, sort_keys=True).encode("utf-8")).hexdigest()
    return packet


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--floor1-handoff", required=True)
    parser.add_argument("--policy-handoff", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    packet = emit(args.floor1_handoff, args.policy_handoff)
    out = Path(args.output)
    if out.suffix != ".json":
        raise HandoffError("packet output must be JSON")
    out.write_text(json.dumps(packet, indent=1) + "\n", encoding="utf-8")
    print("packet %s" % packet["packet_sha256"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
