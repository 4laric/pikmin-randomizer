"""P1 floor-1 runtime-import contract for p2-cave-yakushima_4 (issue #161).

Lane shard-caves-yakushima-yakushima4-p1, generation 2. P1 floor-1 only: this
module consumes the done P0 decode and the #129/#132 provider contracts and
produces/validates the *native staging inputs and boot observation* for
yakushima_4 floor 1. It never invents placements: every row is derived from
the real decoded source or the pinned P0 audit packet.

It also fails closed with the exact missing prerequisite. The accepted
generator provider module (pc_p2_cave_generate) and the P0 adapter are NOT
present in the lane's pinned root/native worktrees, so a real floor-1 unit
staging boot cannot be produced on these pins; that is reported explicitly
rather than simulated.
"""
import hashlib
import json
import re
from pathlib import Path

ISSUE = 161
SOURCE_ID = "yakushima_4"
SCHEMA = "p2-cave-yakushima_4-p1/1"
FLOOR = 1
P0_SCHEMA = "p2-cave-yakushima_4-p0/1"
CAVE_ENTRY_VERSION = "P2_CAVE_ENTRY_1"
UNIT_POOL_FLOOR1 = "2_units_gw_l_conc.txt"

# Files that must be present in the private native worktree for a real
# floor-1 unit-staging boot on the accepted generator pins (#129).
PROVIDER_NATIVE_FILES = (
    "pc_port/pc_p2_cave_generate.h",
    "pc_port/pc_p2_cave_generate.cpp",
)
# P0 adapter that must be present in the private root worktree.
P0_ADAPTER = "experimental/content_lanes/p2-cave-yakushima_4.py"

_READY = re.compile(r'P2_CAVE_READY floor=(\d+) survivors=(\d+) health=(\S+)')
_NAV = re.compile(
    r'P2_CAVE_NAV seq=(\d+) floor=(\d+) captain=(\d+) x=(\S+) y=(\S+) z=(\S+) '
    r'.* inside=(\d) state=(\d+) walk=(\d+) safe=(\d+)')


class StagingError(Exception):
    """Raised when staging inputs or an observation violate the contract."""


def sha256_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_p0_packet(path):
    """Read the pinned P0 audit packet (read-only input)."""
    packet = json.loads(Path(path).read_text(encoding="utf-8"))
    if packet.get("schema") != P0_SCHEMA or packet.get("source_id") != SOURCE_ID:
        raise StagingError("unexpected P0 packet identity: " + str(path))
    floors = packet.get("floors")
    if not isinstance(floors, list) or not floors:
        raise StagingError("P0 packet has no floors")
    return packet


def floor1_plan(p0_packet):
    """Select the floor-1 staging rows from the real P0 decode.

    Returns pool, roster counts and treasure ids exactly as decoded; no
    weights are turned into spawn instances.
    """
    row = next((f for f in p0_packet["floors"]
                if f.get("first") == FLOOR and f.get("last") == FLOOR), None)
    if row is None:
        raise StagingError("P0 packet has no floor-1 entry")
    if row.get("unit_pool") != UNIT_POOL_FLOOR1:
        raise StagingError("floor-1 unit pool drift: " + str(row.get("unit_pool")))
    treasures = row.get("treasure_ids")
    if not isinstance(treasures, list):
        raise StagingError("floor-1 treasure ids missing")
    return {
        "floor": FLOOR,
        "unit_pool": row["unit_pool"],
        "enemy_definitions": int(row["enemies"]),
        "treasure_definitions": int(row["treasures"]),
        "gates": int(row.get("gates", 0)),
        "caps": int(row.get("caps", 0)),
        "treasure_ids": list(treasures),
    }


def provider_pins(root_worktree, native_worktree):
    """Report which provider prerequisites are actually present at the pins.

    No file is created; this is a read-only presence probe used to decide
    whether a real floor-1 unit-staging boot is possible.
    """
    root = Path(root_worktree)
    native = Path(native_worktree)
    missing = [f for f in PROVIDER_NATIVE_FILES if not (native / f).is_file()]
    adapter = (root / P0_ADAPTER).is_file()
    return {
        "native_provider_files_present": not missing,
        "missing_native_provider_files": missing,
        "p0_adapter_present": adapter,
        "native_unit_staging_consumer": False,
        "boot_possible": not missing,
    }


