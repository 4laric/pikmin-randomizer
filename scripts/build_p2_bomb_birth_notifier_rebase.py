"""Private leased build helper for the #726 notifier rebase (no shared edits).

Acquires a canonical registry build lease, configures the private native worktree
(cmake/Ninja, no tree edits), records `ninja -n` dry-run state, then performs the
engine-free proof link exactly per the reviewed #715 pattern (direct g++ against the
wave-tip provider TUs, no CMake membership needed):

  g++ -std=c++17 -Ipc_port -DP2_BOMB_MGR_BIRTH_NO_HOST
      tools/p2_bomb_birth_notifier_rebase_fixture.cpp
      pc_port/pc_p2_bomb_notifier.cpp pc_port/pc_p2_bomb_mgr_birth.cpp
      pc_port/pc_p2_bomb_payload_actor.cpp pc_port/pc_p2_bombsarai_blast.cpp
      -o <out>/p2_bomb_birth_notifier_rebase.exe
  (the blast TU joined at the evolved wave tip: the manager core now routes
  through p2_bombsarai_route_blast; same engine-free scope, no gameplay)

Runs the exe, hashes exe + hook log, and writes a JSON record. The
`native/CMakeLists.txt` membership stays untouched (owned by #725).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

CANONICAL_ROOT = Path("C:/Users/alari/pikmin-randomizer")

sys.path.insert(0, str(CANONICAL_ROOT))
from workflow.registry import Registry

FIXTURE = "p2_bomb_birth_notifier_rebase_fixture.cpp"
TUS = ("pc_port/pc_p2_bomb_notifier.cpp",
       "pc_port/pc_p2_bomb_mgr_birth.cpp",
       "pc_port/pc_p2_bomb_payload_actor.cpp",
       "pc_port/pc_p2_bombsarai_blast.cpp")
GUARD_SHA256 = "d2f678c9eda75e151eb534077dff9e30ad36ae4796881d971bbd09945f3c3474"


def sha256(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--native", type=Path, required=True)
    parser.add_argument("--build", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--lane-key", required=True)
    parser.add_argument("--generation", type=int, required=True)
    parser.add_argument("--no-lease", action="store_true")
    args = parser.parse_args(argv)
    native, build, out = Path(args.native), Path(args.build), Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    build.mkdir(parents=True, exist_ok=True)
    record = {"lane": args.lane_key, "generation": args.generation,
              "native": str(native), "build": str(build), "steps": {}}
    log = out / "build.log"
    reg = Registry(CANONICAL_ROOT / "output/workflow/registry.sqlite3", CANONICAL_ROOT)
    resource = "build:" + str(build.resolve())
    # Idle child holds the lease (supervisor pattern): the holder must be
    # stopped before release, so the parent works while the child sleeps.
    holder = None
    token = None
    if not args.no_lease:
        holder = subprocess.Popen(
            [sys.executable, "-c", "import time; time.sleep(3600)"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        got = reg.acquire(args.lane_key, args.generation, resource, holder.pid, 3600)
        if not got.get("acquired"):
            holder.terminate()
            print(json.dumps({"status": "waiting",
                              "reason": got.get("reason", "lease unavailable")}))
            return 3
        token = got["lease"]["token"]
    try:
        import ninja as _ninja_pkg
        _ninja_dir = str(Path(_ninja_pkg.BIN_DIR))
    except Exception:
        _ninja_dir = None
    _path = "C:/msys64/mingw64/bin;" + (_ninja_dir + ";" if _ninja_dir else "") + os.environ.get("PATH", "")
    env = dict(os.environ, PATH=_path)
    _make = ["-DCMAKE_MAKE_PROGRAM=" + str(Path(_ninja_dir) / "ninja.exe")] if _ninja_dir else []
    code = 1
    try:
        with log.open("w", encoding="utf-8") as stream:
            cfg = subprocess.run(
                ["cmake", "-S", str(native), "-B", str(build), "-G", "Ninja",
                 "-DCMAKE_C_COMPILER=gcc", "-DCMAKE_CXX_COMPILER=g++"] + _make + [
                 "-DCMAKE_BUILD_TYPE=Release",
                 "-DP2_CHALLENGE_GUARD_INCLUDE_DIR=" + str(CANONICAL_ROOT / "scripts")],
                cwd=str(native), env=env, stdout=stream, stderr=subprocess.STDOUT)
            record["steps"]["configure"] = {"exit": cfg.returncode}
            if cfg.returncode != 0:
                return 2
            from shutil import which
            ninja = which("ninja", path=env["PATH"]) or "ninja"
            dry = subprocess.run([ninja, "-n", "-C", str(build)], capture_output=True,
                                 text=True, encoding="utf-8", errors="replace", env=env)
            record["steps"]["dry_run"] = {"exit": dry.returncode,
                                          "no_work": "ninja: no work to do." in (dry.stdout or "")}
            (out / "dryrun.log").write_text((dry.stdout or "") + (dry.stderr or ""),
                                            encoding="utf-8")
            exe = build / "p2_bomb_birth_notifier_rebase.exe"
            link = subprocess.run(
                ["g++", "-std=c++17", "-Wall", "-Wextra", "-Werror",
                 "-Ipc_port", "-DP2_BOMB_MGR_BIRTH_NO_HOST",
                 "tools/" + FIXTURE] + list(TUS) + ["-o", str(exe)],
                cwd=str(native), env=env, stdout=stream, stderr=subprocess.STDOUT)
            record["steps"]["fixture_link"] = {"exit": link.returncode,
                                               "exe": str(exe)}
            if link.returncode != 0:
                return 2
            record["exe_sha256"] = sha256(exe)
            run = subprocess.run([str(exe)], cwd=str(out), env=env, capture_output=True,
                                 text=True, encoding="utf-8", errors="replace", timeout=300)
            (out / "hook.log").write_text(run.stdout or "", encoding="utf-8")
            record["steps"]["run"] = {"exit": run.returncode}
            record["hook_log_sha256"] = sha256(out / "hook.log")
            record["hook_notify_lines"] = [
                line for line in (run.stdout or "").splitlines()
                if "P2_BOMB_BIRTH_HOOK_NOTIFY" in line]
            record["all_fixture_pass"] = "ALL_FIXTURE_PASS" in (run.stdout or "")
            code = 0 if (run.returncode == 0 and record["all_fixture_pass"]) else 2
    finally:
        if holder is not None:
            holder.terminate()
            try:
                holder.wait(timeout=30)
            except Exception:
                holder.kill()
        if token is not None:
            try:
                reg.release(args.lane_key, args.generation, resource, token)
            except Exception as exc:
                print("lease release: %s" % exc)
    record["guard_sha256"] = sha256(CANONICAL_ROOT / "scripts/p2_fixture_captain_guard.h")
    (out / "record.json").write_text(json.dumps(record, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({k: record[k] for k in ("steps", "exe_sha256", "hook_log_sha256")},
                     indent=1))
    return code


if __name__ == "__main__":
    raise SystemExit(main())