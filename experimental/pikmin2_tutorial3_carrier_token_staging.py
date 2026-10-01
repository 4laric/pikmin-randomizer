"""tutorial_3 carrier-token staging contract for floors 3/5/8 (#826).

Root-only staging contract binding two DONE handoffs to the downstream
consumer p2-cave-tutorial_3-p1-later-floors (#812, blocked gen2) closure:

- Handoff A (read-only): p2-cave-tutorial_3-p1-source-recovery (#153, done
  gen2, root 5c12c69916ae2cc6bb0084e4848ce5f9e9cb7c3f) pins the
  tutorial_3.txt source bytes (offset 770672856, size 9701,
  sha256 adcc816653957fbf00919c313291142cb110b5479c7790d997399e380c9b1abb).
- Handoff B (read-only): provider-placement-carrier-landing (#657, done gen2,
  root 4a4e367b420fc3f3bca1e5dff4d464e78db9db61) pins carrier-landing
  checks. Its slot-99 Waterwraith scope is recorded read-only and MUST NOT be
  reused as tutorial_3 carrier semantics.

Consumer: p2-cave-tutorial_3-p1-later-floors (#812, blocked gen2) pins root
base fdd558123223f94d706b9a00973037553e864756 head
2a97c0682c6bead1990f8f4cedb469623da18e06, native base
a95040b66a0ffc9cdbfc649502569a29e66949a7 head
a6a63f0ddd18f3ab9d08a7e6110c464766b9bd92. Its adapter stages floors 2/4/6/7
clean and refuses floors 3/5/8 fail-closed on non-exact carrier tokens.
Recovery request 9002486c30bb9ab1e6dd030aa8cb82d317750911844ed2aca2c84d35e0d08372
is recorded in the emitted packet.

This module invents no placements, no carrier semantics, no engine behavior.
Floors 3/5/8 stage as BLOCKED carrier-token rows awaiting an explicit
follow-on carrier implementation. Any missing/unknown pin or handoff raises
fail-closed (FileNotFoundError/ValueError). No native edits, no builds, no
launches, no ADMIT. All six runtime gates UNTESTED.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

LANE = "tutorial3-carrier-token-staging"
ISSUE = 826
CAVE_ID = "tutorial_3"
SCHEMA = 1
PACKET_SCHEMA = "p2-cave-import-p0-1"
EXPECTED_FLOOR_COUNT = 8
CARRIER_FLOORS = (3, 5, 8)
EXACT_FLOORS = (2, 4, 6, 7)

SOURCE_PATH = "user/Mukki/mapunits/caveinfo/tutorial_3.txt"
SOURCE_OFFSET = 770672856
SOURCE_SIZE = 9701
SOURCE_SHA256 = "adcc816653957fbf00919c313291142cb110b5479c7790d997399e380c9b1abb"

HANDOFF_SOURCE_RECOVERY = {
    "lane": "p2-cave-tutorial_3-p1-source-recovery",
    "issue": 153,
    "generation": 2,
    "state": "done",
    "root": "5c12c69916ae2cc6bb0084e4848ce5f9e9cb7c3f",
}

HANDOFF_CARRIER_LANDING = {
    "lane": "provider-placement-carrier-landing",
    "issue": 657,
    "generation": 2,
    "state": "done",
    "root": "4a4e367b420fc3f3bca1e5dff4d464e78db9db61",
    "catalog_pin": "7a21ce6af09dcc6d4807a7f09cbec333f1e6b088",
    "catalog_blob": "96ddeb89b11e678de1365856db3f5317cc6e5258",
    "packaging_pin": "04d58d33af3336ba5190d49ca4856a7d96c4b0f2",
    "packaging_blob": "7f45258825a3dfa0cb7f8dc2cc9b53f91627528e",
    "native_pin_recorded_only": "e2aa476ec7795cdbec69083d3d6e6a9329c4743b",
    "scope": "slot-99 Waterwraith only; not reusable for tutorial_3 carriers",
}

CONSUMER = {
    "lane": "p2-cave-tutorial_3-p1-later-floors",
    "issue": 812,
    "generation": 2,
    "state": "blocked",
    "root_base": "fdd558123223f94d706b9a00973037553e864756",
    "root_head": "2a97c0682c6bead1990f8f4cedb469623da18e06",
    "native_base": "a95040b66a0ffc9cdbfc649502569a29e66949a7",
    "native_head": "a6a63f0ddd18f3ab9d08a7e6110c464766b9bd92",
    "adapter": "experimental/content_lanes/p2-cave-tutorial_3_p1_later_floors.py",
    "adapter_tests": "tests/content_lanes/test_p2_cave_tutorial_3_p1_later_floors.py",
    "adapter_doc": "docs/content_lanes/p2-cave-tutorial_3-p1-later-floors.md",
    "fixture": "native/tools/p2_tutorial3_p1_later_floors_fixture.cpp",
}

RECOVERY_REQUEST = "9002486c30bb9ab1e6dd030aa8cb82d317750911844ed2aca2c84d35e0d08372"

KNOWN_PINS = {
    "source_sha256": SOURCE_SHA256,
    "source_root": HANDOFF_SOURCE_RECOVERY["root"],
    "carrier_root": HANDOFF_CARRIER_LANDING["root"],
    "consumer_root_head": CONSUMER["root_head"],
    "consumer_native_head": CONSUMER["native_head"],
}


class StagingRejected(ValueError):
    """Missing or unknown pin/handoff/row; never a placement."""


def check_pins(pins=None):
    """Fail closed unless every named pin exactly matches the known pins."""
    pins = dict(KNOWN_PINS if pins is None else pins)
    missing = [k for k in KNOWN_PINS if k not in pins]
    if missing:
        raise StagingRejected("missing pins: " + ", ".join(sorted(missing)))
    divergent = [k for k in KNOWN_PINS if pins.get(k) != KNOWN_PINS[k]]
    if divergent:
        raise StagingRejected("unknown pins: " + ", ".join(sorted(divergent)))
    extra = [k for k in pins if k not in KNOWN_PINS]
    if extra:
        raise StagingRejected("unknown pins: " + ", ".join(sorted(extra)))
    return dict(pins)


def check_handoffs(handoffs=None):
    """Fail closed unless both done handoffs match lane/issue/root/state."""
    expected = {
        HANDOFF_SOURCE_RECOVERY["lane"]: HANDOFF_SOURCE_RECOVERY,
        HANDOFF_CARRIER_LANDING["lane"]: HANDOFF_CARRIER_LANDING,
    }
    if handoffs is None:
        return {k: dict(v) for k, v in expected.items()}
    if not isinstance(handoffs, dict):
        raise StagingRejected("handoffs must be a mapping")
    missing = [k for k in expected if k not in handoffs]
    if missing:
        raise StagingRejected("missing handoffs: " + ", ".join(sorted(missing)))
    for key, want in expected.items():
        got = handoffs.get(key)
        if not isinstance(got, dict):
            raise StagingRejected("handoff %s must be a mapping" % key)
        for field in ("lane", "issue", "root", "state", "generation"):
            if got.get(field) != want[field]:
                raise StagingRejected(
                    "handoff %s field %s mismatch (unknown handoff)" % (key, field)
                )
    return {k: dict(v) for k, v in handoffs.items()}


def load_packet(path):
    """Load and validate the P0 packet envelope (read-only, fail-closed)."""
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError("Missing P0 packet: " + str(path))
    packet = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(packet, dict) or packet.get("schema") != PACKET_SCHEMA:
        raise StagingRejected("P0 packet schema must be %r" % PACKET_SCHEMA)
    if packet.get("cave") != CAVE_ID:
        raise StagingRejected("P0 packet cave must be %r" % CAVE_ID)
    if packet.get("source_sha256") != SOURCE_SHA256:
        raise StagingRejected("P0 packet source_sha256 must match the pinned locator hash")
    floors = packet.get("floors")
    if not isinstance(floors, list) or not floors:
        raise StagingRejected("P0 packet must carry a non-empty floors list")
    numbers = sorted({int(f["first_floor"]) for f in floors})
    if numbers != list(range(1, EXPECTED_FLOOR_COUNT + 1)):
        raise StagingRejected(
            "P0 packet floor coverage is %s, expected 1..%d" % (numbers, EXPECTED_FLOOR_COUNT)
        )
    return packet


def floor_definition(packet, number):
    matches = [
        f for f in packet["floors"]
        if int(f["first_floor"]) <= number <= int(f["last_floor"])
    ]
    if len(matches) != 1:
        raise StagingRejected("floor %d must be covered by exactly one definition" % number)
    return matches[0]


def is_carrier_source(source):
    """A definition row is a carrier token unless exactly exact."""
    if not isinstance(source, dict):
        raise StagingRejected("malformed definition row: %r" % (source,))
    if source.get("carried_treasure") is not None:
        return True
    try:
        drop = int(source.get("drop_mode", 0))
    except (TypeError, ValueError):
        raise StagingRejected("malformed drop_mode: %r" % (source,))
    return drop != 0


def carrier_rows(packet, number):
    """Return the raw carrier-token source rows for one floor (no semantics)."""
    floor = floor_definition(packet, number)
    rows = floor.get("enemies") or []
    if not rows:
        raise StagingRejected("floor %d has no enemy definitions" % number)
    out = []
    for row in rows:
        source = row.get("source") if isinstance(row, dict) else None
        if not isinstance(source, dict) or not source.get("enemy_id"):
            raise StagingRejected("floor %d carries a malformed row" % number)
        if is_carrier_source(source):
            out.append(
                {
                    "enemy_id": str(source.get("enemy_id")),
                    "source_token": str(source.get("source_token")),
                    "carried_treasure": source.get("carried_treasure"),
                    "drop_mode": source.get("drop_mode", 0),
                }
            )
    return out


def stage_floor(packet, number, pins=None, handoffs=None):
    """Stage one floor fail-closed: exact floors pass through, carrier floors block."""
    check_pins(pins)
    check_handoffs(handoffs)
    if number == 1:
        raise StagingRejected("floor 1 owned by the DONE floor-1 lane; refused here")
    if number in EXACT_FLOORS:
        floor = floor_definition(packet, number)
        rows = carrier_rows(packet, number)
        if rows:
            raise StagingRejected(
                "floor %d expected exact but carries carrier tokens: %r" % (number, rows)
            )
        pool = (floor.get("parameters") or {}).get("f008")
        if not isinstance(pool, str) or not pool:
            raise StagingRejected("floor %d has no unit pool" % number)
        return {
            "floor": number,
            "status": "EXACT",
            "unit_pool": pool,
            "carrier_rows": [],
        }
    if number in CARRIER_FLOORS:
        rows = carrier_rows(packet, number)
        if not rows:
            raise StagingRejected(
                "floor %d expected carrier tokens but carries none; refusing to invent" % number
            )
        floor = floor_definition(packet, number)
        pool = (floor.get("parameters") or {}).get("f008")
        if not isinstance(pool, str) or not pool:
            raise StagingRejected("floor %d has no unit pool" % number)
        return {
            "floor": number,
            "status": "BLOCKED_CARRIER_TOKEN",
            "unit_pool": pool,
            "carrier_rows": rows,
            "reason": (
                "non-exact carrier token (carried_treasure/drop_mode); "
                "no carrier semantics invented; awaits explicit follow-on"
            ),
        }
    raise StagingRejected("floor %r outside tutorial_3 scope 1..8" % (number,))


def consumer_check():
    """Concrete re-run commands the #812 consumer uses to close floors 3/5/8."""
    return {
        "consumer": CONSUMER["lane"],
        "issue": CONSUMER["issue"],
        "recovery_request": RECOVERY_REQUEST,
        "commands": [
            "py -3.12 -m unittest tests.content_lanes.test_p2_cave_tutorial_3_p1_later_floors -v",
            "py -3.12 experimental/content_lanes/p2-cave-tutorial_3_p1_later_floors.py"
            " --packet <p0-packet.json> --output <out> --floors 2,4,6,7",
            "py -3.12 experimental/content_lanes/p2-cave-tutorial_3_p1_later_floors.py"
            " --packet <p0-packet.json> --output <out> --floors 3,5,8"
            "  # must exit nonzero with 'non-exact token' until this staging contract lands",
            "py -3.12 experimental/pikmin2_tutorial3_carrier_token_staging.py"
            " --packet <p0-packet.json> --output <out> --floors 3,5,8",
        ],
        "expected": (
            "floors 2/4/6/7 stage EXACT; floors 3/5/8 stage BLOCKED_CARRIER_TOKEN "
            "with explicit carrier rows; no invented placements"
        ),
    }


