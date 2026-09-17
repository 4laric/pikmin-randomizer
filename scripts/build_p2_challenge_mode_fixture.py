"""Private leased build/run harness for the #651 challenge host-mode fixture.

Builds ``native/tools/p2_challenge_mode_fixture.cpp`` (a replacement-main TU)
against a private leased ``pikmin_pc`` build using the established
replacement-main pattern (``scripts/build_pikmin2_fixture.py``: build.ninja
edge reuse, no shared CMake/CTest edit), then runs the guarded chain.

Phases: ``configure`` (leased cmake), ``build`` (leased pikmin_pc + ninja -n),
``fixture`` (provenance-checked link, exe SHA-256),
``guardcheck`` (live self-test + compiled header-only negative path),
``run`` (headed chain run with ordered-marker validation), ``all``.

The #651 fixture consumes the captain guard header-only
(``p2_fixture_captain_guard.h``), which lives in the canonical checkout's
``scripts/`` -- outside any native include dir. The harness does NOT copy or
edit it: it resolves the file read-only, records its SHA-256, and exposes it
to the fixture compile via ``CPLUS_INCLUDE_PATH`` (a standard compiler
mechanism; the header then enters the builder's own fixture-input snapshot,
so provenance pins it automatically).

Captain safety #632: the guard runs before every observed fixture tick; a
captain-down exits 86 (BLOCKED) with ``P2_FIXTURE_CAPTAIN_DOWN`` and can never
be recorded as a live tick. Protected observation cannot prove captain damage.
"""

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CANONICAL_ROOT = Path("C:/Users/alari/pikmin-randomizer")
sys.path.insert(0, str(CANONICAL_ROOT))

FIXTURE_REL = Path("tools/p2_challenge_mode_fixture.cpp")
GUARD_NAME = "p2_fixture_captain_guard.h"
NEGATIVE_EXIT = 86