def cave_entry_line(floor, survivors, health, token):
    """Emit the real native entry manifest line consumed by pc_p2_cave.cpp.

    The native loader requires floor 1..2, 0 < health <= 1 and 1..100
    survivors; this validates those bounds instead of emitting a bad line.
    """
    if floor not in (1, 2):
        raise StagingError("entry floor must be 1 or 2")
    if not (0.0 < float(health) <= 1.0):
        raise StagingError("entry health must be in (0, 1]")
    if not (1 <= int(survivors) <= 100):
        raise StagingError("entry survivors must be 1..100")
    if not token or any(c.isspace() for c in token):
        raise StagingError("entry token must be a single nonempty word")
    return "%s %s %d %.9g %d" % (CAVE_ENTRY_VERSION, token, int(floor),
                                 float(health), int(survivors))


def staging_manifest(p0_path, root_worktree, native_worktree):
    """Assemble the floor-1 staging contract packet plus honest blockers."""
    packet = load_p0_packet(p0_path)
    plan = floor1_plan(packet)
    pins = provider_pins(root_worktree, native_worktree)
    blockers = []
    if not pins["p0_adapter_present"]:
        blockers.append("P0 adapter absent from the private root pin: " + P0_ADAPTER)
    if pins["missing_native_provider_files"]:
        blockers.append("accepted cave generator provider #129 absent from the private "
                        "native pin: " + ", ".join(pins["missing_native_provider_files"]))
    blockers.append("no native unit-staging consumer at the pin: pc_p2_cave.cpp "
                    "consumes a floor entry and emits P2_CAVE_NAV, but does not stage "
                    "per-floor generator units from the cave decode")
    return {
        "schema": SCHEMA,
        "issue": ISSUE,
        "source_id": SOURCE_ID,
        "source_sha256": packet["source_sha256"],
        "p0_packet_sha256": sha256_file(p0_path),
        "floor": plan,
        "entry_manifest": cave_entry_line(FLOOR, 20, 1.0, "yakushima4-floor1"),
        "provider_pins": pins,
        "blockers": blockers,
        "floor1_unit_staging_observed": False,
        "generated": False,
    }


def parse_observation(log_text):
    """Parse the real floor-1 boot markers emitted by pc_p2_cave.cpp."""
    events = []
    for number, raw in enumerate(log_text.splitlines(), 1):
        line = raw.strip()
        match = _READY.search(line)
        if match:
            events.append({"kind": "ready", "line": number,
                           "floor": int(match[1]), "survivors": int(match[2]),
                           "health": float(match[3])})
            continue
        match = _NAV.search(line)
        if match:
            events.append({"kind": "nav", "line": number,
                           "seq": int(match[1]), "floor": int(match[2]),
                           "captain": int(match[3]), "inside": int(match[7]),
                           "state": int(match[8]), "walk": int(match[9]),
                           "safe": int(match[10])})
    return events


def validate_observation(events):
    """Require a real floor-1 boot with a walking captain inside the anchor.

    Returns the observation summary or raises StagingError. Floor mismatch,
    a missing walk sample or a captain that never reaches the anchor is
    refused; unit staging is never inferred from nav lines.
    """
    ready = [e for e in events if e["kind"] == "ready"]
    if not ready:
        raise StagingError("no P2_CAVE_READY boot marker")
    if any(e["floor"] != FLOOR for e in ready):
        raise StagingError("boot marker is not floor 1")
    if not (1 <= ready[0]["survivors"] <= 100):
        raise StagingError("boot survivor count out of range")
    nav = [e for e in events if e["kind"] == "nav" and e["floor"] == FLOOR]
    if not nav:
        raise StagingError("no P2_CAVE_NAV floor-1 samples")
    walk_inside = [e for e in nav if e["inside"] == 1 and e["walk"] == 1]
    if not walk_inside:
        raise StagingError("captain never walked inside the floor-1 anchor")
    return {
        "floor": FLOOR,
        "survivors": ready[0]["survivors"],
        "nav_samples": len(nav),
        "walk_inside_samples": len(walk_inside),
        "collision_routes": "observed",
        "unit_staging": "NOT_OBSERVED",
    }


def main(argv=None):
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--p0", type=Path, required=True)
    parser.add_argument("--root-worktree", type=Path, required=True)
    parser.add_argument("--native-worktree", type=Path, required=True)
    parser.add_argument("--log", type=Path, default=None)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args(argv)
    packet = staging_manifest(args.p0, args.root_worktree, args.native_worktree)
    if args.log:
        packet["observation"] = validate_observation(
            parse_observation(args.log.read_text(encoding="utf-8", errors="replace")))
    text = json.dumps(packet, indent=2)
    if args.out:
        args.out.write_text(text, encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
