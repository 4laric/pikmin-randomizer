"""Machine-readable provenance for production-binary acceptance runs (#615).

``scripts/build_pikmin2_fixture.py`` emits hash-pinned ``provenance.json``
only for replacement-main fixture builds. Production-binary acceptance runs,
which carry most natural gameplay evidence, had no equivalent artifact: every
runtime handoff hand-rolled native head/dirty, build directory, exe sha256,
arena hash and log hash into prose. This module closes that gap with ONE
additive recorder: given a native worktree/commit, a private build directory,
the built executable, a fresh arena directory and the run log, it verifies
each input and emits a single provenance JSON binding them with timestamps,
failing closed on dirty trees, hash mismatches or missing files.

Builder hash helpers (`sha256`, `snapshot`, `git_state`) are reused by
import; `scripts/build_pikmin2_fixture.py` itself is never modified here.
This module never builds, never runs a game, grants no admission and makes
no gameplay PASS claim: it only binds evidence that already exists.
"""

import argparse
import datetime
import hashlib
import json
import sys
from pathlib import Path

from scripts import build_pikmin2_fixture as builder

SCHEMA = 1
def utcnow():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def _require_file(path, what):
    path = Path(path)
    if not path.is_file():
        raise ValueError("missing %s: %s" % (what, path))
    return path


def file_record(path, what):
    """Snapshot one file with before/after stat guard (via the builder)."""
    path = _require_file(path, what)
    snap = builder.snapshot([path])
    digest = snap[str(path.resolve())]
    with path.open("rb") as stream:
        lines = sum(1 for _ in stream)
    return dict(path=str(path), sha256=digest["sha256"],
                size=digest["size"], lines=lines)


def native_record(native, expected_head):
    """Verify the native tree is clean and at the expected commit."""
    native = Path(native)
    if not (native / ".git").exists() and not _is_worktree(native):
        raise ValueError("not a native git worktree: %s" % native)
    try:
        state = builder.git_state(native)
    except ValueError as error:
        raise ValueError("cannot read native git state: %s" % error)
    if state["head"] != expected_head:
        raise ValueError("native head %s != expected %s"
                         % (state["head"], expected_head))
    modified = state.get("tracked_modified_sha256") or {}
    if state["status"] or modified:
        raise ValueError("native tree dirty: status=%r modified=%s"
                         % (state["status"], sorted(modified)))
    return dict(worktree=str(native), expected_head=expected_head,
                observed_head=state["head"], dirty="",
                tracked_modified_sha256=modified)


def _is_worktree(path):
    return (Path(path) / ".git").is_file()


def arena_record(arena):
    """Bind a fresh arena directory without walking retail junctions.

    Only top-level regular files (receipts, configs, bootstrap/state) are
    hashed; subdirectories such as ``assets`` or ``capture`` are recorded by
    name only so overlay junctions are never traversed.
    """
    arena = Path(arena)
    if not arena.is_dir():
        raise ValueError("missing arena directory: %s" % arena)
    top_files = sorted(p for p in arena.iterdir() if p.is_file())
    snap = builder.snapshot(top_files) if top_files else {}
    files = {p.name: {"sha256": snap[str(p.resolve())]["sha256"],
                      "size": snap[str(p.resolve())]["size"]}
             for p in top_files}
    subdirs = sorted(p.name for p in arena.iterdir() if p.is_dir())
    manifest = files.get("arena.json", {}).get("sha256")
    return dict(directory=str(arena), files=files, subdirs=subdirs,
                arena_json_sha256=manifest)


def record(native, expected_head, build_dir, exe, arena, log):
    """Verify every input and return the provenance record (no I/O besides reads)."""
    build_dir = Path(build_dir)
    if not build_dir.is_dir():
        raise ValueError("missing build directory: %s" % build_dir)
    rec = dict(schema=SCHEMA, kind="production-run-provenance",
               created_utc=utcnow(),
               tool="scripts/pikmin2_provenance_run.py",
               native=native_record(native, expected_head),
               build=dict(directory=str(build_dir),
                          executable=file_record(exe, "executable")),
               arena=arena_record(arena),
               log=file_record(log, "run log"))
    self_check(rec)
    return rec


def self_check(record):
    """Validate a provenance record shape; read-only, raises on violation."""
    if not isinstance(record, dict):
        raise ValueError("record must be a dict")
    if record.get("schema") != SCHEMA:
        raise ValueError("unsupported provenance schema")
    if record.get("kind") != "production-run-provenance":
        raise ValueError("wrong provenance kind")
    native = record.get("native") or {}
    if not native.get("observed_head") or native.get("dirty") != "":
        raise ValueError("native identity not clean-pinned")
    exe = ((record.get("build") or {}).get("executable")) or {}
    for key in ("sha256", "size"):
        if not exe.get(key):
            raise ValueError("executable %s missing" % key)
    if len(str(exe.get("sha256") or "")) != 64:
        raise ValueError("executable sha256 malformed")
    log = record.get("log") or {}
    for key in ("sha256", "size", "lines"):
        if log.get(key) in (None, ""):
            raise ValueError("log %s missing" % key)
    arena = record.get("arena") or {}
    if not isinstance(arena.get("files"), dict):
        raise ValueError("arena file manifest missing")
    return True


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--native", type=Path, required=True)
    parser.add_argument("--expected-head", required=True)
    parser.add_argument("--build-dir", type=Path, required=True)
    parser.add_argument("--exe", type=Path, required=True)
    parser.add_argument("--arena", type=Path, required=True)
    parser.add_argument("--log", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    rec = record(args.native, args.expected_head, args.build_dir,
                 args.exe, args.arena, args.log)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(rec, indent=2, sort_keys=True) + "\n",
                           encoding="utf-8")
    print(json.dumps({"provenance": str(args.output),
                      "exe": rec["build"]["executable"]["sha256"],
                      "log": rec["log"]["sha256"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())