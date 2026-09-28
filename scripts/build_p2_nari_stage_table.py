"""Leased-build + fixture-build + guarded-run driver for the NARI rows (#769).

Thin wrapper over the canonical tools (never reimplements them):
1. Configures the private Ninja build (sanitized PATH: msys64 first, so no
   foreign DLL hijacks cc1plus).
2. Builds pikmin_pc through canonical scripts/workflow_native_build.py
   (lease acquisition + evidence + ninja dry-run handled there).
3. Builds the guarded fixture through scripts/build_pikmin2_fixture.py.
4. Stages a minimal practice-overlay run dir and executes the fixture
   through canonical scripts/run_pikmin2_fixture.py (bounded supervisor).
Usage: python scripts/build_p2_nari_stage_table.py --source <native> --build
<dir> --output <evidence-dir> --lane <lane> --generation <gen> --head <sha>.
Prints hashed evidence paths. Exits nonzero on any failure.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import uuid
from pathlib import Path

CANONICAL = Path("C:/Users/alari/pikmin-randomizer")
PY = Path("C:/Users/alari/AppData/Local/Microsoft/WindowsApps/"
          "PythonSoftwareFoundation.Python.3.12_qbz5n2kfra8p0/python.exe")
FIXTURE = "tools/p2_nari_stage_table_fixture.cpp"
PASS_MARKERS = ["P2_NARI_STAGE_TABLE_DONE stages=2"]


def clean_env() -> dict:
    env = dict(os.environ)
    env["PATH"] = os.pathsep.join([
        "C:/Program Files/CMake/bin", "C:/msys64/mingw64/bin", "C:/msys64/usr/bin",
        str(Path.home() / "AppData/Local/Packages/PythonSoftwareFoundation.Python.3.12_qbz5n2kfra8p0/LocalCache/local-packages/Python312/Scripts"),
        "C:/Windows/system32", "C:/Windows",
    ]) + os.pathsep + env.get("PATH", "")
    env["CC"] = "C:/msys64/mingw64/bin/gcc.exe"
    env["CXX"] = "C:/msys64/mingw64/bin/g++.exe"
    return env


def run(command, **kwargs):
    proc = subprocess.run(command, capture_output=True, text=True, **kwargs)
    if proc.returncode != 0:
        raise SystemExit("FAILED %s\n%s" % (" ".join(map(str, command)), proc.stderr[-2000:]))
    return proc


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--build", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--lane", required=True)
    parser.add_argument("--generation", type=int, required=True)
    parser.add_argument("--head", required=True)
    args = parser.parse_args(argv)
    env = clean_env()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    run(["cmake", "-S", str(args.source), "-B", str(args.build), "-G", "Ninja",
         "-DCMAKE_BUILD_TYPE=Release", "-DPIKMIN_NATIVE_JAUDIO=ON"], env=env)
    build_req = {"lane": args.lane, "generation": args.generation,
                 "source": str(args.source), "build": str(args.build),
                 "expected_head": args.head,
                 "executable": str(args.build / "bin/nectar.exe"),
                 "output": str(out / "production-build"), "jobs": 6}
    (out / "native-build-request.json").write_text(json.dumps(build_req, indent=1), encoding="utf-8")
    run([str(PY), str(CANONICAL / "scripts/workflow_native_build.py"),
         "--root", str(CANONICAL), "--request", str(out / "native-build-request.json")], env=env)
    run([str(PY), str(CANONICAL / "scripts/build_pikmin2_fixture.py"),
         "--build", str(args.build), "--source", str(args.source),
         "--fixture", str(args.source / FIXTURE),
         "--output", str(out / "fixture-build"),
         "--expected-native-head", args.head], env=env)
    exe = out / "fixture-build/fixture.exe"
    print("fixture.exe sha256:", hashlib.sha256(exe.read_bytes()).hexdigest())
    for extra in (["--self-test"], ["--negative-test"], ["4"], ["5"], []):
        name = "selftest" if extra == ["--self-test"] else (
            "negative" if extra == ["--negative-test"] else (
                "ui" + extra[0] if extra else "both"))
        log = out / ("fixture-" + name + ".log")
        proc = subprocess.run([str(exe), *extra], capture_output=True, text=True, timeout=120)
        log.write_text(proc.stdout + proc.stderr, encoding="utf-8")
        print("%s exit=%d sha256=%s" % (
            name, proc.returncode, hashlib.sha256(log.read_bytes()).hexdigest()))
    print("EVIDENCE_DIR=%s" % out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
