"""Build + run helper for the leafchappy stage-table fixture (#774).

Compiles the engine-free provider and its guarded fixture with the system
MinGW g++ (never CMake, never the maintained build), runs the fixture plus
the guard self-test and negative test, validates the P2_LEAFCHAPPY_STAGE_*
markers, and records executable/log hashes. Refuses loudly on any failure.
Usage (from the lane root worktree)::

    py -3.12 scripts/build_p2_leafchappy_stage_table.py --native <native-worktree> --output <new-private-dir>

The output directory must be new and outside the native worktree. Nothing
is built in the shared native checkout; no CMakeLists.txt is touched.
"""
import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path


GPP_EXE = "C:\\msys64\\mingw64\\bin\\g++.exe"
MINGW_BIN = "C:\\msys64\\mingw64\\bin"


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run(args, cwd):
    # Absolute compiler path with native separators: CreateProcess PATH
    # lookup does not reliably resolve forward-slash entries, so the bare
    # "g++" name is rewritten to the full executable path. MinGW bin (with
    # native separators) is prepended so the compiler's own DLLs resolve.
    import os as _os
    env = dict(_os.environ)
    if MINGW_BIN.lower() not in env.get("PATH", "").lower():
        env["PATH"] = MINGW_BIN + ";" + env.get("PATH", "")
    fixed = [GPP_EXE if (isinstance(a, str) and a == "g++") else str(a)
             for a in args]
    completed = subprocess.run(
        fixed, cwd=str(cwd), env=env,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, encoding="utf-8", errors="replace", timeout=300)
    return completed.returncode, completed.stdout


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--native", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)

    native = args.native.resolve()
    output = args.output.resolve()
    provider = native / "pc_port" / "pc_p2_challenge_leafchappy_stage.cpp"
    fixture = native / "tools" / "p2_leafchappy_stage_table_fixture.cpp"
    for path in (provider, fixture):
        if not path.is_file():
            parser.exit(1, "missing source: %s\n" % path)
    header = native / "pc_port" / "pc_p2_challenge_leafchappy_stage.h"
    if not header.is_file():
        parser.exit(1, "missing header: %s\n" % header)
    if output.exists():
        parser.exit(1, "output must be a NEW directory: %s\n" % output)
    try:
        output.mkdir(parents=True, exist_ok=False)
    except OSError as error:
        parser.exit(1, "cannot create output: %s\n" % error)

    exe = output / "p2_leafchappy_stage_table_fixture.exe"
    code, text = run(["g++", "-std=c++17", "-Wall", "-Wextra", "-Werror",
                      "-Ipc_port", str(fixture), str(provider),
                      "-o", str(exe)], native)
    (output / "compile.log").write_text(text, encoding="utf-8")
    if code != 0 or not exe.is_file():
        parser.exit(1, "fixture compile failed; see compile.log\n")

    code, text = run([str(exe)], native)
    (output / "fixture-run.log").write_text(text, encoding="utf-8")
    if code != 0:
        parser.exit(1, "fixture run failed; see fixture-run.log\n")
    if "P2_LEAFCHAPPY_STAGE_RESOLVED cave=ch_ABEM_LeafChappy ui=17 floors=2" not in text:
        parser.exit(1, "RESOLVED marker missing\n")
    if "P2_LEAFCHAPPY_STAGE_REFUSED reason=unknown-key" not in text:
        parser.exit(1, "REFUSED marker missing\n")
    if "checks=" not in text or "failures=0" not in text.replace(" ", ""):
        parser.exit(1, "fixture did not report zero failures\n")

    code, text = run([str(exe), "--guard-self-test"], native)
    (output / "selftest.log").write_text(text, encoding="utf-8")
    if code != 0 or "P2_LEAFCHAPPY_SELFTEST_PASS rows=7" not in text:
        parser.exit(1, "guard self-test failed; see selftest.log\n")

    code, text = run([str(exe), "--guard-negative-test"], native)
    (output / "negative.log").write_text(text, encoding="utf-8")
    if code != 86 or "P2_FIXTURE_CAPTAIN_DOWN" not in text:
        parser.exit(1, "guard negative test failed; see negative.log\n")
    if "PASS TUTORIAL" in text or "P2_LEAFCHAPPY_STAGE_RESOLVED" in text:
        parser.exit(1, "negative test must emit no PASS or resolution\n")

    record = {
        "schema": 1,
        "status": "built",
        "native": str(native),
        "executable": str(exe),
        "executable_sha256": sha256(exe),
        "log": str(output / "fixture-run.log"),
        "log_sha256": sha256(output / "fixture-run.log"),
        "selftest_sha256": sha256(output / "selftest.log"),
        "negative_sha256": sha256(output / "negative.log"),
    }
    (output / "provenance.json").write_text(json.dumps(record, indent=2) + "\n",
                                            encoding="utf-8")
    print(json.dumps({"status": "built",
                      "executable_sha256": record["executable_sha256"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
