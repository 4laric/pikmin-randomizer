"""Audit the canonical P2 enemy roster and eligibility ledger (lane 02, #438).

Read-only. Verifies the committed snapshot against the live decompilation when
available, cross-references the content inventory and engine native modules, and
writes a coverage/gap report.

    py -3.12 scripts/audit_pikmin2_roster.py
    py -3.12 scripts/audit_pikmin2_roster.py --source native/pikmin2-research --output output/lane02/roster-audit.json
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from experimental.pikmin2_enemy_roster import (  # noqa: E402
    GATE_IDS,
    ROSTER_PATH,
    entries_from_payload,
    load_roster,
    parse_enum_header,
    parse_info_table,
    summarize,
    validate_roster,
)

DEFAULT_SOURCE = ROOT / "native/pikmin2-research"
INVENTORY = ROOT / "docs/PIKMIN2_CONTENT_INVENTORY.json"
ENGINE_PORT = ROOT / "engine/pc_port"


def inventory_identities(path: Path) -> set[str]:
    if not path.is_file():
        return set()
    payload = json.loads(path.read_text(encoding="utf-8"))
    names: set[str] = set()
    for cave in payload.get("story_caves", []):
        for floor in cave.get("floors", []):
            names.update(floor.get("enemy_ids", []))
    return names


def categorize_inventory_tokens(tokens: set[str], enum_names: set[str]) -> dict:
    """Split inventory ``enemy_ids`` tokens into exact IDs, generator variants,
    treasure-carrier aliases (``Enum_suffix``) and unrecognized tokens.

    The inventory's ``enemy_ids`` field also carries treasure-carrier and
    ``$N``-prefixed generator tokens, so an exact-name-only comparison
    overstates the gap.
    """
    lowered = {name.lower(): name for name in enum_names}
    exact, variant, carrier, unknown = set(), set(), set(), set()
    carrier_bases: dict[str, set[str]] = {}
    for token in tokens:
        if token in enum_names:
            exact.add(token)
            continue
        stripped = token.lstrip("$")
        while stripped and stripped[0].isdigit():
            stripped = stripped[1:]
        if stripped.lower() in lowered:
            variant.add(lowered[stripped.lower()])
            continue
        base = stripped.split("_", 1)[0]
        if base.lower() in lowered:
            carrier.add(token)
            carrier_bases.setdefault(lowered[base.lower()], set()).add(token)
            continue
        unknown.add(token)
    return {
        "exact": sorted(exact),
        "generator_variants": sorted(variant),
        "treasure_carriers": sorted(carrier),
        "carrier_bases": {k: sorted(v) for k, v in sorted(carrier_bases.items())},
        "unknown": sorted(unknown),
    }


def native_modules(port_dir: Path) -> set[str]:
    if not port_dir.is_dir():
        return set()
    return {path.stem for path in port_dir.glob("pc_p2_*.cpp")}


def verify_source_parity(roster, source: Path) -> list[str]:
    h_path = source / "include/Game/enemyInfo.h"
    cpp_path = source / "src/plugProjectYamashitaU/enemyInfo.cpp"
    if not h_path.is_file() or not cpp_path.is_file():
        return [f"source checkout not found at {source}"]
    enum_records = parse_enum_header(h_path.read_text(encoding="utf-8"))
    table_records = parse_info_table(cpp_path.read_text(encoding="utf-8"))
    snapshot_ids = {entry.source_id: entry.enum_name for entry in roster}
    problems: list[str] = []
    for enum_name, record in enum_records.items():
        expected = record["source_id"]
        if expected < 0:
            continue
        actual = snapshot_ids.get(expected)
        if actual != enum_name:
            problems.append(f"source {enum_name}={expected} vs snapshot {expected}={actual}")
    for name in table_records:
        if name not in {entry.enum_name for entry in roster}:
            problems.append(f"source table has {name} missing from snapshot")
    return problems


def build_report(roster, inventory: set[str], modules: set[str], parity: list[str]) -> dict:
    summary = summarize(roster)
    enum_names = {e.enum_name for e in roster}
    categories = categorize_inventory_tokens(inventory, enum_names)
    enemies_not_in_inventory = sorted(
        e.enum_name for e in roster
        if e.is_randomizable_candidate and e.enum_name not in categories["exact"]
        and e.enum_name not in categories["generator_variants"]
    )
    unclassified = [e.enum_name for e in roster if not e.classification]
    return {
        "schema": "p2-enemy-roster-audit-1",
        "roster_path": str(ROSTER_PATH.relative_to(ROOT)),
        "summary": summary,
        "gate_ids": list(GATE_IDS),
        "eligibility": {
            e.enum_name: {"classification": e.classification, "eligibility": e.eligibility,
                          "gates": e.gates, "native_module": e.native_module}
            for e in roster if e.eligibility != "denied"
        },
        "native_modules_available": sorted(modules),
        "coverage": {
            "inventory_identities": len(inventory),
            "inventory_exact_identities": len(categories["exact"]),
            "inventory_generator_variants": categories["generator_variants"],
            "inventory_treasure_carriers": categories["carrier_bases"],
            "inventory_unrecognized_tokens": categories["unknown"],
            "randomizable_identities_absent_from_inventory": enemies_not_in_inventory,
            "identities_without_info_table_row": sorted(e.enum_name for e in roster if not e.in_info_table),
            "unclassified_identities": unclassified,
        },
        "source_parity_problems": parity,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE,
                        help="pikmin2-research checkout; pass an empty path to skip parity")
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--strict", action="store_true",
                        help="fail on source parity problems or unclassified identities")
    args = parser.parse_args()

    roster = load_roster()
    validate_roster(roster)
    parity = verify_source_parity(roster, args.source) if args.source else []
    report = build_report(roster, inventory_identities(INVENTORY), native_modules(ENGINE_PORT), parity)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    summary = report["summary"]
    print(f"roster identities: {summary['entry_count']}  candidates: {summary['randomizable_candidates']}")
    print("classifications:", summary["classification_counts"])
    print("roles:", summary.get("role_counts", {}))
    print(f"admitted seedable identities: {summary.get('admitted_count', 0)} "
          f"{summary.get('admitted_ids', [])}")
    coverage = report["coverage"]
    print(f"inventory identities: {coverage['inventory_identities']} "
          f"(exact {coverage['inventory_exact_identities']}, "
          f"variants {len(coverage['inventory_generator_variants'])}, "
          f"carriers {sum(len(v) for v in coverage['inventory_treasure_carriers'].values())}, "
          f"unrecognized {len(coverage['inventory_unrecognized_tokens'])})")
    print(f"identities without info-table row: {len(coverage['identities_without_info_table_row'])}")
    print(f"source parity problems: {len(parity)}")
    for problem in parity[:10]:
        print("  -", problem)

    if args.strict and (parity or coverage["unclassified_identities"]):
        print("STRICT FAIL", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
