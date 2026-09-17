#!/usr/bin/env python3
"""Private leased build/run helper for lane challenge-runtime-bridge-port-native (#722).

Exclusive private build dir under output/; canonical lease CLI; live elastic
cap (no hardcoded slots). Builds pikmin_pc (default config), compiles/links the
guarded runtime-bridge fixture as a replacement main, runs its guard self-test
/ negative test and a bounded headed run from a staged asset root (so the boot
reaches idle and the bridge can emit its markers), then records all hashes.
Never touches native/build-randomizer, the maintained checkout, or CMakeLists.
No ADMIT; the run adopts the #632 guard inside the fixture.
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
LANE_DIR = os.path.join(ROOT, "output", "workflow", "autofill",
                        "prerequisites", "challenge-runtime-bridge-port-native")
NATIVE_DIR = os.path.join(
    ROOT, "output", "workflow", "autofill", "prerequisites",
    "challenge-runtime-bridge-port-native-native")
BUILD_DIR = os.path.join(ROOT, "output", "challenge-runtime-bridge-build")
OUT_DIR = os.path.join(LANE_DIR, "out")
RESOURCE = "build:output/challenge-runtime-bridge-build"
STAGED_ROOT = os.path.join(ROOT, "output", "bomb-joint-runs", "chappy")
NINJA = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Packages",
                     "PythonSoftwareFoundation.Python.3.12_qbz5n2kfra8p0",
                     "LocalCache", "local-packages", "Python312",
                     "Scripts", "ninja.exe")
KEY, GEN = "challenge-runtime-bridge-port-native", 2
ISSUE = 722

CONFIGURE = ["cmake", "-S", NATIVE_DIR, "-B", BUILD_DIR, "-G", "Ninja",
             "-DCMAKE_C_COMPILER=gcc", "-DCMAKE_CXX_COMPILER=g++",
             "-DCMAKE_MAKE_PROGRAM=" + NINJA, "-DCMAKE_BUILD_TYPE=Release",
             "-DPIKMIN_NATIVE_OPTIMIZE=OFF",
             "-DCMAKE_EXPORT_COMPILE_COMMANDS=ON",
             "-DP2_CHALLENGE_GUARD_INCLUDE_DIR=" + os.path.join(ROOT, "scripts")]


def sha256_file(path):
    with open(path, "rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def cli(command, request):
    rp = os.path.join(OUT_DIR, "lease-%s-%d.json"
                      % (command, int(time.time() * 1000) % 1000000))
    json.dump(request, open(rp, "w", encoding="utf-8"))
    proc = subprocess.run(CLI + ["--request", rp, command],
                          capture_output=True, text=True, encoding="utf-8",
                          errors="replace")
    return proc.returncode, proc.stdout + proc.stderr


def run_logged(log, argv, cwd=None, env=None, timeout=None):
    log.write("+ %s\n" % " ".join(argv))
    log.flush()
    proc = subprocess.Popen(argv, cwd=cwd, env=env, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, text=True,
                            errors="replace")
    try:
        out, _ = proc.communicate(timeout=timeout)
        code = proc.returncode
    except subprocess.TimeoutExpired:
        proc.kill()
        out, _ = proc.communicate()
        code = None
    log.write(out or "")
    log.flush()
    return code, out or ""


def main():
    os.environ["PATH"] = (r"C:\msys64\mingw64\bin;"
                          + os.environ.get("PATH", ""))
    os.makedirs(OUT_DIR, exist_ok=True)
    stamp = str(int(time.time() * 1000000))
    log = open(os.path.join(OUT_DIR, "leased-build-%s.log" % stamp),
               "w", encoding="utf-8")
    record = {"lane": KEY, "issue": ISSUE, "stamp": stamp,
              "build_dir": BUILD_DIR, "staged_root": STAGED_ROOT, "steps": {}}
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
    exe = os.path.join(BUILD_DIR, "p2_challenge_runtime_bridge.exe")
    try:
        code, _ = run_logged(log, CONFIGURE, env=env)
        record["steps"]["configure"] = {"exit": code}
        save()
        if code != 0:
            return code
        code, _ = run_logged(log, ["cmake", "--build", BUILD_DIR,
                                   "--target", "pikmin_pc", "-j", "6"], env=env)
        record["steps"]["pikmin_pc"] = {"exit": code}
        save()
        if code != 0:
            return code
        code, dry = run_logged(log, [NINJA, "-n", "-C", BUILD_DIR], env=env)
        record["steps"]["dry_run"] = {"exit": code,
                                      "no_work": "no work to do" in dry,
                                      "tail": dry.strip().splitlines()[-1:]}
        commands = json.load(open(os.path.join(
            BUILD_DIR, "compile_commands.json"), encoding="utf-8"))
        ref_cmd = ref_file = None
        for end in ("tools/p2_kurage_runtime.cpp", "pc_port/pc_main.cpp"):
            for entry in commands:
                if entry["file"].replace("\\", "/").endswith(end):
                    ref_cmd, ref_file = entry["command"], entry["file"]
                    break
            if ref_cmd:
                break
        assert ref_cmd, "no reference TU"
        src_token = ref_file.replace("/", "\\")
        src = os.path.join(NATIVE_DIR, "tools",
                           "p2_challenge_runtime_bridge_fixture.cpp")
        obj = os.path.join(BUILD_DIR, "p2_challenge_runtime_bridge_fixture.obj")
        cmd = ref_cmd.replace(src_token, src)
        cmd, n = re.subn(r"-o\s+\S+", lambda m: "-o " + obj, cmd, count=1)
        assert n == 1
        code, _ = run_logged(log, ["cmd", "/c", cmd], cwd=BUILD_DIR, env=env)
        record["steps"]["fixture_compile"] = {"exit": code}
        save()
        if code != 0:
            return code
        ninja_text = open(os.path.join(BUILD_DIR, "build.ninja"),
                          encoding="utf-8", errors="replace").read()
        edge = link_libs = None
        lines = ninja_text.splitlines()
        for i, line in enumerate(lines):
            if "CXX_EXECUTABLE_LINKER__pikmin_pc" in line and line.startswith("build "):
                edge = line.replace("C$:/", "C:/")
                for j in range(i + 1, min(i + 20, len(lines))):
                    if lines[j].startswith("  LINK_LIBRARIES = "):
                        link_libs = lines[j].split("=", 1)[1].strip()
                        break
                break
        assert edge and link_libs
        objects = [t for t in edge.split()[2:]
                   if t.endswith(".obj") and "LINKER__" not in t]
        swapped = False
        for i, o in enumerate(objects):
            if o.replace("\\", "/").endswith("pc_port/pc_main.cpp.obj"):
                objects[i] = obj
                swapped = True
        assert swapped
        rsp = os.path.join(BUILD_DIR, "p2_challenge_runtime_bridge.rsp")
        with open(rsp, "w", encoding="utf-8") as f:
            f.write("\n".join('"' + o + '"' for o in objects))
        code, _ = run_logged(log, ["g++", "@" + rsp, "-mconsole", "-o", exe]
                             + link_libs.split(), cwd=BUILD_DIR, env=env)
        record["steps"]["fixture_link"] = {"exit": code, "exe": exe,
                                           "objects": len(objects)}
        save()
        if code != 0:
            return code
        record["exe_sha256"] = sha256_file(exe)
        code, out = run_logged(log, [exe, "--guard-self-test"], env=env)
        record["steps"]["self_test"] = {"exit": code, "pass": code == 0}
        if code != 0:
            return code
        code, out = run_logged(log, [exe, "--guard-negative-test"], env=env)
        record["steps"]["negative_test"] = {
            "exit": code,
            "verified": code == 86 and "P2_FIXTURE_CAPTAIN_DOWN" in out}
        if not record["steps"]["negative_test"]["verified"]:
            return 1
        # Headed run from the staged asset root so the boot reaches idle and the
        # engine bridge emits P2_CHALLENGE_MODE_BOOT/_TICK.
        run_env = dict(env)
        run_env["SDL_AUDIODRIVER"] = "dummy"
        run_env["PIKMIN_RANDOMIZER_TEST_BACKGROUND"] = "1"
        markers = os.path.join(OUT_DIR, "marker-run.log")
        rcode, out = run_logged(
            log, [exe, "--experimental-pikmin2-room",
                  "--experimental-challenge-stage", "ch_NARI_01kusachi",
                  "--ticks", "90"],
            cwd=STAGED_ROOT, env=run_env, timeout=180)
        with open(markers, "w", encoding="utf-8", newline="") as f:
            f.write(out)
        boot = "P2_CHALLENGE_MODE_BOOT" in out
        ticks = out.count("P2CHALLENGE_WIRING_TICK") + out.count("P2_CHALLENGE_MODE_TICK")
        record["steps"]["marker_run"] = {
            "exit": rcode, "boot_marker": boot, "tick_markers": ticks,
            "log": markers, "log_sha256": sha256_file(markers)}
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
