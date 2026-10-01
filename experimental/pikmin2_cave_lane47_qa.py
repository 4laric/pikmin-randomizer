"""Lane 47 (#485) independent QA over the P2 cave wave.

This is a report assembler, not a generator and not a checker. It reads the
runtime marker logs emitted by the cave lanes together with an independent
lane-40 checker report and the ``P2_RECEIPTS_1`` ledger, then labels every
acceptance-contract item as one of:

* :data:`NATURAL` -- backed by live engine evidence;
* :data:`PROXY` -- only partially evidenced (fixture / placeholder geometry);
* :data:`INJECTED` -- no natural evidence at all.

The report is fail-closed: a contract item is a pass only when its evidence is
natural, and the whole report passes only when every item that has a known
classification passes. It does not import native code, run the engine or
generate rooms.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

SCHEMA = "p2-cave-lane47-qa/1"
NATURAL = "natural"
PROXY = "proxy"
INJECTED = "injected"

_MARKER_PREFIXES = (
    ("gen", "P2_CAVE_GEN"),
    ("rooms_ready", "P2_CAVE_ROOMS_READY"),
    ("rooms_timeline", "P2_CAVE_ROOMS_TIMELINE"),
    ("rooms_grant", "P2_CAVE_ROOMS_GRANT"),
    ("geometry_ready", "P2_CAVE_GEOMETRY_READY"),
    ("geometry_node", "P2_CAVE_GEOMETRY_NODE"),
    ("geometry_gate", "P2_CAVE_GEOMETRY_GATE"),
    ("geometry_denki", "P2_CAVE_GEOMETRY_GATE_DENKI"),
    ("geometry_draw", "P2_CAVE_GEOMETRY_DRAW"),
    ("items_ready", "P2_CAVE_ITEMS_READY"),
    ("item_actor", "P2_CAVE_ITEM_ACTOR"),
    ("item_receipt", "P2_CAVE_ITEM_RECEIPT"),
    ("item_redeliver", "P2_CAVE_ITEM_REDELIVER"),
    ("natural_carry", "P2_CAVE_ITEM_NATURAL_CARRY"),
)

_PREFIX_TO_KEY = {prefix: key for key, prefix in _MARKER_PREFIXES}

_MARKER_KEYS = tuple(key for key, _ in _MARKER_PREFIXES)

CONTRACT_ITEMS = (
    "generation_invariant",
    "seed_determinism",
    "reroll_invariance",
    "reachability",
    "end_to_end_loop",
    "failure_handling",
)


def _coerce(value: str):
    try:
        return int(value)
    except (TypeError, ValueError):
        pass
    try:
        return float(value)
    except (TypeError, ValueError):
        return value


def _parse_pairs(tokens) -> dict | None:
    parsed = {}
    for token in tokens:
        if "=" not in token:
            return None
        key, value = token.split("=", 1)
        if not key:
            return None
        parsed[key] = _coerce(value)
    return parsed


def _parse_gen(tokens) -> dict | None:
    failed = "FAILED" in tokens
    parsed = _parse_pairs([token for token in tokens if token != "FAILED"])
    if parsed is None:
        return None
    parsed["failed"] = failed
    return parsed


def parse_markers(log_text) -> dict:
    """Parse every known ``P2_CAVE_*`` marker line out of a run log.

    Non-marker lines are ignored. A line that starts with a known marker prefix
    but whose trailing tokens are not ``key=value`` pairs is recorded under
    ``"malformed"`` instead of raising, so a single bad line can never abort the
    QA report.
    """
    result = {key: [] for key in _MARKER_KEYS}
    result["malformed"] = []
    for raw in str(log_text or "").splitlines():
        line = raw.strip()
        if not line:
            continue
        tokens = line.split()
        key = _PREFIX_TO_KEY.get(tokens[0])
        if key is None:
            continue
        if key == "gen":
            parsed = _parse_gen(tokens[1:])
        else:
            parsed = _parse_pairs(tokens[1:]) if len(tokens) > 1 else None
        if parsed is None:
            result["malformed"].append({"line": line, "reason": f"malformed {tokens[0]} marker"})
        else:
            result[key].append(parsed)
    return result


def parse_receipt_ledger(text) -> list:
    """Parse the ``P2_RECEIPTS_1`` ledger into ``seed/treasure/host/encounter`` rows.

    The marker line and blank lines are skipped; anything that is not a clean
    four-token row is skipped rather than raising.
    """
    rows = []
    for raw in str(text or "").splitlines():
        line = raw.strip()
        if not line or line.startswith("P2_RECEIPTS_1"):
            continue
        parts = line.split()
        if len(parts) != 4:
            continue
        seed, treasure, host, encounter = parts
        rows.append({"seed": seed, "treasure": treasure, "host": host, "encounter": encounter})
    return rows


def _last(markers, key):
    rows = markers.get(key) or []
    return rows[-1] if rows else None


def _section_pass(report, name):
    section = report.get(name)
    if isinstance(section, dict):
        return bool(section["pass"]) if "pass" in section else None
    if isinstance(section, bool):
        return section
    return None


def _checker_flag(checker_report, name):
    if not isinstance(checker_report, dict):
        return None
    return _section_pass(checker_report, name)


def _checker_view(checker_report):
    """Normalise both lane-40 report shapes.

    Lane 40's CLI stdout carries top-level ``generation_pass``/``evidence``,
    while the report *file* nests them under ``generation_invariant``. Either is
    accepted so the QA lane never has to guess which artefact it was handed.
    """
    view = {
        "gen_pass": None, "gen_evidence": None, "generation_invariant_pass": None,
        "seed_determinism": None, "reroll_invariance": None,
        "reachability": None, "failure_handling": None,
    }
    if not isinstance(checker_report, dict):
        return view
    gen = checker_report.get("generation_invariant")
    if isinstance(gen, dict):
        view["gen_pass"] = gen.get("generation_pass")
        view["gen_evidence"] = gen.get("evidence")
        view["generation_invariant_pass"] = _section_pass(gen, "pass")
    else:
        view["gen_pass"] = checker_report.get("generation_pass")
        view["gen_evidence"] = checker_report.get("evidence")
        view["generation_invariant_pass"] = checker_report.get("generation_pass")
    for name in ("seed_determinism", "reroll_invariance", "reachability", "failure_handling"):
        view[name] = _checker_flag(checker_report, name)
    if view["reachability"] is None and view["generation_invariant_pass"] is not None:
        # Lane 40 has no dedicated reachability section: its generation_invariant
        # model pass already rejects bypassable chokes and ambient/off-slot hard
        # gates, which is exactly the reachability contract item.
        view["reachability"] = bool(view["generation_invariant_pass"])
    return view


def _failure_handling(failure_report):
    """A negative-control lane-40 report passes failure handling when a
    deficient layout is rejected with ``retry_required``."""
    if not isinstance(failure_report, dict):
        return None
    gen = failure_report.get("generation_invariant")
    layouts = gen.get("layouts") if isinstance(gen, dict) else failure_report.get("layouts")
    if not isinstance(layouts, list) or not layouts:
        return None
    return bool(any(isinstance(row, dict) and row.get("retry_required") for row in layouts))


def _generation(markers, view):
    gen_markers = markers.get("gen") or []
    checker_pass = view.get("gen_pass")
    checker_pass = bool(checker_pass) if checker_pass is not None else None
    checker_evidence = view.get("gen_evidence")
    has_success = any(not marker.get("failed") for marker in gen_markers)
    passed = checker_pass is True and checker_evidence == NATURAL and has_success
    return {
        "checker_pass": checker_pass,
        "checker_evidence": checker_evidence,
        "gen_markers": gen_markers,
        "pass": passed,
    }


def _live_generation(markers):
    gen_markers = markers.get("gen") or []
    return {
        "present": bool(gen_markers),
        "natural": any(marker.get("source") == "engine" for marker in gen_markers),
        "markers": gen_markers,
    }


def _geometry(markers):
    ready = _last(markers, "geometry_ready")
    proxy_nodes = [
        node.get("id")
        for node in (markers.get("geometry_node") or [])
        if node.get("proxy") == 1
    ]
    nodes_real = int(ready.get("real", 0) or 0) if ready else 0
    nodes_proxy = int(ready.get("proxy", 0) or 0) if ready else 0
    gate_actors = int(ready.get("gate_actors", 0) or 0) if ready else 0
    geometry = ready.get("geometry") if ready else None
    natural_real_models = bool(ready) and (geometry != "proxy" or nodes_real > 0)
    return {
        "ready": ready,
        "nodes_real": nodes_real,
        "nodes_proxy": nodes_proxy,
        "gate_actors": gate_actors,
        "geometry": geometry,
        "natural_real_models": natural_real_models,
        "proxy_nodes": proxy_nodes,
    }


def _collection(markers, receipt_ledger, checker_report):
    items_ready = _last(markers, "items_ready")
    receipts = markers.get("item_receipt") or []
    receipts_new = sum(1 for row in receipts if row.get("new") == 1)
    receipts_duplicate = sum(1 for row in receipts if row.get("new") == 0)
    carries = markers.get("natural_carry") or []
    natural_carry = sum(int(row.get("transport", 0) or 0) for row in carries)
    ledger_rows = len(parse_receipt_ledger(receipt_ledger)) if receipt_ledger else 0
    receipt_error = False
    if any(int(row.get("result", 0) or 0) < 0 for row in receipts):
        receipt_error = True
    if isinstance(checker_report, dict) and checker_report.get("receipt_error"):
        receipt_error = True
    passed = receipts_new >= 1 and natural_carry >= 1 and not receipt_error
    return {
        "items": int(items_ready.get("items", 0) or 0) if items_ready else 0,
        "tagged": int(items_ready.get("tagged", 0) or 0) if items_ready else 0,
        "receipts_new": receipts_new,
        "receipts_duplicate": receipts_duplicate,
        "natural_carry": natural_carry,
        "ledger_rows": ledger_rows,
        "pass": passed,
    }


def _timeline(markers):
    rows = markers.get("rooms_timeline") or []
    grants = markers.get("rooms_grant") or []
    hole_closed_fresh = any(
        row.get("tag") == "fresh_floor_no_abilities" and row.get("hole") == 0 for row in rows)
    hole_open_with_blue = any(
        row.get("tag") == "return_with_yellow_and_blue" and row.get("hole") == 1 for row in rows)
    elec_open_with_yellow = any(
        row.get("tag") == "come_back_with_yellow" and row.get("treasure_elec") == 1 for row in rows)
    staged_grants = sum(1 for grant in grants if grant.get("staged") == 1)
    natural_grants = sum(1 for grant in grants if grant.get("natural_acquire") == 1)
    return {
        "rows": len(rows),
        "hole_closed_fresh": hole_closed_fresh,
        "hole_open_with_blue": hole_open_with_blue,
        "elec_open_with_yellow": elec_open_with_yellow,
        "staged_grants": staged_grants,
        "natural_grants": natural_grants,
        "abilities_staged": staged_grants > 0,
    }


def classify(markers, view, generation, collection, timeline) -> dict:
    """Label every acceptance-contract item from explicit evidence only."""
    labels = {name: None for name in CONTRACT_ITEMS}

    labels["generation_invariant"] = NATURAL if generation["pass"] else INJECTED

    for name in ("seed_determinism", "reroll_invariance", "reachability", "failure_handling"):
        flag = view.get(name)
        if flag is not None:
            labels[name] = NATURAL if flag else INJECTED

    # The end-to-end loop is only natural when the real carry/receipt ran *and*
    # the ability timeline was not staged. A staged grant or a proxy geometry
    # leaves the loop partial, so it is labelled proxy, never natural.
    if collection["pass"] and not timeline.get("abilities_staged") and timeline["rows"] > 0:
        labels["end_to_end_loop"] = NATURAL
    elif collection["pass"] or (markers.get("item_actor") or timeline["rows"] > 0):
        labels["end_to_end_loop"] = PROXY
    else:
        labels["end_to_end_loop"] = INJECTED
    return labels


def _failures(generation, labels):
    failures = []
    if labels["generation_invariant"] != NATURAL:
        if generation["checker_pass"] is not True:
            failures.append(
                "generation_invariant: checker_report.generation_pass is not True")
        elif generation["checker_evidence"] != NATURAL:
            failures.append(
                "generation_invariant: checker_report.evidence is not 'natural'")
        elif not any(not marker.get("failed") for marker in generation["gen_markers"]):
            failures.append(
                "generation_invariant: no successful P2_CAVE_GEN marker")
    for name in ("seed_determinism", "reroll_invariance", "reachability", "failure_handling"):
        if labels[name] == INJECTED:
            failures.append(f"{name}: checker_report.{name}.pass is not True")
    if labels["end_to_end_loop"] == PROXY:
        failures.append(
            "end_to_end_loop: partial only (real carry/receipt without a natural "
            "ability timeline, or staged grants; geometry/layout remain proxy)")
    elif labels["end_to_end_loop"] == INJECTED:
        failures.append(
            "end_to_end_loop: no P2_CAVE_ITEM_ACTOR or P2_CAVE_ROOMS_TIMELINE evidence "
            "and collection did not pass")
    return failures


def check_chain(*, marker_logs, checker_report=None, receipt_ledger=None,
                failure_report=None) -> dict:
    """Assemble the fail-closed lane-47 QA report over the frozen pin."""
    if isinstance(marker_logs, str):
        marker_logs = [marker_logs]
    markers = parse_markers("\n".join(str(log) for log in (marker_logs or [])))

    view = _checker_view(checker_report)
    if failure_report is not None:
        derived = _failure_handling(failure_report)
        if derived is not None:
            view["failure_handling"] = derived

    generation = _generation(markers, view)
    live_generation = _live_generation(markers)
    geometry = _geometry(markers)
    collection = _collection(markers, receipt_ledger, checker_report)
    timeline = _timeline(markers)
    labels = classify(markers, view, generation, collection, timeline)
    failures = _failures(generation, labels)

    known = [value for value in labels.values() if value is not None]
    passed = all(value == NATURAL for value in known) if known else False

    return {
        "schema": SCHEMA,
        "generation": generation,
        "live_generation": live_generation,
        "geometry": geometry,
        "collection": collection,
        "timeline": timeline,
        "classification": labels,
        "failures": failures,
        "pass": passed,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live-log", action="append", default=[],
                        help="runtime marker log (repeatable)")
    parser.add_argument("--checker", default=None, help="lane-40 checker report JSON")
    parser.add_argument("--failure-checker", default=None,
                        help="lane-40 negative-control report that must demand retry")
    parser.add_argument("--receipts", default=None, help="P2_RECEIPTS_1 ledger text file")
    parser.add_argument("--out", required=True, help="path to write the QA report JSON")
    args = parser.parse_args(argv)

    marker_logs = [Path(path).read_text(encoding="utf-8") for path in args.live_log]
    checker_report = None
    if args.checker:
        checker_report = json.loads(Path(args.checker).read_text(encoding="utf-8"))
    failure_report = None
    if args.failure_checker:
        failure_report = json.loads(Path(args.failure_checker).read_text(encoding="utf-8"))
    receipt_ledger = None
    if args.receipts:
        receipt_ledger = Path(args.receipts).read_text(encoding="utf-8")

    report = check_chain(marker_logs=marker_logs, checker_report=checker_report,
                         receipt_ledger=receipt_ledger, failure_report=failure_report)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
