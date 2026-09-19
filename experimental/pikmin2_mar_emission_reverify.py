"""Private re-verification driver: Mar corpse emission vs landed #772 fix (#814)."""
import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import uuid
from pathlib import Path

CANONICAL_ROOT = Path("C:/Users/alari/pikmin-randomizer")
GUARD_SHA256 = "d2f678c9eda75e151eb534077dff9e30ad36ae4796881d971bbd09945f3c3474"
GUARD_NAME = "p2_fixture_captain_guard.h"
FIXTURE = "tools/p2_mar_corpse_emission_fixture.cpp"
PASS_MARKER = "PASS P2_MAR_CORPSE_EMISSION"
EMITTED_RE = re.compile(r"P2_MAR_CORPSE_EMITTED_OBSERVED generator=(\d+) source_id=(\d+) pellet=(0x[0-9a-fA-F]+|\(nil\)|0+)")
RECEIPT_MARKER = "P2_MAR_CORPSE_RECEIPT_RESOLVED"
CAPTAIN_DOWN = "P2_FIXTURE_CAPTAIN_DOWN"
FAIL_RE = re.compile(r"FAIL P2_MAR_CORPSE (\S+)")

GATES = ("identity_spawn", "movement_animation", "attacks_receivers", "death_corpse",
         "transport_reward", "cleanup_reentry")


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def guard_record(guard_dir=None):
    candidate = Path(guard_dir) / GUARD_NAME if guard_dir else CANONICAL_ROOT / "scripts" / GUARD_NAME
    if not candidate.is_file():
        raise ValueError("Missing captain guard header")
    digest = sha256(candidate)
    if digest != GUARD_SHA256:
        raise ValueError("Captain guard hash drift: " + digest)
    return {"path": str(candidate), "sha256": digest}


def check_markers(text):
    emitted = EMITTED_RE.search(text)
    pellet = emitted.group(3) if emitted else None
    bound = bool(emitted) and pellet not in (None, "(nil)", "0x0", "0x00000000", "0")
    fail = FAIL_RE.search(text)
    return {
        "pass_marker": PASS_MARKER in text,
        "emitted": bool(emitted),
        "pellet": pellet,
        "pellet_bound": bound,
        "receipt": RECEIPT_MARKER in text,
        "captain_down": CAPTAIN_DOWN in text,
        "fail": fail.group(1) if fail else None,
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--native", type=Path, required=True)
    ap.add_argument("--build", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--expected-native-head", required=True)
    ap.add_argument("--arena-src", type=Path, required=True)
    ap.add_argument("--guard-dir", default=None)
    ap.add_argument("--timeout", type=int, default=900)
    args = ap.parse_args(argv)
    out = args.output
    guard = guard_record(args.guard_dir)
    builder = [sys.executable, str(CANONICAL_ROOT / "scripts" / "build_pikmin2_fixture.py"),
               "--source", str(args.native.resolve()), "--build", str(args.build.resolve()),
               "--fixture", str((args.native / FIXTURE).resolve()), "--output", str(out.resolve()),
               "--expected-native-head", args.expected_native_head]
    proc = subprocess.run(builder, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                          text=True, errors="replace", timeout=3600)
    (out / "builder.log").parent.mkdir(parents=True, exist_ok=True)
    (out / "builder.log").write_text(proc.stdout, encoding="utf-8")
    if proc.returncode != 0:
        print("builder step failed")
        return 2
    exe = None
    for base in (out, args.build):
        for name in ("fixture.exe", "p2_mar_corpse_emission.exe"):
            cand = Path(base) / name
            if cand.is_file():
                exe = cand
                break
    if exe is None:
        print("fixture exe missing after build")
        return 2
    run = out / "runs" / uuid.uuid4().hex
    run.mkdir(parents=True)
    import _winapi
    _winapi.CreateJunction(str(args.arena_src.resolve()), str(run / "assets"))
    for name in ("arena.json", "mar-override.json", "p2-economy.txt",
                 "muse-mar-validation.json", "flying-install.json",
                 "p2-flying-actors.txt", "p2-flying-bank.txt"):
        src = args.arena_src / name
        if src.is_file():
            shutil.copy2(src, run / name)
    for name in ("save", "capture"):
        (run / name).mkdir(exist_ok=True)
    env = dict(os.environ, SDL_AUDIODRIVER="dummy", PIKMIN_P2_ROOM_WINDOW="960x540")
    proc = subprocess.Popen([str(exe.resolve()), "--experimental-pikmin2-room"], cwd=str(run),
                            env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            text=True, errors="replace")
    try:
        text, _ = proc.communicate(timeout=args.timeout)
    except subprocess.TimeoutExpired:
        proc.kill()
        text, _ = proc.communicate()
        text += "\nRUN TIMEOUT\n"
    (run / "native.log").write_text(text, encoding="utf-8")
    facts = check_markers(text)
    facts.update({"exit_code": proc.returncode, "exe_sha256": sha256(exe),
                  "guard_sha256": guard["sha256"], "run_dir": str(run)})
    (out / "facts.json").write_text(json.dumps(facts, indent=1), encoding="utf-8")
    print(json.dumps({"pellet_bound": facts["pellet_bound"], "receipt": facts["receipt"],
                      "pass": facts["pass_marker"], "exit": proc.returncode}))
    if facts["captain_down"] or not facts["pellet_bound"]:
        return 1
    return 0 if (proc.returncode == 0 and facts["pass_marker"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
