#!/usr/bin/env python3
"""P1 Challenge Forest (chal1) runtime acceptance driver (issue #564)."""
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

STAGE = "chal1"
LEVEL = 1
ISSUE = 564
LANE = "p1-challenge-forest-runtime-acceptance"
SCHEMA = "p2-challenge-forest-acceptance-1"
KEY = LANE
GENERATION = 2

GUARD_REL = "scripts/p2_fixture_captain_guard.h"

LAYOUT_RE = re.compile(r"\[Pikipelago\] CHALLENGE_LAYOUT_READY id=(challenge-\d+)")
GEN_RE = re.compile(r"\[PC Generator\] (\w+): initialised (\d+) recognised generators, spawned (\d+) creatures")
SQUAD_RE = re.compile(r"P2_CHALLENGE_SQUAD pikis=(\d+)")
BOOT_RE = re.compile(r"P2_CHALLENGE_BOOT level=([0-4]) slot=(chal[0-4])")
PARK_RE = re.compile(r"P2_CHALLENGE_PARK nx=([-\d.]+) ny=([-\d.]+) nz=([-\d.]+)")
PASS_RE = re.compile(r"^PASS P2_CHALLENGE_GUARDED_BOOT\b", re.MULTILINE)
DOWN_RE = re.compile(r"^\s*P2_[A-Z0-9_]*CAPTAIN_DOWN(?:\s|$)", re.MULTILINE)
WINDOW_RE = re.compile(r"SDL2 Window & OpenGL Context initialized successfully \(960x540\)")
CENTERED_RE = re.compile(r"windowed and centered|centered=1")


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fail(msg):
    print("REFUSED reason=%s" % msg)
    return msg


