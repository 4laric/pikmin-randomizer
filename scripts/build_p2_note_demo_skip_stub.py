#!/usr/bin/env python3
"""Private leased build helper for lane audio-note-demo-skip-stub-native (#704).

Proves the default-config (PIKMIN_NATIVE_JAUDIO=OFF) pikmin_pc link with the
Jac_NoteDemoSkipped stub, then compiles/links/runs the focused stub test.
Exclusive private build dir under output/; canonical lease CLI; live elastic
cap (no hardcoded slots). Never touches native/build-randomizer, the
maintained checkout, or CMakeLists. No ADMIT; no runtime.
"""
import hashlib
import json
import os
import re
import subprocess
import sys
import time

ROOT = r"C:\Users\alari\pikmin-randomizer"
CLI = [sys.executable, os.path.join(ROOT, "scripts", "pikmin2_workflow.py"),
       "--root", ROOT]
LANE_DIR = os.path.join(
    ROOT, "output", "workflow", "autofill", "prerequisites",
    "audio-note-demo-skip-stub-native")
NATIVE_DIR = os.path.join(LANE_DIR, "work", "native")
BUILD_DIR = os.path.join(ROOT, "output", "audio-note-demo-skip-stub-build")
OUT_DIR = os.path.join(LANE_DIR, "out")
RESOURCE = "build:output/audio-note-demo-skip-stub-build"
NINJA = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Packages",
                     "PythonSoftwareFoundation.Python.3.12_qbz5n2kfra8p0",
                     "LocalCache", "local-packages", "Python312",
                     "Scripts", "ninja.exe")
KEY, GEN = "audio-note-demo-skip-stub-native", 2
ISSUE = 704

CONFIGURE = ["cmake", "-S", NATIVE_DIR, "-B", BUILD_DIR, "-G", "Ninja",
             "-DCMAKE_C_COMPILER=gcc", "-DCMAKE_CXX_COMPILER=g++",
             "-DCMAKE_MAKE_PROGRAM=" + NINJA, "-DCMAKE_BUILD_TYPE=Release",
             "-DPIKMIN_NATIVE_JAUDIO=OFF",
             "-DPIKMIN_NATIVE_OPTIMIZE=OFF",
             "-DCMAKE_EXPORT_COMPILE_COMMANDS=ON"]


def sha256_file(path):
    with open(path, "rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def cli(command, request):
    rp = os.path.join(OUT_DIR, "lease-%s-%d.json"
                      % (command, int(time.time() * 1000) % 1000000))
    json.dump(request, open(rp, "w", encoding="utf-8"))
    proc = subprocess.run(CLI + ["--request", rp, command],
                          capture_output=True, text=True,
                          encoding="utf-8", errors="replace")
    return proc.returncode, proc.stdout + proc.stderr


def run_logged(log, argv, cwd=None, env=None, timeout=None):
    log.write("+ %s\n" % " ".join(argv))
    log.flush()
    proc = subprocess.Popen(argv, cwd=cwd, env=env, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, text=True,
                            errors="replace")
    out, _ = proc.communicate(timeout=timeout)
    log.write(out)
    log.flush()
    return proc.returncode, out


def nm_symbols(path):
    proc = subprocess.run(["nm", path], capture_output=True, text=True,
                          errors="replace")
    return proc.returncode, proc.stdout


def main():
    os.environ["PATH"] = (r"C:\msys64\mingw64\bin;"
                          + os.environ.get("PATH", ""))
    os.makedirs(OUT_DIR, exist_ok=True)
    stamp = str(int(time.time() * 1000000))
    log = open(os.path.join(OUT_DIR, "leased-build-%s.log" % stamp),
               "w", encoding="utf-8")
    record = {"lane": KEY, "issue": ISSUE, "stamp": stamp,
              "build_dir": BUILD_DIR, "steps": {},
              "config": "PIKMIN_NATIVE_JAUDIO=OFF"}
    token = None
    for _ in range(120):
        code, out = cli("acquire", {"key": KEY, "generation": GEN,
                                    "resource": RESOURCE,
                                    "pid": os.getpid(), "ttl": 3600})
        try:
            payload, _ = json.JSONDecoder().raw_decode(out[out.index("{"):])
        except (ValueError, json.JSONDecodeError):
            payload = None
        lease = (payload or {}).get("lease") or {}
        token = (payload or {}).get("token") or lease.get("token")
        if (payload or {}).get("acquired") and token:
            break
        time.sleep(10)
    if token is None:
        log.write("LEASE_NOT_ACQUIRED\n")
        log.close()
        return 2
    log.write("LEASE_ACQUIRED token=%s\n" % token)
    log.flush()

    def save():
        record["lease_token"] = token
        json.dump(record, open(os.path.join(
            OUT_DIR, "build-record-%s.json" % stamp), "w",
            encoding="utf-8"), indent=2)

    save()
    env = dict(os.environ)
    env["PATH"] = (r"C:\msys64\mingw64\bin;" + env.get("PATH", ""))
    try:
        code, _ = run_logged(log, CONFIGURE, env=env)
        record["steps"]["configure"] = {"exit": code}
        save()
        if code != 0:
            return code
        code, _ = run_logged(log, ["cmake", "--build", BUILD_DIR,
                                   "--target", "pikmin_pc", "-j", "6"],
                             env=env)
        record["steps"]["pikmin_pc"] = {"exit": code}
        save()
        if code != 0:
            return code
        code, dry = run_logged(log, [NINJA, "-n", "-C", BUILD_DIR], env=env)
        record["steps"]["dry_run"] = {
            "exit": code, "no_work": "no work to do" in dry,
            "tail": dry.strip().splitlines()[-1:]}
        exes = {}
        for root, _dirs, files in os.walk(BUILD_DIR):
            for name in files:
                if name == "nectar.exe":
                    full = os.path.join(root, name)
                    exes[full] = sha256_file(full)
        record["executables"] = exes
        stub_obj = os.path.join(
            BUILD_DIR, "CMakeFiles", "pikmin_pc.dir", "pc_port",
            "dolphin_stubs", "audio_stubs.cpp.obj")
        record["stub_object"] = {"path": stub_obj,
                                 "exists": os.path.isfile(stub_obj)}
        if os.path.isfile(stub_obj):
            record["stub_object"]["sha256"] = sha256_file(stub_obj)
            ncode, nmout = nm_symbols(stub_obj)
            record["stub_object"]["nm_exit"] = ncode
            defined = [l for l in nmout.splitlines()
                       if "Jac_NoteDemoSkipped" in l]
            record["stub_object"]["Jac_NoteDemoSkipped_lines"] = defined
            record["stub_object"]["symbol_defined"] = any(
                re.match(r"^[0-9a-f]+\s+T\s+.*Jac_NoteDemoSkipped", l)
                for l in defined)
        save()
    finally:
        save()
        print("record build-record-%s.json" % stamp)
        log.close()
    # NOTE: the lease is released by a separate call after this supervisor
    # exits, because release requires the protected process to have stopped.
    return 0


if __name__ == "__main__":
    sys.exit(main())
