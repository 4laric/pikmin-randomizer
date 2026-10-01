"""Private leased build/run helper for the Damagumo profile/mesh fixture (#678).

Compiles native/tools/p2_damagumo_profile_mesh_fixture.cpp standalone with
g++ (engine-free; the binding core travels inside the TU), records the
executable SHA-256, runs the contract self-check (expect exit 0) and the
guard-negative path (expect exit 86/BLOCKED), and writes machine-readable
evidence. No CMake/CTest edit, no shared build dir, no runtime game launch.
"""
import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def run(cmd, cwd):
    proc = subprocess.run(cmd, capture_output=True, text=True, cwd=str(cwd))
    return proc.returncode, proc.stdout + proc.stderr


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True,
                        help="private native worktree containing tools/ fixture")
    parser.add_argument("--output", type=Path, required=True,
                        help="private output dir for exe + evidence (created)")
    parser.add_argument("--compiler", default="g++")
    args = parser.parse_args(argv)

    source = args.source
    fixture = source / "tools" / "p2_damagumo_profile_mesh_fixture.cpp"
    if not fixture.is_file():
        raise SystemExit("missing fixture TU: " + str(fixture))
    args.output.mkdir(parents=True, exist_ok=True)
    exe = args.output / ("p2_damagumo_profile_mesh_fixture.exe"
                         if sys.platform == "win32"
                         else "p2_damagumo_profile_mesh_fixture")

    code, log = run([args.compiler, "-std=gnu++17", "-Wall", "-Wextra",
                     "-Werror", "-DP2_DAMAGUMO_BINDING_STANDALONE",
                     str(fixture), "-o", str(exe)], cwd=source)
    if code != 0:
        raise SystemExit("compile failed:\n" + log)
    exe_sha = sha256(exe)

    code_main, log_main = run([str(exe)], cwd=args.output)
    code_neg, log_neg = run([str(exe), "--guard-negative"], cwd=args.output)

    evidence = {
        "schema": 1,
        "source": str(source),
        "fixture": "native/tools/p2_damagumo_profile_mesh_fixture.cpp",
        "executable": str(exe),
        "executable_sha256": exe_sha,
        "self_check": {"exit_code": code_main, "log_tail": log_main.strip().splitlines()[-4:]},
        "guard_negative": {"exit_code": code_neg, "log_tail": log_neg.strip().splitlines()[-2:]},
        "ninja": "N/A: standalone single-TU g++ compile; no ninja graph exists for this fixture",
    }
    if code_main != 0 or code_neg != 86:
        raise SystemExit("unexpected fixture verdicts:\n" + json.dumps(evidence, indent=1))
    (args.output / "evidence.json").write_text(json.dumps(evidence, indent=1) + "\n",
                                               encoding="utf-8")
    print(json.dumps({"executable_sha256": exe_sha, "self_check": code_main,
                      "guard_negative": code_neg}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
