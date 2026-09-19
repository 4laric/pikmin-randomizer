#!/usr/bin/env python3
"""Private leased probe of the #674 wrapper --fixture selection path (#680).

Consumes the committed #674 wrapper (scripts/build_p2_cave_guarded_boot_fixture.py)
READ-ONLY: this helper never edits or duplicates it. It drives that wrapper's
`--fixture` selection path:

1. Probe: builds native/tools/p2_tutorial1_wrapper_probe_fixture.cpp (owned by
   #680) in the lane's private native worktree, then runs the produced exe and
   checks its guard self-test / negative markers.
2. Consumer: builds the consumer-owned native/tools/p2_tutorial1_p1_fixture.cpp
   UNMODIFIED against the consumer's private native worktree under the same
   wrapper mechanism, verifying its sha256 before and after (byte-identity).

Lease contract: a canonical registry build lease is acquired BEFORE any heavy
work and released only after its protected process has stopped. Following the
maintained supervisor pattern, the heavy wrapper runs in a dedicated idle child
that holds the lease; this helper acquires with that child's pid, waits for it
to exit, then releases. A refused/queued acquisition fails closed (no build).

The captain guard (#632) is hash-verified. No shared/maintained build dir, no
ADMIT, no consumer-file edits.

Usage (from the lane root worktree):
  py -3.12 scripts/build_p2_tutorial1_wrapper_probe.py \
      --wrapper <674-root>/scripts/build_p2_cave_guarded_boot_fixture.py \
      --probe-native <native> --probe-build <build> --out <out> \
      --probe-build --probe-run
  py -3.12 scripts/build_p2_tutorial1_wrapper_probe.py \
      --wrapper ... --consumer-native <prepared/tutorial1-p1-native> \
      --consumer-build <build> --consumer-sha <64hex> \
      --out <out> --consumer-build
"""
import argparse
import hashlib
import json
import os
import subprocess
import sys
import time

GUARD_REL = os.path.join("scripts", "p2_fixture_captain_guard.h")
GUARD_SHA256 = "d2f678c9eda75e151eb534077dff9e30ad36ae4796881d971bbd09945f3c3474"
PROBE_FIXTURE = "p2_tutorial1_wrapper_probe_fixture.cpp"
PROBE_PASS = "PASS TUTORIAL1_WRAPPER_PROBE"
PROBE_SELFTEST = "P2_TUTORIAL1_WRAPPER_PROBE_SELFTEST_PASS"
CONSUMER_FIXTURE = "p2_tutorial1_p1_fixture.cpp"
CONSUMER_PASS = "PASS TUTORIAL1_P1"
CAPTAIN_DOWN = "P2_FIXTURE_CAPTAIN_DOWN"
NINJA = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Packages",
                     "PythonSoftwareFoundation.Python.3.12_qbz5n2kfra8p0",
                     "LocalCache", "local-packages", "Python312",
                     "Scripts", "ninja.exe")

# Idle child: reads one command JSON from stdin, runs it, mirrors stdout, exits
# with the child command's exit code. Holds the registry lease for the build.
CHILD_CODE = (
    "import json,subprocess,sys\n"
    "d=json.loads(sys.stdin.readline())\n"
    "p=subprocess.run(d['command'],cwd=d.get('cwd'),stdout=subprocess.PIPE,"
    "stderr=subprocess.STDOUT,text=True,errors='replace')\n"
    "sys.stdout.write(p.stdout)\n"
    "sys.exit(p.returncode)\n"
)


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_guard(root):
    path = os.path.join(root, GUARD_REL)
    if not os.path.isfile(path):
        return False, "missing guard header: %s" % path, None
    actual = sha256_file(path)
    if actual != GUARD_SHA256:
        return False, "guard hash drift: %s" % actual, actual
    return True, "guard hash pinned", actual


def verify_consumer_fixture(native_dir, expect_sha):
    path = os.path.join(native_dir, "tools", CONSUMER_FIXTURE)
    if not os.path.isfile(path):
        return False, "missing consumer fixture: %s" % path, None
    actual = sha256_file(path)
    if actual != expect_sha:
        return False, "consumer fixture drift: expected %s got %s" % (
            expect_sha, actual), actual
    return True, "consumer fixture byte-identical", actual


def fixture_exe(build_dir, fixture_name):
    stem = fixture_name[:-len(".cpp")]
    base = stem[:-len("_fixture")] if stem.endswith("_fixture") else stem
    return os.path.join(build_dir, base + ".exe")


