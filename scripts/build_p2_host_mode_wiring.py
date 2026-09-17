#!/usr/bin/env python3
"""Private leased build/run wrapper for the host-mode wiring fixture (#702).

Builds native/tools/p2_host_mode_wiring_fixture.cpp (a replacement-main TU)
against the private pikmin_pc graph WITHOUT editing shared build files: the
script configures the lane-private build dir, builds the existing pikmin_pc
target (tree health), compiles the fixture TU with the exact flags from
compile_commands.json, then reuses the pikmin_pc link command (build.ninja
edge + response file) with the pc_main object swapped for the fixture object.

Outputs (all under the lane out/ dir, never the shared tree):
  build-<ts>.log   full configure/build/link transcript
  build-<ts>.json  machine-readable record: exe SHA-256, source pins, guard
                   hash, dry-run and self-test evidence

Usage (from the canonical root):
  py -3.12 scripts/build_p2_host_mode_wiring.py --configure --build
  py -3.12 scripts/build_p2_host_mode_wiring.py --self-test
  py -3.12 scripts/build_p2_host_mode_wiring.py --verify-negative
  py -3.12 scripts/build_p2_host_mode_wiring.py --run <rundir> [-- <exe-args>]
"""
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time

NINJA = os.path.join(os.environ.get("LOCALAPPDATA", ""),
                     "Packages",
                     "PythonSoftwareFoundation.Python.3.12_qbz5n2kfra8p0",
                     "LocalCache", "local-packages", "Python312",
                     "Scripts", "ninja.exe")
CONFIGURE = ["cmake", "-S", "{native}", "-B", "{build}", "-G", "Ninja",
             "-DCMAKE_C_COMPILER=gcc", "-DCMAKE_CXX_COMPILER=g++",
             "-DCMAKE_MAKE_PROGRAM=" + NINJA, "-DCMAKE_BUILD_TYPE=Release",
             "-DPIKMIN_NATIVE_JAUDIO=ON", "-DPIKMIN_NATIVE_OPTIMIZE=OFF",
             "-DCMAKE_EXPORT_COMPILE_COMMANDS=ON"]


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run_logged(log, argv, cwd=None, env=None):
    log.write("+ %s\n" % " ".join(argv))
    log.flush()
    proc = subprocess.Popen(argv, cwd=cwd, env=env, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, text=True, errors="replace")
    out, _ = proc.communicate()
    log.write(out)
    log.flush()
    return proc.returncode, out


def reference_command(build_dir):
    cc_path = os.path.join(build_dir, "compile_commands.json")
    commands = json.load(open(cc_path, encoding="utf-8"))
    for end in ("tools/p2_kurage_runtime.cpp", "pc_port/pc_main.cpp"):
        for entry in commands:
            if entry["file"].replace("\\", "/").endswith(end):
                return entry["command"], entry["file"]
    raise RuntimeError("no reference TU in compile_commands.json")
