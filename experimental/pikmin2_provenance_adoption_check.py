"""Reusable adoption checker for the production-run provenance recorder (#615).

Any family lane can use this to certify its own provenance record WITHOUT
importing engine code or the recorder tree: the checker shells out to a
recorder root's `scripts/pikmin2_provenance_run.py` (stdlib subprocess only),
loads the emitted JSON, and validates it end to end against caller-supplied
expectations (native head/dirty, exe sha256, log sha256, arena directory).

It also maps recorder output onto the handoff evidence fields lanes already
use (`exe`, `nativelog`, arena files, build provenance), so adoption is a
mechanical translation, not prose. Malformed input fails closed with
ValueError. Nothing here builds, runs a game, flips a gate, or admits
anything: staged versus production exes must be labelled by the caller.
"""
import json
import re
import subprocess
from pathlib import Path

HEX64_RE = re.compile(r"[0-9a-f]{64}")
HEX40_RE = re.compile(r"[0-9a-f]{40}")


class AdoptionError(ValueError):
    pass


def run_recorder(recorder_root, native, expected_head, build_dir, exe, arena,
                 log, output, python="py -3.12"):
    """Run the integrated recorder read-only; return its stdout summary dict.

    The recorder only reads its inputs and writes the provenance JSON to
    `output`. `recorder_root` is the tree containing
    `scripts/pikmin2_provenance_run.py` (e.g. the p2-main-review checkout).
    """
    script = Path(recorder_root) / "scripts" / "pikmin2_provenance_run.py"
    if not script.is_file():
        raise AdoptionError("recorder script missing: %s" % script)
    command = python.split() + [str(script), "--native", str(native),
                                "--expected-head", str(expected_head),
                                "--build-dir", str(build_dir),
                                "--exe", str(exe), "--arena", str(arena),
                                "--log", str(log), "--output", str(output)]
    try:
        proc = subprocess.run(command, capture_output=True, text=True,
                              errors="replace", timeout=600)
    except (OSError, subprocess.SubprocessError) as error:
        raise AdoptionError("recorder launch failed: %s" % error) from None
    if proc.returncode != 0:
        raise AdoptionError("recorder rejected inputs: %s"
                            % (proc.stderr.strip() or proc.stdout.strip()))
    try:
        return json.loads(proc.stdout)
    except ValueError as error:
        raise AdoptionError("recorder printed no JSON summary: %s" % error) from None


def load_provenance(path):
    """Load and shape-validate a provenance record (read-only)."""
    try:
        record = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise AdoptionError("unreadable provenance: %s" % error) from None
    if not isinstance(record, dict):
        raise AdoptionError("provenance must be a JSON object")
    if record.get("schema") != 1:
        raise AdoptionError("unsupported provenance schema")
    if record.get("kind") != "production-run-provenance":
        raise AdoptionError("wrong provenance kind")
    native = record.get("native") or {}
    if not HEX40_RE.fullmatch(str(native.get("observed_head") or "")):
        raise AdoptionError("native observed_head is not a full commit")
    if native.get("dirty") != "":
        raise AdoptionError("native identity is not clean-pinned")
    exe = ((record.get("build") or {}).get("executable")) or {}
    if not HEX64_RE.fullmatch(str(exe.get("sha256") or "")):
        raise AdoptionError("executable sha256 malformed")
    if not exe.get("size"):
        raise AdoptionError("executable size missing")
    log = record.get("log") or {}
    if not HEX64_RE.fullmatch(str(log.get("sha256") or "")):
        raise AdoptionError("log sha256 malformed")
    if log.get("lines") in (None, ""):
        raise AdoptionError("log line count missing")
    arena = record.get("arena") or {}
    if not isinstance(arena.get("files"), dict):
        raise AdoptionError("arena file manifest missing")
    return record


def check_record(record, expected_head=None, dirty="", exe_sha256=None,
                 log_sha256=None, arena_dir=None):
    """Cross-check a loaded record against caller expectations.

    Returns a findings dict; every check is explicit so a lane can cite
    exactly what matched. Raises AdoptionError on the first mismatch.
    """
    findings = {}
    native = record.get("native") or {}
    if expected_head is not None:
        findings["native_head"] = native.get("observed_head") == expected_head
        if not findings["native_head"]:
            raise AdoptionError("native head %s != expected %s"
                                % (native.get("observed_head"), expected_head))
    findings["native_clean"] = native.get("dirty", "?", ) == dirty
    if native.get("dirty") != dirty:
        raise AdoptionError("native dirty state %r != %r" % (native.get("dirty"), dirty))
    exe = ((record.get("build") or {}).get("executable")) or {}
    if exe_sha256 is not None:
        findings["exe_sha256"] = exe.get("sha256") == exe_sha256
        if not findings["exe_sha256"]:
            raise AdoptionError("executable sha256 mismatch")
    else:
        findings["exe_sha256"] = True
    log = record.get("log") or {}
    if log_sha256 is not None:
        findings["log_sha256"] = log.get("sha256") == log_sha256
        if not findings["log_sha256"]:
            raise AdoptionError("log sha256 mismatch")
    else:
        findings["log_sha256"] = True
    arena = record.get("arena") or {}
    if arena_dir is not None:
        findings["arena_dir"] = Path(arena.get("directory", "")) == Path(arena_dir)
        if not findings["arena_dir"]:
            raise AdoptionError("arena directory mismatch")
    else:
        findings["arena_dir"] = True
    findings["complete"] = True
    return findings


def map_to_handoff_evidence(record):
    """Translate recorder output onto handoff evidence fields.

    Returns {field: (path, sha256)} for `exe`, `nativelog`, plus the arena
    file manifest and the record itself under `provenance`. A lane copies
    these into its handoff `evidence` map instead of hand-rolling prose.
    """
    exe = ((record.get("build") or {}).get("executable")) or {}
    log = record.get("log") or {}
    arena = record.get("arena") or {}
    mapping = {
        "exe": (exe.get("path"), exe.get("sha256")),
        "nativelog": (log.get("path"), log.get("sha256")),
    }
    for name, info in arena.get("files", {}).items():
        mapping["arena:" + name] = (str(Path(arena.get("directory", "")) / name),
                                    info.get("sha256"))
    return mapping


def certify(recorder_root, native, expected_head, build_dir, exe, arena, log,
            output, exe_sha256=None, log_sha256=None, python="py -3.12"):
    """Run the recorder and certify its output in one call.

    Returns (record, findings, mapping). Raises AdoptionError on any failure.
    """
    run_recorder(recorder_root, native, expected_head, build_dir, exe, arena,
                 log, output, python)
    record = load_provenance(output)
    findings = check_record(record, expected_head=expected_head, dirty="",
                            exe_sha256=exe_sha256, log_sha256=log_sha256,
                            arena_dir=str(arena))
    return record, findings, map_to_handoff_evidence(record)
