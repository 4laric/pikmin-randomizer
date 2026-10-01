#!/usr/bin/env python3
"""Private leased build/run helper for lane impact-fixture-gating-fix-native (#739).

Exclusive private build dir under output/; canonical lease CLI; live elastic
cap (no hardcoded slots). (1) Builds pikmin_pc (default config) to validate
the tree. (2) Splices the fixed fixture fragment into preview_p2_room.cpp (in
output/, never the tree) and links the guarded fixture against the private
pikmin_pc graph. (3) Compiles + runs the standalone probe. (4) Runs headed
from a staged asset root and captures the log. Never touches
native/build-randomizer, the maintained checkout, or CMakeLists. No ADMIT; the
run adopts the #632 guard inside the fixture.
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
                        "prerequisites", "impact-fixture-gating-fix-native")
NATIVE_DIR = os.path.join(
    ROOT, "output", "workflow", "autofill", "prerequisites",
    "impact-fixture-gating-fix-native-native")
BUILD_DIR = os.path.join(ROOT, "output", "impact-fixture-gating-fix-build")
OUT_DIR = os.path.join(LANE_DIR, "out")
RESOURCE = "build:output/impact-fixture-gating-fix-build"
STAGED_ROOT = os.path.join(ROOT, "output", "bomb-joint-runs", "chappy")
NINJA = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Packages",
                     "PythonSoftwareFoundation.Python.3.12_qbz5n2kfra8p0",
                     "LocalCache", "local-packages", "Python312",
                     "Scripts", "ninja.exe")
KEY, GEN = "impact-fixture-gating-fix-native", 2
ISSUE = 739

FIXTURE_BEGIN = "// MUSE-CHALLENGE-BOOT-INCLUDES-BEGIN"
FIXTURE_SPLIT = "// MUSE-CHALLENGE-BOOT-INCLUDES-END"
FIXTURE_APP = "// MUSE-CHALLENGE-BOOT-APP-BEGIN"
FIXTURE_END = "// MUSE-CHALLENGE-BOOT-APP-END"
ROOM_REQUIRE = 'require(pc_pikipelago_room_preview(),"requires --experimental-pikmin2-room");'
CHALLENGE_REQUIRE = ('require(pc_pikipelago_challenge_level()>=0 && !pc_pikipelago_room_preview(),'
                     '"requires --experimental-challenge-level 0-4");')

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
    exe = os.path.join(BUILD_DIR, "p2_impact_gating_fix_fixture.exe")
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
        # Splice the fixed fragment into a private room.cpp copy.
        fixture_text = open(os.path.join(
            NATIVE_DIR, "tools", "p2_challenge_guarded_boot_fixture.cpp"),
            encoding="utf-8").read()
        includes = fixture_text.split(FIXTURE_BEGIN, 1)[1].split(FIXTURE_SPLIT, 1)[0]
        app = fixture_text.split(FIXTURE_APP, 1)[1].split(FIXTURE_END, 1)[0]
        assert "class RoomApp : public PlugPikiApp {" in app
        assert "P2_CHALLENGE_GATE_DIAG" in app and "P2_CHALLENGE_PARK_ALIVE" in app
        room_src = open(os.path.join(NATIVE_DIR, "tools", "preview_p2_room.cpp"),
                        encoding="utf-8").read()
        start = room_src.index("class RoomApp : public PlugPikiApp {")
        end = room_src.index("int main(", start)
        room = (room_src[:start] + includes + app + room_src[end:]).replace(
            ROOM_REQUIRE, CHALLENGE_REQUIRE, 1)
        room_path = os.path.join(BUILD_DIR, "p2_impact_gating_fix_room.cpp")
        open(room_path, "w", encoding="utf-8", newline="").write(room)
        # Quoted sibling includes (preview_p2_*.inc) resolve against the
        # including file's directory; mirror them next to the spliced TU.
        import glob as _glob
        for inc in _glob.glob(os.path.join(NATIVE_DIR, "tools", "preview_p2_*.inc")):
            with open(inc, "rb") as fsrc, open(
                    os.path.join(BUILD_DIR, os.path.basename(inc)), "wb") as fdst:
                fdst.write(fsrc.read())
        record["steps"]["splice"] = {"exit": 0, "room": room_path,
                                     "room_sha256": sha256_file(room_path)}
        # Standalone probe first (fast, engine-free).
        probe_src = os.path.join(NATIVE_DIR, "tools", "p2_impact_gating_fix_probe.cpp")
        probe_exe = os.path.join(BUILD_DIR, "p2_impact_gating_fix_probe.exe")
        code, _ = run_logged(
            log, ["g++", "-std=c++17", "-Wall", "-Wextra", "-Werror",
                  "-o", probe_exe, probe_src], cwd=BUILD_DIR, env=env)
        record["steps"]["probe_compile"] = {"exit": code}
        save()
        if code != 0:
            return code
        fixture_src = os.path.join(
            NATIVE_DIR, "tools", "p2_challenge_guarded_boot_fixture.cpp")
        code, out = run_logged(
            log, [probe_exe, "--fixture-src", fixture_src], env=env)
        with open(os.path.join(OUT_DIR, "probe-run.log"), "w",
                  encoding="utf-8", newline="") as f:
            f.write("exit=%d\n%s" % (code, out))
        record["steps"]["probe_run"] = {
            "exit": code,
            "pass": code == 0 and "ALL_PROBE_PASS" in out}
        save()
        if code != 0:
            return code
        # Compile the spliced room TU with reference flags, link fixture exe.
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
        room_obj = os.path.join(BUILD_DIR, "p2_impact_gating_fix_room.obj")
        cmd = ref_cmd.replace(ref_file.replace("/", "\\"), room_path)
        cmd, n = re.subn(r"-o\s+\S+", lambda m: "-o " + room_obj, cmd, count=1)
        assert n == 1
        code, _ = run_logged(log, ["cmd", "/c", cmd], cwd=BUILD_DIR, env=env)
        record["steps"]["room_compile"] = {"exit": code}
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
                objects[i] = room_obj
                swapped = True
        assert swapped
        rsp = os.path.join(BUILD_DIR, "p2_impact_gating_fix.rsp")
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
        # Headed run from the staged asset root (boot must reach idle).
        run_env = dict(env)
        run_env["SDL_AUDIODRIVER"] = "dummy"
        run_env["PIKMIN_RANDOMIZER_TEST_BACKGROUND"] = "1"
        runlog = os.path.join(OUT_DIR, "headed-run.log")
        rcode, out = run_logged(
            log, [exe, "--experimental-challenge-level", "0"],
            cwd=STAGED_ROOT, env=run_env, timeout=240)
        with open(runlog, "w", encoding="utf-8", newline="") as f:
            f.write(out)
        record["steps"]["headed_run"] = {
            "exit": rcode, "log": runlog, "log_sha256": sha256_file(runlog)}
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
