"""Lane 33 mixed-scene performance and actor budget acceptance (#444, assignment 4).

Assignment 4 requires the two P2 identities to be tested together "with recorded
frame-time, memory and actor budgets". This module owns the *acceptance* side of
that: it consumes a measured mixed-scene manifest
(``mixed-scene-validation.json`` from
:mod:`experimental.pikmin2_mixed_scene_behavior`) and an explicit budget policy,
then resolves the ``frame_budget`` and ``memory_budget`` QA-matrix cells.

It does not measure anything itself and it never invents a budget. The existing
:data:`experimental.pikmin2_mixed_scene_behavior.PROPOSED_BUDGETS` are marked
``proposed_not_accepted`` for integration review; until an accepted policy
exists, every budget metric resolves to ``BLOCKED`` with that reason, so a
proposed limit can never be reported as an accepted PASS.

Usage::

    py -3.12 -m experimental.pikmin2_performance_budget evaluate \
        --manifest <run>/mixed-scene-validation.json --budgets budgets.json \
        --output <run>/budget-evaluation.json
    py -3.12 -m experimental.pikmin2_performance_budget records \
        --report <run>/budget-evaluation.json --kind fixture --stage install \
        --root-commit <root> --executable <exe> --executable-sha256 <64-hex> \
        --output output/lane33-records
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from experimental import pikmin2_qa_matrix as qa
from experimental.pikmin2_generated_session_acceptance import (
    AcceptanceError,
    Pin,
    PinMismatch,
)

BUDGET_SCHEMA = "p2-performance-budgets-v1"
ACCEPTED = "accepted"
PROPOSED = "proposed_not_accepted"
BUDGET_STATUSES = (ACCEPTED, PROPOSED)

# Keys mirror experimental.pikmin2_mixed_scene_behavior.PROPOSED_BUDGETS.
FRAME_BUDGET_KEYS = ("target_mean_frame_ms_max", "slowest_window_mean_ms_max")
MEMORY_BUDGET_KEYS = ("tracked_texture_peak_mib_max", "total_pose_bank_bytes_max")
BUDGET_KEYS = FRAME_BUDGET_KEYS + MEMORY_BUDGET_KEYS
ACTOR_BUDGET_KEY = "actor_count_max"

CELL_METRICS = {
    "frame_budget": ("mean_frame_ms", "slowest_window_mean_ms"),
    "memory_budget": ("tracked_texture_peak_mib", "total_pose_bank_bytes", "actor_count"),
}


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def validate_budgets(data):
    """Normalize an accepted/proposed budget policy; raise on malformed input."""
    if not isinstance(data, dict):
        raise AcceptanceError("budget policy must be a JSON object")
    if data.get("schema") != BUDGET_SCHEMA:
        raise AcceptanceError(f"budget schema must be {BUDGET_SCHEMA}")
    status = data.get("status")
    if status not in BUDGET_STATUSES:
        raise AcceptanceError(f"budget status must be one of {BUDGET_STATUSES}")
    normalized = {"schema": BUDGET_SCHEMA, "status": status,
                  "revision": str(data.get("revision", ""))}
    for key in BUDGET_KEYS:
        value = data.get(key)
        if not isinstance(value, (int, float)) or isinstance(value, bool) or value <= 0:
            raise AcceptanceError(f"budget {key} must be a positive number")
        normalized[key] = value
    if ACTOR_BUDGET_KEY in data:
        actors = data[ACTOR_BUDGET_KEY]
        if not isinstance(actors, int) or isinstance(actors, bool) or actors <= 0:
            raise AcceptanceError(f"budget {ACTOR_BUDGET_KEY} must be a positive integer")
        normalized[ACTOR_BUDGET_KEY] = actors
    return normalized


def _measured(assessment, key, fallback):
    entry = assessment.get(key)
    if isinstance(entry, dict) and entry.get("measured") is not None:
        return entry["measured"]
    return fallback


def measurements_from_manifest(manifest):
    """Extract the recorded metrics from a mixed-scene validation manifest."""
    if not isinstance(manifest, dict):
        raise AcceptanceError("measured manifest must be a JSON object")
    assessment = manifest.get("budget_assessment") or {}
    frame = manifest.get("frame_time") or {}
    textures = manifest.get("texture_memory") or {}
    last = textures.get("last") or {}
    if not isinstance(last, dict):
        last = {}
    actor_count = manifest.get("actor_count")
    if actor_count is None and isinstance(manifest.get("scene"), dict):
        actor_count = manifest["scene"].get("actor_count")
    return {
        "mean_frame_ms": _measured(assessment, "mean_frame_ms", frame.get("mean_frame_ms")),
        "slowest_window_mean_ms": _measured(assessment, "slowest_window_mean_ms",
                                            frame.get("slowest_window_mean_ms")),
        "tracked_texture_peak_mib": _measured(
            assessment, "tracked_texture_peak_mib",
            last.get("peak_mib_rounded_down", textures.get("maximum_reported_mib"))),
        "total_pose_bank_bytes": _measured(assessment, "total_pose_bank_bytes",
                                           manifest.get("total_pose_bank_bytes")),
        "actor_count": actor_count,
    }


def _metric(name, measured, budget, status, reason):
    return {"measured": measured, "budget": budget, "status": status, "reason": reason}


def evaluate(manifest, budgets):
    """Resolve the frame/memory budget cells from a measured manifest.

    ``budgets`` must be an accepted policy for a PASS. A proposed/unaccepted
    policy, a missing measurement or an incomplete capture resolves to
    ``BLOCKED``; an exceeded budget resolves to ``FAIL``.
    """
    budgets = validate_budgets(budgets)
    measured = measurements_from_manifest(manifest)
    capture = manifest.get("capture") or {}
    capture_invalid = (capture.get("exit_code") not in (0, None)
                       or bool(capture.get("timed_out")))

    def resolve(name, value, budget):
        if capture_invalid:
            return _metric(name, value, budget, qa.FAIL, "capture did not complete cleanly")
        if value is None:
            return _metric(name, None, budget, qa.BLOCKED, "measurement was not recorded")
        if value > budget:
            return _metric(name, value, budget, qa.FAIL, f"{value} exceeds budget {budget}")
        return _metric(name, value, budget, qa.PASS, f"{value} within budget {budget}")

    metrics = {
        "mean_frame_ms": resolve("mean_frame_ms", measured["mean_frame_ms"],
                                 budgets["target_mean_frame_ms_max"]),
        "slowest_window_mean_ms": resolve("slowest_window_mean_ms",
                                          measured["slowest_window_mean_ms"],
                                          budgets["slowest_window_mean_ms_max"]),
        "tracked_texture_peak_mib": resolve("tracked_texture_peak_mib",
                                            measured["tracked_texture_peak_mib"],
                                            budgets["tracked_texture_peak_mib_max"]),
        "total_pose_bank_bytes": resolve("total_pose_bank_bytes",
                                         measured["total_pose_bank_bytes"],
                                         budgets["total_pose_bank_bytes_max"]),
    }
    if ACTOR_BUDGET_KEY in budgets:
        metrics["actor_count"] = resolve("actor_count", measured["actor_count"],
                                         budgets[ACTOR_BUDGET_KEY])
    else:
        metrics["actor_count"] = _metric("actor_count", measured["actor_count"], None,
                                         qa.BLOCKED, "no accepted actor-count budget")

    if budgets["status"] != ACCEPTED:
        for metric in metrics.values():
            metric["status"] = qa.BLOCKED
            metric["reason"] = "budget policy is proposed, not accepted"

    cells = {}
    for cell, names in CELL_METRICS.items():
        statuses = [metrics[name]["status"] for name in names]
        if qa.FAIL in statuses:
            status = qa.FAIL
        elif qa.BLOCKED in statuses:
            status = qa.BLOCKED
        else:
            status = qa.PASS
        cells[cell] = {"status": status,
                       "reasons": [metrics[name]["reason"] for name in names
                                   if metrics[name]["status"] != qa.PASS] or ["all metrics within budget"]}

    if any(cell["status"] == qa.FAIL for cell in cells.values()):
        overall = qa.FAIL
    elif any(cell["status"] == qa.BLOCKED for cell in cells.values()):
        overall = qa.BLOCKED
    else:
        overall = qa.PASS

    return {
        "schema": 1,
        "generated_by": "experimental.pikmin2_performance_budget",
        "status": overall,
        "budgets": budgets,
        "capture_invalid": capture_invalid,
        "measured": measured,
        "metrics": metrics,
        "cells": cells,
    }


def records_from_evaluation(report, pin, *, kind, stage="install", evidence_paths,
                            scenario=None):
    """Convert a budget evaluation into validated QA-matrix records.

    ``frame_budget`` and ``memory_budget`` are boundary scenarios, so a private
    fixture may satisfy them; ``natural`` still requires the pinned executable.
    """
    if kind not in qa.EVIDENCE_KINDS:
        raise AcceptanceError(f"unknown evidence kind: {kind!r}")
    if not evidence_paths:
        raise AcceptanceError("at least one evidence path is required")
    if kind == qa.KIND_NATURAL:
        pin.verify()
    records = []
    for cell in ("frame_budget", "memory_budget"):
        record = {
            "id": f"lane33-{stage}-{cell}",
            "stage": stage,
            "scenario": scenario or cell,
            "kind": kind,
            "status": report["cells"][cell]["status"],
            "root_commit": pin.root_commit,
            "native_commit": pin.native_commit,
            "build_sha256": pin.executable_sha256,
            "evidence_paths": [str(path) for path in evidence_paths],
            "notes": "; ".join(report["cells"][cell]["reasons"]),
        }
        problems = qa.validate_record(record)
        if problems:
            raise AcceptanceError(f"invalid generated record {record['id']}: {problems}")
        records.append(record)
    return records


def write_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _pin_args(parser):
    parser.add_argument("--root-commit", default="")
    parser.add_argument("--native-commit", default="")
    parser.add_argument("--executable", default="")
    parser.add_argument("--executable-sha256", default="")
    parser.add_argument("--assets", default="")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    evaluate_parser = sub.add_parser("evaluate", help="resolve budget cells from a measured manifest")
    evaluate_parser.add_argument("--manifest", type=Path, required=True)
    evaluate_parser.add_argument("--budgets", type=Path, required=True)
    evaluate_parser.add_argument("--output", type=Path, required=True)

    records_parser = sub.add_parser("records", help="emit QA-matrix records from an evaluation")
    records_parser.add_argument("--report", type=Path, required=True)
    records_parser.add_argument("--kind", choices=list(qa.EVIDENCE_KINDS), required=True)
    records_parser.add_argument("--stage", default="install")
    records_parser.add_argument("--output", type=Path, required=True)
    _pin_args(records_parser)

    args = parser.parse_args(argv)

    if args.command == "evaluate":
        report = evaluate(load_json(args.manifest), load_json(args.budgets))
        write_json(args.output, report)
        print(json.dumps({"status": report["status"],
                          "cells": {name: cell["status"] for name, cell in report["cells"].items()}}))
        return 0 if report["status"] == qa.PASS else 2 if report["status"] == qa.BLOCKED else 1

    if args.command == "records":
        report = load_json(args.report)
        pin = Pin(root_commit=args.root_commit, native_commit=args.native_commit,
                  executable=args.executable, executable_sha256=args.executable_sha256,
                  assets=args.assets)
        emitted = records_from_evaluation(report, pin, kind=args.kind, stage=args.stage,
                                          evidence_paths=[args.report.resolve()])
        out = args.output
        for record in emitted:
            write_json(out / f"{record['id']}.json", record)
        print(f"wrote {len(emitted)} records to {out}")
        return 0

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
