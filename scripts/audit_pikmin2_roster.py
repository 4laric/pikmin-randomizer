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
    admission_contract,
    candidate_review,
    entries_from_payload,
    inventory_encounters,
    load_roster,
    parse_enum_header,
    parse_info_table,
    summarize,
    validate_roster,
    write_admission,
)

DEFAULT_SOURCE = ROOT / "native/pikmin2-research"
INVENTORY = ROOT / "docs/PIKMIN2_CONTENT_INVENTORY.json"
ENGINE_PORT = ROOT / "engine/pc_port"

# Module names used in the evidence overlay that do not correspond to a single
# .cpp translation unit (an identity FSM often lives inside a family vehicle).
MODULE_ALIASES = {
    "pc_p2_snow": "pc_p2_enemy",
}

# Native pc_p2_*.cpp stems that are NOT a single-identity enemy module: provider
# seams, Pikmin-species modules, projectiles/hazard primitives, cross-family
# display vehicles and family sub-modules. An identity is covered by the row
# whose native_module resolves (via MODULE_ALIASES) to the family's head stem;
# every other stem is allowlisted here so "a native module lacks a row" only
# fires for a real identity module.
SHARED_MODULES = frozenset("""\
pc_p2_batch3 pc_p2_bigtreasure_animclock pc_p2_bigtreasure_attacks pc_p2_bigtreasure_elements
pc_p2_bigtreasure_fsm pc_p2_bigtreasure_fsmhost pc_p2_bigtreasure_host pc_p2_bigtreasure_map_trace
pc_p2_bigtreasure_motion pc_p2_bigtreasure_ordinary pc_p2_bigtreasure_save pc_p2_bigtreasure_visual
pc_p2_bombsarai_arena pc_p2_bombsarai_blast pc_p2_bombsarai_bomb pc_p2_bombsarai_hover
pc_p2_bombsarai_map_trace pc_p2_bombsarai_terrain pc_p2_breadbug_visual pc_p2_bulbmin pc_p2_cannon_stone
pc_p2_captain pc_p2_cave pc_p2_color_binding pc_p2_dangomushi_hazard pc_p2_demon_bridge
pc_p2_demon_drop_state pc_p2_demon_escape_state pc_p2_economy pc_p2_egg_hazard pc_p2_fuefuki_motion
pc_p2_giant_breadbug_visual pc_p2_groink_arena pc_p2_groink_attack pc_p2_groink_hit pc_p2_groink_map_trace
pc_p2_groink_strike pc_p2_groink_target pc_p2_groink_volley pc_p2_hardlanes pc_p2_input_script
pc_p2_kabuto_binding pc_p2_kabuto_events pc_p2_kabuto_muzzle pc_p2_kochappy_fsm pc_p2_kochappy_stun
pc_p2_kurage_arena pc_p2_kurage_receiver pc_p2_kurage_teki pc_p2_kurage_visual pc_p2_long_legs_fsm
pc_p2_mamuta_rules pc_p2_material_binding pc_p2_material_scope pc_p2_onikurage_mouth pc_p2_onikurage_teki
pc_p2_preview pc_p2_projectile_host pc_p2_projectile_receiver pc_p2_projectiles pc_p2_purple
pc_p2_purple_direct pc_p2_purple_feedback pc_p2_purple_flight pc_p2_purple_impact pc_p2_purple_motion
pc_p2_receipt_host pc_p2_rock_hazard pc_p2_second_captain pc_p2_snagret_fsm pc_p2_species
pc_p2_specular_layer pc_p2_teki_lifetime pc_p2_waterwraith_actor pc_p2_waterwraith_encounter
pc_p2_waterwraith_host pc_p2_waterwraith_register pc_p2_waterwraith_visual pc_p2_white pc_p2_white_poison
""".split())

# docs/PIKMIN2_*_NATIVE.md files that are not per-identity enemy source slices and
# are legitimately exempt from the "every NATIVE doc is cited" coverage rule.
NON_IDENTITY_NATIVE_DOCS = frozenset({
    "PIKMIN2_BILLBOARD_NATIVE.md",
    "PIKMIN2_BEASTS_FLOOR3_FAILURE_NATIVE.md",
})


def native_source_docs() -> list[str]:
    """Relative filenames of the source-slice docs (``docs/PIKMIN2_*_NATIVE.md``)."""
    return sorted(p.name for p in (ROOT / "docs").glob("PIKMIN2_*_NATIVE.md"))


def _resolve_module(name: str) -> str:
    return MODULE_ALIASES.get(name, name)


