#!/usr/bin/env python3
"""Private leased build helper for lane bomb-birth-hook-notifier-port-native (#715).

Exclusive private build dir under output/; canonical lease CLI; live elastic
cap (no hardcoded slots). Configures and builds pikmin_pc plus the
p2_bomb_birth_notifier_test provider target, runs the provider test, records
the ninja dry run and all hashes. Usage:
  build_p2_bomb_birth_notifier.py [default|jaudio-on]
Default (no arg) is the default config; jaudio-on passes
PIKMIN_NATIVE_JAUDIO=ON into a separate build dir. Never touches
native/build-randomizer, the maintained checkout, or CMakeLists. No ADMIT; the
provider test itself is engine-free (no runtime run).
"""
import hashlib
import json
import os
import subprocess
import sys
import time

ROOT = r"C:\Users\alari\pikmin-randomizer"
CLI = [sys.executable, os.path.join(ROOT, "scripts", "pikmin2_workflow.py"),
       "--root", ROOT]
LANE_DIR = os.path.join(
    ROOT, "output", "workflow", "autofill", "prerequisites",
    "bomb-birth-hook-notifier-port-native")
NATIVE_DIR = os.path.join(
    ROOT, "output", "workflow", "autofill", "prerequisites",
    "bomb-birth-hook-notifier-port-native-native")
VARIANT = sys.argv[1] if len(sys.argv) > 1 else "default"
SUFFIX = "" if VARIANT == "default" else "-jaudioon"
BUILD_DIR = os.path.join(
    ROOT, "output", "bomb-birth-hook-notifier-build" + SUFFIX)
OUT_DIR = os.path.join(LANE_DIR, "out")
RESOURCE = "build:output/bomb-birth-hook-notifier-build" + SUFFIX
NINJA = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Packages",
                     "PythonSoftwareFoundation.Python.3.12_qbz5n2kfra8p0",
                     "LocalCache", "local-packages", "Python312",
                     "Scripts", "ninja.exe")
KEY, GEN = "bomb-birth-hook-notifier-port-native", 2
ISSUE = 715

CONFIGURE = ["cmake", "-S", NATIVE_DIR, "-B", BUILD_DIR, "-G", "Ninja",
             "-DCMAKE_C_COMPILER=gcc", "-DCMAKE_CXX_COMPILER=g++",
             "-DCMAKE_MAKE_PROGRAM=" + NINJA, "-DCMAKE_BUILD_TYPE=Release",
             "-DPIKMIN_NATIVE_OPTIMIZE=OFF",
             "-DCMAKE_EXPORT_COMPILE_COMMANDS=ON",
             "-DP2_CHALLENGE_GUARD_INCLUDE_DIR=" + os.path.join(ROOT, "scripts")]
if VARIANT == "jaudio-on":
    CONFIGURE.append("-DPIKMIN_NATIVE_JAUDIO=ON")


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


def main():
    os.environ["PATH"] = (r"C:\msys64\mingw64\bin;"
                          + os.environ.get("PATH", ""))
    os.makedirs(OUT_DIR, exist_ok=True)
    stamp = str(int(time.time() * 1000000))
    tag = "leased-build-%s%s" % (stamp, ("-" + VARIANT) if SUFFIX else "")
    log = open(os.path.join(OUT_DIR, tag + ".log"), "w", encoding="utf-8")
    record = {"lane": KEY, "issue": ISSUE, "stamp": stamp,
              "variant": VARIANT, "build_dir": BUILD_DIR, "steps": {}}
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
            OUT_DIR, "build-record-%s%s.json" % (stamp, SUFFIX)), "w",
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
        code, _ = run_logged(log, ["cmake", "--build", BUILD_DIR,
                                   "--target", "p2_bomb_birth_notifier_test",
                                   "-j", "6"], env=env)
        record["steps"]["provider_test_build"] = {"exit": code}
        save()
        if code != 0:
            return code
        code, out = run_logged(log, ["ctest", "--test-dir", BUILD_DIR,
                                     "-R", "p2_bomb_birth_notifier_test",
                                     "--output-on-failure"], env=env)
        record["steps"]["provider_test_run"] = {
            "exit": code, "pass": code == 0 and "Passed" in out}
        save()
        if code != 0:
            return code
        test_exe = os.path.join(BUILD_DIR, "p2_bomb_birth_notifier_test.exe")
        record["steps"]["provider_test_exe"] = {"path": test_exe,
                                                "exists": os.path.isfile(test_exe)}
        if os.path.isfile(test_exe):
            record["steps"]["provider_test_exe"]["sha256"] = sha256_file(test_exe)
            code, out = run_logged(log, [test_exe], env=env)
            with open(os.path.join(
                    OUT_DIR, "ctest-%s.log" % stamp), "w", encoding="utf-8",
                    newline="") as f:
                f.write("exit=%d\n%s" % (code, out))
            record["steps"]["provider_direct_run"] = {
                "exit": code,
                "pass": code == 0 and "ALL_FIXTURE_PASS" in out
                and "FAIL" not in out.replace("ALL_FIXTURE_PASS", "")}
            save()
            if code != 0:
                return code
        code, dry = run_logged(log, [NINJA, "-n", "-C", BUILD_DIR], env=env)
        record["steps"]["dry_run"] = {
            "exit": code, "no_work": "no work to do" in dry,
            "tail": dry.strip().splitlines()[-1:]}
        for root, _dirs, files in os.walk(BUILD_DIR):
            for name in files:
                if name in ("nectar.exe", "p2_bomb_birth_notifier_test.exe"):
                    full = os.path.join(root, name)
                    record.setdefault("executables", {})[full] = sha256_file(full)
        save()
    finally:
        save()
        print("record build-record-%s%s.json" % (stamp, SUFFIX))
        log.close()
    # NOTE: the lease is released by a separate call after this supervisor
    # exits, because release requires the protected process to have stopped.
    return 0


if __name__ == "__main__":
    sys.exit(main())
