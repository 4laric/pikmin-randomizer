"""Prepare/run the bounded Kurage ingestion lifecycle fixture.

This lane does not execute the fixture: the OniKurage worker owns the real-GL
slot.  The script records the controlled `--receiver-ingestion` scenario so it
can be driven later from an isolated room session:

    py -3.12 tools/run_kurage_ingestion.py \
        --fixture output/kurage-ingestion-fixture-01/fixture.exe \
        --base-session output/kurage-host-sessions/b643272d465b4c7c9984399d18037c60 \
        --run output/kurage-ingestion-runtime-01

The base session supplies the room assets, the converted `kurage_wait.mod` /
`kurage_attack.mod` and the retail-shaped `p2-kurage-arena.txt` profile.
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
parser.add_argument("--run", type=Path, required=True)
args = parser.parse_args()

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

environment = os.environ.copy()
environment["PATH"] = "C:/msys64/mingw64/bin;" + environment["PATH"]
with (args.run / "receiver-ingestion.log").open("w", encoding="utf-8") as log:
    completed = subprocess.run(
        [str(args.fixture), "--experimental-pikmin2-room", "--receiver-ingestion"],
        cwd=args.run, env=environment, stdout=log, stderr=subprocess.STDOUT, timeout=120)
record = {
    "returncode": completed.returncode,
    "fixture_sha256": sha256(args.fixture),
    "arena_profile": "P2_KURAGE_ARENA_1 position 0 150 0 params 90 35",
    "scenario": "--receiver-ingestion",
    "entry_point": "pc_p2_kurage_arena_setup + pc_p2_kurage_receiver_admit",
}
(args.run / "receiver-ingestion.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
if completed.returncode:
    raise SystemExit(completed.returncode)
