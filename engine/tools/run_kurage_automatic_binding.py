"""Run the isolated normal-lifecycle Kurage binding fixture.

The Frog generator profile is supplied explicitly because it is evidence input,
not a production asset.  It must contain the validated generated Frog with
generator identity 201001.  The sidecar is written before process startup, so
GameCoreSection::finalSetup is the only binding entry point in the process.

Two scenarios:

    binding  (default) -- verify GameCoreSection::finalSetup bound the generated
                           Frog to the private Kurage adapter.
    auto-fsm           -- additionally enable the source flight lifecycle on the
                           ordinary generated actor and prove its Attack state
                           autonomously admits a nearby Pikmin.
"""
from argparse import ArgumentParser
from hashlib import file_digest
from pathlib import Path
import json
import os
import shutil
import subprocess

SCENARIOS = {
    "binding": ("--receiver-automatic-binding", "automatic-binding"),
    "auto-fsm": ("--receiver-auto-fsm", "auto-fsm"),
    "auto-fsm-move": ("--receiver-auto-fsm-move", "auto-fsm-move"),
}


def sha256(path):
    with path.open("rb") as stream:
        return file_digest(stream, "sha256").hexdigest()

parser = ArgumentParser()
parser.add_argument("--fixture", type=Path, required=True)
parser.add_argument("--base-session", type=Path, required=True)
parser.add_argument("--frog-default-gen", type=Path, required=True)
parser.add_argument("--attack-model", type=Path, required=True)
parser.add_argument("--scenario", choices=sorted(SCENARIOS), default="binding")
parser.add_argument("--run", type=Path, required=True)
args = parser.parse_args()

flag, log_stem = SCENARIOS[args.scenario]
if args.run.exists():
    raise SystemExit("run directory already exists: " + str(args.run))
for value in (args.fixture, args.frog_default_gen, args.attack_model):
    if not value.is_file():
        raise SystemExit("missing file: " + str(value))
if not (args.base_session / "assets").is_dir():
    raise SystemExit("missing base-session assets")

args.run.mkdir(parents=True)
shutil.copytree(args.base_session / "assets", args.run / "assets")
target_gen = args.run / "assets/dataDir/stages/chal0/default.gen"
target_gen.parent.mkdir(parents=True, exist_ok=True)
shutil.copy2(args.frog_default_gen, target_gen)
shutil.copy2(args.attack_model, args.run / "assets/dataDir/courses/pikmin2room/kurage_attack.mod")
(args.run / "p2-kurage-teki.txt").write_text("P2_KURAGE_TEKI_1 1 201001 0\n", encoding="ascii")
# The generated-Frog profile deliberately contains no preview treasure.  This
# isolates the actor lifecycle from cargo setup while retaining the normal room
# stage and its finalSetup ordering.
(args.run / "p2-cargo-free.txt").write_text("P2_CARGO_FREE_1\n", encoding="ascii")

environment = os.environ.copy()
environment["PATH"] = "C:/msys64/mingw64/bin;" + environment["PATH"]
environment["PIKMIN_P2_ROOM_WINDOW"] = "960x540"
log_name = log_stem + ".log"
with (args.run / log_name).open("w", encoding="utf-8") as log:
    completed = subprocess.run(
        [str(args.fixture), "--experimental-pikmin2-room", flag],
        cwd=args.run, env=environment, stdout=log, stderr=subprocess.STDOUT, timeout=180)
record = {
    "returncode": completed.returncode,
    "fixture_sha256": sha256(args.fixture),
    "frog_default_gen_sha256": sha256(args.frog_default_gen),
    "attack_model_sha256": sha256(args.attack_model),
    "sidecar": "P2_KURAGE_TEKI_1 1 201001 0",
    "scenario": flag,
    "entry_point": "GameCoreSection::finalSetup",
    "direct_fixture_bind_calls": 0,
}
(args.run / (log_stem + ".json")).write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
if completed.returncode:
    raise SystemExit(completed.returncode)