def coverage_gaps(roster, modules: set[str], native_docs=None, *, existing_docs=None) -> dict:
    """Ledger coverage gaps: rows citing missing docs/modules, uncited source
    slices, and identity modules with no row. Empty everywhere == complete.

    ``existing_docs`` (optional) is the set of doc filenames used for the
    doc-existence integrity check; it defaults to the files under ``docs/`` and
    exists only so synthetic tests can inject a mock document set.

    Returns a dict with four list[str] keys (empty lists mean no gap):
      - ``rows_citing_missing_docs``    : "enum=id <doc>" rows whose source doc absent
      - ``rows_citing_missing_modules`` : "enum=id <module>" rows whose module absent
      - ``uncited_native_docs``         : NATIVE docs (minus exempt) no row cites
      - ``uncovered_identity_modules``  : non-shared modules no row cites
    """
    docs_dir = ROOT / "docs"
    native_docs = list(native_source_docs()) if native_docs is None else list(native_docs)
    on_disk = (existing_docs if existing_docs is not None
               else {p.name for p in docs_dir.glob("*.md")})
    missing_docs, missing_modules = [], []
    cited_docs, cited_modules = set(), set()
    for entry in roster:
        for src in entry.source:
            if src in on_disk:
                cited_docs.add(src)
            else:
                missing_docs.append(f"{entry.enum_name}={entry.source_id} {src}")
        if entry.native_module:
            stem = _resolve_module(entry.native_module)
            if stem in modules:
                cited_modules.add(stem)
            else:
                missing_modules.append(f"{entry.enum_name}={entry.source_id} {entry.native_module}")
    uncited = sorted(d for d in native_docs
                     if d not in cited_docs and d not in NON_IDENTITY_NATIVE_DOCS)
    uncovered = sorted(m for m in modules if m not in SHARED_MODULES and m not in cited_modules)
    return {
        "rows_citing_missing_docs": sorted(missing_docs),
        "rows_citing_missing_modules": sorted(missing_modules),
        "uncited_native_docs": uncited,
        "uncovered_identity_modules": uncovered,
    }


def load_inventory(path: Path) -> dict:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def inventory_identities(payload: dict) -> set[str]:
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


def build_report(roster, inventory: set[str], modules: set[str], parity: list[str],
                 encounters: dict | None = None) -> dict:
    summary = summarize(roster)
    enum_names = {e.enum_name for e in roster}
    categories = categorize_inventory_tokens(inventory, enum_names)
    review = candidate_review(roster, encounters or {})
    missing_modules = sorted({row["native_module"] for row in review
                              if row["native_module"] and _resolve_module(row["native_module"]) not in modules})
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
        "native_modules_missing": missing_modules,
        "candidate_review": review,
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
        "ledger_coverage": coverage_gaps(roster, modules),
        "source_parity_problems": parity,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE,
                        help="pikmin2-research checkout; pass an empty path to skip parity")
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--strict", action="store_true",
                        help="fail on source parity problems or unclassified identities")
    parser.add_argument("--review", action="store_true",
                        help="print per-candidate readiness rows and enforce ledger coverage (exit 1 on any gap)")
    parser.add_argument("--admit", action="store_true",
                        help="evaluate the admission contract: print the admitted set and, per candidate, the blocking gates")
    parser.add_argument("--write-admission", action="store_true",
                        help="persist the admission contract's admitted set into the evidence JSON")
    args = parser.parse_args(argv)

    roster = load_roster()
    validate_roster(roster)
    payload = load_inventory(INVENTORY)
    parity = verify_source_parity(roster, args.source) if args.source else []
    report = build_report(roster, inventory_identities(payload), native_modules(ENGINE_PORT), parity,
                          inventory_encounters(payload, roster))

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
    review = report["candidate_review"]
    print(f"candidates with inventory encounters: "
          f"{sum(1 for row in review if row['encounters'])}/{len(review)}")
    if report["native_modules_missing"]:
        print(f"declared native modules missing from engine/pc_port: {report['native_modules_missing']}")
    print(f"source parity problems: {len(parity)}")
    for problem in parity[:10]:
        print("  -", problem)
    if args.review:
        for row in review:
            if row["eligibility"] == "denied" and not row["encounters"]:
                continue
            print(f"  [{row['eligibility']}] {row['source_id']:>3} {row['enum_name']:<14} "
                  f"role={row['role']:<8} lane={row['owner_lane']} module={row['native_module']} "
                  f"encounters={len(row['encounters'])} missing={','.join(row['missing_gates'])}")

    ledger_gaps = report["ledger_coverage"]
    if args.review:
        print("ledger coverage gaps:")
        for key, label in (
            ("rows_citing_missing_docs", "rows citing missing docs"),
            ("rows_citing_missing_modules", "rows citing missing modules"),
            ("uncited_native_docs", "uncited source-slice docs"),
            ("uncovered_identity_modules", "identity modules without a row"),
        ):
            if ledger_gaps[key]:
                print(f"  - {label}: {ledger_gaps[key]}")
        print(f"ledger coverage complete: {not any(ledger_gaps.values())}")
        if any(ledger_gaps.values()):
            print("LEDGER COVERAGE FAIL", file=sys.stderr)
            return 1

    if args.strict and (parity or coverage["unclassified_identities"]):
        print("STRICT FAIL", file=sys.stderr)
        return 1

    if args.write_admission:
        result = write_admission(roster)
        print(f"admission written: admitted {result['admitted']}, "
              f"blocked {len(result['blocking'])}")

    if args.admit:
        contract = admission_contract(roster)
        print(f"admission contract: admitted {contract['admitted']}")
        by_enum = {e.source_id: e.enum_name for e in roster}
        for source_id, missing in sorted(contract["blocking"].items()):
            print(f"  {by_enum.get(source_id, source_id)} ({source_id}): "
                  f"blocking={','.join(missing)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