def build_packet(packet_path, pins=None, handoffs=None):
    """Build the hashed staging packet binding both handoffs to the #812 closure."""
    pins = check_pins(pins)
    handoffs = check_handoffs(handoffs)
    packet = load_packet(packet_path)
    floors = {}
    for number in CARRIER_FLOORS:
        staged = stage_floor(packet, number, pins=pins, handoffs=handoffs)
        floors[str(number)] = staged
    body = {
        "schema": SCHEMA,
        "lane": LANE,
        "issue": ISSUE,
        "cave_id": CAVE_ID,
        "packet_schema": PACKET_SCHEMA,
        "source": {
            "path": SOURCE_PATH,
            "offset": SOURCE_OFFSET,
            "size": SOURCE_SIZE,
            "sha256": SOURCE_SHA256,
        },
        "handoffs": handoffs,
        "pins": pins,
        "floors": floors,
        "downstream_consumer": dict(CONSUMER),
        "recovery_request": RECOVERY_REQUEST,
        "consumer_check": consumer_check(),
        "limitations": [
            "Staging only: per-floor carrier rows are recorded, never resolved.",
            "No placements, topology, transport, reward or save semantics invented.",
            "Floors 3/5/8 remain BLOCKED for gameplay until an explicit carrier "
            "implementation lands and the #812 consumer re-runs its real commands.",
            "All six runtime gates UNTESTED; no gameplay claim.",
        ],
    }
    digest = hashlib.sha256(json.dumps(body, sort_keys=True).encode("utf-8")).hexdigest()
    return {"packet": body, "packet_sha256": digest}


