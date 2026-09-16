"""Generated-session Snow launch acceptance for lanes 02/03/05 (assignment 1).

Exits the product code path with a private explicit-cohort monkeypatch (lane 02
still denies source 45), stages the real extracted Snow bank through the lane 05
asset overlay, launches the standalone native game with the generated ENEMY_P2
bootstrap, and asserts that the bound placement target resolves to a live native
actor. It is not a combat/reward/restart acceptance; those belong to the family
lifecycle fixture.

    py -3.12 scripts/test_p2_generated_snow_launch.py \
        --exe <build>/bin/nectar.exe \
        --assets C:/Users/alari/bbft/dist/cohesion/pikmin/assets \
        --snow-import output/p2-asg1-snow-import \
        --output output/p2-asg1-snow-launch
"""
import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from experimental import pikmin2_seed_bridge as bridge  # noqa: E402
from experimental.pikmin2_enemy import content_manifest  # noqa: E402
from experimental.pikmin2_staging import stage_session_content  # noqa: E402
from randomizer import p2_placement as placement  # noqa: E402
from randomizer.p2_placement_catalog import build_document  # noqa: E402
from randomizer.runner import NativeRun  # noqa: E402
from randomizer.seed import generate  # noqa: E402
from randomizer.session import Session  # noqa: E402

SNOW_SOURCE_ID = 45
MARKERS = ("P2_SNOW_BANK", "P2_ENEMY_READY", "P2_SNOW_GENERATED_READY",
           "P2_SNOW_DRAW", "START_COLOR_READY", "PIKMIN_WORLD_RENDERED")


def place_snow_on_early_dwarf_slot():
    """Bind Snow to an ordinary renewable Stage 1 Dwarf generator."""
    document = build_document()
    profile = next(p for p in document["profiles"] if p["identity"] == "YellowKochappy")
    slot = next(s for s in document["slots"] if s["stage"] == 1 and s.get("cohort") == "dwarf"
                and s.get("first_day", 1) <= 2 and s.get("respawn_days", 0) > 0
                and not placement.compatibility(s, profile, {}))
    slot["evidence"] = {"xyz": True, "terrain": True, "route": True}
    profile["accepted_gates"] = ["xyz"]
    return {"schema": document["schema"], "slots": [slot], "profiles": [profile]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--exe", type=Path, required=True)
    parser.add_argument("--assets", type=Path, required=True)
    parser.add_argument("--snow-import", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seconds", type=float, default=70.0)
    args = parser.parse_args()
    exe = args.exe.resolve(strict=True)
    assets = args.assets.resolve(strict=True)
    snow_import = args.snow_import.resolve(strict=True)
    output = args.output.resolve()
    if output.exists():
        raise FileExistsError(f"Use a fresh private output directory: {output}")

    original = bridge.admitted_ids
    bridge.admitted_ids = lambda roster: [SNOW_SOURCE_ID]
    try:
        manifest = generate("p2-snow-launch", collection_checks=True, p2_enemies=True,
                            p2_placement=place_snow_on_early_dwarf_slot())
        binding = manifest["p2_layout"]["bindings"][0]
        assert binding["source_id"] == SNOW_SOURCE_ID and "p2-enemy-bridge-v1" in manifest["capabilities"]
        session = Session(manifest, output)
        run = NativeRun(session)
        receipt = stage_session_content(content_manifest(snow_import), run.directory / "assets",
                                        required_identities=[SNOW_SOURCE_ID], retail_assets=assets)
        assert receipt["mode"] == "asset-overlay" and receipt["identities"] == [str(SNOW_SOURCE_ID)]
    finally:
        bridge.admitted_ids = original

    env = dict(os.environ)
    env["PATH"] = r"C:\msys64\mingw64\bin" + os.pathsep + env.get("PATH", "")
    env["PIKMIN_RANDOMIZER_TEST_BACKGROUND"] = "1"
    env["SDL_AUDIODRIVER"] = "dummy"
    env.pop("BBFT_PORT", None)
    log_path = run.directory / "native.log"
    startup = subprocess.STARTUPINFO()
    startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    with log_path.open("w", encoding="utf-8") as stream:
        process = subprocess.Popen([str(exe), "--randomizer-seed", str(run.bootstrap.resolve())],
                                   cwd=run.directory, env=env, stdout=stream,
                                   stderr=subprocess.STDOUT, startupinfo=startup)
        terminated_by_harness = False
        try:
            deadline = time.monotonic() + args.seconds
            while process.poll() is None and time.monotonic() < deadline:
                run.poll()
                run.write_state(True)
                if all(m in log_path.read_text(encoding="utf-8", errors="replace") for m in MARKERS):
                    break
                time.sleep(0.2)
        finally:
            if process.poll() is None:
                terminated_by_harness = True
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=10)
    if process.returncode != 0 and not (terminated_by_harness and process.returncode == 1):
        raise RuntimeError(f"Unexpected native exit: {process.returncode}")
    log = log_path.read_text(encoding="utf-8", errors="replace")
    for required in MARKERS:
        assert required in log, f"missing {required}"
    for marker in ("abort", "Assertion failed"):
        assert marker.lower() not in log.lower(), f"native failure: {marker}"

    lines = log.splitlines()
    bank = next((line for line in lines if line.startswith("P2_SNOW_BANK")), "")
    ready = next((line for line in lines if line.startswith("P2_ENEMY_READY")), "")
    generated = next((line for line in lines if line.startswith("P2_SNOW_GENERATED_READY")), "")
    assert bank, "missing P2_SNOW_BANK"
    assert generated, "missing P2_SNOW_GENERATED_READY"
    assert "species=YellowKochappy" in ready, ready
    assert f"generator={binding['target']}" in ready, ready
    assert any(line.startswith("START_COLOR_READY") or "START_COLOR_READY" in line for line in lines)
    report = {"candidate_scope": "private-snow-launch", "product_admission": False,
              "placement_evidence": "synthetic diagnostic selection; not audited placement acceptance",
              "binding": binding, "receipt_identities": receipt["identities"],
              "bank": bank, "enemy_ready": ready, "generated_ready": generated,
              "log": str(log_path)}
    (run.directory / "generated-snow-launch.json").write_text(json.dumps(report, indent=2))
    print("P2 generated Snow launch passed: " + json.dumps({k: report[k] for k in
          ("binding", "bank", "enemy_ready", "generated_ready")}))


if __name__ == "__main__":
    main()
