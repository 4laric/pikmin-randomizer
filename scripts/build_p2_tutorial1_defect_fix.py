"""Private leased build/run helper proving the #686 wrapper -c fix (#686).

Drives the fixed wrapper (scripts/build_p2_cave_guarded_boot_fixture.py) to
configure + build a private pikmin_pc and compile/link BOTH the new probe
fixture (native/tools/p2_tutorial1_defect_fix_fixture.cpp) AND the
consumer-owned tutorial1 fixture (native/tools/p2_tutorial1_p1_fixture.cpp,
verified byte-identical before/after, never edited), then runs guarded
self-test, negative and run markers for each.

The #674 defect replaced the reference TU basename in the whole compile
command, so -c became pc_port/<fixture>.cpp instead of tools/<fixture>.cpp.
The fix (in the wrapper this helper drives) replaces the full reference TU
path with native_dir/tools/<fixture>. The probe fixture additionally proves
the fixed directory at runtime via __FILE__.

Phases: configure, build, guardcheck, run, all. Lease: canonical
build:<dir> held by an idle child while commands run (renew/release after
exit). No shared CMakeLists/preview/consumer edits; no ADMIT.

Captain safety #632: guarded markers only; a captain-down exits 86
(BLOCKED) with P2_FIXTURE_CAPTAIN_DOWN and is never recorded as a pass.
Protected observation cannot prove captain damage.
"""

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CANONICAL_ROOT = Path("C:/Users/alari/pikmin-randomizer")
sys.path.insert(0, str(CANONICAL_ROOT))

PROBE_FIXTURE = "p2_tutorial1_defect_fix_fixture.cpp"
PROBE_MARKER = "PASS TUTORIAL1_DEFECTFIX"
PROBE_SELFTEST = "P2_TUTORIAL1_DEFECTFIX_SELFTEST_PASS"
CONSUMER_FIXTURE = "p2_tutorial1_p1_fixture.cpp"
CONSUMER_MARKER = "PASS TUTORIAL1_P1"
CONSUMER_SELFTEST = "P2_TUTORIAL1_SELFTEST_PASS"
GUARD_NAME = "p2_fixture_captain_guard.h"
GUARD_SHA256 = "d2f678c9eda75e151eb534077dff9e30ad36ae4796881d971bbd09945f3c3474"
NEGATIVE_EXIT = 86
CAPTAIN_DOWN = "P2_FIXTURE_CAPTAIN_DOWN"


