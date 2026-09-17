#!/usr/bin/env python3
"""Private leased build/run helper for the challenge content-loading fixture (#694).

Drives the maintained generic fixture builder
(scripts/build_pikmin2_fixture.py) for
native/tools/p2_challenge_content_loading_fixture.cpp, then runs the guarded
content-boot observation and validates markers. The consumer P1 lanes
(#533/#561/#562) and providers (#651/#656/#672/#688) are never touched.

Usage (from the canonical root):
  py -3.12 scripts/build_p2_challenge_content_loading.py --source <native> --build <build>
      --output <out> --expected-native-head <40hex> [--check-only] [--run <rundir>]

  When driven under a leased lane worktree (whose cwd is the lane root), set
  PIKMIN2_CANONICAL_ROOT to the canonical checkout so the maintained generic
  fixture builder below is resolved there; otherwise it defaults to the cwd
  (canonical-root usage).

Steps: builder --check-only (or full build), ninja -n dry run, exe SHA-256,
fixture provenance `built`, guarded run asserting PASS P2_CHALLENGE_CONTENT_RUN
with live squad/actors markers and no CAPTAIN_DOWN / injection markers. Heavy
jobs require a canonical registry build lease held beforehand; this script never
acquires one itself. No maintained/CMakeLists/preview/consumer edits.
"""
import argparse
import hashlib
import json
import os
import subprocess
import sys

FIXTURE = "tools/p2_challenge_content_loading_fixture.cpp"
PASS_MARKER = "PASS P2_CHALLENGE_CONTENT_RUN"
LIVE_MARKER = "P2_CHALLENGE_CONTENT_LIVE"
READY_MARKER = "P2_CHALLENGE_CONTENT_READY"
CAPTAIN_DOWN = "P2_FIXTURE_CAPTAIN_DOWN"
INJECTED_TOKENS = ("P2_LL_INJECT", "P2_LIFECYCLE_INJECT", "injected_health",
                   "mHealth=", "Transport(")
GUARD_SHA256 = "d2f678c9eda75e151eb534077dff9e30ad36ae4796881d971bbd09945f3c3474"
# Maintained generic fixture builder. Resolved against the canonical checkout
# (never the lane worktree, which may carry a stale copy): the leased runner
# executes this helper with cwd set to the lane root.
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
    """PASS + live content present, no captain-down, no injection."""
    if CAPTAIN_DOWN in text:
        return False, "captain-down interruption present"
    if PASS_MARKER not in text:
        return False, "run PASS marker absent"
    if LIVE_MARKER not in text:
        return False, "no live-content marker"
    injected = [t for t in INJECTED_TOKENS if t in text]
    if injected:
        return False, "injection markers present: %s" % ",".join(injected)
    return True, "run PASS with live content observed"


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
        for name in ("fixture.exe", "p2_challenge_content_loading.exe"):
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
        out, _ = proc.communicate(timeout=600)
    except subprocess.TimeoutExpired:
        proc.kill()
        print("run timed out")
        return 2
    ok, detail = check_run_markers(out)
    record["run"] = {"exit": proc.returncode, "detail": detail, "pass": ok}
    print(detail)
    with open(os.path.join(args.output, "content-loading-run.json"), "w",
              encoding="utf-8") as f:
        json.dump(record, f, indent=1)
    return 0 if (proc.returncode == 0 and ok) else 1


if __name__ == "__main__":
    sys.exit(main())