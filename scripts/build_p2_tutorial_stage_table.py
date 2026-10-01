"""Build + guarded-run helper for the tutorial stage-table row (#754).

Private end-to-end driver for the lane-owned provider: leases the private
build directory through the canonical registry, configures and builds the
private pikmin_pc graph (never CMake/touch shared files), links the
game-linked guarded fixture with the maintained builder, runs the guard
self-test and negative test, stages a fresh private arena with the
starting-Pikmin overlay plus the P2_TUTORIAL_STAGE_SELECT_1 record, then
supervises the guarded boot with --experimental-pikmin2-room
--experimental-challenge-stage ch_ABEM_tutorial and validates the
P2_TUTORIAL_STAGE_* markers. Refuses loudly on any failure. Usage (from the
lane root worktree)::

    py -3.12 scripts/build_p2_tutorial_stage_table.py --native <native-worktree>
        --build <private-build-dir> --output <new-private-dir>
        --assets <legal-assets> --converted <room105>

The output directory must be new. Nothing is built in the shared native
checkout; pc_bbft.cpp/CMakeLists.txt are never touched (serialized
integration stays follow-on).
"""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

MINGW_BIN = "C:\\msys64\\mingw64\\bin"
GUARD_INCLUDE_DIR = "C:/Users/alari/pikmin-randomizer/scripts"
GUARD_SHA256 = "d2f678c9eda75e151eb534077dff9e30ad36ae4796881d971bbd09945f3c3474"

