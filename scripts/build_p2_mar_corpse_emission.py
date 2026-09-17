#!/usr/bin/env python3
"""Private leased build/run helper for the Mar corpse-emission fixture (#716).

Drives the maintained generic fixture builder
(scripts/build_pikmin2_fixture.py) for
native/tools/p2_mar_corpse_emission_fixture.cpp, then runs the guarded
emission proof and validates markers. The #668 receipt/preview files and all
other family/shared files are never touched.

Usage (from the canonical root):
  py -3.12 scripts/build_p2_mar_corpse_emission.py --source <native> --build <build>
      --output <out> --expected-native-head <40hex> [--check-only] [--run <rundir>]

The run directory must stage the Mar arena (generator 375001, same contract as
the #375 observer); the fixture fails closed naming that input when no Mar is
present. Heavy jobs require a canonical registry build lease held beforehand;
this script never acquires one itself. No maintained/CMakeLists/preview edits.
"""
import argparse
import hashlib
import json
import os
import subprocess
import sys

FIXTURE = "tools/p2_mar_corpse_emission_fixture.cpp"
PASS_MARKER = "PASS P2_MAR_CORPSE_EMISSION"
EMITTED_MARKER = "P2_MAR_CORPSE_EMITTED_OBSERVED"
RECEIPT_MARKER = "P2_MAR_CORPSE_RECEIPT_RESOLVED"
CAPTAIN_DOWN = "P2_FIXTURE_CAPTAIN_DOWN"
INJECTED_TOKENS = ("P2_LL_INJECT", "P2_LIFECYCLE_INJECT", "injected_health",
                   "mHealth=", "Transport(")
GUARD_SHA256 = "d2f678c9eda75e151eb534077dff9e30ad36ae4796881d971bbd09945f3c3474"
# Canonical builder (never the lane worktree, which may carry a stale copy).
MAINTAINED_ROOT = os.environ.get("PIKMIN2_CANONICAL_ROOT", os.getcwd())
MAINTAINED_BUILDER = os.path.join(MAINTAINED_ROOT, "scripts",
                                  "build_pikmin2_fixture.py")


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def check_run_markers(text):
    """PASS + emission + receipt present, no captain-down, no injection."""
    if CAPTAIN_DOWN in text:
        return False, "captain-down interruption present"
    if PASS_MARKER not in text:
        return False, "run PASS marker absent"
    if EMITTED_MARKER not in text:
        return False, "no corpse-emission marker"
    if RECEIPT_MARKER not in text:
        return False, "no receipt-resolution marker"
    injected = [t for t in INJECTED_TOKENS if t in text]
    if injected:
        return False, "injection markers present: %s" % ",".join(injected)
    return True, "run PASS with corpse emission + receipt observed"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, help="native worktree")
    parser.add_argument("--build", required=True, help="private build dir (leased)")
    parser.add_argument("--output", required=True, help="private output dir")
    parser.add_argument("--expected-native-head", required=True)
    parser.add_argument("--check-only", action="store_true")
    parser.add_argument("--run", metavar="RUNDIR")
    args = parser.parse_args(argv)

    builder = [sys.executable,
               MAINTAINED_BUILDER,
               "--source", os.path.abspath(args.source),
               "--build", os.path.abspath(args.build),
               "--fixture", os.path.join(os.path.abspath(args.source), FIXTURE),
               "--output", os.path.abspath(args.output),
               "--expected-native-head", args.expected_native_head]
    if args.check_only:
        builder.append("--check-only")
    code = subprocess.call(builder)
    if code != 0:
        print("builder step failed")
        return code
    if args.run is None:
        print("build/check step complete; no run requested")
        return 0
    rundir = os.path.abspath(args.run)
    record = {"fixture": FIXTURE, "rundir": rundir, "guard_sha256": GUARD_SHA256}
    exe_candidates = []
    for base in (args.output, args.build):
        for name in ("fixture.exe", "p2_mar_corpse_emission.exe"):
            path = os.path.join(base, name)
            if os.path.isfile(path):
                exe_candidates.append(path)
    if not exe_candidates:
        print("fixture exe missing: build first")
        return 2
    exe = exe_candidates[0]
    record["exe"] = exe
    record["exe_sha256"] = sha256_file(exe)
    env = dict(os.environ)
    env["SDL_AUDIODRIVER"] = "dummy"
    env["PIKMIN_P2_ROOM_WINDOW"] = "960x540"
    proc = subprocess.Popen([exe, "--experimental-pikmin2-room"], cwd=rundir,
                            env=env, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, text=True,
                            errors="replace")
    try:
        out, _ = proc.communicate(timeout=900)
    except subprocess.TimeoutExpired:
        proc.kill()
        print("run timed out")
        return 2
    ok, detail = check_run_markers(out)
    record["run"] = {"exit": proc.returncode, "detail": detail, "pass": ok}
    print(detail)
    with open(os.path.join(args.output, "mar-corpse-emission-run.json"), "w",
              encoding="utf-8") as f:
        json.dump(record, f, indent=1)
    return 0 if (proc.returncode == 0 and ok) else 1


if __name__ == "__main__":
    sys.exit(main())