def sha256(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def lease_key():
    return "tutorial1-wrapper-defect-fix-native"


def lease_generation(reg=None):
    if reg is None:
        from workflow.registry import Registry
        reg = Registry(CANONICAL_ROOT / "output/workflow/registry.sqlite3",
                       CANONICAL_ROOT)
    return reg.status()["lanes"][lease_key()]["generation"]


def child_env(ninja_dir):
    return dict(os.environ,
                PATH="C:/msys64/mingw64/bin;" + str(ninja_dir) + ";"
                + os.environ.get("PATH", ""))


def run_under_lease(resource, commands, cwd, log_path, poll=5, env=None):
    """Run shell commands under the private-build/pool lease (idle child)."""
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
                    reg.renew(lease_key(), lease_generation(reg),
                              resource, lease["token"], ttl=300)
                except Rejected:
                    if child.poll() is None:
                        raise
                    break
                time.sleep(poll)
            result = child.wait()
        finally:
            if lease is not None and child.poll() is not None:
                try:
                    reg.release(lease_key(), lease_generation(reg),
                                resource, lease["token"])
                except Rejected:
                    pass
    return result


def toolchain(ninja_dir=None):
    if ninja_dir is None:
        import ninja
        ninja_dir = str(Path(ninja.BIN_DIR))
    return ninja_dir


FIXTURES = (("p2_tutorial1_defect_fix_fixture.cpp",
               "p2_tutorial1_defect_fix",
               PROBE_SELFTEST, PROBE_MARKER),
              ("p2_tutorial1_p1_fixture.cpp",
               "p2_tutorial1_p1",
               CONSUMER_SELFTEST, CONSUMER_MARKER))


def check_fixture_built(build_dir, stem, log_path):
    base = stem[:-len("_fixture")] if stem.endswith("_fixture") else stem
    exe = Path(build_dir) / (base + ".exe")
    if not exe.is_file():
        raise RuntimeError("Missing fixture exe: " + str(exe))
    return exe


def run_logged(exe, args, log_path, timeout=600):
    env = dict(os.environ, PATH="C:/msys64/mingw64/bin;"
               + os.environ.get("PATH", ""))
    proc = subprocess.run(
        [str(exe)] + [str(a) for a in args],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, encoding="utf-8", errors="replace", timeout=timeout,
        env=env,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    Path(log_path).write_text(proc.stdout, encoding="utf-8")
    return proc.returncode, proc.stdout


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--native", type=Path, required=True)
    parser.add_argument("--build", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--wrapper", type=Path, required=True,
                        help="fixed wrapper script to drive")
    parser.add_argument("--consumer-sha", required=True,
                        help="pinned sha256 of the consumer fixture TU")
    parser.add_argument("--rundir", type=Path, default=None,
                        help="guarded input-package rundir for consumer boot")
    parser.add_argument("--ninja-dir", default=None)
    parser.add_argument("phases", nargs="+",
                        choices=("configure", "build", "guardcheck",
                                 "run", "all"))
    args = parser.parse_args(argv)
    ninja_dir = args.ninja_dir or toolchain()
    native, build, out = Path(args.native), Path(args.build), Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    wrapper = str(args.wrapper)
    resource = "build:" + str(build.resolve())
    env = child_env(ninja_dir)
    if "all" in args.phases:
        order = ("configure", "build", "guardcheck", "run")
    else:
        order = args.phases
    exes = {}
    for phase in order:
        if phase == "configure":
            code = run_under_lease(
                resource,
                [[sys.executable, wrapper, "--root", str(ROOT),
                  "--native-dir", str(native), "--build-dir", str(build),
                  "--out-dir", str(out), "--configure"]],
                ROOT, out / "configure.log", env=env)
        elif phase == "build":
            code = run_under_lease(
                resource,
                [[sys.executable, wrapper, "--root", str(ROOT),
                  "--native-dir", str(native), "--build-dir", str(build),
                  "--out-dir", str(out), "--configure"]
                 ] + [
                    [sys.executable, wrapper, "--root", str(ROOT),
                     "--native-dir", str(native), "--build-dir", str(build),
                     "--out-dir", str(out), "--build",
                     "--fixture", name]
                    for name, _, _, _ in FIXTURES],
                ROOT, out / "build.log", env=env)
            if code == 0:
                for name, _, _, _ in FIXTURES:
                    stem = name[:-len(".cpp")]
                    exes[stem] = str(check_fixture_built(
                        build, stem, out / "build.log"))
        elif phase == "guardcheck":
            code = 0
            if not exes:
                for name, _, _, _ in FIXTURES:
                    stem = name[:-len(".cpp")]
                    exes[stem] = str(check_fixture_built(
                        build, stem, out / "guardcheck.log"))
            lines = []
            for name, _, selftest, _ in FIXTURES:
                stem = name[:-len(".cpp")]
                exe = exes[stem]
                scode, stext = run_logged(exe, ["--guard-self-test"],
                                          out / ("selftest-%s.log" % stem))
                if scode != 0 or selftest not in stext:
                    raise RuntimeError("self-test failed for " + stem)
                ncode, ntext = run_logged(exe, ["--guard-negative-test"],
                                          out / ("negative-%s.log" % stem))
                if (ncode != NEGATIVE_EXIT or CAPTAIN_DOWN not in ntext
                        or "PASS " in ntext):
                    raise RuntimeError("negative path failed for " + stem)
                lines.append("%s: self-test exit=0, negative exit=86" % stem)
            Path(out / "guardcheck.log").write_text(
                "\n".join(lines) + "\n", encoding="utf-8")
        elif phase == "run":
            code = 0
            if not exes:
                for name, _, _, _ in FIXTURES:
                    stem = name[:-len(".cpp")]
                    exes[stem] = str(check_fixture_built(
                        build, stem, out / "run.log"))
            pcode, ptext = run_logged(exes["p2_tutorial1_defect_fix_fixture"],
                                      [], out / "run-probe.log")
            if pcode != 0 or PROBE_MARKER not in ptext:
                raise RuntimeError("probe run failed")
            Path(out / "run.log").write_text(
                "probe: exit=0 %s\n" % PROBE_MARKER, encoding="utf-8")
            if args.rundir is not None:
                ccode, ctext = run_logged(
                    exes["p2_tutorial1_p1_fixture"],
                    ["--experimental-pikmin2-room"],
                    out / "run-consumer.log", timeout=900)
                with open(out / "run.log", "a", encoding="utf-8") as handle:
                    handle.write("consumer: exit=%d marker=%s\n"
                                 % (ccode, CONSUMER_MARKER in ctext))
                if ccode != 0 or CONSUMER_MARKER not in ctext:
                    raise RuntimeError("consumer boot run failed")
        if code:
            raise SystemExit("Phase %s failed" % phase)
    print(json.dumps({"status": "ok", "output": str(out.resolve()),
                      "exes": exes}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
