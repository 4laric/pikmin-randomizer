#!/usr/bin/env python3
"""Leased private build + replacement-main link for #732 (root worktree copy).

Owns no build graph: configures a private Ninja/MinGW build dir from the
lane's private native worktree, builds pikmin_pc, records the `ninja -n`
dry run, then links tools/p2_bomb_birth_hook_callsite_fixture.cpp against
the pikmin_pc object graph (all objects except pc_main) using the exact
pikmin_pc link.txt line. Prints executable SHA-256 hashes.

Usage:
  py -3.12 scripts/build_p2_bomb_birth_hook_callsite.py --native <wt> --build <dir>
  py -3.12 scripts/build_p2_bomb_birth_hook_callsite.py --native <wt> --build <dir> --run <arena> -- [fixture args]
"""
import argparse
import hashlib
import os
import shlex
import subprocess
import sys

MINGW = r"C:\msys64\mingw64\bin"


def ninja_exe():
    try:
        import ninja  # noqa
        return os.path.join(ninja.BIN_DIR, "ninja.exe")
    except Exception:
        return "ninja.exe"


def run(cmd, cwd=None, env=None, timeout=None):
    print("+", " ".join(cmd), flush=True)
    return subprocess.run(cmd, cwd=cwd, env=env, timeout=timeout)


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def read_flags(build_dir):
    """Compile defines/includes/flags for pikmin_pc from build.ninja."""
    import re
    text = open(os.path.join(build_dir, "build.ninja"),
                encoding="utf-8", errors="replace").read()
    m = re.search(r"build CMakeFiles/pikmin_pc\.dir/pc_port/pc_bbft\.cpp\.obj:.*?"
                  r"DEFINES = ([^\n]*)\n.*?FLAGS = ([^\n]*)\n.*?INCLUDES = ([^\n]*)\n",
                  text, re.S)
    if not m:
        raise RuntimeError("pikmin_pc compile recipe not found in build.ninja")
    return {"CXX_DEFINES": m.group(1).strip(),
            "CXX_FLAGS": m.group(2).strip(),
            "CXX_INCLUDES": m.group(3).strip()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--native", required=True)
    ap.add_argument("--build", required=True)
    ap.add_argument("--jobs", default="6")
    ap.add_argument("--run", default=None)
    ap.add_argument("--run-timeout", type=int, default=240)
    ap.add_argument("extra", nargs=argparse.REMAINDER)
    args = ap.parse_args()

    src = os.path.abspath(args.native)
    bld = os.path.abspath(args.build)
    env = dict(os.environ)
    env["PATH"] = MINGW + os.pathsep + env.get("PATH", "")

    if not os.path.exists(os.path.join(bld, "build.ninja")):
        rc = run(["cmake", "-S", src, "-B", bld, "-G", "Ninja",
                  "-DCMAKE_C_COMPILER=gcc", "-DCMAKE_CXX_COMPILER=g++",
                  "-DCMAKE_BUILD_TYPE=Release", "-DPIKMIN_NATIVE_JAUDIO=ON",
                  "-DP2_CHALLENGE_GUARD_INCLUDE_DIR=C:/Users/alari/pikmin-randomizer/scripts",
                  "-DCMAKE_MAKE_PROGRAM=" + ninja_exe()], env=env).returncode
        if rc:
            return rc
    rc = run(["cmake", "--build", bld, "--target", "pikmin_pc",
              "-j", args.jobs], env=env).returncode
    if rc:
        return rc
    dry = run(["cmake", "--build", bld, "--target", "pikmin_pc",
               "--", "-n"], env=env)
    print("ninja -n exit:", dry.returncode, flush=True)

    # The pikmin_pc target links as bin/nectar.exe (see build.ninja
    # CXX_EXECUTABLE_LINKER__pikmin_pc_Release).
    exe = os.path.join(bld, "bin", "nectar.exe")
    if not os.path.exists(exe):
        exe = os.path.join(bld, "pikmin_pc.exe")
    print("engine exe sha256:", sha256(exe), flush=True)

    # Compile the callsite fixture with pikmin_pc's own flags.
    flags = read_flags(bld)
    obj_dir = os.path.join(bld, "callsite-fixture")
    os.makedirs(obj_dir, exist_ok=True)
    fixture_src = os.path.join(src, "tools",
                               "p2_bomb_birth_hook_callsite_fixture.cpp")
    fixture_obj = os.path.join(obj_dir,
                               "p2_bomb_birth_hook_callsite_fixture.cpp.obj")
    compile_cmd = ([os.path.join(MINGW, "g++.exe")]
                   + shlex.split(flags["CXX_DEFINES"])
                   + shlex.split(flags["CXX_INCLUDES"])
                   + shlex.split(flags["CXX_FLAGS"])
                   + ["-o", fixture_obj, "-c", fixture_src])
    rc = run(compile_cmd, cwd=bld, env=env).returncode
    if rc:
        return rc

    # Link: parse the pikmin_pc link edge from build.ninja (Ninja writes no
    # link.txt): same objects minus pc_main, plus the fixture object, same
    # FLAGS/LINK_FLAGS/LINK_LIBRARIES, cwd=build dir for relative libs.
    import re
    ninja_text = open(os.path.join(bld, "build.ninja"),
                      encoding="utf-8", errors="replace").read()
    edge = re.search(r"build bin/nectar\.exe: \S+ ([^\n]+)", ninja_text)
    if not edge:
        raise RuntimeError("pikmin_pc link edge not found in build.ninja")
    objs = [w for w in edge.group(1).split() if w.endswith(".obj")
            and os.path.basename(w).lower() != "pc_main.cpp.obj"]
    blk = ninja_text[edge.end():edge.end() + 3000]
    def var(name):
        m = re.search(r"^  " + name + r" = ([^\n]*)$", blk, re.M)
        return m.group(1).strip() if m else ""
    out_exe = os.path.join(obj_dir, "p2_bomb_birth_hook_callsite_fixture.exe")
    link_cmd = ([os.path.join(MINGW, "g++.exe")] + objs + [fixture_obj]
                + ["-o", out_exe] + shlex.split(var("FLAGS"))
                + shlex.split(var("LINK_FLAGS"))
                + shlex.split(var("LINK_LIBRARIES")))
    print("+ link.txt objects kept:", len(objs), flush=True)
    rc = run(link_cmd, cwd=bld, env=env).returncode
    if rc:
        return rc
    print("fixture exe sha256:", sha256(out_exe), flush=True)

    if args.run:
        extra = [a for a in args.extra if a != "--"]
        rc = run([out_exe] + extra, cwd=os.path.abspath(args.run),
                 env=env, timeout=args.run_timeout).returncode
        print("fixture run exit:", rc, flush=True)
        return 0 if rc == 0 else rc
    return 0


if __name__ == "__main__":
    sys.exit(main())
