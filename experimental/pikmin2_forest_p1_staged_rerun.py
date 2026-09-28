"""Staged-asset re-run adapter for the forest P1 native runtime (#660).

Recovery 91743167: the done #660 lane proved its fixture builds and guards green,
but its headed boot stalled pre-idle. The #717 diagnosis proved that stall class
data-dependent (a run root missing assets/dataDir/SndData blocks inside
System::Initialise; a staged root reaches idle). This adapter stages a private run
root carrying the forest P1 layout plus the hash-pinned JAudio asset set, reusing the
#660 fixture + runner read-only (never edited, never re-owned).

Fail-closed: absent disc sources, missing required JAudio members, hash drift, or a
tampered layout raise before any verdict. The adapter writes only the run root. No
engine, no gameplay claims; gates are claimed solely on observed markers.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

ISSUE = 660
DOWNSTREAM_ISSUE = 149

# Required JAudio members under assets/dataDir/SndData (relative). Siblings
# (*.aw wave archives) are staged opportunistically and pinned when present.
REQUIRED_JAUDIO = ("Seqs/pikiseq.arc", "Banks/pikibank.bx")


class StageGapError(ValueError):
    """Staging inputs are missing, drifted, or unusable; fail closed."""


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_runner(runner_path):
    """Import the #660 runner read-only by path (never edited, never owned)."""
    path = Path(runner_path)
    if not path.is_file():
        raise StageGapError("runner missing: %s" % path)
    spec = importlib.util.spec_from_file_location("p2_forest_p1_runner_ro", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def stage_jaudio(source_snddata, run_root):
    """Copy SndData into the run root and hash-pin every staged file."""
    source = Path(source_snddata)
    if not source.is_dir():
        raise StageGapError("SndData source missing: %s" % source)
    dest = Path(run_root) / "assets" / "dataDir" / "SndData"
    pins = {}
    staged = []
    for member in sorted(p for p in source.rglob("*") if p.is_file()):
        rel = member.relative_to(source).as_posix()
        target = dest / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(member.read_bytes())
        digest = sha256_file(target)
        pins["assets/dataDir/SndData/" + rel] = digest
        staged.append(rel)
    for required in REQUIRED_JAUDIO:
        if "assets/dataDir/SndData/" + required not in pins:
            raise StageGapError("required JAudio member missing: %s" % required)
    return {"pins": pins, "staged": staged}


def stage_run_root(manifest_path, seed_path, source_snddata, run_root, runner,
                   pins=None):
    """Stage the forest P1 layout (via #660, read-only) plus JAudio pins."""
    manifest_path, seed_path = Path(manifest_path), Path(seed_path)
    for label, path in (("manifest", manifest_path), ("seed", seed_path)):
        if not path.is_file():
            raise StageGapError("missing %s: %s" % (label, path))
    run_root = Path(run_root)
    run_root.mkdir(parents=True, exist_ok=True)
    record = runner.stage_run_layout(str(manifest_path), str(seed_path),
                                     str(run_root), dict(pins or {}))
    jaudio = stage_jaudio(source_snddata, run_root)
    record["jaudio_pins"] = jaudio["pins"]
    record["jaudio_staged"] = jaudio["staged"]
    meta_path = run_root / "forest-p1" / "run-metadata.json"
    meta_path.write_text(json.dumps(record, indent=1, sort_keys=True) + "\n",
                         encoding="utf-8")
    return record


def validate_staged_root(run_root, runner):
    """Refuse a staged root whose layout or JAudio pins drifted."""
    problems = list(runner.validate_run_layout(str(run_root)))
    meta_path = Path(run_root) / "forest-p1" / "run-metadata.json"
    try:
        record = json.loads(meta_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return problems + ["missing-or-bad-run-metadata"]
    for rel, digest in (record.get("jaudio_pins") or {}).items():
        target = Path(run_root) / rel
        try:
            actual = sha256_file(target)
        except OSError:
            problems.append("missing-staged-asset:" + rel)
            continue
        if actual != digest:
            problems.append("hash-mismatch-staged-asset:" + rel)
    return problems


def verify_run_log(runner, log_text):
    """Map a headed run log to boundary verdicts via the #660 verifier."""
    if not isinstance(log_text, str):
        raise StageGapError("run log must be text")
    return runner.verify_run_log(log_text)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--seed", required=True)
    parser.add_argument("--snddata", required=True)
    parser.add_argument("--runner", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--pins", default="{}")
    parser.add_argument("--check", action="store_true",
                        help="validate an already-staged root instead of staging")
    args = parser.parse_args(argv)
    try:
        runner = load_runner(args.runner)
        if args.check:
            problems = validate_staged_root(args.out, runner)
            print(json.dumps({"problems": problems}, indent=1))
            return 0 if not problems else 1
        try:
            pins = json.loads(args.pins)
        except ValueError as exc:
            print("bad --pins JSON: %s" % exc)
            return 2
        record = stage_run_root(args.manifest, args.seed, args.snddata,
                                args.out, runner, pins)
    except (StageGapError, ValueError, OSError) as exc:
        print("refused: %s" % exc)
        return 2
    print(json.dumps({k: record[k] for k in ("schema", "jaudio_staged")
                      if k in record}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())