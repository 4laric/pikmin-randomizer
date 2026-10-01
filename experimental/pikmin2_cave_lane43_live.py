"""Lane 43 (#481) live-gate glue for native cave generation.

The native engine, when ``PIKMIN_CAVE_GENERATOR_TABLE`` is set, runs the
generator and emits a single ``P2_CAVE_GEN`` marker line on stdout while
writing a ``p2-cave-observed-layout/1`` JSON with ``source: engine`` to
``PIKMIN_CAVE_GENERATOR_OUT``. This module turns that runtime evidence into a
re-roll-invariant comparison against an independent (standalone) layout:

* :func:`parse_marker` reads exactly one ``P2_CAVE_GEN`` line;
* :func:`logical_projection` strips geometry (unit, salt, attempts, seed) so
  two re-rolls of one seed can be compared on topology alone;
* :func:`check_live_generation` reports whether the live run is natural engine
  output that matches the standalone layout;
* :func:`check_unset_env` verifies the unset-env control run is unchanged.

It generates nothing itself: the only generator in this path is the native one.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

LAYOUT_SCHEMA = "p2-cave-observed-layout/1"
MARKER_PREFIX = "P2_CAVE_GEN"


class LiveGateError(ValueError):
    """Raised when the live cave-generation evidence is malformed."""


def _marker_lines(log_text) -> list:
    return [line for line in str(log_text or "").splitlines() if line.startswith(MARKER_PREFIX)]


def parse_marker(log_text) -> dict | None:
    """Parse the single ``P2_CAVE_GEN`` marker from a run log.

    Exactly one marker line is required. Returns ``None`` when the marker's
    tokens are not well-formed ``key=value`` pairs; raises :class:`LiveGateError`
    when there are zero or several marker lines, or when the single line is a
    ``FAILED`` marker.
    """
    lines = _marker_lines(log_text)
    if len(lines) == 0:
        raise LiveGateError("no P2_CAVE_GEN marker line found")
    if len(lines) > 1:
        raise LiveGateError(f"expected one P2_CAVE_GEN marker line, found {len(lines)}")
    tokens = lines[0].split()
    if "FAILED" in tokens:
        raise LiveGateError(f"native generator reported failure: {lines[0].strip()}")
    if len(tokens) < 2:
        return None
    parsed = {}
    for token in tokens[1:]:
        if "=" not in token:
            return None
        key, value = token.split("=", 1)
        parsed[key] = value
    return parsed


def logical_projection(layout: dict) -> dict:
    """Project a layout onto its re-roll-invariant logical structure.

    Node kind/hazard, the sorted per-node item lists, the edge set, the entrance
    and the hole are kept. Geometry (unit, salt, attempts, seed) is excluded.
    """
    layout = layout or {}
    nodes = {}
    items = {}
    for node in layout.get("nodes", []):
        node_id = node.get("id")
        nodes[node_id] = {"kind": node.get("kind"), "hazard": node.get("hazard") or None}
        items[node_id] = sorted(node.get("items") or [])
    edges = frozenset(tuple(sorted(edge)) for edge in layout.get("edges", []))
    return {
        "nodes": nodes,
        "items": items,
        "edges": edges,
        "entrance": layout.get("entrance"),
        "hole": layout.get("hole"),
    }


def compare_live_and_standalone(live: dict, standalone: dict) -> list:
    """Return human-readable differences between two layouts' projections."""
    live_projection = logical_projection(live)
    standalone_projection = logical_projection(standalone)
    differences = []

    if live_projection["entrance"] != standalone_projection["entrance"]:
        differences.append(
            f"entrance: live={live_projection['entrance']!r} "
            f"standalone={standalone_projection['entrance']!r}"
        )
    if live_projection["hole"] != standalone_projection["hole"]:
        differences.append(
            f"hole: live={live_projection['hole']!r} standalone={standalone_projection['hole']!r}"
        )

    node_ids = sorted(
        set(live_projection["nodes"]) | set(standalone_projection["nodes"]),
        key=lambda value: (value is None, str(value)),
    )
    for node_id in node_ids:
        live_node = live_projection["nodes"].get(node_id)
        standalone_node = standalone_projection["nodes"].get(node_id)
        if live_node != standalone_node:
            differences.append(f"node {node_id!r}: live={live_node} standalone={standalone_node}")
        live_items = live_projection["items"].get(node_id)
        standalone_items = standalone_projection["items"].get(node_id)
        if live_items != standalone_items:
            differences.append(
                f"items {node_id!r}: live={live_items} standalone={standalone_items}"
            )

    for edge in sorted(live_projection["edges"] - standalone_projection["edges"]):
        differences.append(f"edge only in live: {list(edge)}")
    for edge in sorted(standalone_projection["edges"] - live_projection["edges"]):
        differences.append(f"edge only in standalone: {list(edge)}")

    return differences


def check_live_generation(run_log_text, live_layout: dict, standalone_layout: dict) -> dict:
    """Report whether the live run is natural engine output matching standalone."""
    report = {
        "pass": False,
        "evidence": "natural",
        "marker": None,
        "layout_source": None,
        "differences": [],
        "standalone_matches": False,
    }
    try:
        marker = parse_marker(run_log_text)
    except LiveGateError as exc:
        report["differences"] = [f"marker: {exc}"]
        return report
    report["marker"] = marker

    live_layout = live_layout or {}
    standalone_layout = standalone_layout or {}
    report["layout_source"] = live_layout.get("source")

    differences = compare_live_and_standalone(live_layout, standalone_layout)
    report["differences"] = differences
    report["standalone_matches"] = not differences

    report["pass"] = (
        marker is not None
        and marker.get("source") == "engine"
        and live_layout.get("schema") == LAYOUT_SCHEMA
        and live_layout.get("source") == "engine"
        and not differences
    )
    return report


def check_unset_env(control_log_text) -> dict:
    """Verify the unset-env control run emitted no ``P2_CAVE_GEN`` lines."""
    markers = len(_marker_lines(control_log_text))
    return {"pass": markers == 0, "markers": markers}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-log", required=True, help="live run log with the P2_CAVE_GEN marker")
    parser.add_argument("--layout", required=True, help="live p2-cave-observed-layout/1 JSON")
    parser.add_argument("--standalone", required=True, help="standalone layout JSON to compare against")
    parser.add_argument("--control-log", default=None, help="unset-env control run log")
    parser.add_argument("--report-json", default=None, help="path to write the JSON report")
    args = parser.parse_args(argv)

    run_log_text = Path(args.run_log).read_text(encoding="utf-8")
    live_layout = json.loads(Path(args.layout).read_text(encoding="utf-8"))
    standalone_layout = json.loads(Path(args.standalone).read_text(encoding="utf-8"))

    generation = check_live_generation(run_log_text, live_layout, standalone_layout)
    report = {"generation": generation, "run_log": args.run_log,
              "layout": args.layout, "standalone": args.standalone}

    passed = generation["pass"]
    if args.control_log is not None:
        control_text = Path(args.control_log).read_text(encoding="utf-8")
        control = check_unset_env(control_text)
        report["control"] = control
        passed = passed and control["pass"]

    print(json.dumps(report, indent=2, sort_keys=True))
    if args.report_json:
        report_path = Path(args.report_json)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
