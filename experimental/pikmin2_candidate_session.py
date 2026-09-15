"""Private pre-admission Snow/Dwarf Orange QA. Never changes the normal admitted roster.

Use plan/prepare with the same arguments as generated_session_acceptance, then
run --prepared <report>. Placement, content and native pin checks still apply.
The process-local override is deliberately confined to this diagnostic CLI.
``--source`` selects the private identity (default 45 Snow; 44 Dwarf Orange).
"""
from __future__ import annotations
import argparse
from contextlib import contextmanager
import json
from pathlib import Path
import sys
from unittest.mock import patch
from experimental import pikmin2_generated_session_acceptance as qa

SCOPE = "private-snow-candidate-v1"
SOURCE = 45


def scope_name(source):
    names = {45: "snow", 44: "dwarf-orange"}
    return f"private-{names.get(source, 'source-' + str(source))}-candidate-v1"

def _add_source_arg(parser):
    parser.add_argument("--source", type=int, default=SOURCE,
                        help="private identity: 45 Snow (default) or 44 Dwarf Orange")

@contextmanager
def candidate_scope(source=SOURCE):
    from experimental import pikmin2_seed_bridge as bridge
    # seed.validate imports this function from bridge at call time too.
    with patch.object(bridge, "admitted_ids", lambda roster: [source]):
        yield

def validate_candidate(manifest, source=SOURCE):
    bindings = (manifest.get("p2_layout") or {}).get("bindings") or []
    if not bindings or any(b.get("source_id") != source for b in bindings):
        raise qa.AcceptanceError(
            f"private candidate session supports only source {source} (Snow 45 or Dwarf Orange 44)")

def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for command in ("plan", "prepare"):
        p = sub.add_parser(command)
        qa._pin_args(p)
        p.add_argument("--seed", required=True)
        p.add_argument("--slot", default="Player1")
        p.add_argument("--placement", type=Path, required=True)
        p.add_argument("--output", type=Path, required=True)
        _add_source_arg(p)
        if command == "prepare":
            p.add_argument("--session-dir", type=Path, required=True)
            p.add_argument("--content-manifest", type=Path, required=True)
            p.add_argument("--content-base", type=Path)
    run = sub.add_parser("run")
    run.add_argument("--prepared", type=Path, required=True)
    _add_source_arg(run)
    args = parser.parse_args(argv)
    scope = scope_name(args.source)
    if args.command == "run":
        report = qa.load_json(args.prepared)
        if report.get("candidate_scope") != scope:
            raise qa.AcceptanceError(f"expected a private candidate preparation for source {args.source}")
        pin = qa.Pin.from_dict(report["pin"])
        pin.verify()
        manifest = qa.load_json(report["manifest"])
        validate_candidate(manifest, args.source)
        # Reconstruct arguments from verified inputs; never execute a report's
        # arbitrary launch command. The ordinary launcher stages real content.
        command = qa.launch_command(report["manifest"], report["session_dir"], pin,
                                    report["content_manifest_path"])
        from randomizer.__main__ import main as launch
        # candidate_scope (the bridge.admitted_ids patch) is the only private path;
        # the product admission set is never widened by environment variables.
        with candidate_scope(args.source), patch.object(sys, "argv", ["randomizer", *command[3:]]):
            return launch()
    pin = qa._pin_from_args(args)
    pin.verify()
    placement = qa.load_json(args.placement)
    with candidate_scope(args.source):
        if args.command == "plan":
            report = qa.plan_report(pin, args.seed, placement, slot=args.slot)
        else:
            manifest = qa.generate_pinned_session(args.seed, placement, slot=args.slot)
            validate_candidate(manifest, args.source)
            report = qa.prepare_session(pin, manifest, args.session_dir,
                       content_manifest=qa.load_json(args.content_manifest),
                       content_base=args.content_base or args.content_manifest.resolve().parent)
            report["content_manifest_path"] = str(args.content_manifest.resolve())
            report["launch"] = [sys.executable, "-m", __name__ if __name__ != "__main__"
                                else "experimental.pikmin2_candidate_session",
                                "run", "--prepared", str(args.output.resolve())]
    report["candidate_scope"] = scope
    report["product_admission"] = False
    report["evidence_kind"] = "pre_admission_candidate"
    qa.write_json(args.output, report)
    print(json.dumps({"candidate_scope": scope, "status": report.get("status", "PREPARED"),
                      "blocked_by": report.get("blocked_by", ""), "output": str(args.output)}))
    return 2 if report.get("status") == "BLOCKED" else 0

if __name__ == "__main__":
    raise SystemExit(main())
