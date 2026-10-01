#!/usr/bin/env python3
"""Private leased build/run helper for the Damagumo bind-mod fixture (#727).

Configures + builds pikmin_pc in a private leased dir, links the guarded
fixture via the maintained replacement-main builder
(scripts/build_pikmin2_fixture.py), stages the produced
longlegs_Damagumo_bind_00.mod into the run assets tree, and runs the guard
modes plus the load proof, validating markers. No maintained, CMakeLists,
family/shared or consumer edits. Heavy jobs require a canonical registry
build lease held beforehand; this script never acquires one itself.
"""
import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

FIXTURE = os.path.join("tools", "p2_damagumo_bind_mod_fixture.cpp")
MOD_NAME = "longlegs_Damagumo_bind_00.mod"
MOD_REL = "assets/dataDir/courses/pikmin2room/" + MOD_NAME
PASS_MARKER = "PASS P2_DAMAGUMO_BIND_MOD_LOADED"
LOADED_MARKER = "P2_DAMAGUMO_BIND_LOADED"
CAPTAIN_DOWN = "P2_FIXTURE_CAPTAIN_DOWN"
INJECTED_TOKENS = ("P2_LL_INJECT", "P2_LIFECYCLE_INJECT", "injected_health",
                   "mHealth=", "Transport(")
GUARD_SHA256 = "d2f678c9eda75e151eb534077dff9e30ad36ae4796881d971bbd09945f3c3474"
MINGW_BIN = "C:/msys64/mingw64/bin"


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run_command(argv, cwd=None, env=None, timeout=None):
    base = dict(env if env is not None else os.environ)
    if MINGW_BIN.lower() not in base.get("PATH", "").lower():
        base["PATH"] = MINGW_BIN + ";" + base.get("PATH", "")
    proc = subprocess.Popen([str(a) for a in argv], cwd=str(cwd) if cwd else None,
                            env=base, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, text=True, errors="replace")
    try:
        out, _ = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        proc.kill()
        out, _ = proc.communicate()
        return proc.returncode, out + "\n[TIMEOUT]\n"
    return proc.returncode, out