def sidecar_text(staged_packet):
    body = staged_packet["packet"]
    lines = [
        "P2_TUTORIAL3_CARRIER_STAGING_1",
        "lane %s issue #%d" % (body["lane"], body["issue"]),
        "cave %s source_sha256 %s" % (body["cave_id"], body["source"]["sha256"]),
        "handoff %s root %s" % (
            HANDOFF_SOURCE_RECOVERY["lane"], HANDOFF_SOURCE_RECOVERY["root"]),
        "handoff %s root %s" % (
            HANDOFF_CARRIER_LANDING["lane"], HANDOFF_CARRIER_LANDING["root"]),
        "consumer %s root %s native %s" % (
            CONSUMER["lane"], CONSUMER["root_head"], CONSUMER["native_head"]),
        "recovery %s" % RECOVERY_REQUEST,
    ]
    for number in sorted(int(k) for k in body["floors"]):
        staged = body["floors"][str(number)]
        lines.append("floor %d %s rows=%d pool=%s" % (
            number, staged["status"], len(staged["carrier_rows"]), staged["unit_pool"]))
        for row in staged["carrier_rows"]:
            lines.append("  carrier %s token=%s treasure=%r drop=%r" % (
                row["enemy_id"], row["source_token"],
                row["carried_treasure"], row["drop_mode"]))
    lines.append("packet_sha256 " + staged_packet["packet_sha256"])
    lines.append("gates UNTESTEDx6; no gameplay claim")
    lines.append("end")
    return "\n".join(lines) + "\n"


