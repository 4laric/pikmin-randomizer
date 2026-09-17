#!/usr/bin/env python3
"""Private leased build/run helper for the owned tutorial1 P1 fixture (#674).

Drives the extended shared wrapper
(scripts/build_p2_cave_guarded_boot_fixture.py, --fixture support) to build
and run the consumer-owned native/tools/p2_tutorial1_p1_fixture.cpp
UNMODIFIED for blocked consumer p2-cave-tutorial_1-p1-runtime (#114):

1. Verifies the consumer fixture byte-identical against a caller-pinned
   --expect-sha (fail closed on any drift; never edits it).
2. Acquires a canonical registry build lease for the private build dir
   (elastic cap enforced by the registry, never assumed here).
3. Invokes the wrapper (--configure/--build, then --run) with
   --fixture p2_tutorial1_p1_fixture.cpp and --pass-marker "PASS TUTORIAL1_P1".
4. Verifies the run PASS marker, the absence of CAPTAIN_DOWN, and the #632
   guard hash; emits a machine-readable record. Releases the lease.

Usage (from the canonical root):
  py -3.12 scripts/build_p2_tutorial1_select_fixture.py
      --consumer-root <prepared/tutorial1-p1-root> --expect-sha <64hex>
      --rundir <input-package> --configure --build --run
"""
import argparse
import hashlib
import json
import os
import subprocess
import sys

FIXTURE = "p2_tutorial1_p1_fixture.cpp"
PASS_MARKER = "PASS TUTORIAL1_P1"
GUARD_PATH = os.path.join("scripts", "p2_fixture_captain_guard.h")
GUARD_SHA256 = "d2f678c9eda75e151eb534077dff9e30ad36ae4796881d971bbd09945f3c3474"
CAPTAIN_DOWN = "P2_FIXTURE_CAPTAIN_DOWN"
INJECTED_TOKENS = ("P2_LL_INJECT", "P2_LIFECYCLE_INJECT", "injected_health",
                   "Transport(", "direct transport assigned")


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_consumer_fixture(native_dir, expect_sha):
    """Fail closed unless the consumer TU exists and matches the pinned hash."""
    path = os.path.join(native_dir, "tools", FIXTURE)
    if not os.path.isfile(path):
        return False, "missing consumer fixture: %s" % path, None
    actual = sha256_file(path)
    if actual != expect_sha:
        return False, "consumer fixture drift: expected %s got %s" % (
            expect_sha, actual), actual
    return True, "byte-identical", actual


def verify_guard(root):
    """Fail closed unless the canonical #632 guard matches its pinned hash."""
    path = os.path.join(root, GUARD_PATH)
    if not os.path.isfile(path):
        return False, "missing guard header: %s" % path
    actual = sha256_file(path)
    if actual != GUARD_SHA256:
        return False, "guard hash drift: %s" % actual
    return True, actual


def check_run_markers(text):
    """PASS marker present, no captain-down, no injection markers."""
    if CAPTAIN_DOWN in text:
        return False, "captain-down interruption present"
    if PASS_MARKER not in text:
        return False, "run PASS marker absent"
    injected = [t for t in INJECTED_TOKENS if t in text]
    if injected:
        return False, "injection markers present: %s" % ",".join(injected)
    return True, "run PASS, no interruption, no injection"


def acquire_lease(root, key, generation, resource, pid, ttl=300):
    """Acquire a canonical registry build lease (elastic cap enforced there)."""
    from workflow.registry import Registry
    root = os.path.abspath(root)
    reg = Registry(os.path.join(root, "output", "workflow", "registry.sqlite3"),
                   root)
    return reg.acquire(key, generation, resource, pid, ttl)


def release_lease(root, key, generation, resource, token):
    from workflow.registry import Registry
    root = os.path.abspath(root)
    reg = Registry(os.path.join(root, "output", "workflow", "registry.sqlite3"),
                   root)
    return reg.release(key, generation, resource, token)


def main(argv=None, runner=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".",
                        help="canonical root (registry + guard live here)")
    parser.add_argument("--consumer-root", required=True,
                        help="consumer lane root worktree (native/ beside it)")
    parser.add_argument("--expect-sha", required=True,
                        help="pinned sha256 of the consumer fixture TU")
    parser.add_argument("--rundir",
                        help="guarded input-package rundir for --run")
    parser.add_argument("--configure", action="store_true")
    parser.add_argument("--build", action="store_true")
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--lane-key", default="tutorial1-fixture-build-support")
    parser.add_argument("--generation", type=int, default=2)
    parser.add_argument("--workdir", default=None,
                        help="private work dir holding build/ and out/ (required for --build/--run)")
    args = parser.parse_args(argv)
    run = runner or (lambda cmd, **kw: _run(cmd, **kw))

    root = os.path.abspath(args.root)
    consumer_root = os.path.abspath(args.consumer_root)
    consumer_lane = os.path.dirname(consumer_root.rstrip(os.sep))
    native_dir = os.path.join(consumer_lane, "tutorial1-p1-native")
    if (args.build or args.run) and not args.workdir:
        print("--workdir (private build/out parent) required for --build/--run")
        return 2
    workdir = os.path.abspath(args.workdir) if args.workdir else None
    build_dir = os.path.join(workdir, "build") if workdir else None
    out_dir = os.path.join(workdir, "out") if workdir else None
    wrapper = os.path.join(root, "scripts",
                           "build_p2_cave_guarded_boot_fixture.py")

    ok, detail, actual = verify_consumer_fixture(native_dir, args.expect_sha)
    if not ok:
        print(detail)
        return 2
    ok, detail = verify_guard(root)
    if not ok:
        print(detail)
        return 2
    lease = None
    lease_token = None
    if args.configure or args.build or args.run:
        lease_resource = "build:" + build_dir
        try:
            leased = acquire_lease(root, args.lane_key, args.generation,
                                   lease_resource, os.getpid())
            held = leased.get("lease", leased) if isinstance(leased, dict) else leased
            lease_token = held.get("token", held) if isinstance(held, dict) else held
            lease = True
        except Exception as exc:
            print("lease unavailable: %s" % exc)
            return 2
    try:
        base = [sys.executable, wrapper, "--root", consumer_root,
                "--fixture", FIXTURE, "--pass-marker", PASS_MARKER,
                "--native-dir", native_dir, "--build-dir", build_dir,
                "--out-dir", out_dir]
        if args.configure or args.build:
            code, _ = run(base + ["--configure", "--build"])
            if code != 0:
                print("wrapper build failed")
                return code
        if args.run:
            if not args.rundir:
                print("--rundir required for --run")
                return 2
            code, text = run(base + ["--run", os.path.abspath(args.rundir)])
            ok, detail = check_run_markers(text)
            print(detail)
            return 0 if (code == 0 and ok) else 1
    finally:
        if lease_token is not None:
            try:
                release_lease(root, args.lane_key, args.generation,
                              lease_resource, lease_token)
            except Exception as exc:
                print("lease release failed: %s" % exc)
    print("consumer fixture verified byte-identical; guard verified; nothing to run")
    return 0


def _run(cmd, **kw):
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, text=True,
                            errors="replace")
    out, _ = proc.communicate()
    return proc.returncode, out


if __name__ == "__main__":
    sys.exit(main())