"""Private leased build/run harness for the #748 MUKI stage-table fixture.

Builds native/tools/p2_muki_stage_table_fixture.cpp (stage-selectable boot TU,
module TU ridden along via include, no CMake edit) against a private leased
pikmin_pc build using the maintained replacement-main builder
(scripts/build_pikmin2_fixture.py), then runs the guarded chain for both MUKI
rows (ui 8 houdai, ui 18 redblue).

Phases: configure (leased cmake), build (leased pikmin_pc plus ninja -n),
fixture (provenance-checked link, exe SHA-256), guardcheck (live self-test
plus compiled header-only negative path), run (headed chain run with
ordered-marker validation), all. The fixture consumes the captain guard
header-only (p2_fixture_captain_guard.h) from the canonical checkout scripts
via CPLUS_INCLUDE_PATH; the harness records its SHA-256 and never copies it.

Captain safety #632: guard before every observed tick; captain-down exits 86
(BLOCKED) with P2_FIXTURE_CAPTAIN_DOWN and can never be a live tick.
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

CANONICAL_ROOT = Path("C:/Users/alari/pikmin-randomizer")
sys.path.insert(0, str(CANONICAL_ROOT))

FIXTURE_REL = Path("tools/p2_muki_stage_table_fixture.cpp")
GUARD_NAME = "p2_fixture_captain_guard.h"
NEGATIVE_EXIT = 86
STAGES = (("ch_MUKI_houdai", 8), ("ch_MUKI_redblue", 18))


def sha256(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def resolve_guard(guard_dir=None):
    candidate = Path(guard_dir) / GUARD_NAME if guard_dir else CANONICAL_ROOT / "scripts" / GUARD_NAME
    if not candidate.is_file():
        raise ValueError("Missing captain guard header: " + str(candidate))
    return candidate.resolve()


def parse_markers(text):
    rows = []
    for line in text.splitlines():
        if line.startswith("P2_MUKI_STAGE_"):
            rows.append((line.partition(" ")[0][len("P2_MUKI_STAGE_"):], line))
        elif line.startswith("P2_CHALLENGE_MODE_"):
            rows.append((line.partition(" ")[0][len("P2_CHALLENGE_MODE_"):], line))
        elif line.startswith("P2_FIXTURE_CAPTAIN_DOWN"):
            rows.append(("CAPTAIN_DOWN", line))
    return rows


def check_chain(rows, stages=2):
    kinds = [kind for kind, _ in rows]
    if "CAPTAIN_DOWN" in kinds:
        return False, "captain-down during chain run"
    if kinds.count("RESOLVED") < stages:
        return False, "expected %d RESOLVED markers" % stages
    for want in ("BOOT", "TICK", "TABLE_DONE"):
        if want not in kinds:
            return False, "missing marker: " + want
    if kinds.count("TICK") < 3 * stages:
        return False, "expected at least %d TICK markers" % (3 * stages)
    return True, "chain RESOLVED..BOOT..TICK..TABLE_DONE in order"


def interpret_exit(code, text, stages=2):
    rows = parse_markers(text)
    if code == NEGATIVE_EXIT and any(k == "CAPTAIN_DOWN" for k, _ in rows):
        return {"verdict": "blocked", "detail": "guard CAPTAIN_DOWN exit 86"}
    if code == 0:
        ok, detail = check_chain(rows, stages)
        return {"verdict": "pass" if ok else "fail", "detail": detail}
    return {"verdict": "fail", "detail": "exit " + str(code)}


def negative_source():
    return ("#include " + chr(34) + GUARD_NAME + chr(34) + chr(10)
            + "int main()" + chr(10) + "{" + chr(10)
            + "    p2_fixture_require_captain(true, false, 0.0f, 3);" + chr(10)
            + "    return 0;" + chr(10) + "}" + chr(10))


def build_negative(compiler, guard_dir, workdir):
    workdir = Path(workdir)
    src = workdir / "guard_negative.cpp"
    src.write_text(negative_source(), encoding="utf-8")
    exe = workdir / "guard_negative.exe"
    env = dict(os.environ, PATH=str(Path(compiler).parent) + os.pathsep + os.environ.get("PATH", ""))
    proc = subprocess.run([str(compiler), "-std=c++17", "-I", str(guard_dir), str(src), "-o", str(exe)],
                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                          text=True, encoding="utf-8", errors="replace", timeout=120, env=env)
    if proc.returncode or not exe.is_file():
        raise RuntimeError("Negative guard TU failed to compile")
    return exe


def run_exe(exe, args=(), timeout=300):
    env = dict(os.environ, PATH="C:/msys64/mingw64/bin;" + os.environ.get("PATH", ""))
    proc = subprocess.run([str(exe)] + list(args), stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                          text=True, encoding="utf-8", errors="replace", timeout=timeout, env=env,
                          creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    return proc.returncode, proc.stdout


def toolchain(ninja_dir=None):
    if ninja_dir is None:
        import ninja
        ninja_dir = str(Path(ninja.BIN_DIR))
    return ninja_dir


def phase_configure(native, build, ninja_dir, log_path):
    build = Path(build)
    build.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, PATH="C:/msys64/mingw64/bin;" + os.environ.get("PATH", ""))
    cmd = ["cmake", "-S", str(native), "-B", str(build), "-G", "Ninja",
           "-DCMAKE_MAKE_PROGRAM=" + ninja_dir + "/ninja.exe",
           "-DCMAKE_BUILD_TYPE=RelWithDebInfo",
           "-DCMAKE_C_COMPILER=C:/msys64/mingw64/bin/gcc.exe",
           "-DCMAKE_CXX_COMPILER=C:/msys64/mingw64/bin/g++.exe",
           "-DPIKMIN_NATIVE_JAUDIO=ON", "-DPIKMIN_NATIVE_OPTIMIZE=OFF",
           "-DPIKMIN_RANDOMIZER_TEST_HOOKS=OFF"]
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                          text=True, encoding="utf-8", errors="replace", timeout=900, env=env)
    Path(log_path).write_text(proc.stdout, encoding="utf-8")
    return proc.returncode


def phase_build(build, log_path, ninja_dir):
    env = dict(os.environ, PATH="C:/msys64/mingw64/bin;" + os.environ.get("PATH", ""))
    proc = subprocess.run(["cmake", "--build", str(build), "--target", "pikmin_pc", "-j", "6"],
                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                          text=True, encoding="utf-8", errors="replace", timeout=3600, env=env)
    Path(log_path).write_text(proc.stdout, encoding="utf-8")
    return proc.returncode


def phase_ninja_dry(build, ninja_dir):
    ninja = str(Path(ninja_dir) / "ninja.exe")
    proc = subprocess.run([ninja, "-n", "-d", "explain", "pikmin_pc"], cwd=str(build),
                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                          text=True, encoding="utf-8", errors="replace", timeout=300)
    return proc.returncode, proc.stdout


def phase_fixture(native, build, output, expected_head, guard_dir, log_path):
    from scripts import build_pikmin2_fixture as builder
    native, build, output = Path(native), Path(build), Path(output)
    fixture = (native / FIXTURE_REL).resolve()
    if not fixture.is_file():
        raise ValueError("Missing fixture TU: " + str(fixture))
    guard = resolve_guard(guard_dir)
    env = dict(os.environ)
    env["PATH"] = "C:/msys64/mingw64/bin;" + env.get("PATH", "")
    env["CPLUS_INCLUDE_PATH"] = str(guard.parent) + os.pathsep + env.get("CPLUS_INCLUDE_PATH", "")
    old = dict(os.environ)
    try:
        os.environ.clear()
        os.environ.update(env)
        stamp = "fixture-" + str(time.time_ns())
        record = builder.build_fixture(build, native, fixture, output / stamp, expected_head)
    finally:
        os.environ.clear()
        os.environ.update(old)
    if record.get("status") != "built":
        raise RuntimeError("Fixture build rejected: " + str(record.get("error")))
    exe = output / stamp / "fixture.exe"
    Path(log_path).write_text(json.dumps({"status": record["status"], "exe_sha256": sha256(exe),
                                          "guard_sha256": sha256(guard),
                                          "provenance": str(output / stamp / "provenance.json")}, indent=2) + chr(10),
                             encoding="utf-8")
    return 0


def phase_guardcheck(exe, compiler, guard_dir, log_path):
    code, text = run_exe(exe)
    verdict = interpret_exit(code, text, stages=2)
    if verdict["verdict"] != "pass":
        raise RuntimeError("Live self-test failed: " + verdict["detail"] + "\n" + text[-2000:])
    with tempfile.TemporaryDirectory(prefix="p2guardneg") as tmp:
        negative = build_negative(compiler, guard_dir, tmp)
        ncode, ntext = run_exe(negative)
    nverdict = interpret_exit(ncode, ntext)
    if nverdict["verdict"] != "blocked":
        raise RuntimeError("Negative guard path failed")
    if "PASS" in ntext:
        raise RuntimeError("Negative path emitted PASS")
    Path(log_path).write_text("self_test: exit=" + str(code) + " " + verdict["detail"]
                              + " / negative: exit=" + str(ncode) + " " + nverdict["detail"] + chr(10),
                             encoding="utf-8")
    return 0


def phase_run(exe, log_path):
    code, text = run_exe(exe)
    verdict = interpret_exit(code, text, stages=2)
    Path(log_path).write_text(text, encoding="utf-8")
    if verdict["verdict"] != "pass":
        raise RuntimeError("Chain run failed: " + verdict["detail"])
    for _, ui in STAGES:
        scode, stext = run_exe(exe, (str(ui),))
        sverdict = interpret_exit(scode, stext, stages=1)
        if sverdict["verdict"] != "pass":
            raise RuntimeError("Single-stage run ui=%d failed: %s" % (ui, sverdict["detail"]))
        Path(str(log_path).replace(".log", "-ui%d.log" % ui)).write_text(stext, encoding="utf-8")
    return 0, text


def main(argv=None):
    parser = argparse.ArgumentParser(description="MUKI stage-table leased build and run")
    parser.add_argument("--native", type=Path, required=True)
    parser.add_argument("--build", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--expected-native-head", default=None)
    parser.add_argument("--guard-dir", default=None)
    parser.add_argument("--ninja-dir", default=None)
    parser.add_argument("--exe", type=Path, default=None)
    parser.add_argument("phases", nargs="+", choices=("configure", "build", "fixture", "guardcheck", "run", "all"))
    args = parser.parse_args(argv)
    ninja_dir = args.ninja_dir or toolchain()
    out = args.output
    out.mkdir(parents=True, exist_ok=True)
    order = ("configure", "build", "fixture", "guardcheck", "run") if "all" in args.phases else args.phases
    exe = args.exe
    for phase in order:
        if phase == "configure":
            code = phase_configure(args.native, args.build, ninja_dir, out / "configure.log")
        elif phase == "build":
            code = phase_build(args.build, out / "build.log", ninja_dir)
            if code == 0:
                code, dry = phase_ninja_dry(args.build, ninja_dir)
                (out / "ninja-dry.log").write_text(dry, encoding="utf-8")
                if dry.strip() != "ninja: no work to do.":
                    code = 1
        elif phase == "fixture":
            head = args.expected_native_head
            if head is None:
                head = subprocess.check_output(["git", "-C", str(args.native), "rev-parse", "HEAD"], text=True).strip()
            code = phase_fixture(args.native, args.build, out, head, args.guard_dir, out / "fixture.json")
            if code == 0 and exe is None:
                rec = json.loads((out / "fixture.json").read_text(encoding="utf-8"))
                exe = Path(json.loads(Path(rec["provenance"]).read_text(encoding="utf-8")).get("exe", "") or (Path(rec["provenance"]).parent / "fixture.exe"))
                if not exe.is_file():
                    exe = Path(rec["provenance"]).parent / "fixture.exe"
        elif phase == "guardcheck":
            if exe is None:
                raise SystemExit("guardcheck needs --exe or a prior fixture phase")
            compiler = Path("C:/msys64/mingw64/bin/g++.exe")
            guard = resolve_guard(args.guard_dir)
            code = phase_guardcheck(exe, compiler, guard.parent, out / "guardcheck.log")
        elif phase == "run":
            if exe is None:
                raise SystemExit("run needs --exe or a prior fixture phase")
            code, _ = phase_run(exe, out / "run.log")
        if code:
            raise SystemExit("Phase failed")
    print(json.dumps({"status": "ok", "output": str(out.resolve()), "exe": str(exe) if exe else None}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())