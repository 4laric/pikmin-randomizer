#!/usr/bin/env python3
"""Private leased build/run helper for lane yakushima-p1-boot-stall-diagnosis (#717).

Exclusive private build dir under output/; canonical lease CLI; live elastic
cap (no hardcoded slots). Builds pikmin_pc (default config), compiles/links the
diagnosis TU as a replacement main, runs the guarded self-test / negative test
and a bounded headed run, then maps the captured RIP to the nearest symbol.
Never touches native/build-randomizer, the maintained checkout, or CMakeLists.
No ADMIT; the diagnosis run adopts the #632 guard inside the fixture.
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
                        "prerequisites", "yakushima-p1-boot-stall-diagnosis")
NATIVE_DIR = os.path.join(
    ROOT, "output", "workflow", "autofill", "prerequisites",
    "yakushima-p1-boot-stall-diagnosis-native")
VARIANT = sys.argv[1] if len(sys.argv) > 1 else "default"
SUFFIX = "" if VARIANT == "default" else "-jaudioon"
BUILD_DIR = os.path.join(ROOT, "output", "yakushima-p1-boot-diag-build" + SUFFIX)
OUT_DIR = os.path.join(LANE_DIR, "out")
RESOURCE = "build:output/yakushima-p1-boot-diag-build" + SUFFIX
NINJA = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Packages",
                     "PythonSoftwareFoundation.Python.3.12_qbz5n2kfra8p0",
                     "LocalCache", "local-packages", "Python312",
                     "Scripts", "ninja.exe")
KEY, GEN = "yakushima-p1-boot-stall-diagnosis", 2
ISSUE = 717

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
    except subprocess.TimeoutExpired:
        proc.kill()
        out, _ = proc.communicate()
        log.write(out)
        log.flush()
        return None, out
    log.write(out)
    log.flush()
    return proc.returncode, out


def symbol_for(exe, rip):
    """Nearest preceding symbol for rip (nm -n) plus addr2line function."""
    proc = subprocess.run(["nm", "-n", exe], capture_output=True, text=True,
                          errors="replace")
    best = None
    for line in proc.stdout.splitlines():
        parts = line.split()
        if len(parts) < 3:
            continue
        try:
            addr = int(parts[0], 16)
        except ValueError:
            continue
        if addr <= rip and (best is None or addr > best[0]):
            best = (addr, parts[-1])
    result = {"rip": hex(rip)}
    if best:
        result["nearest_symbol"] = best[1]
        result["symbol_offset"] = hex(rip - best[0])
    proc = subprocess.run(["addr2line", "-e", exe, "-f", "-C", hex(rip)],
                          capture_output=True, text=True, errors="replace")
    if proc.returncode == 0:
        result["addr2line"] = proc.stdout.strip().splitlines()
    return result


def main():
    os.environ["PATH"] = (r"C:\msys64\mingw64\bin;"
                          + os.environ.get("PATH", ""))
    os.makedirs(OUT_DIR, exist_ok=True)
    stamp = str(int(time.time() * 1000000))
    tag = "leased-build-%s%s" % (stamp, ("-" + VARIANT) if SUFFIX else "")
    log = open(os.path.join(OUT_DIR, tag + ".log"), "w", encoding="utf-8")
    record = {"lane": KEY, "issue": ISSUE, "stamp": stamp, "variant": VARIANT,
              "build_dir": BUILD_DIR, "steps": {}}
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
    exe = os.path.join(BUILD_DIR, "p2_yakushima_p1_boot_diagnosis.exe")
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
        src = os.path.join(NATIVE_DIR, "tools", "p2_yakushima_p1_boot_diagnosis.cpp")
        obj = os.path.join(BUILD_DIR, "p2_yakushima_p1_boot_diagnosis.obj")
        cmd = ref_cmd.replace(src_token, src)
        cmd, n = re.subn(r"-o\s+\S+", lambda m: "-o " + obj, cmd, count=1)
        assert n == 1
        code, _ = run_logged(log, ["cmd", "/c", cmd], cwd=BUILD_DIR, env=env)
        record["steps"]["diagnosis_compile"] = {"exit": code}
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
        rsp = os.path.join(BUILD_DIR, "p2_yakushima_p1_boot_diagnosis.rsp")
        with open(rsp, "w", encoding="utf-8") as f:
            f.write("\n".join('"' + o + '"' for o in objects))
        code, _ = run_logged(log, ["g++", "@" + rsp, "-mconsole", "-o", exe]
                             + link_libs.split(), cwd=BUILD_DIR, env=env)
        record["steps"]["diagnosis_link"] = {"exit": code, "exe": exe,
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
        # Headed diagnosis run (bounded; the fixture's own watchdog fails closed).
        diag = os.path.join(OUT_DIR, "diagnosis-run%s.log" % SUFFIX)
        rcode, out = run_logged(log, [exe, "--experimental-pikmin2-room",
                                      "--watchdog-seconds", "90",
                                      "--target-idle", "120"],
                                env=env, timeout=180)
        with open(diag, "w", encoding="utf-8", newline="") as f:
            f.write(out)
        record["steps"]["diagnosis_run"] = {
            "exit": rcode, "log": diag, "log_sha256": sha256_file(diag)}
        m = re.search(r"rip=0x([0-9a-fA-F]+)", out)
        if m:
            record["steps"]["diagnosis_run"]["rip_map"] = symbol_for(
                exe, int(m.group(1), 16))
        save()
    finally:
        save()
        print("record build-record-%s%s.json" % (stamp, SUFFIX))
        log.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
