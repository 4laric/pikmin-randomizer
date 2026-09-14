"""Run the source Kurage flight-FSM host fixtures.

Two controlled scenarios are exposed by the private ``p2_kurage_runtime``
fixture and executed here against a fresh room session copied from a
base session that already carries the converted ``kurage_wait.mod`` /
``kurage_attack.mod`` and the retail-shaped ``p2-kurage-arena.txt`` profile:

    py -3.12 tools/run_kurage_flight_fsm.py \
        --fixture output/p2-lane29-fsm-fixture-01/fixture.exe \
        --base-session output/kurage-host-sessions/b643272d465b4c7c9984399d18037c60 \
        --scenario flight-fsm-admission --run output/p2-lane29-fsm-admission-01

The scenarios drive the bounded host with the transcribed source flight
lifecycle (``pc_p2_kurage_fsm.h``).  The slot's real attack.bca event clock
supplies the suction window; ``--flight-fsm-admission`` proves the ordinary
Attack state initiates capture, and ``--flight-fsm-death`` proves an
interrupted release through owner death restores the captured Pikmin.
"""
from argparse import ArgumentParser
from hashlib import file_digest
from pathlib import Path
import json
import os
import shutil
import subprocess

SCENARIOS = {
    "flight-fsm-admission": "--flight-fsm-admission",
    "flight-fsm-death": "--flight-fsm-death",
    "flight-fsm-greater": "--flight-fsm-greater",
    "flight-fsm-greater-drop": "--flight-fsm-greater-drop",
    "flight-fsm-greater-captain": "--flight-fsm-greater-captain",
    "flight-fsm-stuck-flick": "--flight-fsm-stuck-flick",
    "flight-fsm-death-cycle": "--flight-fsm-death-cycle",
    "flight-fsm-patrol": "--flight-fsm-patrol",
}


def sha256(path):
    with path.open("rb") as stream:
        return file_digest(stream, "sha256").hexdigest()


parser = ArgumentParser()
parser.add_argument("--fixture", type=Path, required=True)
parser.add_argument("--base-session", type=Path, required=True)
parser.add_argument("--scenario", choices=sorted(SCENARIOS), required=True)
parser.add_argument("--run", type=Path, required=True)
parser.add_argument("--models", type=Path,
    help="optional converted Kurage pose directory; each <motion>.mod is copied "
         "as kurage_<motion>.mod so the host can draw the per-state source pose")
parser.add_argument("--greater-models", type=Path,
    help="optional converted OniKurage pose directory; copied as "
         "onikurage_<motion>.mod for the Greater variant's per-state pose")
args = parser.parse_args()

flag = SCENARIOS[args.scenario]
if args.run.exists():
    raise SystemExit("run directory already exists: " + str(args.run))
if not args.fixture.is_file():
    raise SystemExit("missing fixture: " + str(args.fixture))
for name in ("assets", "p2-kurage-arena.txt"):
    if not (args.base_session / name).exists():
        raise SystemExit("missing base-session input: " + str(args.base_session / name))

args.run.mkdir(parents=True)
shutil.copytree(args.base_session / "assets", args.run / "assets")
shutil.copy2(args.base_session / "p2-kurage-arena.txt", args.run / "p2-kurage-arena.txt")
def copy_models(models, target, prefix):
    copied = []
    # Flat converted layout: <motion>.mod.  Material-patched/envmap layout:
    # <motion>/patched.mod (experimental.pikmin2_kurage_material_patch #282 /
    # _envmap #286).
    for model in sorted(models.glob("*.mod")):
        shutil.copy2(model, target / (prefix + model.name))
        copied.append(model.name)
    for patched in sorted(models.glob("*/patched.mod")):
        shutil.copy2(patched, target / (prefix + patched.parent.name + ".mod"))
        copied.append(patched.parent.name + "/patched.mod")
    return copied


target = args.run / "assets/dataDir/courses/pikmin2room"
if args.models is not None or args.greater_models is not None:
    target.mkdir(parents=True, exist_ok=True)
if args.models is not None:
    print("kurage models copied:", ", ".join(copy_models(args.models, target, "kurage_")))
if args.greater_models is not None:
    print("onikurage models copied:", ", ".join(copy_models(args.greater_models, target, "onikurage_")))

environment = os.environ.copy()
environment["PATH"] = "C:/msys64/mingw64/bin;" + environment["PATH"]
environment["PIKMIN_P2_ROOM_WINDOW"] = "960x540"
log_name = args.scenario + ".log"
with (args.run / log_name).open("w", encoding="utf-8") as log:
    completed = subprocess.run(
        [str(args.fixture), "--experimental-pikmin2-room", flag],
        cwd=args.run, env=environment, stdout=log, stderr=subprocess.STDOUT, timeout=180)
record = {
    "returncode": completed.returncode,
    "fixture_sha256": sha256(args.fixture),
    "arena_profile": "P2_KURAGE_ARENA_1 position 0 150 0 params 90 35",
    "scenario": flag,
    "window": "PIKMIN_P2_ROOM_WINDOW=960x540",
    "entry_point": "pc_p2_kurage_arena_fsm_enable + source Attack suction scan",
}
(args.run / (args.scenario + ".json")).write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
if completed.returncode:
    raise SystemExit(completed.returncode)
