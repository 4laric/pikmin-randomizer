#!/usr/bin/env python3
"""P1 Challenge Spring (chal3) runtime acceptance driver (issue #566)."""
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

STAGE = "chal3"
LEVEL = 3
ISSUE = 566
LANE = "p1-challenge-spring-runtime-acceptance"
SCHEMA = "p2-challenge-spring-acceptance-1"
KEY = LANE
GENERATION = 2

GUARD_REL = "scripts/p2_fixture_captain_guard.h"
GUARD_SHA256 = "d2f678c9eda75e151eb534077dff9e30ad36ae4796881d971bbd09945f3c3474"

# Pinned integration-line inputs (verified at startup, fail-closed on drift).
WAVE_ROOT_TIP = "347526301a4a91df673a631c7d7ab0579e5823a9"
WAVE_NATIVE_TIP = "58df488eb1d9582b0ef625d46874f3427c18628d"
C531_TIP = "3eb8806997ec3d9cdf72a9fb3f93b0461045a956"
CONTRACT_PIN = "9aa6faad2c76b3182b5ad3de3f564d5e5431ba90"
CONTRACT_SHA256 = "21e1caf02eda06acd9f686bf1b72bce2d6ea3bf366594bb2e8cb416c3aff1b87"
HARNESS_SHA256 = "27b7abb1204409122cdb553dfac61dcf2f4ec097bc6f95acd43104a5b7470099"
INPUTS_SHA256 = "8dde9bbf643507fa02140a74081e442b133474dbe6247687e409ee2c58b07614"
FIXTURE_SHA256 = "950c9222fae306ee3149ae7beb576d7ce525f95e6b00463e981cccee2aee6c1b"

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


def git_head(repo):
    p = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"],
                       capture_output=True, text=True, encoding="utf-8", timeout=60)
    if p.returncode:
        raise ValueError("git rev-parse failed: " + repo)
    return p.stdout.strip()


def sha256_normalized(path):
    data = Path(path).read_bytes().replace(b'\r\n', b'\n').replace(b'\r', b'\n')
    return hashlib.sha256(data).hexdigest()


def git_clean(repo):
    p = subprocess.run(["git", "-C", str(repo), "status", "--porcelain"],
                       capture_output=True, text=True, encoding="utf-8", timeout=60)
    if p.returncode:
        raise ValueError("git status failed: " + repo)
    return not p.stdout.strip()