def sha256(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def resolve_guard(guard_dir=None):
    """Locate the canonical guard header read-only; fail closed if absent."""
    if guard_dir is not None:
        candidate = Path(guard_dir) / GUARD_NAME
    else:
        candidate = ROOT / "scripts" / GUARD_NAME
    if not candidate.is_file():
        raise ValueError("Missing captain guard header: " + str(candidate))
    return candidate.resolve()


def guard_record(guard_dir=None):
    path = resolve_guard(guard_dir)
    return {"path": str(path), "sha256": sha256(path)}


def parse_markers(text):
    """Extract (kind, fields) challenge/guard markers from fixture output."""
    rows = []
    for line in text.splitlines():
        if line.startswith("P2_CHALLENGE_MODE_"):
            head, _, _ = line.partition(" ")
            kind = head[len("P2_CHALLENGE_MODE_"):]
            rows.append((kind, line))
        elif line.startswith("P2_FIXTURE_CAPTAIN_DOWN"):
            rows.append(("CAPTAIN_DOWN", line))
    return rows


def check_chain(rows):
    """Require the headed chain's ordered markers; return (ok, detail)."""
    kinds = [kind for kind, _ in rows]
    if "CAPTAIN_DOWN" in kinds:
        return False, "captain-down during chain run"
    required = ["BOOT", "TICK", "DONE"]
    positions = {}
    for want in required:
        try:
            positions[want] = kinds.index(want)
        except ValueError:
            return False, "missing marker: " + want
    if not (positions["BOOT"] < positions["TICK"] < positions["DONE"]):
        return False, "markers out of order"
    ticks = kinds.count("TICK")
    if ticks < 3:
        return False, "expected at least 3 TICK markers, saw %d" % ticks
    return True, "chain BOOT..TICK(x%d)..DONE in order" % ticks


def interpret_exit(code, text):
    """Classify a fixture exit: live PASS, guard BLOCKED, or failure."""
    rows = parse_markers(text)
    if code == NEGATIVE_EXIT and any(k == "CAPTAIN_DOWN" for k, _ in rows):
        return {"verdict": "blocked", "detail": "guard CAPTAIN_DOWN exit 86"}
    if code == 0:
        ok, detail = check_chain(rows)
        return {"verdict": "pass" if ok else "fail", "detail": detail}
    return {"verdict": "fail", "detail": "exit %d" % code}


def negative_source():
    return ('#include "%s"\n'
            "int main()\n"
            "{\n"
            "    p2_fixture_require_captain(true, false, 0.0f, 7);\n"
            '    std::printf("P2_CHALLENGE_MODE_NEGATIVE_UNREACHABLE\\n");\n'
            "    return 0;\n"
            "}\n" % GUARD_NAME)


def build_negative(compiler, guard_dir, workdir):
    """Compile the header-only negative TU; return the exe path."""
    workdir = Path(workdir)
    src = workdir / "guard_negative.cpp"
    src.write_text(negative_source(), encoding="utf-8")
    exe = workdir / "guard_negative.exe"
    env = dict(os.environ, PATH=str(Path(compiler).parent) + os.pathsep
               + os.environ.get("PATH", ""))
    proc = subprocess.run(
        [str(compiler), "-std=c++17", "-I", str(guard_dir),
         str(src), "-o", str(exe)],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
        encoding="utf-8", errors="replace", timeout=120, env=env)
    if proc.returncode or not exe.is_file():
        raise RuntimeError("Negative guard TU failed to compile: "
                           + proc.stdout[-2000:])
    return exe


def run_exe(exe, timeout=300):
    proc = subprocess.run(
        [str(exe)], stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, encoding="utf-8", errors="replace", timeout=timeout,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    return proc.returncode, proc.stdout

def evidence_record(**fields):
    record = {"schema": 1, "kind": "p2-challenge-mode-build"}
    record.update(fields)
    return record


def validate_evidence(record):
    if not isinstance(record, dict) or record.get("schema") != 1:
        raise ValueError("Evidence schema must be 1")
    for key in ("native_head", "exe_sha256", "guard_sha256",
                "ninja_dry_run", "chain", "exit"):
        if key not in record:
            raise ValueError("Evidence missing: " + key)
    if record["chain"] != "pass":
        raise ValueError("Chain run did not pass")
    if record["exit"] != 0:
        raise ValueError("Fixture exit was not 0")
    return record


def toolchain(ninja_dir=None):
    if ninja_dir is None:
        import ninja
        ninja_dir = str(Path(ninja.BIN_DIR))
    return ninja_dir


def lease_key():
    return "p2-challenge-host-mode-build-harness"


def lease_generation(reg=None):
    """Current lane generation (never a stale hardcoded fence)."""
    if reg is None:
        from workflow.registry import Registry
        reg = Registry(CANONICAL_ROOT / "output/workflow/registry.sqlite3",
                       CANONICAL_ROOT)
    return reg.status()["lanes"][lease_key()]["generation"]


def acquire(resource, pid, ttl=300):
    from workflow.registry import Registry
    reg = Registry(CANONICAL_ROOT / "output/workflow/registry.sqlite3", CANONICAL_ROOT)
    return reg, reg.acquire(lease_key(), lease_generation(), resource, pid,
                            ttl=ttl)


def renew(reg, resource, token, ttl=300):
    return reg.renew(lease_key(), lease_generation(), resource, token, ttl=ttl)


def release(reg, resource, token):
    return reg.release(lease_key(), lease_generation(), resource, token)


def child_env(ninja_dir):
    return dict(os.environ,
                PATH="C:/msys64/mingw64/bin;" + str(ninja_dir) + ";"
                + os.environ.get("PATH", ""))


def run_under_lease(resource, commands, cwd, log_path, poll=5, env=None):
    """Run shell commands under the private-build/pool lease.

    Mirrors the established leased-runner pattern: an idle child holds the
    lease while the parent feeds it commands and renews; the lease is
    released only after the child exits.
    """
    from workflow.handoff import Rejected
    code = ("import json,subprocess,sys\n"
            "d=json.loads(sys.stdin.readline())\n"
            "for command in d['commands']:\n"
            ' print("COMMAND "+json.dumps(command),flush=True)\n'
            " result=subprocess.run(command,cwd=d['cwd'])\n"
            " if result.returncode: sys.exit(result.returncode)\n")
    log_path = Path(log_path)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("w", encoding="utf-8") as stream:
        child = subprocess.Popen(
            [sys.executable, "-u", "-c", code], stdin=subprocess.PIPE,
            stdout=stream, stderr=subprocess.STDOUT, text=True, env=env,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        from workflow.registry import Registry
        reg = Registry(CANONICAL_ROOT / "output/workflow/registry.sqlite3", CANONICAL_ROOT)
        lease = None
        try:
            waited = 0
            while lease is None:
                result = reg.acquire(lease_key(), lease_generation(),
                                     resource, child.pid, ttl=300)
                if result["acquired"]:
                    lease = result["lease"]
                    break
                if waited % 60 == 0:
                    stream.write("LEASE_WAIT reason=%s\n"
                                 % result.get("reason", "queued"))
                    stream.flush()
                time.sleep(poll)
                waited += poll
            child.stdin.write(json.dumps(
                {"commands": commands, "cwd": str(cwd)}) + "\n")
            child.stdin.close()
            while child.poll() is None:
                try:
                    renew(reg, resource, lease["token"], ttl=300)
                except Rejected:
                    if child.poll() is None:
                        raise
                    break
                time.sleep(poll)
            result = child.wait()
        finally:
            if lease is not None and child.poll() is not None:
                try:
                    release(reg, resource, lease["token"])
                except Rejected:
                    pass
    return result


def phase_configure(native, build, ninja_dir, log_path):
    native, build = Path(native), Path(build)
    return run_under_lease(
        "build:" + str(build.resolve()),
        [["cmake", "-S", str(native), "-B", str(build), "-G", "Ninja",
          "-DCMAKE_C_COMPILER=gcc", "-DCMAKE_CXX_COMPILER=g++",
          "-DCMAKE_MAKE_PROGRAM=" + str(Path(ninja_dir) / "ninja.exe"),
          "-DCMAKE_BUILD_TYPE=Release", "-DPIKMIN_NATIVE_JAUDIO=ON",
          "-DPIKMIN_NATIVE_OPTIMIZE=OFF"]],
        native, log_path, env=child_env(ninja_dir))


def phase_build(build, log_path, ninja_dir):
    build = Path(build)
    return run_under_lease(
        "build:" + str(build.resolve()),
        [["cmake", "--build", str(build), "--target", "pikmin_pc", "-j", "6"],
         ["cmake", "--build", str(build), "--target", "pikmin_pc",
          "--", "-n"]],
        build, log_path, env=child_env(ninja_dir))


def phase_fixture(native, build, output, expected_head, guard_dir, log_path):
    from scripts import build_pikmin2_fixture as builder
    native, build, output = Path(native), Path(build), Path(output)
    fixture = (native / FIXTURE_REL).resolve()
    if not fixture.is_file():
        raise ValueError("Missing fixture TU: " + str(fixture))
    guard = resolve_guard(guard_dir)
    env = dict(os.environ)
    env["PATH"] = "C:/msys64/mingw64/bin;" + env.get("PATH", "")
    env["CPLUS_INCLUDE_PATH"] = (str(guard.parent)
                                 + os.pathsep
                                 + env.get("CPLUS_INCLUDE_PATH", ""))
    old = dict(os.environ)
    try:
        os.environ.clear()
        os.environ.update(env)
        stamp = "fixture-%d" % time.time_ns()
        record = builder.build_fixture(build, native, fixture,
                                       output / stamp, expected_head)
    finally:
        os.environ.clear()
        os.environ.update(old)
    if record.get("status") != "built":
        raise RuntimeError("Fixture build rejected: "
                           + str(record.get("error")))
    exe = output / stamp / "fixture.exe"
    Path(log_path).write_text(json.dumps(
        {"status": record["status"],
         "exe_sha256": sha256(exe),
         "provenance": str(output / stamp / "provenance.json")},
        indent=2) + "\n", encoding="utf-8")
    return 0

def phase_guardcheck(exe, compiler, guard_dir, log_path):
    code, text = run_exe(exe)
    verdict = interpret_exit(code, text)
    if verdict["verdict"] != "pass":
        raise RuntimeError("Live self-test failed: "
                           + verdict["detail"] + "\n" + text[-2000:])
    with tempfile.TemporaryDirectory(prefix="p2guardneg") as tmp:
        negative = build_negative(compiler, guard_dir, tmp)
        ncode, ntext = run_exe(negative)
    nverdict = interpret_exit(ncode, ntext)
    if nverdict["verdict"] != "blocked":
        raise RuntimeError("Negative guard path failed: exit %d\n%s"
                           % (ncode, ntext[-2000:]))
    if "PASS" in ntext:
        raise RuntimeError("Negative path emitted PASS")
    Path(log_path).write_text(
        "self_test: exit=%d %s\nnegative: exit=%d %s\n"
        % (code, verdict["detail"], ncode, nverdict["detail"]),
        encoding="utf-8")
    return 0


def phase_run(exe, log_path):
    code, text = run_exe(exe)
    verdict = interpret_exit(code, text)
    Path(log_path).write_text(text, encoding="utf-8")
    if verdict["verdict"] != "pass":
        raise RuntimeError("Chain run failed: " + verdict["detail"])
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--native", type=Path, required=True)
    parser.add_argument("--build", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--expected-native-head", default=None)
    parser.add_argument("--guard-dir", default=None)
    parser.add_argument("--ninja-dir", default=None)
    parser.add_argument("--exe", type=Path, default=None)
    parser.add_argument("phases", nargs="+",
                        choices=("configure", "build", "fixture",
                                 "guardcheck", "run", "all"))
    args = parser.parse_args(argv)
    ninja_dir = args.ninja_dir or toolchain()
    out = args.output
    out.mkdir(parents=True, exist_ok=True)
    if "all" in args.phases:
        order = ("configure", "build", "fixture", "guardcheck", "run")
    else:
        order = args.phases
    exe = args.exe
    for phase in order:
        if phase == "configure":
            code = phase_configure(args.native, args.build, ninja_dir,
                                   out / "configure.log")
        elif phase == "build":
            code = phase_build(args.build, out / "build.log", ninja_dir)
        elif phase == "fixture":
            head = args.expected_native_head
            if head is None:
                head = subprocess.check_output(
                    ["git", "-C", str(args.native), "rev-parse", "HEAD"],
                    text=True).strip()
            code = phase_fixture(args.native, args.build, out, head,
                                 args.guard_dir, out / "fixture.json")
            if code == 0 and exe is None:
                exe = max(out.glob("fixture-*/fixture.exe"),
                          key=lambda p: p.stat().st_mtime_ns)
        elif phase == "guardcheck":
            if exe is None:
                raise SystemExit("guardcheck needs --exe or a prior fixture phase")
            compiler = Path("C:/msys64/mingw64/bin/g++.exe")
            guard = resolve_guard(args.guard_dir)
            code = phase_guardcheck(exe, compiler, guard.parent,
                                    out / "guardcheck.log")
        elif phase == "run":
            if exe is None:
                raise SystemExit("run needs --exe or a prior fixture phase")
            code = phase_run(exe, out / "run.log")
        if code:
            raise SystemExit("Phase %s failed; see %s"
                             % (phase, out / (phase + ".log")))
    print(json.dumps({"status": "ok", "output": str(out.resolve()),
                      "exe": str(exe) if exe else None}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())