def check_stage_package(package_path):
    try:
        obj = json.loads(Path(package_path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return None, fail("unreadable-input-package: %s" % exc)
    if not isinstance(obj, dict) or obj.get("schema") != 1:
        return None, fail("bad-input-package-schema")
    stages = obj.get("stages")
    if not isinstance(stages, list):
        return None, fail("bad-input-package-stages")
    for stage in stages:
        if stage.get("slot") == STAGE:
            if stage.get("challenge_level") != LEVEL:
                return None, fail("chal1-level-mismatch")
            argv = stage.get("argv") or []
            if argv[-2:] != ["--experimental-challenge-level", str(LEVEL)]:
                return None, fail("chal1-argv-mismatch")
            return stage, None
    return None, fail("chal1-stage-missing")


def parse_run_log(text):
    layout = LAYOUT_RE.search(text)
    gens = GEN_RE.findall(text)
    squad = SQUAD_RE.search(text)
    boot = BOOT_RE.search(text)
    park = PARK_RE.search(text)
    facts = {
        "window_960x540": bool(WINDOW_RE.search(text)),
        "window_centered": bool(CENTERED_RE.search(text)),
        "layout_id": layout.group(1) if layout else None,
        "generators": [{"pool": pool, "recognised": int(r), "spawned": int(s)}
                       for pool, r, s in gens],
        "spawned_total": sum(int(s) for _p, _r, s in gens),
        "squad_pikis": int(squad.group(1)) if squad else None,
        "boot_level": int(boot.group(1)) if boot else None,
        "boot_slot": boot.group(2) if boot else None,
        "park": ([float(park.group(1)), float(park.group(2)), float(park.group(3))]
                 if park else None),
        "fixture_pass_marker": bool(PASS_RE.search(text)),
        "captain_down": bool(DOWN_RE.search(text)),
    }
    return facts


def accept_facts(facts, guard_sha):
    uninterrupted = not facts["captain_down"] and facts["fixture_pass_marker"]
    spawn_ok = (facts["layout_id"] == "challenge-1"
                and facts["boot_level"] == LEVEL and facts["boot_slot"] == STAGE
                and facts["spawned_total"] > 0
                and (facts["squad_pikis"] or 0) >= 1)
    gates = {
        "identity_spawn": {
            "status": ("PASS" if (spawn_ok and uninterrupted) else "UNTESTED"),
            "method": "natural" if (spawn_ok and uninterrupted) else "unobserved",
            "detail": ("Stage identity row, generator recognition/spawn counts and "
                       "live starting squad observed without interruption."
                       if (spawn_ok and uninterrupted) else
                       "Boot/spawn/squad facts incomplete or run interrupted; not observed."),
        },
    }
    for gate in ("movement_animation", "attacks_receivers", "death_corpse",
                 "transport_reward", "cleanup_reentry"):
        gates[gate] = {
            "status": "UNTESTED",
            "method": "unobserved",
            "detail": ("A boot-only observation cannot exercise %s; no combat, death, "
                       "haul, or reentry was observed." % gate),
        }
    return {
        "schema": SCHEMA,
        "lane": LANE,
        "issue": ISSUE,
        "stage": STAGE,
        "facts": facts,
        "gates": gates,
        "guard": {"path": GUARD_REL, "sha256": guard_sha,
                  "adopted": True,
                  "note": "Fixture runs the canonical guard FIRST on every idle tick; "
                          "CAPTAIN_DOWN exits BLOCKED and can never substantiate PASS."},
        "runtime_claim": False,
    }


def run_command(argv, cwd=None, env=None, timeout=None):
    proc = subprocess.Popen(argv, cwd=cwd, env=env, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, text=True, errors="replace")
    try:
        out, _ = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        proc.kill()
        out, _ = proc.communicate()
        return proc.returncode, out + "\n[TIMEOUT]\n"
    return proc.returncode, out

def _registry(reg_root):
    sys.path.insert(0, str(reg_root))
    from workflow.registry import Registry
    from workflow.processes import identify
    reg = Registry.__new__(Registry)
    reg.root = Path(reg_root)
    return reg, identify


def acquire_lease(canonical, resource, timeout_s=600):
    import sqlite3
    reg, identify = _registry(canonical)
    norm = reg.resource(resource)
    me = identify(os.getpid())
    cli = [sys.executable, str(Path(canonical) / "scripts" / "pikmin2_workflow.py"),
           "--root", str(canonical)]
    req_path = str(Path(os.environ.get("TEMP", "/tmp")) / ("acq-%d.json" % me["pid"]))
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        json.dump({"key": KEY, "generation": GENERATION, "resource": resource,
                   "pid": me["pid"], "ttl": 3600},
                  open(req_path, "w", encoding="utf-8"))
        subprocess.run(cli + ["--request", req_path, "acquire"],
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace")
        con = sqlite3.connect(str(Path(canonical) / "output" / "workflow" / "registry.sqlite3"))
        try:
            state = json.loads(con.execute("select body from registry").fetchone()[0])
        finally:
            con.close()
        lease = state.get("leases", {}).get(norm)
        if lease and (lease.get("lane"), lease.get("generation")) == (KEY, GENERATION) \
                and lease.get("process") == me:
            try:
                os.remove(req_path)
            except OSError:
                pass
            return lease["token"]
        time.sleep(15)
    try:
        os.remove(req_path)
    except OSError:
        pass
    return None


def release_lease(canonical, resource, token):
    req_path = str(Path(os.environ.get("TEMP", "/tmp")) / ("rel-%d.json" % os.getpid()))
    json.dump({"key": KEY, "generation": GENERATION, "resource": resource,
               "token": token}, open(req_path, "w", encoding="utf-8"))
    cli = [sys.executable, str(Path(canonical) / "scripts" / "pikmin2_workflow.py"),
           "--root", str(canonical)]
    proc = subprocess.run(cli + ["--request", req_path, "release"],
                          capture_output=True, text=True, encoding="utf-8",
                          errors="replace")
    try:
        os.remove(req_path)
    except OSError:
        pass
    return proc.returncode, (proc.stdout + proc.stderr)[:200]

def do_build(args, out, root649, native649):
    build_dir = out / "build"
    build_out = out / "build-out"
    resource = "build:" + str(build_dir.relative_to(Path(args.canonical))).replace("\\", "/")
    token = acquire_lease(args.canonical, resource)
    if token is None:
        print("REFUSED reason=lease-not-acquired")
        return 2
    try:
        ninja = (Path(os.environ.get("LOCALAPPDATA", "")) / "Packages" /
                 "PythonSoftwareFoundation.Python.3.12_qbz5n2kfra8p0" / "LocalCache" /
                 "local-packages" / "Python312" / "Scripts" / "ninja.exe")
        cfg = ["cmake", "-S", str(native649), "-B", str(build_dir), "-G", "Ninja",
               "-DCMAKE_C_COMPILER=gcc", "-DCMAKE_CXX_COMPILER=g++",
               "-DCMAKE_MAKE_PROGRAM=" + str(ninja),
               "-DCMAKE_BUILD_TYPE=Release",
               "-DPIKMIN_NATIVE_JAUDIO=ON", "-DPIKMIN_NATIVE_OPTIMIZE=OFF",
               "-DCMAKE_EXPORT_COMPILE_COMMANDS=ON"]
        code, text = run_command(cfg)
        (out / "cmake-configure.log").write_text(text, encoding="utf-8", errors="replace")
        if code != 0:
            print("REFUSED reason=fixture-configure-failed")
            return 2
        code, text = run_command(
            ["cmake", "--build", str(build_dir), "--target", "pikmin_pc",
             "--config", "Release", "-j", "6"])
        (out / "cmake-build-pikmin-pc.log").write_text(
            text, encoding="utf-8", errors="replace")
        if code != 0:
            print("REFUSED reason=production-build-failed")
            return 2
        cmd = [sys.executable,
               str(root649 / "scripts" / "build_p2_challenge_guarded_boot_fixture.py"),
               "--native", str(native649), "--build-dir", str(build_dir),
               "--output", str(build_out), "--head", args.head649]
        code, text = run_command(cmd, cwd=str(root649))
        (out / "build-run.log").write_text(text, encoding="utf-8", errors="replace")
        if code != 0:
            print("REFUSED reason=fixture-build-failed")
            return 2
        ninja = (Path(os.environ.get("LOCALAPPDATA", "")) / "Packages" /
                 "PythonSoftwareFoundation.Python.3.12_qbz5n2kfra8p0" / "LocalCache" /
                 "local-packages" / "Python312" / "Scripts" / "ninja.exe")
        code, text = run_command([str(ninja), "-n", "-C", str(build_dir)])
        (out / "ninja-dry-run.log").write_text(text, encoding="utf-8", errors="replace")
        exe = build_out / "fixture.exe"
        if not exe.is_file():
            print("REFUSED reason=fixture-exe-missing")
            return 2
        prov = {"native_commit": args.head649,
                "executable": str(exe),
                "executable_sha256": sha256_file(str(exe)),
                "ninja_dry_exit": code,
                "ninja_no_work": "no work to do" in text}
        (out / "build-provenance.json").write_text(json.dumps(prov, indent=1) + "\n",
                                                   encoding="utf-8")
        print("built exe=%s" % prov["executable_sha256"][:16])
        return 0
    finally:
        release_lease(args.canonical, resource, token)


def do_run(args, out):
    package = out / "inputs" / "challenge-runtime-inputs.json"
    stage, problem = check_stage_package(str(package))
    if problem:
        return 2
    prov = json.loads((out / "build-provenance.json").read_text(encoding="utf-8"))
    exe = prov["executable"]
    if not Path(exe).is_file():
        print("REFUSED reason=fixture-exe-missing")
        return 2
    rundir = out / "run-chal1"
    rundir.mkdir(parents=True, exist_ok=True)
    assets_link = rundir / "assets"
    if not assets_link.exists():
        try:
            assets_link.symlink_to(Path(args.assets), target_is_directory=True)
        except OSError:
            import shutil as _shutil
            _shutil.copytree(str(args.assets), str(assets_link))
    env = dict(os.environ, SDL_AUDIODRIVER="dummy", PYTHONUTF8="1",
               PIKMIN_P2_ROOM_WINDOW="960x540",
               PATH=r"C:\msys64\mingw64\bin;" + os.environ.get("PATH", ""))
    argv = [exe] + list(stage.get("argv", [])[1:])
    code, text = run_command(argv, cwd=str(rundir), env=env, timeout=args.timeout)
    (rundir / "native.log").write_text(text, encoding="utf-8", errors="replace")
    print("exit=%d bytes=%d" % (code, len(text)))
    return 0


def do_accept(args, out):
    package = out / "inputs" / "challenge-runtime-inputs.json"
    stage, problem = check_stage_package(str(package))
    if problem:
        return 2
    try:
        text = Path(args.log).read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        print("REFUSED reason=unreadable-run-log: %s" % exc)
        return 2
    facts = parse_run_log(text)
    guard_path = Path(args.canonical) / GUARD_REL
    try:
        guard_sha = sha256_file(str(guard_path))
    except OSError:
        guard_sha = "unavailable-canonical-root"
    record = accept_facts(facts, guard_sha)
    record["evidence"] = {"package": str(package),
                          "package_sha256": sha256_file(str(package)),
                          "run_log": args.log,
                          "run_log_sha256": sha256_file(args.log)}
    Path(args.record_out).write_text(json.dumps(record, indent=1) + "\n",
                                     encoding="utf-8")
    n_pass = sum(1 for g in record["gates"].values() if g["status"] == "PASS")
    print("gates_pass=%d gates_untested=%d captain_down=%s" % (
        n_pass, 6 - n_pass, facts["captain_down"]))
    return 0

def main(argv=None):
    parser = argparse.ArgumentParser(description="P1 Challenge Forest runtime acceptance driver")
    parser.add_argument("--canonical", required=True)
    parser.add_argument("--root649", required=True)
    parser.add_argument("--native649", required=True)
    parser.add_argument("--assets", required=True)
    parser.add_argument("--out", required=True)
    sub = parser.add_subparsers(dest="command", required=True)
    build_inputs = sub.add_parser("build-inputs")
    build_inputs.add_argument("--head649", required=True)
    build_exe = sub.add_parser("build")
    build_exe.add_argument("--build-dir", required=True)
    build_exe.add_argument("--head649", required=True)
    run = sub.add_parser("run")
    run.add_argument("--timeout", type=int, default=1200)
    accept = sub.add_parser("accept")
    accept.add_argument("--log", required=True)
    accept.add_argument("--record-out", required=True)
    args = parser.parse_args(argv)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    root649 = Path(args.root649)

    if args.command == "build-inputs":
        cmd = [sys.executable, "-m", "experimental.pikmin2_challenge_runtime_inputs",
               "--root", str(root649), "--assets", str(args.assets),
               "--output", str(out / "inputs")]
        code, text = run_command(cmd, cwd=str(root649))
        (out / "build-inputs.log").write_text(text, encoding="utf-8", errors="replace")
        if code != 0:
            print("REFUSED reason=inputs-builder-failed")
            return 2
        try:
            record = json.loads(text[text.index("{"):])
            package = Path(record["path"])
        except (ValueError, KeyError) as exc:
            print("REFUSED reason=inputs-record-unparseable: %s" % exc)
            return 2
        stage, problem = check_stage_package(str(package))
        if problem:
            return 2
        print("package=%s" % package)
        return 0

    if args.command == "build":
        return do_build(args, out, root649, Path(args.native649))

    if args.command == "run":
        return do_run(args, out)

    if args.command == "accept":
        return do_accept(args, out)
    return 2


if __name__ == "__main__":
    sys.exit(main())
