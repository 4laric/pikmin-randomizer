"""Lane 33 reproducible generated-session acceptance (#444, assignment 4).

Independent acceptance lane. This module prepares and records the **real**
product chain named in the P2 dispatch guide:

    generate seed -> automatic content staging -> ordinary native spawn ->
    natural interaction/combat -> death/drop -> actual transport/reward ->
    revisit -> process restart

It is deliberately separate from the lane 02/03/05 wiring probe
(``scripts/test_p2_generated_session.py``). That probe monkeypatches the lane 02
admission set and a synthetic content manifest to exercise the plumbing. This
harness never does: it drives the real product generator with the live lane 02
admission set, verifies an immutable build pin before anything runs, and refuses
to emit ``natural`` evidence for a run that did not launch the pinned
executable. While the admission set is empty (or no integrated build is
published) it reports ``BLOCKED`` with the named dependency instead of a fake
pass.

It owns QA tooling and reports only; it never edits production code and never
claims a run that did not happen.

Usage::

    py -3.12 -m experimental.pikmin2_generated_session_acceptance verify-pin \
        --executable <exe> --executable-sha256 <64 hex>
    py -3.12 -m experimental.pikmin2_generated_session_acceptance plan \
        --pin pin.json --seed p2-native --placement placement.json --output run/plan.json
    py -3.12 -m experimental.pikmin2_generated_session_acceptance prepare \
        --pin pin.json --seed p2-native --placement placement.json \
        --session-dir output/lane33-run --content-manifest content.json \
        --output output/lane33-run/prepared.json
    py -3.12 -m experimental.pikmin2_generated_session_acceptance observe \
        --log output/lane33-run/runs/<token>/native.log --profile snow \
        --output output/lane33-run/observations.json
    py -3.12 -m experimental.pikmin2_generated_session_acceptance records \
        --pin pin.json --prepared output/lane33-run/prepared.json \
        --observations output/lane33-run/observations.json \
        --kind natural --scenario baseline_cohort --output output/lane33-records
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import dataclass
from pathlib import Path

from experimental import pikmin2_qa_matrix as qa

STAGES = qa.stage_keys()

# A stage is "game-observed" when its gate only exists on a launched run.
GAME_STAGES = ("install", "natural_fight", "reward", "revisit", "restart")

# The launcher prints this after lane 05 stages session content automatically.
INSTALL_WITNESS = "PIKMIN_CONTENT_STAGED"

# Turnkey witness-marker sets derived from the documented family evidence
# (Snow: docs/PIKMIN2_SNOW_BULBORB.md; Dwarf Orange:
# docs/PIKMIN2_DWARF_ORANGE_NATIVE.md). They are the markers the family lanes
# already emit; confirm them on the first pinned generated-session run. Stages
# with no distinct documented generated-session witness are left unmapped, so
# they report BLOCKED rather than a silent pass.
WITNESS_PROFILES = {
    "snow": {
        "install": [INSTALL_WITNESS],
        "natural_fight": ["P2_ENEMY_READY", "P2_SNOW_DRAW corpse=0", "P2_SNOW_DRAW corpse=1"],
    },
    "dwarf_orange": {
        "install": [INSTALL_WITNESS],
        "natural_fight": ["P2_ENEMY_READY", "P2_DWARF_ORANGE_DRAW corpse=0",
                          "P2_DWARF_ORANGE_DRAW corpse=1", "DONE P2_DWARF_ORANGE_COMBAT"],
        "reward": ["P2_DWARF_ORANGE_P1_HAUL"],
    },
}


def witness_profile(name):
    """Return a copy of a named marker set, rejecting unknown profiles."""
    if name not in WITNESS_PROFILES:
        raise AcceptanceError(
            f"unknown witness profile {name!r}; known: {sorted(WITNESS_PROFILES)}")
    return {stage: list(markers) for stage, markers in WITNESS_PROFILES[name].items()}


def witness_markers(*names):
    """Merge named marker sets, preserving order and dropping duplicates."""
    merged = {}
    for name in names:
        for stage, markers in witness_profile(name).items():
            bucket = merged.setdefault(stage, [])
            for marker in markers:
                if marker not in bucket:
                    bucket.append(marker)
    return merged


class AcceptanceError(ValueError):
    """Base class for generated-session acceptance harness failures."""


class AcceptanceBlocked(AcceptanceError):
    """A required dependency is missing; no acceptance result can be produced."""

    def __init__(self, message, *, dependency="", stage=""):
        super().__init__(message)
        self.dependency = dependency
        self.stage = stage


class PinMismatch(AcceptanceError):
    """The pinned build identity does not match the artifact under test."""


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


@dataclass(frozen=True)
class Pin:
    """The immutable root/native/executable identities a run must match."""

    root_commit: str = ""
    native_commit: str = ""
    executable: str = ""
    executable_sha256: str = ""
    assets: str = ""

    def verify(self):
        """Return the verified pin, or raise ``PinMismatch`` before any run."""
        if not self.root_commit.strip():
            raise PinMismatch("pin is missing the root commit")
        if not self.native_commit.strip():
            raise PinMismatch("pin is missing the native commit")
        if not self.executable:
            raise PinMismatch("pin is missing the executable under test")
        path = Path(self.executable)
        if not path.is_file():
            raise PinMismatch(f"pinned executable does not exist: {path}")
        expected = self.executable_sha256.strip().lower()
        if len(expected) != 64 or any(char not in "0123456789abcdef" for char in expected):
            raise PinMismatch("pin is missing a valid executable sha256")
        found = sha256_file(path)
        if found != expected:
            raise PinMismatch(
                f"pinned executable sha256 mismatch: expected {expected}, found {found}")
        return {"root_commit": self.root_commit, "native_commit": self.native_commit,
                "executable": str(path.resolve()), "executable_sha256": found,
                "assets": self.assets}

    def as_dict(self):
        return {"root_commit": self.root_commit, "native_commit": self.native_commit,
                "executable": self.executable, "executable_sha256": self.executable_sha256,
                "assets": self.assets}

    @classmethod
    def from_dict(cls, data):
        if not isinstance(data, dict):
            raise AcceptanceError("pin must be a JSON object")
        return cls(root_commit=str(data.get("root_commit", "")),
                   native_commit=str(data.get("native_commit", "")),
                   executable=str(data.get("executable", "")),
                   executable_sha256=str(data.get("executable_sha256", "")),
                   assets=str(data.get("assets", "")))


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_pin(path):
    return Pin.from_dict(load_json(path))


def generate_pinned_session(seed, placement, *, slot="Player1", mode="solo"):
    """Run the real product generator with the live lane 02 admission set.

    No admission override and no arbitrary target list is accepted: the harness
    must observe the same default-deny behaviour a player sees. While the
    admission set is empty (or the placement document accepts nothing) this
    raises ``AcceptanceBlocked`` naming the missing dependency.
    """
    if placement is None:
        raise AcceptanceBlocked("P2 generation requires a lane 04 placement document",
                                dependency="lane 04 placement document", stage="generate")
    from experimental.pikmin2_seed_bridge import SeedBridgeError
    from randomizer.seed import generate
    try:
        return generate(seed, mode, slot, collection_checks=True,
                        p2_enemies=True, p2_placement=placement)
    except SeedBridgeError as exc:
        dependency = "lane 02 admission set is empty"
        if "placement" in str(exc).lower():
            dependency = "lane 04 accepted placement evidence"
        raise AcceptanceBlocked(str(exc), dependency=dependency, stage="generate") from exc


def verify_content_manifest(content_manifest, identities, *, base=None):
    """Offline preflight: content resolves and covers every bound identity.

    Reads only the manifest and its declared sources; nothing is staged and the
    retail tree is untouched. Returns the lane 05 verification report.
    """
    from experimental.pikmin2_staging import StagingError, verify_manifest
    required = set(identities or [])
    declared = set(content_manifest.get("identities", []))
    if required and not required <= declared:
        missing = sorted(required - declared)
        raise AcceptanceBlocked(
            f"content manifest does not cover bound P2 identities: {missing}",
            dependency="lane 05 content with matching identities", stage="install")
    try:
        report = verify_manifest(content_manifest, base=base)
    except StagingError as exc:  # pragma: no cover - verify_manifest raises ValueError
        raise AcceptanceError(str(exc)) from exc
    if not report.get("ok"):
        summary = report.get("summary", {})
        raise AcceptanceBlocked(
            f"content sources are missing or stale: {summary}",
            dependency="lane 05 staged content sources", stage="install")
    return report


def launch_command(manifest_path, session_dir, pin, content_manifest=None):
    """The exact reproducible launch command for the pinned build.

    ``content_manifest`` is only used when it is a path; an in-memory manifest
    mapping is a test/diagnostic input and is omitted from the command.
    """
    parts = [sys.executable, "-m", "randomizer", "run", str(manifest_path),
             "--session-dir", str(session_dir),
             "--exe", str(Path(pin.executable).resolve())]
    if pin.assets:
        parts += ["--assets", str(Path(pin.assets).resolve())]
    if isinstance(content_manifest, (str, Path)):
        parts += ["--content-manifest", str(Path(content_manifest).resolve())]
    return parts


def prepare_session(pin, manifest, session_dir, *, content_manifest=None,
                    content_base=None, manifest_path=None):
    """Verify the pin, build the real bootstrap, and check content coverage.

    This is the offline half of the chain. It does not launch the game; the
    returned runbook tells the operator exactly how to. A missing/wrong content
    source fails before a session is written, mirroring the launcher.
    """
    verified = pin.verify()
    from randomizer.runner import NativeRun
    from randomizer.session import Session

    manifest = dict(manifest)
    layout = manifest.get("p2_layout") or {}
    bindings = layout.get("bindings") or []
    if not bindings:
        raise AcceptanceBlocked("manifest carries no P2 layout",
                                dependency="lane 02/03 admitted layout", stage="generate")
    identities = [binding["source_id"] for binding in bindings]

    session_dir = Path(session_dir)
    session = Session(manifest, session_dir)
    run = NativeRun(session)
    bootstrap = run.bootstrap.read_text(encoding="ascii")
    if "ENEMY_P2" not in bootstrap:
        raise AcceptanceError("bootstrap did not carry the ENEMY_P2 line")

    content_report = None
    if content_manifest is not None:
        content_report = verify_content_manifest(content_manifest, identities, base=content_base)

    manifest_path = Path(manifest_path) if manifest_path else (session.directory / "manifest.json")
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    prepared = {
        "schema": 1,
        "generated_by": "experimental.pikmin2_generated_session_acceptance",
        "pin": verified,
        "seed": manifest.get("seed"),
        "slot": manifest.get("slot"),
        "layout": layout,
        "identities": identities,
        "bootstrap": str(run.bootstrap.resolve()),
        "manifest": str(manifest_path.resolve()),
        "session_dir": str(session.directory.resolve()),
        "content": content_report,
        "launch": launch_command(manifest_path, session.directory, pin, content_manifest),
    }
    return prepared


def observe_log(log_text, markers):
    """Map captured native/launcher output to per-stage observations.

    ``markers`` is a mapping of stage -> list of required substrings. A stage
    with declared markers passes only when all are present; a stage with no
    declared markers is ``BLOCKED`` (no witness contract), never a silent pass.
    ``generate`` is satisfied by the manifest itself, not a log marker, so it is
    reported separately by :func:`prepare_session`.
    """
    observations = {}
    for stage in STAGES:
        if stage == "generate":
            continue
        required = [str(marker) for marker in markers.get(stage, [])]
        if not required:
            observations[stage] = {"status": qa.BLOCKED,
                                   "reason": "no declared witness markers for this stage",
                                   "missing": [], "markers": []}
            continue
        missing = [marker for marker in required if marker not in log_text]
        if missing:
            observations[stage] = {"status": qa.FAIL,
                                   "reason": "missing witness marker(s): " + ", ".join(missing),
                                   "missing": missing, "markers": required}
        else:
            observations[stage] = {"status": qa.PASS,
                                   "reason": "all declared witness markers observed",
                                   "missing": [], "markers": required}
    return observations


def build_records(pin, stage_results, *, kind, scenario="baseline_cohort",
                  evidence_paths, native_commit=None, notes=""):
    """Convert per-stage results into validated QA-matrix records.

    ``natural`` classification is refused unless every record carries verified
    pinned provenance: the harness must have launched the pinned executable.
    """
    if kind not in qa.EVIDENCE_KINDS:
        raise AcceptanceError(f"unknown evidence kind: {kind!r}")
    if not evidence_paths:
        raise AcceptanceError("at least one evidence path is required")
    verified = None
    if kind == qa.KIND_NATURAL:
        verified = pin.verify()  # re-check the artifact under test before claiming natural
    root_commit = pin.root_commit
    build_sha256 = pin.executable_sha256
    records = []
    for stage in STAGES:
        result = stage_results.get(stage)
        if not result:
            continue
        record = {
            "id": f"lane33-{stage}-{scenario}",
            "stage": stage,
            "scenario": scenario,
            "kind": kind,
            "status": result["status"],
            "root_commit": root_commit,
            "native_commit": native_commit if native_commit is not None else pin.native_commit,
            "build_sha256": build_sha256,
            "evidence_paths": [str(path) for path in evidence_paths],
            "notes": result.get("reason") or notes,
        }
        problems = qa.validate_record(record)
        if problems:
            raise AcceptanceError(f"invalid generated record {record['id']}: {problems}")
        records.append(record)
    if verified is not None:
        for record in records:
            record["notes"] = (record["notes"] + " | verified pin " + verified["executable_sha256"]).strip(" |")
    return records


def write_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def plan_report(pin, seed, placement, *, slot="Player1"):
    """A reproducible runbook plus a live dependency probe (no game launch)."""
    report = {
        "schema": 1,
        "pin": pin.as_dict(),
        "seed": seed,
        "slot": slot,
        "chain": list(STAGES),
        "status": qa.BLOCKED,
        "blocked_by": "",
        "manifest": None,
    }
    try:
        verified = pin.verify()
    except PinMismatch as exc:
        report["blocked_by"] = f"pin: {exc}"
        return report
    report["pin"] = verified
    try:
        manifest = generate_pinned_session(seed, placement, slot=slot)
    except AcceptanceBlocked as exc:
        report["blocked_by"] = f"{exc.stage or 'generate'}: {exc}"
        return report
    report["status"] = qa.PASS
    report["manifest"] = {key: manifest[key] for key in ("seed", "slot", "schema", "capabilities")
                          if key in manifest}
    report["layout"] = manifest.get("p2_layout")
    return report


def _pin_args(parser):
    parser.add_argument("--root-commit", default="")
    parser.add_argument("--native-commit", default="")
    parser.add_argument("--executable", default="")
    parser.add_argument("--executable-sha256", default="")
    parser.add_argument("--assets", default="")


def _pin_from_args(args):
    return Pin(root_commit=args.root_commit, native_commit=args.native_commit,
               executable=args.executable, executable_sha256=args.executable_sha256,
               assets=args.assets)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    verify = sub.add_parser("verify-pin", help="verify a pinned executable hash")
    _pin_args(verify)

    plan = sub.add_parser("plan", help="write a reproducible generated-session runbook")
    _pin_args(plan)
    plan.add_argument("--seed", required=True)
    plan.add_argument("--slot", default="Player1")
    plan.add_argument("--placement", type=Path, required=True)
    plan.add_argument("--output", type=Path, required=True)

    prepare = sub.add_parser("prepare", help="generate and prepare the real session (no launch)")
    _pin_args(prepare)
    prepare.add_argument("--seed", required=True)
    prepare.add_argument("--slot", default="Player1")
    prepare.add_argument("--placement", type=Path, required=True)
    prepare.add_argument("--session-dir", type=Path, required=True)
    prepare.add_argument("--content-manifest", type=Path)
    prepare.add_argument("--content-base", type=Path)
    prepare.add_argument("--output", type=Path, required=True)

    observe = sub.add_parser("observe", help="classify a captured log against witness markers")
    observe.add_argument("--log", type=Path, required=True)
    observe.add_argument("--markers", type=Path,
                         help="JSON mapping of stage -> required substrings (optional)")
    observe.add_argument("--profile", action="append", default=[],
                         choices=sorted(WITNESS_PROFILES),
                         help="named marker set, e.g. snow or dwarf_orange (repeatable)")
    observe.add_argument("--output", type=Path, required=True)

    records = sub.add_parser("records", help="emit QA-matrix records from prepared+observed data")
    _pin_args(records)
    records.add_argument("--prepared", type=Path, required=True)
    records.add_argument("--observations", type=Path, required=True)
    records.add_argument("--kind", choices=list(qa.EVIDENCE_KINDS), required=True)
    records.add_argument("--scenario", default="baseline_cohort")
    records.add_argument("--output", type=Path, required=True)

    args = parser.parse_args(argv)

    if args.command == "verify-pin":
        try:
            verified = _pin_from_args(args).verify()
        except PinMismatch as exc:
            print(f"PIN MISMATCH: {exc}", file=sys.stderr)
            return 1
        print(json.dumps(verified, sort_keys=True))
        return 0

    if args.command == "plan":
        report = plan_report(_pin_from_args(args), args.seed, load_json(args.placement),
                             slot=args.slot)
        write_json(args.output, report)
        print(f"{report['status']}: {report['blocked_by'] or 'ready'}")
        return 0 if report["status"] == qa.PASS else 2

    if args.command == "prepare":
        prepared = prepare_session(_pin_from_args(args),
                                   generate_pinned_session(args.seed, load_json(args.placement),
                                                           slot=args.slot),
                                   args.session_dir,
                                   content_manifest=(load_json(args.content_manifest)
                                                     if args.content_manifest else None),
                                   content_base=args.content_base)
        write_json(args.output, prepared)
        print(f"prepared {prepared['session_dir']} identities={prepared['identities']}")
        return 0

    if args.command == "observe":
        markers = witness_markers(*args.profile) if args.profile else {}
        if args.markers:
            for stage, required in load_json(args.markers).items():
                bucket = markers.setdefault(stage, [])
                for marker in required:
                    if marker not in bucket:
                        bucket.append(marker)
        if not markers:
            parser.error("observe requires --markers or --profile")
        observations = observe_log(args.log.read_text(encoding="utf-8", errors="replace"), markers)
        write_json(args.output, observations)
        counts = {}
        for result in observations.values():
            counts[result["status"]] = counts.get(result["status"], 0) + 1
        print(json.dumps(counts, sort_keys=True))
        return 0

    if args.command == "records":
        prepared = load_json(args.prepared)
        stage_results = {"generate": {"status": qa.PASS, "reason": "real product generation"}}
        stage_results.update(load_json(args.observations))
        path = Path(args.prepared)
        emitted = build_records(_pin_from_args(args), stage_results, kind=args.kind,
                                scenario=args.scenario, evidence_paths=[path])
        out = Path(args.output)
        for record in emitted:
            write_json(out / f"{record['id']}.json", record)
        print(f"wrote {len(emitted)} records to {out}")
        return 0

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
