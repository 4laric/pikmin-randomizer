"""Bounded #1164 fixture launch; requires an exact supplied executable hash."""
import argparse
import json
import math
import os
from pathlib import Path
import re
import sys
import uuid

from stage_elecbug_contact_runtime import prepare, sha, ROOT
from run_pikmin2_cave_fixture import supervise


def validate_artifact(exe, expected_sha, native_commit, native_tree):
    """Refuse incomplete provider metadata before staging or process startup."""
    if not all(re.fullmatch(r"[0-9a-f]{40}", value) for value in (native_commit, native_tree)):
        raise ValueError("expected native commit/tree must be full lowercase Git identities")
    if sha(exe) != expected_sha:
        raise ValueError("executable hash mismatch")
    fields = {}
    for line in (exe.parent / "BUILD_INFO.txt").read_text().splitlines():
        key, _, value = line.partition(" ")
        if key in fields:
            raise ValueError("duplicate artifact identity field: " + key)
        fields[key] = value
    expected = dict(compiled_commit=native_commit, compiled_tree=native_tree,
                    profile="netplay=ON", selected_target="pikmin_ci_fixture_elecbug_contact",
                    guard_root="36ac5ddd2877b9308276f96b28a81e137ae58c5a",
                    guard_sha256="ee2bfeaba96020f4f0ae310f9cf98dfabbd824353d20de6fb78fec17001f3ff9")
    for key, value in expected.items():
        if fields.get(key) != value:
            raise ValueError("artifact identity mismatch: " + key)
    manifest = {}
    for line in (exe.parent / "sha256.txt").read_text().splitlines():
        digest, separator, name = line.partition(" *")
        name = name.removeprefix("./")
        if (not separator or not re.fullmatch(r"[0-9a-f]{64}", digest)
                or not name or "/" in name or "\\" in name or ":" in name or name in manifest):
            raise ValueError("invalid artifact checksum manifest")
        manifest[name] = digest
    required = {exe.name, "SDL2.dll", "libgcc_s_seh-1.dll", "libstdc++-6.dll", "libwinpthread-1.dll"}
    if not required <= manifest.keys():
        raise ValueError("incomplete artifact checksum manifest")
    if not {p.name for p in exe.parent.glob("*.dll")} <= manifest.keys():
        raise ValueError("unrecorded artifact DLL")
    for name, digest in manifest.items():
        if sha(exe.parent / name) != digest:
            raise ValueError("artifact checksum mismatch: " + name)
    return fields


def contact_witness(text, mode="landing"):
    """Correlate real dispatch to one observed ordinary throw; fail closed."""
    if any(line.startswith("P2_ELECBUG_GUARD_OBSERVATION ") and "injected=1" in line for line in text.splitlines()):
        return None
    histories = {}
    white_acquired = {}
    ivory_frame = None
    electric = mode in ("red-electric", "white-electric")
    species = "4" if mode == "white-electric" else "1"
    if mode not in ("landing", "red-electric", "white-electric"):
        return None
    for line in text.splitlines():
        tag, _, tail = line.partition(" ")
        if tag not in {"P2_ELECBUG_THROW", "P2_ELECBUG_OFF_CONTACT",
                       "P2_ELECBUG_CONTACT_DISPATCH", "P2_ELECBUG_CONTACT_CANDIDATE",
                       "P2_ELECBUG_PRESS_DENKI", "P2_ELECBUG_IVORY_SPROUT", "P2_ELECBUG_WHITE_ACQUIRED"}:
            continue
        pairs = [part.split("=", 1) for part in tail.split()]
        if any(len(pair) != 2 for pair in pairs) or len({p[0] for p in pairs}) != len(pairs):
            return None
        fields = dict(pairs)
        if tag == "P2_ELECBUG_IVORY_SPROUT":
            sprout = fields.get("sprout", "").lower().removeprefix("0x")
            ivory_seen = (fields.get("generator") == "25" and fields.get("species") == "4"
                          and fields.get("population") == "20" and bool(re.fullmatch(r"[0-9a-f]+", sprout))
                          and int(sprout, 16) != 0)
            ivory_frame = int(fields["frame"]) if ivory_seen else None
            continue
        pointer = fields.get("piki", "").lower().removeprefix("0x")
        if not re.fullmatch(r"[0-9a-f]+", pointer) or int(pointer, 16) == 0:
            return None
        pointer = str(int(pointer, 16))
        history = histories.get(pointer)
        if tag == "P2_ELECBUG_WHITE_ACQUIRED":
            acquired_frame = int(fields["frame"])
            if (ivory_frame is not None and acquired_frame >= ivory_frame and fields.get("species") == "4"
                    and fields.get("population") == "20" and fields.get("ordinary_pluck") == "1"):
                white_acquired[pointer] = acquired_frame
            continue
        if tag == "P2_ELECBUG_THROW":
            phase = fields.get("phase")
            if phase == "held":
                if mode != "white-electric" or (pointer in white_acquired and int(fields["frame"]) >= white_acquired[pointer]):
                    histories[pointer] = ["held", int(fields["frame"])]
            elif phase == "invalidated":
                histories.pop(pointer, None)
            elif history:
                expected = {"released": "held", "rising": "released", "descending": "rising"}
                frame = int(fields["frame"])
                later = frame >= history[1] if phase == "released" else frame > history[1]
                if expected.get(phase) == history[0] and later:
                    histories[pointer] = [phase, frame]
                else:
                    histories.pop(pointer, None)
        elif fields.get("generator") == "346002" and history:
            if tag == "P2_ELECBUG_OFF_CONTACT":
                frame = int(fields["frame"])
                if history[0] == "descending" and frame >= history[1] and fields.get("contact") == "0":
                    histories[pointer] = ["off_contact", frame]
            elif tag == "P2_ELECBUG_PRESS_DENKI" and electric:
                if (history[0] == "off_contact" and fields.get("target") == species
                        and fields.get("accepted") == "1" and fields.get("target_state") == "35(DenkiDying)"):
                    histories[pointer] = ["denki", history[1]]
                else:
                    histories.pop(pointer, None)
            elif tag == "P2_ELECBUG_CONTACT_DISPATCH":
                vy = float(fields.get("vy", "nan"))
                before = {"discharge", "childdischarge"} if electric else {"wait", "turn", "move", "charge", "childcharge", "discharge", "childdischarge"}
                if (history[0] == ("denki" if electric else "off_contact") and math.isfinite(vy) and vy < -.01
                        and fields.get("contact") == "1" and fields.get("species") == species
                        and fields.get("enemy_before") in before
                        and fields.get("enemy_after") == "reverse"):
                    histories[pointer] = ["dispatch", history[1]]
                else:
                    histories.pop(pointer, None)
            elif tag == "P2_ELECBUG_CONTACT_CANDIDATE":
                if (history[0] == "dispatch" and int(fields["frame"]) > history[1]
                        and fields.get("observed_reverse") == "1"
                        and (not electric or (fields.get("mode") == mode and fields.get("species") == species))):
                    return dict(generator=346002, piki_hex=hex(int(pointer)), ordinary_throw=True,
                                ordered_off_contact_dispatch_reverse=True, mode=mode,
                                electric_reaction=electric, ordinary_white_acquisition=mode == "white-electric")
    return None