def check_markers(text):
    if CAPTAIN_DOWN in text:
        return False, "captain-down interruption present"
    if PASS_MARKER not in text:
        return False, "run PASS marker absent"
    if LOADED_MARKER not in text:
        return False, "bind loaded marker absent"
    hits = [t for t in INJECTED_TOKENS if t in text]
    if hits:
        return False, "injection markers present: " + ",".join(hits)
    return True, "bind artifact loaded with markers"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--native", type=Path, required=True)
    parser.add_argument("--build", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--artifact", type=Path, required=True,
                        help="produced longlegs_Damagumo_bind_00.mod")
    parser.add_argument("--artifact-sha256", required=True)
    parser.add_argument("--expected-native-head", required=True)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--guard-dir", type=Path, default=None)
    args = parser.parse_args(argv)
    native, build, out = Path(args.native), Path(args.build), Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    guard = Path(args.guard_dir) / "p2_fixture_captain_guard.h" if args.guard_dir \
        else Path("C:/Users/alari/pikmin-randomizer/scripts/p2_fixture_captain_guard.h")
    if not guard.is_file() or sha256_file(str(guard)) != GUARD_SHA256:
        print("REFUSED reason=guard-mismatch")
        return 2
    if sha256_file(str(args.artifact)) != args.artifact_sha256:
        print("REFUSED reason=artifact-hash-mismatch")
        return 2
    ninja = (Path(os.environ.get("LOCALAPPDATA", "")) / "Packages" /
             "PythonSoftwareFoundation.Python.3.12_qbz5n2kfra8p0" / "LocalCache" /
             "local-packages" / "Python312" / "Scripts" / "ninja.exe")
    cfg = ["cmake", "-S", str(native), "-B", str(build), "-G", "Ninja",
           "-DCMAKE_C_COMPILER=" + MINGW_BIN + "/gcc.exe",
           "-DCMAKE_CXX_COMPILER=" + MINGW_BIN + "/g++.exe",
           "-DCMAKE_MAKE_PROGRAM=" + str(ninja),
           "-DCMAKE_BUILD_TYPE=Release",
           "-DPIKMIN_NATIVE_JAUDIO=ON", "-DPIKMIN_NATIVE_OPTIMIZE=OFF",
           "-DCMAKE_EXPORT_COMPILE_COMMANDS=ON",
           "-DP2_CHALLENGE_GUARD_INCLUDE_DIR=C:/Users/alari/pikmin-randomizer/scripts"]
    code, text = run_command(cfg, timeout=900)
    (out / "cmake-configure.log").write_text(text, encoding="utf-8", errors="replace")
    if code != 0:
        print("REFUSED reason=configure-failed")
        return 2
    code, text = run_command(["cmake", "--build", str(build), "--target", "pikmin_pc",
                              "--config", "Release", "-j", "6"], timeout=5400)
    (out / "cmake-build-pikmin-pc.log").write_text(text, encoding="utf-8", errors="replace")
    if code != 0:
        print("REFUSED reason=production-build-failed")
        return 2
    sys.path.insert(0, "C:/Users/alari/pikmin-randomizer/scripts")
    import build_pikmin2_fixture as builder
    fixture_src = native / FIXTURE
    if not fixture_src.is_file():
        print("REFUSED reason=fixture-source-missing")
        return 2
    record = builder.build_fixture(build, native, fixture_src, out / "fixture",
                                   args.expected_native_head)
    if record.get("status") != "built":
        print("REFUSED reason=fixture-build-rejected")
        return 2
    exe = out / "fixture" / "fixture.exe"
    if not exe.is_file():
        print("REFUSED reason=fixture-exe-missing")
        return 2
    code, text = run_command([str(ninja), "-n", "-C", str(build), "pikmin_pc"], timeout=300)
    (out / "ninja-dry-run.log").write_text(text, encoding="utf-8", errors="replace")
    if code != 0 or "ninja: no work to do." not in text:
        print("REFUSED reason=ninja-dry-run-dirty")
        return 2
    rundir = Path(args.run)
    assets_mod = rundir / MOD_REL
    assets_mod.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(str(args.artifact), str(assets_mod))
    if sha256_file(str(assets_mod)) != args.artifact_sha256:
        print("REFUSED reason=staged-artifact-mismatch")
        return 2
    env = dict(os.environ, SDL_AUDIODRIVER="dummy", PYTHONUTF8="1",
               PATH=MINGW_BIN + ";" + os.environ.get("PATH", ""))
    for mode, want_exit in (("--guard-self-test", 0), ("--guard-negative-test", 86)):
        code, text = run_command([str(exe), mode], cwd=str(rundir), env=env, timeout=300)
        (out / ("guard-" + mode.strip("-").replace("-", "_") + ".log")).write_text(
            "exit=%d\n%s" % (code, text), encoding="utf-8", errors="replace")
        if mode == "--guard-self-test" and (code != 0 or "SELFTEST_PASS" not in text):
            print("REFUSED reason=guard-selftest-failed")
            return 2
        if mode == "--guard-negative-test" and (code != 86 or CAPTAIN_DOWN not in text
                                                or "PASS" in text):
            print("REFUSED reason=guard-negative-failed")
            return 2
    code, text = run_command([str(exe)], cwd=str(rundir), env=env, timeout=600)
    (rundir / "native.log").write_text(text, encoding="utf-8", errors="replace")
    ok, detail = check_markers(text)
    print(detail)
    if code != 0 or not ok:
        print("REFUSED reason=fixture-run-failed")
        return 2
    prov = {"native_commit": args.expected_native_head,
            "executable": str(exe),
            "executable_sha256": sha256_file(str(exe)),
            "artifact": str(assets_mod),
            "artifact_sha256": args.artifact_sha256,
            "fixture_log": str(rundir / "native.log"),
            "fixture_log_sha256": sha256_file(str(rundir / "native.log")),
            "ninja_no_work": True,
            "guard_sha256": GUARD_SHA256}
    (out / "build-provenance.json").write_text(json.dumps(prov, indent=1) + "\n",
                                               encoding="utf-8")
    print("built exe=%s artifact=%s" % (prov["executable_sha256"][:16],
                                        prov["artifact_sha256"][:16]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