def main(argv=None):
    parser = argparse.ArgumentParser(description="Build/run the host-mode wiring fixture")
    parser.add_argument("--root", default=".",
                        help="lane root/ worktree (canonical checkout or private worktree)")
    parser.add_argument("--configure", action="store_true")
    parser.add_argument("--build", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--verify-negative", action="store_true")
    parser.add_argument("--run", metavar="RUNDIR")
    parser.add_argument("exe_args", nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)
    if args.exe_args and args.exe_args[0] == "--":
        args.exe_args = args.exe_args[1:]

    root = os.path.abspath(args.root)
    lane_base = root[:-len("-root")] if root.endswith("-root") else root
    native_dir = lane_base + "-native"
    build_dir = os.path.join(lane_base, "build")
    out_dir = os.path.join(lane_base, "out")
    if not os.path.isdir(os.path.join(native_dir, "tools")):
        print("native worktree not found at %s" % native_dir)
        return 2
    os.makedirs(out_dir, exist_ok=True)

    stamp = str(int(time.time() * 1000000))
    log_path = os.path.join(out_dir, "build-%s.log" % stamp)
    record_path = os.path.join(out_dir, "build-%s.json" % stamp)
    record = {"lane": "host-mode-runtime-wiring-native", "issue": 702,
              "stamp": stamp, "build_dir": build_dir, "steps": {}}
    exe = os.path.join(build_dir, "p2_host_mode_wiring.exe")
    with open(log_path, "w", encoding="utf-8") as log:
        if args.configure:
            cmd = [a.format(native=native_dir, build=build_dir) for a in CONFIGURE]
            code, _ = run_logged(log, cmd)
            record["steps"]["configure"] = {"exit": code}
            if code != 0:
                return code
        if args.build:
            code, _ = run_logged(log, ["cmake", "--build", build_dir,
                                       "--target", "pikmin_pc", "--config", "Release"])
            record["steps"]["pikmin_pc"] = {"exit": code}
            if code != 0:
                return code
            code, dry = run_logged(log, [NINJA, "-n", "-C", build_dir])
            record["steps"]["dry_run"] = {"exit": code,
                                          "no_work": "no work to do" in dry}
            ref_cmd, ref_file = reference_command(build_dir)
            record["steps"]["reference_tu"] = {"file": ref_file}
            fixture_src = os.path.join(native_dir, "tools",
                                       "p2_host_mode_wiring_fixture.cpp")
            fixture_obj = os.path.join(build_dir, "p2_host_mode_wiring.obj")
            ref_base = os.path.basename(ref_file)
            if ref_base in ref_cmd:
                compile_cmd = ref_cmd.replace(ref_base, "p2_host_mode_wiring_fixture.cpp")
            else:
                compile_cmd = ref_cmd + " " + fixture_src
            compile_cmd, n_sub = re.subn(r"-o\s+\S+",
                                         lambda m: "-o " + fixture_obj,
                                         compile_cmd, count=1)
            assert n_sub == 1, "no -o output in reference compile command"
            code, _ = run_logged(log, ["cmd", "/c", compile_cmd], cwd=build_dir)
            record["steps"]["fixture_compile"] = {"exit": code, "object": fixture_obj}
            if code != 0:
                return code
            mode_src = os.path.join(native_dir, "pc_port", "pc_p2_challenge_mode.cpp")
            mode_obj = os.path.join(build_dir, "pc_p2_challenge_mode.obj")
            mode_cmd = re.sub(r"[^\s']*p2_host_mode_wiring_fixture\.cpp", lambda m: mode_src, compile_cmd)
            mode_cmd, n_sub = re.subn(r"-o\s+\S+", lambda m: "-o " + mode_obj, mode_cmd, count=1)
            assert n_sub == 1
            code, _ = run_logged(log, ["cmd", "/c", mode_cmd], cwd=build_dir)
            record["steps"]["mode_compile"] = {"exit": code, "object": mode_obj}
            if code != 0:
                return code
            ninja_text = open(os.path.join(build_dir, "build.ninja"),
                              encoding="utf-8", errors="replace").read()
            edge = link_libs = None
            for i, line in enumerate(ninja_text.splitlines()):
                if line.startswith("build bin/nectar.exe: CXX_EXECUTABLE_LINKER__pikmin_pc"):
                    edge = line.replace("C$:/", "C:/")
                    for j in range(i + 1, min(i + 20, len(ninja_text.splitlines()))):
                        cand = ninja_text.splitlines()[j]
                        if cand.startswith("  LINK_LIBRARIES = "):
                            link_libs = cand.split("=", 1)[1].strip()
                            break
                    break
            if edge is None or not link_libs:
                print("pikmin_pc link edge not found in build.ninja")
                record["steps"]["fixture_link"] = {"exit": 3}
                return 3
            objects = [tok for tok in edge.split()[2:]
                       if tok.endswith(".obj") and "LINKER__" not in tok]
            swapped = False
            for i, obj in enumerate(objects):
                if obj.replace("\\", "/").endswith("pc_port/pc_main.cpp.obj"):
                    objects[i] = fixture_obj
                    swapped = True
            if not swapped:
                print("pc_main object not on the pikmin_pc link edge")
                record["steps"]["fixture_link"] = {"exit": 3}
                return 3
            objects.append(mode_obj)
            rsp = os.path.join(build_dir, "p2_host_mode_wiring.rsp")
            with open(rsp, "w", encoding="utf-8") as f:
                f.write("\n".join('"' + o + '"' for o in objects))
            code, _ = run_logged(log, ["g++", "@" + rsp, "-mconsole", "-o", exe]
                                 + link_libs.split(), cwd=build_dir)
            record["steps"]["fixture_link"] = {"exit": code, "exe": exe,
                                               "objects": len(objects)}
            if code != 0:
                return code
            record["exe_sha256"] = sha256_file(exe)
        if args.self_test:
            if not os.path.isfile(exe):
                print("fixture exe missing: build first")
                return 2
            code, out = run_logged(log, [exe, "--guard-self-test"])
            record["steps"]["self_test"] = {
                "exit": code,
                "pass": code == 0 and "P2_HOST_MODE_SELFTEST_PASS" in out}
            if code != 0:
                return code
        if args.verify_negative:
            if not os.path.isfile(exe):
                print("fixture exe missing: build first")
                return 2
            code, out = run_logged(log, [exe, "--guard-negative-test"])
            ok = (code == 86 and "P2_FIXTURE_CAPTAIN_DOWN" in out
                  and "PASS HOST_MODE_WIRING" not in out)
            record["steps"]["verify_negative"] = {"exit": code, "verified": ok}
            if ok:
                log.write("P2_HOST_MODE_NEGATIVETEST_PASS\n")
                print("P2_HOST_MODE_NEGATIVETEST_PASS")
                return 0
            print("negative behavior NOT verified")
            return 1
        if args.run:
            if not os.path.isfile(exe):
                print("fixture exe missing: build first")
                return 2
            rundir = os.path.abspath(args.run)
            env = dict(os.environ, SDL_AUDIODRIVER="dummy")
            code, out = run_logged(log, [exe] + args.exe_args,
                                   cwd=rundir, env=env)
            record["steps"]["run"] = {
                "exit": code, "rundir": rundir,
                "pass": code == 0 and "PASS HOST_MODE_WIRING" in out,
                "stage_entry": "P2CHALLENGE_STAGE_ENTRY" in out,
                "captain_down": "P2_FIXTURE_CAPTAIN_DOWN" in out}
            return code
    json.dump(record, open(record_path, "w", encoding="utf-8"), indent=2)
    print("record %s" % record_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