def write_staging(packet_path, output_dir, floors=CARRIER_FLOORS, pins=None, handoffs=None):
    staged = build_packet(packet_path, pins=pins, handoffs=handoffs)
    selected = {str(n): staged["packet"]["floors"][str(n)] for n in floors}
    if set(selected) != {str(n) for n in floors}:
        raise StagingRejected("requested floors unavailable")
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "p2-tutorial3-carrier-token-staging.json"
    txt_path = output_dir / "p2-tutorial3-carrier-token-staging.txt"
    json_path.write_text(json.dumps(staged["packet"], indent=2) + "\n", encoding="utf-8")
    text = sidecar_text(staged)
    txt_path.write_text(text, encoding="utf-8")
    return {
        "json": str(json_path),
        "sidecar": str(txt_path),
        "packet_sha256": staged["packet_sha256"],
        "sidecar_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packet", required=True, help="P0 packet JSON path")
    parser.add_argument("--output", required=True, help="output directory")
    parser.add_argument("--floors", default=",".join(str(n) for n in CARRIER_FLOORS))
    args = parser.parse_args(argv)
    numbers = tuple(int(v) for v in args.floors.split(",") if v.strip())
    if set(numbers) != set(CARRIER_FLOORS):
        raise StagingRejected(
            "this contract stages exactly floors %s; got %s" % (CARRIER_FLOORS, numbers))
    result = write_staging(args.packet, args.output, floors=numbers)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
