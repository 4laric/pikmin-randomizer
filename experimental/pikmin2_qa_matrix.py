"""Lane 33 mixed-scene and seeded-run QA matrix (#444, dispatch #435/#186).

Independent acceptance lane 33 of ``docs/PIKMIN2_IMPLEMENTATION_FANOUT.md``.
This module defines the machine-readable acceptance matrix and turns pinned
evidence records into a per-cell PASS/FAIL/BLOCKED/UNTESTED report. It owns QA
tooling only; it never fixes production code and it never claims a run that
did not happen.

The matrix is the cross product of:

* a pipeline **stage** (generate, install, natural_fight, reward, revisit,
  restart), and
* a **scenario** class (baseline cohort, adversarial density/ownership,
  weak/strong stats, minimum cap, paused events, scheduled births, interrupted
  capture, address reuse, missing assets, frame/memory budget).

Every cell defaults to ``UNTESTED``. A cell only becomes ``PASS`` when a
pinned evidence record with the required provenance (root commit, build hash
and at least one evidence path) is supplied *and* the record's evidence kind is
strong enough for that cell:

* ``natural`` records may satisfy any cell (real seed / real input run);
* ``fixture`` records may satisfy cells that do not require a natural run;
* ``injected``/``synthetic``/``mocked`` records never satisfy a cell -- a mocked
  scene is not a real seed.

Usage::

    py -3.12 -m experimental.pikmin2_qa_matrix report --records <dir> --output <dir>
    py -3.12 -m experimental.pikmin2_qa_matrix validate --records <dir>
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCHEMA = 1

PASS = "PASS"
FAIL = "FAIL"
BLOCKED = "BLOCKED"
UNTESTED = "UNTESTED"
NA = "N/A"

STATUSES = (PASS, FAIL, BLOCKED, UNTESTED, NA)

# Evidence kinds, strongest first. Only `natural` may satisfy a natural-only
# cell; `fixture` may satisfy tooling/private-fixture cells; the rest are
# informational and can never produce a PASS.
KIND_NATURAL = "natural"
KIND_FIXTURE = "fixture"
KIND_INJECTED = "injected"
KIND_SYNTHETIC = "synthetic"
KIND_MOCKED = "mocked"
EVIDENCE_KINDS = (KIND_NATURAL, KIND_FIXTURE, KIND_INJECTED, KIND_SYNTHETIC, KIND_MOCKED)

# Pipeline stages, in order. `natural_required` marks the stages whose gate is
# only meaningful on a real seeded/playable run rather than a private fixture.
STAGES = (
    ("generate", "Real seed generates with the P2 cohort selected and content resolved", False),
    ("install", "Content staged automatically with no manual sidecar copying", False),
    ("natural_fight", "Natural combat through death/corpse with no injected state", True),
    ("reward", "Exactly-once reward/cargo receipt on the real reward path", True),
    ("revisit", "Seed re-entered with the same roster/rewards and no duplicate grant", True),
    ("restart", "Process restart restores the same session without stale references", True),
)

# Scenario classes. `natural_required` marks scenarios that must be exercised
# by a real run (density, ownership, stat extremes); the boundary/negative
# scenarios may be exercised by a private runtime fixture but never a mock.
SCENARIOS = {
    "baseline_cohort": {
        "label": "Admitted baseline cohort end to end",
        "natural_required": True,
        "description": "First admitted P2 cohort through every stage.",
    },
    "adversarial_density": {
        "label": "Adversarial spawn density",
        "natural_required": True,
        "description": "Target-density mixed roster, helper/projectile budgets.",
    },
    "ownership_conflict": {
        "label": "Adversarial ownership/capture conflict",
        "natural_required": True,
        "description": "Simultaneous captor/attachment/dependent ownership.",
    },
    "weak_stats": {
        "label": "Weak-stat build",
        "natural_required": True,
        "description": "Low attack/defense party versus the cohort.",
    },
    "strong_stats": {
        "label": "Strong-stat build",
        "natural_required": True,
        "description": "High attack/defense party versus the cohort.",
    },
    "minimum_cap": {
        "label": "Minimum squad cap",
        "natural_required": False,
        "description": "Fight and extinction boundary at the minimum squad cap.",
    },
    "paused_events": {
        "label": "Paused event execution",
        "natural_required": False,
        "description": "Exactly-once events across pause/resume and frame skips.",
    },
    "scheduled_births": {
        "label": "Scheduled/late births",
        "natural_required": False,
        "description": "Timed and late-birth actors and helpers.",
    },
    "interrupted_capture": {
        "label": "Interrupted capture",
        "natural_required": False,
        "description": "Capture interrupted by damage/death/whistle/state change.",
    },
    "address_reuse": {
        "label": "Recycled actor address",
        "natural_required": False,
        "description": "Freed actor memory reused without stale references.",
    },
    "missing_assets": {
        "label": "Missing/wrong content",
        "natural_required": False,
        "description": "Missing or mismatched source content is rejected, not substituted.",
    },
    "frame_budget": {
        "label": "Frame-time budget",
        "natural_required": False,
        "description": "Frame time at target density stays within the agreed budget.",
    },
    "memory_budget": {
        "label": "Memory budget",
        "natural_required": False,
        "description": "Per-species bank/actor memory stays within the agreed budget.",
    },
}

REQUIRED_FIELDS = ("id", "stage", "scenario", "kind", "status")


def stage_keys():
    return [key for key, _label, _natural in STAGES]


def stage_natural_required(stage):
    for key, _label, natural in STAGES:
        if key == stage:
            return natural
    raise KeyError(stage)


def cell_required(stage, scenario):
    """True when a cell must be satisfied by a real (non-fixture) run."""
    scenario_natural = SCENARIOS[scenario]["natural_required"]
    return bool(stage_natural_required(stage) or scenario_natural)


def matrix_cells():
    return [(stage, scenario) for stage in stage_keys() for scenario in SCENARIOS]


def pass_allowed(kind, natural_required):
    if kind == KIND_NATURAL:
        return True
    if kind == KIND_FIXTURE:
        return not natural_required
    return False


def validate_record(record):
    """Return a list of human-readable problems, empty when the record is valid."""
    problems = []
    if not isinstance(record, dict):
        return ["record is not an object"]
    for field in REQUIRED_FIELDS:
        if field not in record:
            problems.append(f"missing field '{field}'")
    if record.get("stage") not in stage_keys():
        problems.append(f"unknown stage {record.get('stage')!r}")
    if record.get("scenario") not in SCENARIOS:
        problems.append(f"unknown scenario {record.get('scenario')!r}")
    if record.get("kind") not in EVIDENCE_KINDS:
        problems.append(f"unknown evidence kind {record.get('kind')!r}")
    status = record.get("status")
    if status not in (PASS, FAIL, BLOCKED):
        problems.append(f"unknown status {status!r}")
    if not str(record.get("id", "")).strip():
        problems.append("empty id")
    return problems


def _provenance_ok(record):
    """A PASS needs a pinned root commit, a build hash and an evidence path."""
    root_commit = str(record.get("root_commit", "")).strip()
    build_hash = str(record.get("build_sha256", record.get("executable_sha256", ""))).strip()
    paths = record.get("evidence_paths") or []
    return bool(root_commit and build_hash and isinstance(paths, list) and paths)


def _record_ref(record):
    return {
        "id": record.get("id"),
        "kind": record.get("kind"),
        "status": record.get("status"),
        "root_commit": record.get("root_commit"),
        "native_commit": record.get("native_commit"),
        "build_sha256": record.get("build_sha256", record.get("executable_sha256")),
        "evidence_paths": list(record.get("evidence_paths") or []),
        "notes": record.get("notes", ""),
    }


def evaluate_cell(records, stage, scenario):
    """Resolve one cell to a status plus the records that justify it."""
    matching = [r for r in records if r.get("stage") == stage and r.get("scenario") == scenario]
    required = cell_required(stage, scenario)
    if not matching:
        return {"stage": stage, "scenario": scenario, "status": UNTESTED,
                "reason": "no evidence record", "evidence": []}
    failed = [r for r in matching if r.get("status") == FAIL]
    if failed:
        return {"stage": stage, "scenario": scenario, "status": FAIL,
                "reason": "at least one pinned record failed",
                "evidence": [_record_ref(r) for r in matching]}
    passing = []
    for record in matching:
        if record.get("status") != PASS:
            continue
        if not pass_allowed(record.get("kind"), required):
            continue
        if not _provenance_ok(record):
            continue
        passing.append(record)
    if passing:
        return {"stage": stage, "scenario": scenario, "status": PASS,
                "reason": "pinned evidence meets the cell requirement",
                "evidence": [_record_ref(r) for r in matching]}
    # PASS attempted but nothing admissible: explain the strongest block.
    attempted_pass = [r for r in matching if r.get("status") == PASS]
    if attempted_pass:
        reasons = []
        for record in attempted_pass:
            if not pass_allowed(record.get("kind"), required):
                reasons.append(f"{record.get('id')}: {record.get('kind')} evidence cannot satisfy this cell")
            elif not _provenance_ok(record):
                reasons.append(f"{record.get('id')}: incomplete provenance (commit/hash/evidence)")
        return {"stage": stage, "scenario": scenario, "status": BLOCKED,
                "reason": "; ".join(dict.fromkeys(reasons)), "evidence": [_record_ref(r) for r in matching]}
    return {"stage": stage, "scenario": scenario, "status": BLOCKED,
            "reason": "all recorded attempts blocked", "evidence": [_record_ref(r) for r in matching]}


def build_report(records, pin=None):
    cells = [evaluate_cell(records, stage, scenario) for stage, scenario in matrix_cells()]
    summary = {status: 0 for status in STATUSES}
    for cell in cells:
        summary[cell["status"]] = summary.get(cell["status"], 0) + 1
    return {
        "schema": SCHEMA,
        "generated_by": "experimental.pikmin2_qa_matrix",
        "pin": dict(pin or {}),
        "stages": [
            {"key": key, "label": label, "natural_required": natural}
            for key, label, natural in STAGES
        ],
        "scenarios": [
            {"key": key, "label": value["label"],
             "natural_required": value["natural_required"],
             "description": value["description"]}
            for key, value in SCENARIOS.items()
        ],
        "cells": cells,
        "summary": summary,
    }


def to_markdown(report):
    lines = ["# P2 mixed-scene and seeded-run QA matrix", "",
             "Generated by `experimental.pikmin2_qa_matrix` (lane 33, #444). "
             "Every cell defaults to UNTESTED; a PASS requires pinned provenance "
             "and admissible evidence.", ""]
    pin = report.get("pin") or {}
    if pin:
        lines.append("Pinned baseline: " + ", ".join(f"`{k}={v}`" for k, v in pin.items()) + ".")
        lines.append("")
    summary = report.get("summary", {})
    lines.append("Summary: " + ", ".join(f"{k}={summary.get(k, 0)}" for k in STATUSES) + ".")
    lines.append("")
    by_stage = {}
    for cell in report["cells"]:
        by_stage.setdefault(cell["stage"], []).append(cell)
    for stage in report["stages"]:
        lines.append(f"## {stage['key']} — {stage['label']}")
        lines.append("")
        lines.append("| scenario | status | reason | evidence |")
        lines.append("|---|---|---|---|")
        for cell in by_stage.get(stage["key"], []):
            evidence = ", ".join(f"{e['id']}({e['kind']})" for e in cell["evidence"]) or "-"
            reason = cell["reason"].replace("|", "\\|")
            lines.append(f"| {cell['scenario']} | {cell['status']} | {reason} | {evidence} |")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _records_from_object(obj, path):
    if isinstance(obj, list):
        return obj
    if isinstance(obj, dict) and isinstance(obj.get("records"), list):
        return obj["records"]
    if isinstance(obj, dict):
        return [obj]
    raise ValueError(f"{path}: top level must be an object or list")


def load_records(path):
    """Load records from a file or recursively from a directory of ``*.json``."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(path)
    files = sorted(path.rglob("*.json")) if path.is_dir() else [path]
    records = []
    for file_path in files:
        try:
            obj = json.loads(file_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as error:
            raise ValueError(f"{file_path}: {error}") from error
        records.extend(_records_from_object(obj, file_path))
    return records


def check_records(records):
    """Validate every record; return a list of ``path-free`` problem strings."""
    problems = []
    seen = set()
    for index, record in enumerate(records):
        errors = validate_record(record)
        for error in errors:
            problems.append(f"record[{index}] ({record.get('id', '?') if isinstance(record, dict) else '?'}): {error}")
        if isinstance(record, dict) and not errors:
            key = (record.get("id"), record.get("stage"), record.get("scenario"))
            if key in seen:
                problems.append(f"record[{index}] ({record.get('id')}): duplicate id/stage/scenario")
            seen.add(key)
    return problems


def _write_outputs(report, output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    (output / "qa-matrix.json").write_text(
        json.dumps(report, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    (output / "qa-matrix.md").write_text(to_markdown(report), encoding="utf-8")
    return output


MANIFEST_STATUS = {
    "passed": PASS,
    "pass": PASS,
    "failed": FAIL,
    "fail": FAIL,
    "error": FAIL,
    "blocked": BLOCKED,
}


def manifest_status(manifest, default=BLOCKED):
    return MANIFEST_STATUS.get(str(manifest.get("status", "")).lower(), default)


def record_from_manifest(manifest, manifest_path, *, record_id, stage, scenario, kind,
                         root_commit="", native_commit="", build_sha256="", notes=""):
    """Convert a run manifest (verification.json etc.) into a validated record.

    The operator supplies the stage/scenario/kind classification; this helper
    only extracts the status and the fixture executable hash and points the
    evidence path at the manifest. The result is validated before returning.
    """
    if not isinstance(manifest, dict):
        raise ValueError("manifest must be a JSON object")
    sha = build_sha256
    if not sha:
        fixture = manifest.get("fixture")
        if isinstance(fixture, dict):
            executable = fixture.get("executable")
            if isinstance(executable, dict):
                sha = str(executable.get("sha256", ""))
    record = {
        "id": record_id,
        "stage": stage,
        "scenario": scenario,
        "kind": kind,
        "status": manifest_status(manifest),
        "root_commit": root_commit,
        "native_commit": native_commit,
        "build_sha256": sha,
        "evidence_paths": [str(manifest_path)],
        "notes": notes or f"imported from {manifest_path}",
    }
    problems = validate_record(record)
    if problems:
        raise ValueError("; ".join(problems))
    return record


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    report_parser = sub.add_parser("report", help="evaluate records into a matrix report")
    report_parser.add_argument("--records", action="append", default=[],
                               help="record file or directory (repeatable)")
    report_parser.add_argument("--output", type=Path, required=True)
    report_parser.add_argument("--root-commit", default="")
    report_parser.add_argument("--native-commit", default="")

    validate_parser = sub.add_parser("validate", help="validate record files")
    validate_parser.add_argument("--records", action="append", default=[])

    import_parser = sub.add_parser("import-run",
                                   help="convert a run manifest into an evidence record")
    import_parser.add_argument("--manifest", type=Path, required=True)
    import_parser.add_argument("--id", required=True)
    import_parser.add_argument("--stage", required=True, choices=stage_keys())
    import_parser.add_argument("--scenario", required=True, choices=sorted(SCENARIOS))
    import_parser.add_argument("--kind", required=True, choices=list(EVIDENCE_KINDS))
    import_parser.add_argument("--root-commit", default="")
    import_parser.add_argument("--native-commit", default="")
    import_parser.add_argument("--build-sha256", default="")
    import_parser.add_argument("--notes", default="")
    import_parser.add_argument("--out", type=Path, required=True)

    args = parser.parse_args(argv)

    if args.command == "import-run":
        manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
        record = record_from_manifest(manifest, args.manifest, record_id=args.id,
                                      stage=args.stage, scenario=args.scenario, kind=args.kind,
                                      root_commit=args.root_commit,
                                      native_commit=args.native_commit,
                                      build_sha256=args.build_sha256, notes=args.notes)
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(record, sort_keys=True, indent=2) + "\n",
                            encoding="utf-8")
        print(f"record id={record['id']} stage={record['stage']} "
              f"scenario={record['scenario']} kind={record['kind']} status={record['status']}")
        print(f"wrote {args.out}")
        return 0

    if args.command == "validate":
        records = []
        for source in args.records:
            records.extend(load_records(source))
        problems = check_records(records)
        for problem in problems:
            print(f"INVALID {problem}")
        print(f"validated {len(records)} records, {len(problems)} problems")
        return 1 if problems else 0

    records = []
    for source in args.records:
        records.extend(load_records(source))
    problems = check_records(records)
    if problems:
        for problem in problems:
            print(f"INVALID {problem}", file=sys.stderr)
        return 1
    pin = {}
    if args.root_commit:
        pin["root_commit"] = args.root_commit
    if args.native_commit:
        pin["native_commit"] = args.native_commit
    report = build_report(records, pin=pin)
    output = _write_outputs(report, args.output)
    print(json.dumps(report["summary"], sort_keys=True))
    print(f"wrote {output / 'qa-matrix.json'} and {output / 'qa-matrix.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
