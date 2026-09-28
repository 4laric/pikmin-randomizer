"""Assemble and launch the Groink live-host GL scenario (lane 21, #198).

Copies the lane-16 staged frog arena (generator 201001 `Frog`, the lane's
generated Groink proxy), writes no sidecar and stages no Pod. The generated
Frog is left alive and driven only by its own source FSM; the staged starting
squad is already inside its sight, so it turns/hops/attacks on its own. The
private fixture (``--groink-live``) witnesses the actor's position/FSM/animation
and each live Piki's ``InteractPress`` health/state change.
"""
import os
import shutil
import subprocess
import sys
from pathlib import Path
from hashlib import file_digest

BASE = Path("C:/Users/alari/pikmin-randomizer/output/dsw/l16-out/run-runtime/stages/1a2f21ebde494a0eb4986841b5446131")
FIXTURE = Path("C:/Users/alari/pikmin-randomizer/output/dsw/l21-out/groink-live-fixture/fixture.exe")
RUN = Path("C:/Users/alari/pikmin-randomizer/output/dsw/l21-out/run-groink-live")


def sha256(path):
    with path.open("rb") as stream:
        return file_digest(stream, "sha256").hexdigest()


if RUN.exists():
    raise SystemExit("run directory already exists: " + str(RUN))
if not (BASE / "assets").is_dir():
    raise SystemExit("missing base-session assets: " + str(BASE))

RUN.mkdir(parents=True)
shutil.copytree(BASE / "assets", RUN / "assets")
shutil.copy2(BASE / "p2-frog.txt", RUN / "p2-frog.txt")
(RUN / "p2-cargo-free.txt").write_text("P2_CARGO_FREE_1\n", encoding="ascii")

env = os.environ.copy()
env["PATH"] = "C:/msys64/mingw64/bin;" + env["PATH"]
env["PIKMIN_P2_ROOM_WINDOW"] = "960x540"
env["PYTHONUTF8"] = "1"

with (RUN / "native.log").open("w", encoding="utf-8") as log:
    completed = subprocess.run(
        [str(FIXTURE), "--experimental-pikmin2-room", "--groink-live"],
        cwd=RUN, env=env, stdout=log, stderr=subprocess.STDOUT, timeout=300)

(RUN / "run.json").write_text(
    '{\n  "returncode": %d,\n  "fixture_sha256": "%s"\n}\n'
    % (completed.returncode, sha256(FIXTURE)),
    encoding="utf-8")

print("returncode", completed.returncode)
if completed.returncode:
    tail = (RUN / "native.log").read_text(encoding="utf-8", errors="replace").splitlines()[-40:]
    sys.stdout.write("\n".join(tail))
    sys.exit(completed.returncode)