def verify_wave_pins(root649, native649):
    if git_head(root649) != WAVE_ROOT_TIP:
        raise ValueError("wave root tip drift")
    if not git_clean(root649):
        raise ValueError("wave root not clean")
    if git_head(native649) != WAVE_NATIVE_TIP:
        raise ValueError("wave native tip drift")
    if not git_clean(native649):
        raise ValueError("wave native not clean")
    checks = [
        (Path(root649) / "scripts/build_p2_challenge_guarded_boot_fixture.py", HARNESS_SHA256),
        (Path(root649) / "experimental/pikmin2_challenge_runtime_inputs.py", INPUTS_SHA256),
        (Path(native649) / "tools/p2_challenge_guarded_boot_fixture.cpp", FIXTURE_SHA256),
    ]
    for path, want in checks:
        if not path.is_file() or sha256_normalized(str(path)) != want:
            raise ValueError("wave input drift: " + str(path))
    return {"wave_root": WAVE_ROOT_TIP, "wave_native": WAVE_NATIVE_TIP,
            "harness": HARNESS_SHA256, "inputs": INPUTS_SHA256,
            "fixture": FIXTURE_SHA256}


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
                return None, fail("chal3-level-mismatch")
            argv = stage.get("argv") or []
            if argv[-2:] != ["--experimental-challenge-level", str(LEVEL)]:
                return None, fail("chal3-argv-mismatch")
            return stage, None
    return None, fail("chal3-stage-missing")


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
    spawn_ok = (facts["layout_id"] == "challenge-3"
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


MINGW_BIN = r"C:\msys64\mingw64\bin"


def build_env(base=None):
    env = dict(base if base is not None else os.environ)
    path = env.get("PATH", "")
    if MINGW_BIN.lower() not in path.lower():
        env["PATH"] = MINGW_BIN + ";" + path
    return env


def run_command(argv, cwd=None, env=None, timeout=None):
    proc = subprocess.Popen(argv, cwd=cwd, env=build_env(env), stdout=subprocess.PIPE,
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


def acquire_lease(canonical, resource, timeout_s=3600):
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

def import_harness(root649):
    root649 = Path(root649)
    for entry in (str(root649 / "scripts"), str(root649)):
        if entry not in sys.path:
            sys.path.insert(0, entry)
    import build_p2_challenge_guarded_boot_fixture as harness
    import experimental.pikmin2_challenge_runtime_inputs as inputs_pkg
    return harness, inputs_pkg


def _patch_builder_rsp(harness, rsp_dir, tag):
    builder_mod = harness.builder
    orig_run = builder_mod.run
    counter = {"n": 0}
    def _run(args, cwd, env=None):
        length = sum(len(str(a)) + 1 for a in args)
        if length <= 7000:
            return orig_run(args, cwd, env)
        counter["n"] += 1
        response = Path(rsp_dir) / ("lane-rsp-%s-%d.rsp" % (tag, counter["n"]))
        lines = []
        for a in args[1:]:
            lines.append('"' + str(a).replace(chr(92), chr(92) + chr(92)).replace('"', chr(92) + '"') + '"')
        response.write_text(chr(10).join(lines) + chr(10), encoding="utf-8")
        return orig_run([args[0], "@" + str(response)], cwd, env)
    builder_mod.run = _run
    return orig_run


def do_build(args, out, root649, native649):
    build_dir = Path(args.build_dir) if getattr(args, "build_dir", None) else out / "build"
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
               "-DCMAKE_C_COMPILER=" + MINGW_BIN + "/gcc.exe",
               "-DCMAKE_CXX_COMPILER=" + MINGW_BIN + "/g++.exe",
               "-DCMAKE_MAKE_PROGRAM=" + str(ninja),
               "-DCMAKE_BUILD_TYPE=Release",
               "-DPIKMIN_NATIVE_JAUDIO=ON", "-DPIKMIN_NATIVE_OPTIMIZE=OFF",
               "-DCMAKE_EXPORT_COMPILE_COMMANDS=ON",
               "-DP2_CHALLENGE_GUARD_INCLUDE_DIR=" + str(Path(args.canonical) / "scripts")]
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
        harness, _ = import_harness(root649)
        stage = out / ('stage-' + str(time.time_ns()))
        orig_run = _patch_builder_rsp(harness, out, stage.name)
        try:
            harness.build(str(native649), str(build_dir), str(stage), args.head649)
        finally:
            harness.builder.run = orig_run
        (out / "build-run.log").write_text(
            "in-process harness.build with lane response-file fallback for "
            "over-long link lines (bit-identical argv transport).", encoding="utf-8")
        ninja = (Path(os.environ.get("LOCALAPPDATA", "")) / "Packages" /
                 "PythonSoftwareFoundation.Python.3.12_qbz5n2kfra8p0" / "LocalCache" /
                 "local-packages" / "Python312" / "Scripts" / "ninja.exe")
        code, text = run_command([str(ninja), "-n", "-C", str(build_dir), "pikmin_pc"])
        (out / "ninja-dry-run.log").write_text(text, encoding="utf-8", errors="replace")
        exe = stage / "fixture.exe"
        if not exe.is_file():
            print("REFUSED reason=fixture-exe-missing")
            return 2
        rsp_files = sorted(str(q) for q in out.glob("lane-rsp-*.rsp"))
        prov = {"native_commit": args.head649,
                "rsp_fallback_files": rsp_files,
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
    rundir = out / "run-chal3"
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
    parser = argparse.ArgumentParser(description="P1 Challenge Spring runtime acceptance driver")
    parser.add_argument("--canonical", required=True)
    parser.add_argument("--root649", required=True)
    parser.add_argument("--native649", required=True)
    parser.add_argument("--assets", required=True)
    parser.add_argument("--out", required=True)
    sub = parser.add_subparsers(dest="command", required=True)
    pins = sub.add_parser("verify-pins")
    build_inputs = sub.add_parser("build-inputs")
    build_inputs.add_argument("--head649", required=True)
    build_inputs.add_argument("--inputs-root", required=True)
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
    native649 = Path(args.native649)

    if args.command == "verify-pins":
        pins = verify_wave_pins(root649, native649)
        print(json.dumps(pins, indent=1))
        return 0

    if args.command == "build-inputs":
        cmd = [sys.executable, "-m", "experimental.pikmin2_challenge_runtime_inputs",
               "--root", str(Path(args.inputs_root)),
               "--assets", str(args.assets),
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
        verify_wave_pins(root649, native649)
        if args.head649 != WAVE_NATIVE_TIP:
            print("REFUSED reason=head649-pin-mismatch")
            return 2
        return do_build(args, out, root649, native649)

    if args.command == "run":
        return do_run(args, out)

    if args.command == "accept":
        return do_accept(args, out)
    return 2


if __name__ == "__main__":
    sys.exit(main())