def linux_preflight(exe, run, args, env):
    """Require adopted #1174 helpers and current controller admission per child."""
    if sys.platform != "linux":
        raise ValueError("Only Windows and Linux fixtures are supported")
    # Deliberately no import from another worktree or fallback launcher.
    import fixture_platform as platform
    import run_pikmin2_cave_fixture as launcher
    for module, expected in ((platform, args.platform_helper_sha256), (launcher, args.supervisor_sha256)):
        path = Path(module.__file__).resolve(strict=True)
        if path.parent != ROOT / "scripts" or not expected or sha(path) != expected:
            raise ValueError("Exact adopted portable helper identity required")
    if (launcher.supervise.__globals__.get("owned_process_options") is not platform.owned_process_options
            or launcher.supervise.__globals__.get("terminate_owned_process") is not platform.terminate_owned_process):
        raise ValueError("Shared supervisor lacks adopted owned-process-group support")
    proof = platform.linux_admission(exe, ROOT, args.output.resolve(strict=True), run)
    expected = {"target": "pikmin_ci_fixture_elecbug_contact", "source": "tools/p2_elecbug_contact_runtime.cpp",
                "exe_sha256": args.exe_sha256, "guard_sha256": sha(ROOT / "scripts/p2_fixture_captain_guard.h")}
    for key, value in expected.items():
        if proof.get(key) != value:
            raise ValueError("Linux admission mismatch: " + key)
    for key, value, length in (("PIKMIN_SHA", args.root_commit, 40), ("NATIVE_SHA", args.native_commit, 40),
                               ("FIXTURE_SOURCE_SHA256", args.fixture_source_sha256, 64)):
        if not value or not re.fullmatch(r"[0-9a-f]{%d}" % length, value) or proof["pins"].get(key) != value:
            raise ValueError("Linux source pin mismatch: " + key)
    runtime = platform.runtime_evidence(exe, env=env, cwd=run)
    if runtime.get("platform") != "linux" or runtime["executable"]["sha256"] != proof["exe_sha256"]:
        raise ValueError("Linux library/executable proof mismatch")
    return {"admission": proof, "runtime": runtime,
            "platform_helper_sha256": args.platform_helper_sha256, "supervisor_sha256": args.supervisor_sha256}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ("exe", "assets", "content", "output"):
        p.add_argument("--" + name, type=Path, required=True)
    p.add_argument("--exe-sha256", required=True)
    p.add_argument("--native-commit", required=True)
    p.add_argument("--native-tree")
    for name in ("root-commit", "fixture-source-sha256", "platform-helper-sha256", "supervisor-sha256"):
        p.add_argument("--" + name)
    p.add_argument("--white", type=Path)
    p.add_argument("--pod", type=Path)
    p.add_argument("--mode", choices=("ready", "positive", "landing", "red-electric", "white-electric", "negative"), required=True)
    p.add_argument("--negative-scene", choices=("landing", "red-electric", "white-electric"))
    p.add_argument("--guard-mask", choices=("active", "inactive", "null-state", "missing-manager"))
    a = p.parse_args()
    exe = a.exe.resolve(strict=True)
    scene = a.negative_scene if a.mode == "negative" else ("landing" if a.mode in ("positive", "ready") else a.mode)
    if not scene or (a.mode != "negative" and a.negative_scene):
        p.error("negative mode requires explicit --negative-scene; other modes forbid it")
    if (a.mode == "negative") != (a.guard_mask is not None):
        p.error("negative mode requires explicit --guard-mask; other modes forbid it")
    if (scene == "white-electric") != (a.white is not None and a.pod is not None):
        p.error("white-electric requires --white and --pod; other scenes must omit them")
    if (a.white is None) != (a.pod is None):
        p.error("--white and --pod must be supplied together")
    if sha(exe) != a.exe_sha256:
        raise ValueError("executable hash mismatch")
    identity = validate_artifact(exe, a.exe_sha256, a.native_commit, a.native_tree or "") if sys.platform == "win32" else None
    if sys.platform not in ("win32", "linux"):
        raise ValueError("Unsupported fixture platform")
    run = prepare(a.assets, a.content, a.output / uuid.uuid4().hex, white=a.white, pod=a.pod)
    private_save = run / "private-save"
    private_save.mkdir()
    env = {k: v for k, v in os.environ.items() if not k.startswith(("P2_ELECBUG_", "PIKMIN_RANDOMIZER_", "PIKMIN_NETPLAY_TEST_"))}
    env.update(NECTAR_SAVE_DIR=str(private_save), NECTAR_EXECUTABLE_PATH=str(exe),
               SDL_AUDIODRIVER="dummy", SDL_JOYSTICK_ALLOW_BACKGROUND_EVENTS="1",
               PIKMIN_RANDOMIZER_TEST_BACKGROUND="1", PIKMIN_P2_ROOM_WINDOW="960x540", P2_ELECBUG_MODE=scene)
    if sys.platform == "linux":
        for key, name in (("HOME", "private-home"), ("XDG_CONFIG_HOME", "private-config"), ("XDG_CACHE_HOME", "private-cache")):
            directory = run / name
            directory.mkdir()
            env[key] = str(directory)
    if a.mode == "negative":
        env["P2_ELECBUG_GUARD_MASK"] = a.guard_mask
    if a.mode == "ready":
        env["P2_ELECBUG_READY_ONLY"] = "1"
    marker = ("PASS P2_ELECBUG_READY_ONLY" if a.mode == "ready" else
              "P2_FIXTURE_CAPTAIN_DOWN" if a.mode == "negative" else "P2_ELECBUG_CONTACT_CANDIDATE")
    provenance = dict(exe=str(exe), exe_sha256=sha(exe), mode=a.mode, wall_seconds=60,
                      compiled_identity=identity,
                      stage_sha256=sha(run / "elecbug-contact-inputs.json"),
                      guard_sha256=sha(ROOT / "scripts/p2_fixture_captain_guard.h"),
                      scene=scene, guard_mask=a.guard_mask,
                      dlls={p.name: sha(p) for p in exe.parent.glob("*.dll")} if sys.platform == "win32" else {},
                      injected="negative captain-down signal only" if a.mode == "negative" else "none")
    if sys.platform == "linux":
        provenance["linux"] = linux_preflight(exe, run, a, env)
    (run / "acceptance-inputs.json").write_text(json.dumps(provenance, indent=2))
    raw = supervise([str(exe), "--experimental-pikmin2-room"], run, 60, env, [marker])
    text = (run / "native.log").read_text(errors="replace")
    expected = 86 if a.mode == "negative" else 0
    witness = None
    passed = not raw.get("timed_out") and raw.get("exit_code") == expected and marker in text
    if a.mode == "negative":
        passed = passed and "PASS P2_ELECBUG" not in text and "P2_ELECBUG_CONTACT_CANDIDATE" not in text
        passed = passed and f"P2_ELECBUG_GUARD_OBSERVATION mask={a.guard_mask} injected=1 " in text
    else:
        passed = passed and "P2_FIXTURE_CAPTAIN_DOWN" not in text
        passed = passed and not any(line.startswith("P2_ELECBUG_GUARD_OBSERVATION ") and "injected=1" in line for line in text.splitlines())
        passed = passed and "P2_ELECBUG_CONTACT_WINDOW size=960x540 centered=1" in text
        passed = passed and "P2_ELECBUG_CONTACT_READY live=20 red=20" in text
        if a.mode != "ready":
            try:
                witness = contact_witness(text, scene)
            except (KeyError, ValueError):
                witness = None
            passed = passed and witness is not None
    result = dict(mode=a.mode, passed=passed, raw=raw, log_sha256=sha(run / "native.log"),
                  natural_contact_validated=passed and a.mode not in ("ready", "negative"),
                  contact_witness=witness,
                  whole_family_acceptance=False)
    (run / "assessment.json").write_text(json.dumps(result, indent=2))
    print(json.dumps(dict(run=str(run), **result), indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
