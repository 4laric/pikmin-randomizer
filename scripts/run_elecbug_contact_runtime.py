"""Bounded #1164 fixture launch; requires an exact supplied executable hash."""
import argparse
import json
import os
from pathlib import Path
import uuid

from stage_elecbug_contact_runtime import prepare, sha, ROOT
from run_pikmin2_cave_fixture import supervise


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ("exe", "assets", "content", "output"):
        p.add_argument("--" + name, type=Path, required=True)
    p.add_argument("--exe-sha256", required=True)
    p.add_argument("--mode", choices=("ready", "positive", "negative"), required=True)
    a = p.parse_args()
    exe = a.exe.resolve(strict=True)
    if sha(exe) != a.exe_sha256:
        raise ValueError("executable hash mismatch")
    run = prepare(a.assets, a.content, a.output / uuid.uuid4().hex)
    private_save = run / "private-save"
    private_save.mkdir()
    env = {k: v for k, v in os.environ.items() if not k.startswith(("P2_ELECBUG_", "PIKMIN_RANDOMIZER_"))}
    env.update(NECTAR_SAVE_DIR=str(private_save), NECTAR_EXECUTABLE_PATH=str(exe),
               SDL_AUDIODRIVER="dummy", SDL_JOYSTICK_ALLOW_BACKGROUND_EVENTS="1",
               PIKMIN_RANDOMIZER_TEST_BACKGROUND="1", PIKMIN_P2_ROOM_WINDOW="960x540")
    if a.mode == "negative":
        env["P2_ELECBUG_FORCE_CAPTAIN_DOWN"] = "1"
    if a.mode == "ready":
        env["P2_ELECBUG_READY_ONLY"] = "1"
    marker = {"ready": "PASS P2_ELECBUG_READY_ONLY", "positive": "PASS P2_ELECBUG_CONTACT",
              "negative": "P2_FIXTURE_CAPTAIN_DOWN"}[a.mode]
    provenance = dict(exe=str(exe), exe_sha256=sha(exe), mode=a.mode, wall_seconds=60,
                      stage_sha256=sha(run / "elecbug-contact-inputs.json"),
                      guard_sha256=sha(ROOT / "scripts/p2_fixture_captain_guard.h"),
                      dlls={p.name: sha(p) for p in exe.parent.glob("*.dll")},
                      injected="negative captain-down signal only" if a.mode == "negative" else "none")
    (run / "acceptance-inputs.json").write_text(json.dumps(provenance, indent=2))
    raw = supervise([str(exe), "--experimental-pikmin2-room"], run, 60, env, [marker])
    text = (run / "native.log").read_text(errors="replace")
    expected = 86 if a.mode == "negative" else 0
    passed = not raw.get("timed_out") and raw.get("exit_code") == expected and marker in text
    if a.mode == "negative":
        passed = passed and "PASS P2_ELECBUG" not in text
    else:
        passed = passed and "P2_FIXTURE_CAPTAIN_DOWN" not in text
        passed = passed and "P2_ELECBUG_CONTACT_WINDOW size=960x540 centered=1" in text
        passed = passed and "P2_ELECBUG_CONTACT_READY live=20 red=20" in text
        if a.mode == "positive":
            passed = passed and "P2_ELECBUG_NATURAL_PRESS" in text
    result = dict(mode=a.mode, passed=passed, raw=raw, log_sha256=sha(run / "native.log"),
                  natural_contact_validated=passed and a.mode == "positive",
                  whole_family_acceptance=False)
    (run / "assessment.json").write_text(json.dumps(result, indent=2))
    print(json.dumps(dict(run=str(run), **result), indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
