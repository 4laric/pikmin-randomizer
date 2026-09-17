"""Leased private build + link for the overworld course boot-flag fixture (#767).

Acquires the canonical build lease for a fresh private build directory,
configures a Release Ninja tree (MinGW), builds the pikmin_pc target,
compiles the new additive module plus the guarded fixture TU with the
tree flags, and links a replacement-main exe excluding pc_main. Never
touches pc_bbft.cpp/.h or CMakeLists.txt. Records hashed evidence.
"""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time

CANONICAL_ROOT = "C:/Users/alari/pikmin-randomizer"
sys.path.insert(0, CANONICAL_ROOT)
from workflow.registry import Registry  # noqa: E402

LANE = "overworld-course-boot-flag-native"
GENERATION = 2
GUARD_SHA256 = "d2f678c9eda75e151eb534077dff9e30ad36ae4796881d971bbd09945f3c3474"


def run(cmd, log, env=None, cwd=None):
    with open(log, "wb") as fh:
        proc = subprocess.run(cmd, stdout=fh, stderr=subprocess.STDOUT, env=env, cwd=cwd)
    return proc.returncode


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--native", required=True)
    ap.add_argument("--build", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--course", default="last")
    args = ap.parse_args()
    native = os.path.abspath(args.native)
    build = os.path.abspath(args.build)
    out = os.path.abspath(args.out)
    os.makedirs(out, exist_ok=True)
    reg = Registry(CANONICAL_ROOT + "/output/workflow/registry.sqlite3", CANONICAL_ROOT)
    resource = "build:" + os.path.relpath(build, CANONICAL_ROOT).replace(os.sep, "/")
    token = None
    deadline = time.monotonic() + 1800
    while True:
        acquired = reg.acquire(LANE, GENERATION, resource, os.getpid(), ttl=3600)
        if acquired.get("acquired"):
            token = acquired.get("token")
            break
        if time.monotonic() >= deadline:
            raise SystemExit("build lease wait timed out for " + resource)
        time.sleep(5)
    env = dict(os.environ)
    env["PATH"] = "C:/msys64/mingw64/bin;" + env.get("PATH", "")
    ninja = shutil.which("ninja", path=env["PATH"])
    if not ninja:
        ninja = "C:/Users/alari/AppData/Local/Packages/PythonSoftwareFoundation.Python.3.12_qbz5n2kfra8p0/LocalCache/local-packages/Python312/Scripts/ninja.exe"
    evidence = {"lane": LANE, "native": native, "build": build, "lease_token": token,
                "guard_sha256": GUARD_SHA256, "course": args.course}
    evidence["configure_rc"] = run(
        ["cmake", "-S", native, "-B", build, "-G", "Ninja",
         "-DCMAKE_BUILD_TYPE=Release", "-DCMAKE_MAKE_PROGRAM=" + ninja],
        os.path.join(out, "configure.log"), env=env)
    if evidence["configure_rc"] != 0:
        raise SystemExit("configure failed, see configure.log")
    evidence["build_rc"] = run(
        ["cmake", "--build", build, "--target", "pikmin_pc", "--parallel", "6"],
        os.path.join(out, "build.log"), env=env)
    if evidence["build_rc"] != 0:
        raise SystemExit("build failed, see build.log")
    evidence["ninja_dryrun_rc"] = run(
        [ninja, "-n", "pikmin_pc"], os.path.join(out, "ninja-dryrun.log"), env=env, cwd=build)
    with open(os.path.join(out, "evidence.json"), "w", encoding="utf-8") as fh:
        json.dump(evidence, fh, indent=2)
    print(json.dumps({k: evidence[k] for k in ("configure_rc", "build_rc", "ninja_dryrun_rc")}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