MARKERS = ("P2_TUTORIAL_STAGE_ARGV",
           "P2_TUTORIAL_STAGE_SIDECAR",
           "P2_TUTORIAL_STAGE_ENGINE_TABLE",
           "P2_TUTORIAL_STAGE_TABLE",
           "P2_TUTORIAL_STAGE_RESOLVED",
           "P2_TUTORIAL_STAGE_WINDOW",
           "P2_TUTORIAL_STAGE_READY",
           "P2_TUTORIAL_STAGE_GATES",
           "PASS TUTORIAL_STAGE_BOOT")


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run(args, cwd, env=None, timeout=1200):
    completed = subprocess.run(
        [str(a) for a in args], cwd=str(cwd), env=env,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, encoding="utf-8", errors="replace", timeout=timeout)
    return completed.returncode, completed.stdout


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--native", type=Path, required=True)
    parser.add_argument("--build", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--expected-native-head", required=True)
    parser.add_argument("--assets", type=Path, required=True)
    parser.add_argument("--converted", type=Path, required=True)
    parser.add_argument("--lane", default="tutorial-stage-table-row-native")
    parser.add_argument("--generation", type=int, default=2)
    parser.add_argument("--timeout", type=float, default=90)
    args = parser.parse_args(argv)

    repo = Path(__file__).resolve().parents[1]
    canon = Path("C:/Users/alari/pikmin-randomizer")
    if str(canon) not in sys.path:
        sys.path.insert(0, str(canon))
    from workflow.registry import Registry
    from scripts import build_pikmin2_fixture as bf
    from scripts.preview_pikmin2_room import prepare
    import importlib.util as _ilu
    _spec = _ilu.spec_from_file_location(
        "pikmin2_tutorial_stage_table_row_lane",
        repo / "experimental" / "pikmin2_tutorial_stage_table_row.py")
    _mod = _ilu.module_from_spec(_spec)
    _spec.loader.exec_module(_mod)
    RECORD_FILE, render_record = _mod.RECORD_FILE, _mod.render_record

    native = args.native.resolve()
    build = args.build.resolve()
    output = args.output.resolve()
    reg = Registry(str(canon / "output" / "workflow" / "registry.sqlite3"), str(canon))
    if output.exists():
        parser.exit(1, "output must be a NEW directory: %s\n" % output)
    output.mkdir(parents=True, exist_ok=False)
    log_path = output / "driver.log"

    record = {"schema": 1, "status": "starting", "lane": args.lane,
              "native": str(native), "build": str(build),
              "expected_native_head": args.expected_native_head,
              "guard_sha256": GUARD_SHA256, "steps": {}}
    lease = None
    resource = "build:" + str(build)

    def emit(text):
        with log_path.open("a", encoding="utf-8") as handle:
            handle.write(text + "\n")
        print(text, flush=True)

    try:
        got = reg.acquire(args.lane, args.generation, resource, os.getpid(), ttl=600)
        if not got.get("acquired"):
            parser.exit(1, "build lease not acquired: %s\n" % got.get("reason"))
        lease = got["lease"]
        emit("lease acquired %s" % resource)

        env = dict(os.environ)
        env["PATH"] = MINGW_BIN + os.pathsep + env.get("PATH", "")
        ninja = Path(os.environ.get("LOCALAPPDATA", "")) / "Packages" / \
            "PythonSoftwareFoundation.Python.3.12_qbz5n2kfra8p0" / "LocalCache" / \
            "local-packages" / "Python312" / "Scripts" / "ninja.exe"

        build.mkdir(parents=True, exist_ok=True)
        code, text = run(["cmake", "-S", str(native), "-B", str(build), "-G", "Ninja",
                          "-DCMAKE_C_COMPILER=C:/msys64/mingw64/bin/gcc.exe",
                          "-DCMAKE_CXX_COMPILER=C:/msys64/mingw64/bin/g++.exe",
                          "-DCMAKE_MAKE_PROGRAM=%s" % ninja,
                          "-DCMAKE_BUILD_TYPE=Release",
                          "-DPIKMIN_NATIVE_JAUDIO=ON",
                          "-DPIKMIN_NATIVE_OPTIMIZE=OFF",
                          "-DP2_CHALLENGE_GUARD_INCLUDE_DIR=%s" % GUARD_INCLUDE_DIR],
                         repo, env)
        (output / "configure.log").write_text(text, encoding="utf-8")
        record["steps"]["configure"] = {"exit": code}
        if code != 0:
            parser.exit(1, "configure failed; see configure.log\n")

        code, text = run(["cmake", "--build", str(build), "--target", "pikmin_pc",
                          "-j", "6"], repo, env)
        (output / "build.log").write_text(text, encoding="utf-8")
        record["steps"]["pikmin_pc"] = {"exit": code}
        if code != 0:
            parser.exit(1, "pikmin_pc build failed; see build.log\n")

        code, text = run([str(ninja), "-n", "-C", str(build), "pikmin_pc"], repo, env)
        (output / "ninja-dryrun.log").write_text(text, encoding="utf-8")
        record["steps"]["dry_run"] = {"exit": code,
                                      "no_work": "no work to do" in text}
        if code != 0 or "no work to do" not in text:
            parser.exit(1, "ninja dry run is not no-work; see ninja-dryrun.log\n")

        fixture_src = (native / "tools" / "p2_tutorial_stage_guarded_fixture.cpp").resolve()
        fixture_out = output / "fixture-out"
        try:
            result = bf.build_fixture(build, native, fixture_src, fixture_out,
                                      args.expected_native_head, False)
        except (bf.BuildRejected, OSError) as error:
            parser.exit(1, "fixture build rejected: %s\n" % error)
        record["steps"]["fixture"] = {"status": result["status"]}
        if result["status"] != "built":
            parser.exit(1, "fixture not built\n")
        exe = fixture_out / "fixture.exe"
        record["exe_sha256"] = sha256(exe)

        code, text = run([str(exe), "--guard-self-test"], build, env, timeout=120)
        (output / "selftest.log").write_text(text, encoding="utf-8")
        record["steps"]["self_test"] = {
            "exit": code, "pass": code == 0 and "P2_TUTORIAL_STAGE_SELFTEST_PASS" in text}
        if code != 0:
            parser.exit(1, "guard self-test failed; see selftest.log\n")

        code, text = run([str(exe), "--guard-negative-test"], build, env, timeout=120)
        (output / "negative.log").write_text(text, encoding="utf-8")
        record["steps"]["negative"] = {
            "exit": code, "verified": code == 86 and "P2_FIXTURE_CAPTAIN_DOWN" in text
            and "PASS TUTORIAL_STAGE_BOOT" not in text}
        if code != 86:
            parser.exit(1, "guard negative test failed; see negative.log\n")

        run_dir = output / "tutorial-run"
        staged = prepare(args.assets.resolve(), args.converted.resolve(), output)
        if run_dir.exists():
            shutil.rmtree(run_dir)
        staged.rename(run_dir)
        sidecar = run_dir / RECORD_FILE
        sidecar.write_text(render_record(), encoding="utf-8")
        record["sidecar_sha256"] = sha256(sidecar)

        run_env = dict(env)
        run_env["SDL_AUDIODRIVER"] = "dummy"
        start = time.monotonic()
        proc = None
        run_log = run_dir / "native.log"
        try:
            with run_log.open("wb") as handle:
                proc = subprocess.Popen(
                    [str(exe), "--experimental-pikmin2-room",
                     "--experimental-challenge-stage", "ch_ABEM_tutorial"],
                    cwd=str(run_dir), env=run_env, stdout=handle,
                    stderr=subprocess.STDOUT)
                try:
                    record["steps"]["run"] = {"exit": proc.wait(timeout=args.timeout),
                                              "timed_out": False}
                except subprocess.TimeoutExpired:
                    proc.kill()
                    record["steps"]["run"] = {"exit": proc.wait(timeout=10),
                                              "timed_out": True}
        finally:
            if proc is not None and proc.poll() is None:
                proc.kill()
                proc.wait(timeout=10)
        record["steps"]["run"]["elapsed"] = round(time.monotonic() - start, 3)
        text = run_log.read_text(errors="replace")
        (output / "runtime.log").write_text(text, encoding="utf-8")
        markers = {marker: marker in text for marker in MARKERS}
        record["steps"]["run"]["markers"] = markers
        record["steps"]["run"]["captain_down"] = "P2_FIXTURE_CAPTAIN_DOWN" in text
        record["steps"]["run"]["refused"] = "P2_TUTORIAL_STAGE_REFUSED" in text
        passed = (not record["steps"]["run"]["timed_out"]
                  and record["steps"]["run"]["exit"] == 0
                  and all(markers.values())
                  and not record["steps"]["run"]["captain_down"]
                  and not record["steps"]["run"]["refused"])
        record["steps"]["run"]["passed"] = passed
        record["log_sha256"] = sha256(output / "runtime.log")
        if not passed:
            parser.exit(1, "guarded run did not pass; see runtime.log\n")

        record["status"] = "built"
        print(json.dumps({"status": "built", "passed": True,
                          "executable_sha256": record["exe_sha256"],
                          "log_sha256": record["log_sha256"]}))
        return 0
    finally:
        (output / "provenance.json").write_text(json.dumps(record, indent=2) + "\n",
                                                encoding="utf-8")
        if lease is not None:
            try:
                reg.release(args.lane, args.generation, resource, lease["token"])
            except Exception:
                pass


if __name__ == "__main__":
    raise SystemExit(main())
