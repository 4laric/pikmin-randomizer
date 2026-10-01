"""Bounded, fresh original-tutorial encounter runner (#1150)."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.stage_pikmin2_tutorial_encounter import prepare
from scripts.run_pikmin2_cave_fixture import supervise

NATIVE = "fea4bc677879c69ee4d0646d3a1a79029db4d2b6"
FIXTURE_SHA = "70b93197c95e186b539408dbe56d3f14a48d324f7064f11c785b2959c669f21f"
BUNDLE = "c8598f04bb884ab396d126b8dfbed6a6ce78d2f6afc92e7b366a5e5c11ccc8d5"
MODES = ("human", "ready", "reset", "positive", "forced-down", "paused-down")


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def parser():
    workspace = ROOT.parent.parent if ROOT.parent.name == "output" else ROOT
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--workspace", type=Path, default=workspace)
    result.add_argument("--fixture", type=Path)
    result.add_argument("--artifact-validation", type=Path)
    result.add_argument("--assets", type=Path, default=Path(os.environ.get("APPDATA", "C:/Users/alari/AppData/Roaming")) / "PikminRandomizer/game-data/assets")
    result.add_argument("--bundle", type=Path)
    result.add_argument("--bank", type=Path)
    result.add_argument("--toolchain", type=Path, default=Path("C:/msys64/mingw64/bin"))
    result.add_argument("--mode", choices=MODES, default="human")
    result.add_argument("--seconds", type=float, default=60)
    result.add_argument("--max-resets", type=int, default=2)
    result.add_argument("--plan", action="store_true")
    return result


def arguments(argv=None):
    p = parser()
    args = p.parse_args(argv)
    if not 15 <= args.seconds <= 60:
        p.error("--seconds must be15..60; each owned child is capped at60 seconds")
    if not 0 <= args.max_resets <= 2:
        p.error("--max-resets must be0..2")
    base = args.workspace / "output/p2-tutorial-encounter"
    args.fixture = args.fixture or base / "windows-fixtures-fea401/pikmin_ci_fixture_tutorial_encounter.exe"
    args.artifact_validation = args.artifact_validation or base / "windows-artifact-validation03.json"
    args.bundle = args.bundle or args.workspace / "output/p2-level-imports/tutorial-09"
    args.bank = args.bank or base / "retail-bank01"
    return args


def environment(mode, toolchain, save, fixture):
    env = {key: value for key, value in os.environ.items()
           if not key.upper().startswith(("PIKMIN_", "P2_", "COOP_", "COOP_ONION_"))
           and key.upper() not in ("NECTAR_SAVE_DIR", "NECTAR_EXECUTABLE_PATH", "SDL_JOYSTICK_ALLOW_BACKGROUND_EVENTS")}
    env.update(PATH=str(toolchain) + os.pathsep + env.get("PATH", ""),
               NECTAR_SAVE_DIR=str(save), NECTAR_EXECUTABLE_PATH=str(fixture),
               SDL_AUDIODRIVER="dummy", SDL_JOYSTICK_ALLOW_BACKGROUND_EVENTS="1",
               PIKMIN_RANDOMIZER_AUTOPLAY="0", PIKMIN_P2_ROOM_WINDOW="960x540",
               PIKMIN_RANDOMIZER_TEST_BACKGROUND="2" if mode == "human" else "1",
               PIKMIN_P2_TEST_START_DAY="5")
    if mode in ("human", "ready", "reset"):
        env["P2_TUTORIAL_HUMAN"] = "1"  # No fixture-scripted SDL input.
    if mode == "ready": env["P2_TUTORIAL_READY_ONLY"] = "1"
    if mode == "forced-down": env["P2_TUTORIAL_FORCE_CAPTAIN_DOWN"] = "1"
    if mode == "paused-down": env["P2_TUTORIAL_FORCE_PAUSED_CAPTAIN_DOWN"] = "1"
    return env


def fresh_attempt(args, index):
    directory = ROOT / "output/tutorial-encounter-smoke" / (uuid.uuid4().hex + f"-{index}")
    fixture = args.fixture.resolve()
    env = environment(args.mode, args.toolchain, directory / "private-save", fixture)
    return directory, env


def next_attempt(mode, raw_exit, index, max_resets):
    return mode == "human" and raw_exit == 90 and index < max_resets


def artifact(args):
    fixture = args.fixture.resolve(strict=True)
    report = json.loads(args.artifact_validation.read_text(encoding="utf8"))
    if not report.get("passed") or report.get("native_head") != NATIVE:
        raise ValueError("Expected reviewed exact native producer artifact validation")
    declared = {Path(row["path"]).name: row["sha256"] for row in report["artifacts"]}
    if digest(fixture) != FIXTURE_SHA or declared.get(fixture.name) != FIXTURE_SHA:
        raise ValueError("Actual tutorial fixture SHA differs from reviewed CI artifact")
    dlls = {}
    for name in ("SDL2.dll", "libstdc++-6.dll", "libgcc_s_seh-1.dll", "libwinpthread-1.dll"):
        value = digest(fixture.parent / name)
        if declared.get(name) != value:
            raise ValueError("Packaged DLL hash mismatch: " + name)
        dlls[name] = value
    return dlls


def source_identity():
    return {"path": str(ROOT), "head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
            "dirty": subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True),
            "stager_sha256": digest(ROOT / "scripts/stage_pikmin2_tutorial_encounter.py"),
            "runner_sha256": digest(__file__), "supervisor_sha256": digest(ROOT / "scripts/run_pikmin2_cave_fixture.py")}


def main(argv=None):
    args = arguments(argv)
    first, env = fresh_attempt(args, 0)
    plan = {"mode": args.mode, "fixture": str(args.fixture.resolve()), "fixture_sha256": FIXTURE_SHA,
            "native": NATIVE, "fresh_arena": str(first), "seconds_per_child": args.seconds,
            "max_fresh_resets": args.max_resets if args.mode == "human" else 0,
            "environment": {k: v for k, v in env.items() if k.startswith(("P2_", "PIKMIN_", "NECTAR_"))},
            "human_launched": False, "human_judgment": "unrecorded"}
    if args.plan:
        print(json.dumps(plan, indent=2))
        return 0
    dlls = artifact(args)
    if args.mode == "human":
        print("Original tutorial Red encounter: fresh20 Reds, day5, source enemy and original Onion.")
        print("Walk toward the Red, throw Reds onto it, then send at least3 to its corpse and watch the Onion delivery.")
        print("Classic defaults: WASD move/face, Space throw, Left Shift whistle; TFGH swarm. F2 enables Mouse Cursor mode.")
        print("Gamepad: left stick move/aim, A throw, B whistle, right stick swarm (physical pad if connected).")
        print(f"F7 resets to a new private scene/save, at most{args.max_resets} resets; each attempt stops after{args.seconds:g} seconds. Close the window to finish.")
        print("Check throw/attack feel, terrain travel and corpse routing. Engineering start/movie skips are staged; no full-campaign or human verdict recorded.")
    for index in range(args.max_resets + 1 if args.mode == "human" else 1):
        folder, env = (first, env) if index == 0 else fresh_attempt(args, index)
        run = prepare(args.assets.resolve(strict=True), args.bundle.resolve(strict=True), BUNDLE,
                      args.bank.resolve(strict=True), folder, 5)
        (folder / "private-save").mkdir(exist_ok=False)
        if args.mode == "reset": (run / "p2-reset-request").write_text("owned reset probe\n", encoding="utf8")
        inputs = dict(plan, fresh_arena=str(run), attempt=index, source=source_identity(),
                      human_launched=args.mode == "human",
                      stage_sha256=digest(run / "tutorial-encounter-inputs.json"),
                      artifact_validation_sha256=digest(args.artifact_validation), dlls=dlls,
                      environment={k: v for k, v in env.items() if k.startswith(("P2_", "PIKMIN_", "NECTAR_"))})
        (run / "smoke-inputs.json").write_text(json.dumps(inputs, indent=2), encoding="utf8")
        marker = {"positive": "PASS P2_TUTORIAL_ENCOUNTER", "ready": "P2_TUTORIAL_READY",
                  "reset": "P2_TUTORIAL_RESET", "forced-down": "P2_FIXTURE_CAPTAIN_DOWN",
                  "paused-down": "P2_FIXTURE_CAPTAIN_DOWN"}.get(args.mode)
        raw = supervise([str(args.fixture.resolve()), "--experimental-pikmin2-surface", "tutorial"],
                        run, args.seconds, env, [marker] if marker else [])
        text = (run / "native.log").read_text(encoding="utf8", errors="replace")
        report = {"raw": raw, "inputs_sha256": digest(run / "smoke-inputs.json"),
                  "gameplay_pass": args.mode == "positive" and raw["exit_code"] == 0 and marker in text,
                  "log_sha256": digest(run / "native.log"), "human_judgment": "unrecorded"}
        (run / "smoke-assessment.json").write_text(json.dumps(report, indent=2), encoding="utf8")
        print(json.dumps({"run": str(run), **report}, indent=2))
        if next_attempt(args.mode, raw["exit_code"], index, args.max_resets):
            print("Reset requested: regenerating a new private arena and save.")
            continue
        if args.mode == "human":
            return 0 if raw["timed_out"] or raw["exit_code"] in (0, 90) else 1
        expected = 86 if args.mode.endswith("down") else 90 if args.mode == "reset" else 0
        return 0 if not raw["timed_out"] and raw["exit_code"] == expected and marker in text else 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
