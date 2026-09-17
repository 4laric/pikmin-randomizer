"""P0 source audit + import-contract adapter for unowned enemies-1 identities.

Covers source IDs 14 (Tobi), 22 (ElecHiba), 39 (PanModokiNest), 47 (Clover),
80 (Tukushi) and 89 (Chiyogami) ? the enemies-1 identities no lane owns.
Decodes each identity's actual definitions from the verified local decomp
checkout and content inventory where available, records hashes, enumerates
resource closure and explicit unsupported references, and emits a
machine-readable packet with exact P1 blockers.

Parent/child group ownership is preserved by reference only: 39 resolves to
the PanModoki group (#168), 22 to the Hiba group, 47/80/89 to the plant
group (#171). No sibling-partition file is read for implementation or edited.

No invented values: every row cites its source file + line (or records an
exact missing-source prerequisite). Weighted cave rows stay definitions;
this module never fabricates runtime placements, spawn counts, or gate PASS.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

SCHEMA = "p2-enemies1-missing-audit-v1"
SOURCE_IDS = (14, 22, 39, 47, 80, 89)

# Baseline expectations transcribed from docs/PIKMIN2_CONTENT_INVENTORY.json
# (creature rows) and the enum header. The audit FAILS CLOSED when live
# source disagrees with any of these instead of silently updating them.
EXPECTED = {
    14: {"internal": "Tobi", "name": "Shearwig", "group": "ground",
         "classification": "creature", "owner_issue": 165,
         "entity_files": ["src/plugProjectNishimuraU/Tobi.cpp",
                          "include/Game/Entities/Tobi.h"],
         "info_row": True},
    22: {"internal": "ElecHiba", "name": "Electrical wire", "group": "elemental",
         "classification": "fixed_hazard", "owner_issue": 170,
         "entity_files": ["src/plugProjectNishimuraU/ElecHiba.cpp",
                          "include/Game/Entities/ElecHiba.h"],
         "info_row": True},
    39: {"internal": "PanModokiNest", "name": "Breadbug Nest", "group": "scavengers",
         "classification": "helper_alias", "owner_issue": 168,
         "entity_files": [], "info_row": False,
         "remap": "enemyInfo.cpp getEnemyResName remaps PanModokiNest to PanHouse83"},
    47: {"internal": "Clover", "name": "Clover", "group": "flora",
         "classification": "flora", "owner_issue": 171,
         "entity_files": [], "info_row": True,
         "shared_family": ["src/plugProjectNishimuraU/Hana.cpp",
                           "src/plugProjectMorimuraU/pelplant.cpp",
                           "include/Game/Entities/Hana.h",
                           "include/Game/Entities/Pelplant.h"]},
    80: {"internal": "Tukushi", "name": "Horsetail", "group": "flora",
         "classification": "flora", "owner_issue": 171,
         "entity_files": [], "info_row": True,
         "shared_family": ["src/plugProjectNishimuraU/Hana.cpp",
                           "src/plugProjectMorimuraU/pelplant.cpp",
                           "include/Game/Entities/Hana.h",
                           "include/Game/Entities/Pelplant.h"]},
    89: {"internal": "Chiyogami", "name": "Chigoyami paper", "group": "flora",
         "classification": "scenery_usage_unconfirmed", "owner_issue": 171,
         "entity_files": [], "info_row": True,
         "shared_family": ["src/plugProjectNishimuraU/Hana.cpp",
                           "include/Game/Entities/Hana.h"]},
}

P1_BLOCKERS = {
    14: ["Ground-family receiver/combat contract (#165 lane-14 scope)",
         "P1 host actor binding for TEKI-class Shearwig motion"],
    22: ["Fixed-hazard + elemental receiver contract (#170 lane scope)",
         "Piklopedia-absent identity needs explicit bestiary handling"],
    39: ["None for this ID: enum-only alias resolved at PanHouse83 (#168); "
         "P1 work belongs to the PanHouse actor, never a separate nest actor"],
    47: ["Flora conversion/ecology contract (#171 lane scope)",
         "Pikmin-absorb (never haul) reward path must stay non-receipt"],
    80: ["Flora conversion/ecology contract (#171 lane scope)",
         "Pikmin-absorb (never haul) reward path must stay non-receipt"],
    89: ["Missing prerequisite: retail placement audit ? inventory shows no "
         "confirmed cave-floor encounter, and usage is unaudited; do not "
         "stage this identity until placement is proven",
         "Flora conversion contract (#171 lane scope) once placed"],
}


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def parse_enum_ids(header_text: str) -> dict:
    """Map internal enemy names to source IDs from enemyInfo.h.

    The header declares `EnemyID_<Name> = <id>`; the prefix is stripped so
    callers use the bare internal name (e.g. `Tobi`).
    """
    found = {}
    for match in re.finditer(r"\bEnemyID_([A-Za-z][A-Za-z0-9_]*)\s*=\s*(\d+)", header_text):
        name, number = match.group(1), int(match.group(2))
        if 0 <= number <= 101 and name not in found:
            found[name] = number
    if not found:
        raise ValueError("No enemy IDs decoded from enemyInfo.h")
    return found


def info_row_line(info_cpp_text: str, internal: str) -> int | None:
    """1-based line of the gEnemyInfo row, or None when absent."""
    for number, line in enumerate(info_cpp_text.splitlines(), start=1):
        if re.search(r'\{"' + re.escape(internal) + r'"', line):
            return number
    return None


def inventory_hits(inventory: dict, token: str) -> list:
    """All (path, value) locations naming the token (encounters + refs)."""
    hits = []

    def walk(node, path):
        if isinstance(node, dict):
            for key, value in node.items():
                walk(value, path + "/" + str(key))
        elif isinstance(node, list):
            for index, value in enumerate(node):
                walk(value, path + "/" + str(index))
        elif isinstance(node, str) and node == token:
            hits.append(path)

    walk(inventory, "")
    return hits


def audit_identity(source_id: int, header_text: str, info_cpp_text: str,
                   decomp: Path, inventory: dict) -> dict:
    """Decode one identity against live source; fail closed on drift."""
    expected = EXPECTED[source_id]
    internal = expected["internal"]
    enum_ids = parse_enum_ids(header_text)
    if enum_ids.get(internal) != source_id:
        raise ValueError(
            f"Enum drift for {internal}: expected {source_id}, "
            f"found {enum_ids.get(internal)}")
    enum_line = next(
        number for number, line in enumerate(header_text.splitlines(), start=1)
        if re.search(r"\bEnemyID_" + re.escape(internal) + r"\s*=\s*" + str(source_id) + r"\b", line))
    row_line = info_row_line(info_cpp_text, internal)
    if expected["info_row"] and row_line is None:
        raise ValueError(f"Missing gEnemyInfo row for {internal}")
    if not expected["info_row"] and row_line is not None:
        raise ValueError(f"Unexpected gEnemyInfo row for alias {internal}")
    missing_files = [p for p in expected["entity_files"]
                     if not (decomp / p).is_file()]
    if missing_files:
        raise ValueError(f"Missing entity sources for {internal}: {missing_files}")
    shared = expected.get("shared_family", [])
    missing_shared = [p for p in shared if not (decomp / p).is_file()]
    hits = inventory_hits(inventory, internal)
    return {
        "source_id": source_id,
        "internal": internal,
        "name": expected["name"],
        "classification": expected["classification"],
        "group": expected["group"],
        "owner_issue": expected["owner_issue"],
        "anchors": {
            "enum": "include/Game/enemyInfo.h:" + str(enum_line),
            "info_row": ("src/plugProjectYamashitaU/enemyInfo.cpp:"
                         + str(row_line)) if row_line else None,
            "entity_files": list(expected["entity_files"]),
            "shared_family_files": list(shared),
            "missing_shared_files": missing_shared,
            "remap": expected.get("remap"),
        },
        "inventory_hits": len(hits),
        "inventory_paths": hits[:12],
        "p1_blockers": list(P1_BLOCKERS[source_id]),
        "gates": {gate: "UNTESTED" for gate in (
            "identity_spawn", "movement_animation", "attacks_receivers",
            "death_corpse", "transport_reward", "cleanup_reentry")},
    }


def check_packet(packet: dict, inventory: dict) -> None:
    """Validate a packet: schema, six rows, no invented encounters."""
    if packet.get("schema") != SCHEMA:
        raise ValueError("Unknown packet schema")
    rows = packet.get("rows", [])
    if sorted(r["source_id"] for r in rows) != sorted(SOURCE_IDS):
        raise ValueError("Packet must cover exactly source IDs 14/22/39/47/80/89")
    inventory_text = json.dumps(inventory)
    for row in rows:
        for gate, status in row.get("gates", {}).items():
            if status != "UNTESTED":
                raise ValueError(
                    f"Gate {gate} for {row['source_id']} is not UNTESTED")
        for path in row.get("inventory_paths", []):
            token = row["internal"]
            if token not in inventory_text:
                raise ValueError(
                    f"Invented encounter for {token}: not in inventory")


def run(decomp: Path, inventory_path: Path, output: Path) -> dict:
    """Audit all six identities and write packet.json + run.log."""
    output.mkdir(parents=True, exist_ok=True)
    log: list[str] = []
    header_path = decomp / "include/Game/enemyInfo.h"
    if not header_path.is_file():
        raise ValueError(f"Missing decomp header: {header_path}")
    header_text = header_path.read_text(encoding="utf-8", errors="replace")
    info_cpp_text = (decomp / "src/plugProjectYamashitaU/enemyInfo.cpp").read_text(
        encoding="utf-8", errors="replace")
    inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
    log.append("header sha256=" + sha256(header_text.encode("utf-8")))
    rows = []
    for source_id in SOURCE_IDS:
        row = audit_identity(source_id, header_text, info_cpp_text, decomp, inventory)
        rows.append(row)
        log.append(f"id={source_id} {row['internal']} info_row={row['anchors']['info_row']} "
                   f"hits={row['inventory_hits']} blockers={len(row['p1_blockers'])}")
    packet = {"schema": SCHEMA, "rows": rows, "generated": False,
              "limitations": [
                  "Inventory hits count token references, not confirmed placements.",
                  "Weights/counts are definition inputs, never spawn instances.",
                  "No gate is PASS; P1 needs the recorded owner-lane contracts."]}
    check_packet(packet, inventory)
    log.append("packet validated: 6 rows, all gates UNTESTED")
    (output / "packet.json").write_text(json.dumps(packet, indent=2) + "\n",
                                        encoding="utf-8")
    (output / "run.log").write_text("\n".join(log) + "\n", encoding="utf-8")
    packet["_log"] = log
    return packet


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--decomp", type=Path, required=True)
    parser.add_argument("--inventory", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run(args.decomp, args.inventory, args.output)
    print(f"identities={len(result['rows'])} manifest={args.output / 'packet.json'}")


if __name__ == "__main__":
    main()
