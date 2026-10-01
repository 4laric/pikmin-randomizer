"""Run the isolated OniKurage automatic-binding fixture.

Mirrors run_kurage_automatic_binding.py but selects the Greater variant: the
sidecar magic `P2_ONIKURAGE_TEKI_1` makes GameCoreSection::finalSetup call
pc_p2_onikurage_teki_setup(), which binds the bounded OniKurage host (shared
Pikmin receiver plus the two captain mouth slots) to the generated actor.
The generated-Frog profile is supplied explicitly as evidence input.
"""
from argparse import ArgumentParser
from hashlib import file_digest
from pathlib import Path
import json
import os
import shutil
import subprocess


def sha256(path):
    with path.open("rb") as stream:
        return file_digest(stream, "sha256").hexdigest()


parser = ArgumentParser()
parser.add_argument("--fixture", type=Path, required=True)
parser.add_argument("--base-session", type=Path, required=True)
parser.add_argument("--frog-default-gen", type=Path, required=True)
parser.add_argument("--attack-model", type=Path, required=True)
parser.add_argument("--run", type=Path, required=True)
args = parser.parse_args()

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
(args.run / "p2-onikurage-teki.txt").write_text("P2_ONIKURAGE_TEKI_1 1 201001 0\n", encoding="ascii")
# Keep the actor lifecycle isolated from cargo setup, as in the Kurage fixture.
(args.run / "p2-cargo-free.txt").write_text("P2_CARGO_FREE_1\n", encoding="ascii")

environment = os.environ.copy()
environment["PATH"] = "C:/msys64/mingw64/bin;" + environment["PATH"]
with (args.run / "automatic-binding.log").open("w", encoding="utf-8") as log:
    completed = subprocess.run(
        [str(args.fixture), "--experimental-pikmin2-room", "--receiver-onikurage-binding"],
        cwd=args.run, env=environment, stdout=log, stderr=subprocess.STDOUT, timeout=180)
record = {
    "returncode": completed.returncode,
    "fixture_sha256": sha256(args.fixture),
    "frog_default_gen_sha256": sha256(args.frog_default_gen),
    "attack_model_sha256": sha256(args.attack_model),
    "sidecar": "P2_ONIKURAGE_TEKI_1 1 201001 0",
    "entry_point": "GameCoreSection::finalSetup",
    "direct_fixture_bind_calls": 0,
}
(args.run / "automatic-binding.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
if completed.returncode:
    raise SystemExit(completed.returncode)
