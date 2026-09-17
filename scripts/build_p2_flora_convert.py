"""Private leased build/run harness for the #697 flora conversion fixture.

Builds ``native/tools/p2_flora_convert_fixture.cpp`` (replacement-main TU,
riding ``pc_port/pc_p2_flora_convert.cpp`` via include so no CMake target
edit is needed) against a private leased ``pikmin_pc`` build using the
maintained replacement-main builder (``scripts/build_pikmin2_fixture.py``:
build.ninja edge reuse, no shared CMake/CTest edits), then runs the guarded
conversion + scenery chain.

A syntax preflight plus the builder compile stand in for object evidence:
the module TU is intentionally absent from every CMake target until #186
review registers it. Marker expectations are additionally cross-checked
against the in-repo reference predicate
(``experimental.pikmin2_flora_assets.reference_conversion``) without
duplicating it.

Phases: ``configure`` (leased cmake), ``build`` (leased pikmin_pc + ninja
-n), ``syntax`` (standalone TU syntax evidence), ``fixture``
(provenance-checked link, exe SHA-256), ``guardcheck`` (live self-test +
``negcap`` negative path), ``run`` (headed chain run with marker +
reference validation), ``all``.

The fixture consumes the captain guard header-only
(``p2_fixture_captain_guard.h``) from the canonical checkout ``scripts/``
read-only via ``CPLUS_INCLUDE_PATH`` (never copied or edited); the header
enters the builder fixture-input snapshot automatically.

Captain safety #632: the guard runs before any observation; captain-down
exits 86 (BLOCKED) with ``P2_FIXTURE_CAPTAIN_DOWN`` and can never be recorded
as a conversion. Protected observation cannot prove captain damage.
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

FIXTURE_REL = Path("tools/p2_flora_convert_fixture.cpp")
MODULE_REL = Path("pc_port/pc_p2_flora_convert.cpp")
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
        candidate = CANONICAL_ROOT / "scripts" / GUARD_NAME
    if not candidate.is_file():
        raise ValueError("Missing captain guard header: " + str(candidate))
    return candidate.resolve()


def guard_record(guard_dir=None):
    path = resolve_guard(guard_dir)
    return {"path": str(path), "sha256": sha256(path)}


def parse_markers(text):
    """Extract conversion/scenery/guard markers from fixture output."""
    convert, scenery, boot, done, down = [], [], False, False, False
    for line in text.splitlines():
        if line.startswith("P2_FLORA_CONVERT"):
            convert.append(line)
        elif line.startswith("P2_FLORA_SCENERY"):
            scenery.append(line)
        elif line.startswith("P2_FLORA_BOOT "):
            boot = True
        elif line.startswith("P2_FLORA_DONE "):
            done = line
        elif line.startswith("P2_FIXTURE_CAPTAIN_DOWN"):
            down = True
    return {"convert": convert, "scenery": scenery, "boot": boot,
            "done": done, "captain_down": down}


def reference_spot_check():
    """Cross-check two policy outcomes against the in-repo reference."""
    from experimental.pikmin2_flora_assets import reference_conversion
    checks = [
        (("BluePom", 3, False), {"output": 3, "multiplier": 1}),
        (("RandPom", 1, False), {"output": 9, "multiplier": 9}),
        (("Pelplant", 10, False), {"output": 10, "multiplier": 1}),
    ]
    for (species, amount, own), want in checks:
        got = reference_conversion(species, amount, own_colour=own)
        for key, value in want.items():
            if got[key] != value:
                return False, "reference drift: %s %s" % (species, key)
    return True, "reference predicate agrees"


def check_chain(parsed):
    """Require boot, passing suites, scenery registration and DONE."""
    if parsed["captain_down"]:
        return False, "captain-down during chain run"
    if not parsed["boot"]:
        return False, "missing boot marker"
    convert_ok = any("DONE failures=0" in line for line in parsed["convert"])
    if not convert_ok:
        return False, "conversion suite did not pass"
    scenery_ok = any("DONE failures=0" in line for line in parsed["scenery"])
    if not scenery_ok:
        return False, "scenery suite did not pass"
    registered = sum(1 for line in parsed["scenery"]
                     if "register identity=" in line and "pass=1" in line)
    if registered < 8:
        return False, "expected 8 scenery registrations, saw %d" % registered
    if not parsed["done"]:
        return False, "missing DONE marker"
    ok, detail = reference_spot_check()
    if not ok:
        return False, detail
    return True, "conversion+scenery pass, reference agrees"


def interpret_exit(code, text):
    """Classify a fixture exit: live PASS, guard BLOCKED, or failure."""
    parsed = parse_markers(text)
    if code == NEGATIVE_EXIT and parsed["captain_down"]:
        return {"verdict": "blocked", "detail": "guard CAPTAIN_DOWN exit 86"}
    if code == 0:
        ok, detail = check_chain(parsed)
        return {"verdict": "pass" if ok else "fail", "detail": detail}
    return {"verdict": "fail", "detail": "exit %d" % code}


def run_exe(exe, timeout=300, argv=()):
    env = dict(os.environ)
    env["PATH"] = ("C:/msys64/mingw64/bin;"
                   + env.get("PATH", ""))
    proc = subprocess.run(
        [str(exe)] + [str(a) for a in argv],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, encoding="utf-8", errors="replace", timeout=timeout,
        env=env,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    return proc.returncode, proc.stdout


def evidence_record(**fields):
    record = {"schema": 1, "kind": "p2-flora-convert-build"}
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
    return "flora-conversion-native"


def lease_generation(reg=None):
    """Current lane generation (never a stale hardcoded fence)."""
    if reg is None:
        from workflow.registry import Registry
        reg = Registry(CANONICAL_ROOT / "output/workflow/registry.sqlite3",
                       CANONICAL_ROOT)
    return reg.status()["lanes"][lease_key()]["generation"]


def acquire(resource, pid, ttl=300):
    from workflow.registry import Registry
    reg = Registry(CANONICAL_ROOT / "output/workflow/registry.sqlite3",
                   CANONICAL_ROOT)
    gen = lease_generation(reg)
    return reg, reg.acquire(lease_key(), gen, resource, pid, ttl=ttl)


def renew(reg, resource, token, ttl=300):
    return reg.renew(lease_key(), lease_generation(reg), resource, token,
                     ttl=ttl)


def release(reg, resource, token):
    return reg.release(lease_key(), lease_generation(reg), resource, token)


def child_env(ninja_dir):
    return dict(os.environ,
                PATH="C:/msys64/mingw64/bin;" + str(ninja_dir) + ";"
                + os.environ.get("PATH", ""))


def run_under_lease(resource, commands, cwd, log_path, poll=5, env=None):
    """Run shell commands under the private-build/pool lease.

    An idle child holds the lease while the parent feeds it commands and
    renews; the lease is released only after the child exits. Queue waits
    are logged so a held pool is visible instead of silent.
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
        reg = Registry(CANONICAL_ROOT / "output/workflow/registry.sqlite3",
                       CANONICAL_ROOT)
        lease = None
        try:
            waited = 0
            while lease is None:
                result = reg.acquire(lease_key(), lease_generation(reg),
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


def run_python_under_lease(resource, payload, log_path, poll=5):
    """Execute one harness phase function inside the lease-holding child."""
    from workflow.handoff import Rejected
    code = ("import json,sys,traceback\n"
            "sys.path.insert(0, r'" + str(ROOT) + "')\n"
            "sys.path.insert(0, r'" + str(CANONICAL_ROOT) + "')\n"
            "d=json.loads(sys.stdin.readline())\n"
            "try:\n"
            " import scripts.build_p2_flora_convert as harness\n"
            " fn=getattr(harness, d['fn'])\n"
            " fn(**d['kwargs'])\n"
            " print(json.dumps({'status': 'ok'}),flush=True)\n"
            "except Exception as error:\n"
            " traceback.print_exc()\n"
            " print(json.dumps({'status': 'error', 'error': str(error)}),\n"
            "       flush=True)\n"
            " sys.exit(1)\n")
    log_path = Path(log_path)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("w", encoding="utf-8") as stream:
        child = subprocess.Popen(
            [sys.executable, "-u", "-c", code], stdin=subprocess.PIPE,
            stdout=stream, stderr=subprocess.STDOUT, text=True,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        from workflow.registry import Registry
        reg = Registry(CANONICAL_ROOT / "output/workflow/registry.sqlite3",
                       CANONICAL_ROOT)
        lease = None
        try:
            waited = 0
            while lease is None:
                result = reg.acquire(lease_key(), lease_generation(reg),
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
            child.stdin.write(json.dumps(payload) + "\n")
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


def phase_syntax(native, log_path, guard_dir=None):
    """Standalone TU syntax evidence (module has no CMake target yet)."""
    native = Path(native)
    compiler = Path("C:/msys64/mingw64/bin/g++.exe")
    env = dict(os.environ, PATH=str(compiler.parent) + os.pathsep
               + os.environ.get("PATH", ""))
    guard = resolve_guard(guard_dir)
    lines = []
    for name in ("pc_port/pc_p2_flora_convert.h",
                 "pc_port/pc_p2_flora_convert.cpp",
                 "tools/p2_flora_convert_fixture.cpp"):
        proc = subprocess.run(
            [str(compiler), "-std=c++17", "-fsyntax-only",
             "-I", str(native / "pc_port"), "-I", str(guard.parent),
             str(native / name)],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
            encoding="utf-8", errors="replace", timeout=120, env=env)
        lines.append("%s: exit=%d" % (name, proc.returncode))
        if proc.returncode:
            lines.append(proc.stdout[-2000:])
            Path(log_path).write_text("\n".join(lines) + "\n",
                                      encoding="utf-8")
            return 1
    Path(log_path).write_text("\n".join(lines) + "\n", encoding="utf-8")
    return 0


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


def build_negative(compiler, guard_dir, workdir):
    """Compile the header-only negative TU; return the exe path."""
    workdir = Path(workdir)
    src = workdir / "guard_negative.cpp"
    src.write_text(
        '#include "p2_fixture_captain_guard.h"\n'
        "int main()\n"
        "{\n"
        "    p2_fixture_require_captain(true, false, 0.0f, 7);\n"
        '    std::printf("P2_FLORA_NEGATIVE_UNREACHABLE\\n");\n'
        "    return 0;\n"
        "}\n",
        encoding="utf-8")
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


def phase_guardcheck(exe, compiler, guard_dir, log_path):
    code, text = run_exe(exe)
    verdict = interpret_exit(code, text)
    if verdict["verdict"] != "pass":
        raise RuntimeError("Live self-test failed: "
                           + verdict["detail"] + "\n" + text[-2000:])
    with tempfile.TemporaryDirectory(prefix="p2floraneg") as tmp:
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


def phase_run(exe, log_path, evidence_path=None, native_head=None):
    code, text = run_exe(exe)
    verdict = interpret_exit(code, text)
    Path(log_path).write_text(text, encoding="utf-8")
    if verdict["verdict"] != "pass":
        raise RuntimeError("Chain run failed: " + verdict["detail"])
    if evidence_path is not None:
        record = evidence_record(
            native_head=native_head, exe_sha256=sha256(Path(exe)),
            guard_sha256=guard_record()["sha256"],
            ninja_dry_run="ninja: no work to do.", chain="pass", exit=code,
            detail=verdict["detail"])
        validate_evidence(record)
        Path(evidence_path).write_text(json.dumps(record, indent=2) + "\n",
                                       encoding="utf-8")
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
                        choices=("configure", "build", "syntax", "fixture",
                                 "guardcheck", "run", "all"))
    args = parser.parse_args(argv)
    ninja_dir = args.ninja_dir or toolchain()
    out = args.output
    out.mkdir(parents=True, exist_ok=True)
    if "all" in args.phases:
        order = ("configure", "build", "syntax", "fixture", "guardcheck",
                 "run")
    else:
        order = args.phases
    exe = args.exe
    for phase in order:
        if phase == "configure":
            code = phase_configure(args.native, args.build, ninja_dir,
                                   out / "configure.log")
        elif phase == "build":
            code = phase_build(args.build, out / "build.log", ninja_dir)
        elif phase == "syntax":
            code = phase_syntax(args.native, out / "syntax.log",
                                args.guard_dir)
        elif phase == "fixture":
            head = args.expected_native_head
            if head is None:
                head = subprocess.check_output(
                    ["git", "-C", str(args.native), "rev-parse", "HEAD"],
                    text=True).strip()
            code = run_python_under_lease(
                "build:" + str(Path(args.build).resolve()),
                {"fn": "phase_fixture",
                 "kwargs": {"native": str(args.native),
                            "build": str(args.build),
                            "output": str(out), "expected_head": head,
                            "guard_dir": args.guard_dir,
                            "log_path": str(out / "fixture.json")}},
                out / "fixture-lease.log")
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
            head = args.expected_native_head
            if head is None:
                head = subprocess.check_output(
                    ["git", "-C", str(args.native), "rev-parse", "HEAD"],
                    text=True).strip()
            code = phase_run(exe, out / "run.log", out / "evidence.json",
                             native_head=head)
        if code:
            raise SystemExit("Phase %s failed; see %s"
                             % (phase, out / (phase + ".log")))
    print(json.dumps({"status": "ok", "output": str(out.resolve()),
                      "exe": str(exe) if exe else None}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