def registry(root):
    from workflow.registry import Registry
    root = os.path.abspath(root)
    return Registry(os.path.join(root, "output", "workflow", "registry.sqlite3"), root)


def leased_run(reg, lane_key, generation, build_dir, command, timeout=1800):
    """Run command in an idle child that holds the build lease; fail closed."""
    resource = "build:" + build_dir
    try:
        with reg.transaction() as state:
            dead = [qid for qid, q in state.get("queue", {}).items()
                    if q.get("lane") == lane_key and q.get("generation") == generation
                    and q.get("resource", "").casefold() == resource.casefold()
                    and reg.probe(q.get("process")) == "dead"]
            for qid in dead:
                del state["queue"][qid]
                try:
                    reg.event(state, 'request_cancelled', lane_key, resource=qid,
                              wait_seconds=0)
                except Exception:
                    pass
    except Exception:
        pass
    child = subprocess.Popen([sys.executable, "-u", "-c", CHILD_CODE],
                             stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT, text=True, errors="replace")
    try:
        acquired = reg.acquire(lane_key, generation, resource, child.pid, ttl=1800)
        if not acquired.get("acquired"):
            child.kill()
            child.wait(timeout=10)
            try:
                with reg.transaction() as state:
                    for qid, q in list(state.get("queue", {}).items()):
                        if (q.get("lane") == lane_key and q.get("generation") == generation
                                and q.get("resource", "").casefold() == resource.casefold()
                                and reg.probe(q.get("process")) == "dead"):
                            del state["queue"][qid]
            except Exception:
                pass
            return {"acquired": False, "resource": resource,
                    "reason": acquired.get("reason")}, None
        lease = acquired["lease"]
        child.stdin.write(json.dumps({"command": list(command)}) + "\n")
        child.stdin.close()
        try:
            text, _ = child.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            child.kill()
            text, _ = child.communicate(timeout=10)
            return {"acquired": True, "timed_out": True, "resource": resource}, text
        lease_info = {"acquired": True, "resource": resource, "token": lease["token"]}
    finally:
        if child.poll() is None:
            child.kill()
            child.wait(timeout=10)
    # The protected child has stopped: release is now permitted.
    try:
        reg.release(lane_key, generation, resource, lease["token"])
        lease_info["released"] = True
    except Exception as exc:  # noqa: BLE001
        lease_info["release_error"] = str(exc)
    return lease_info, text


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".",
                        help="canonical root (registry + guard header live here)")
    parser.add_argument("--wrapper", required=True,
                        help="path to the committed #674 wrapper script")
    parser.add_argument("--out", required=True, help="lane out dir for records")
    parser.add_argument("--lane-key", default="tutorial1-wrapper-probe-native")
    parser.add_argument("--generation", type=int, default=2)
    parser.add_argument("--probe-native", default=None)
    parser.add_argument("--probe-build", dest="probe_build_dir", default=None)
    parser.add_argument("--probe-run", action="store_true")
    parser.add_argument("--consumer-native", default=None)
    parser.add_argument("--consumer-build", dest="consumer_build_dir", default=None)
    parser.add_argument("--consumer-sha", default=None)
    args = parser.parse_args(argv)

    root = os.path.abspath(args.root)
    out = os.path.abspath(args.out)
    os.makedirs(out, exist_ok=True)
    record = {"helper": "build_p2_tutorial1_wrapper_probe", "issue": 680,
              "lane": args.lane_key, "generation": args.generation,
              "root": root, "wrapper": os.path.abspath(args.wrapper), "steps": {}}

    ok, detail, guard_actual = verify_guard(root)
    record["guard"] = {"ok": ok, "detail": detail, "sha256": guard_actual,
                       "expected_sha256": GUARD_SHA256}
    if not ok:
        print(detail)
        return 2
    record["wrapper_sha256"] = sha256_file(args.wrapper)

    probe_native = os.path.abspath(args.probe_native) if args.probe_native else None
    probe_build = os.path.abspath(args.probe_build_dir) if args.probe_build_dir else None
    consumer_native = os.path.abspath(args.consumer_native) if args.consumer_native else None
    consumer_build = os.path.abspath(args.consumer_build_dir) if args.consumer_build_dir else None

    if probe_native:
        fixture = os.path.join(probe_native, "tools", PROBE_FIXTURE)
        if not os.path.isfile(fixture):
            print("probe fixture missing: %s" % fixture)
            return 2
        record["probe_fixture_sha256"] = sha256_file(fixture)

    if consumer_build and args.consumer_sha is None:
        print("--consumer-sha required for consumer build")
        return 2
    if consumer_native and args.consumer_sha:
        ok, detail, actual = verify_consumer_fixture(consumer_native, args.consumer_sha)
        record["consumer_fixture_before"] = {"ok": ok, "detail": detail, "sha256": actual}
        if not ok:
            print(detail)
            return 2

    reg = registry(root)
    jobs = []
    if probe_build:
        jobs.append(("probe", probe_native, probe_build, PROBE_FIXTURE, PROBE_PASS))
    if consumer_build:
        jobs.append(("consumer", consumer_native, consumer_build, CONSUMER_FIXTURE,
                     CONSUMER_PASS))

    for name, native_dir, build_dir, fixture, marker in jobs:
        argv_cmd = [sys.executable, os.path.abspath(args.wrapper),
                    "--root", native_dir, "--fixture", fixture,
                    "--pass-marker", marker, "--native-dir", native_dir,
                    "--build-dir", build_dir, "--out-dir", out,
                    "--configure", "--build"]
        lease_info, text = leased_run(reg, args.lane_key, args.generation, build_dir, argv_cmd)
        step = {"resource": lease_info.get("resource"), "build_dir": build_dir,
                "native_dir": native_dir, "fixture": fixture, "lease": lease_info}
        if not lease_info.get("acquired"):
            step["result"] = "lease refused"
            record["steps"][name] = step
            _write(out, record)
            print("lease refused for %s: %s" % (name, lease_info.get("reason")))
            return 2
        code = 0
        lines = (text or "").strip().splitlines()
        step["wrapper_tail"] = lines[-3:] if lines else []
        if "record " in (text or ""):
            pass
        exe = fixture_exe(build_dir, fixture)
        if os.path.isfile(exe):
            step["exe"] = exe
            step["exe_sha256"] = sha256_file(exe)
            proc = subprocess.Popen([NINJA, "-n", "-C", build_dir, "pikmin_pc"],
                                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                    text=True, errors="replace")
            ninja_out, _ = proc.communicate()
            step["ninja_exit"] = proc.returncode
            step["ninja_no_work"] = "no work to do" in ninja_out
        else:
            step["result"] = "fixture exe missing after build"
        record["steps"][name] = step
        if step.get("result"):
            _write(out, record)
            print("%s: %s" % (name, step["result"]))
            return 1

    if args.probe_run:
        step = record["steps"].get("probe", {})
        exe = step.get("exe")
        if not exe or not os.path.isfile(exe):
            print("probe exe missing for run")
            return 2
        run = {}
        proc = subprocess.Popen([exe], stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                text=True, errors="replace")
        out1, _ = proc.communicate()
        run["default_exit"] = proc.returncode
        run["default_pass"] = (proc.returncode == 0 and PROBE_PASS in out1)
        run["ready_marker"] = "P2_TUTORIAL1_WRAPPER_PROBE_READY" in out1
        run["captain_down"] = CAPTAIN_DOWN in out1
        for mode, key_exit, key_pass, expect in (
                ("--guard-self-test", "selftest_exit", "selftest_pass", 0),
                ("--guard-negative-test", "negative_exit", "negative_verified", 86)):
            proc = subprocess.Popen([exe, mode], stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT, text=True, errors="replace")
            outn, _ = proc.communicate()
            run[key_exit] = proc.returncode
            if mode == "--guard-self-test":
                run[key_pass] = (proc.returncode == 0 and PROBE_SELFTEST in outn)
            else:
                run[key_pass] = (proc.returncode == 86 and CAPTAIN_DOWN in outn
                                 and PROBE_PASS not in outn)
        record["run"] = run

    if consumer_native and args.consumer_sha:
        ok, detail, actual = verify_consumer_fixture(consumer_native, args.consumer_sha)
        record["consumer_fixture_after"] = {"ok": ok, "detail": detail, "sha256": actual}

    path = _write(out, record)
    print("record %s" % path)
    print(json.dumps(record, indent=2))
    return 0


def _write(out, record):
    path = os.path.join(out, "wrapper-probe-%d.json" % int(time.time() * 1e6))
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(record, handle, indent=2)
    return path


if __name__ == "__main__":
    sys.exit(main())
