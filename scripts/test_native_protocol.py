"""Exercise the compiled native adapter and real IPC, without launching a game."""
import argparse
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from randomizer.seed import generate
from randomizer.session import Session
from randomizer.runner import NativeRun
from randomizer.catalog import NAMES


def run_tests(exe):
    env = dict(os.environ); env.pop("BBFT_PORT", None)
    assert subprocess.run([str(exe)], env=env, capture_output=True).returncode == 0
    with tempfile.TemporaryDirectory() as tmp:
        session = Session(generate("native-io"), Path(tmp))
        run = NativeRun(session)
        process = subprocess.Popen([str(exe), "--randomizer-seed", str(run.bootstrap)],
                                   env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        try:
            for _ in range(100):
                run.poll(); run.write_state(run.handshaken)
                if process.poll() is not None: break
                time.sleep(0.05)
            out = process.communicate(timeout=2)[0].decode()
            assert process.returncode == 0, out
            run.poll()
            assert session.data["checked"] == ["Pikmin: Eternal Fuel Dynamo"], session.data
            assert (run.directory / "checks.txt").read_text().splitlines() == [str(NAMES.index("Pikmin: Eternal Fuel Dynamo"))]
        finally:
            if process.poll() is None: process.kill(); process.wait()
        for case in ("version", "placement", "state", "mixed"):
            fresh = NativeRun(session)
            args = [str(exe), "--randomizer-seed", str(fresh.bootstrap)]
            if case in ("version", "placement"):
                text = fresh.bootstrap.read_text()
                text = text.replace("PIKMIN_RANDOMIZER 1", "PIKMIN_RANDOMIZER 2") if case == "version" else text.replace("identity-v1", "shuffle-v1")
                fresh.bootstrap.write_text(text)
            elif case == "state":
                (fresh.directory / "state.txt").write_text("PIKMIN_STATE 1 wrong 1 0 0 0 END")
            else: args += ["--bbft-port", "39000"]
            result = subprocess.run(args, env=env, capture_output=True, timeout=5)
            assert result.returncode == 2, (case, result.stdout, result.stderr)
            assert not (fresh.directory / "hello.txt").exists()
            assert not (fresh.directory / "checks.txt").exists()
        result = subprocess.run([str(exe), "--randomizer-seed", str(run.bootstrap)], env=env, capture_output=True)
        assert result.returncode == 2, "used run directory accepted"
    print("Native IPC passed: opt-out, handshake, durable dedup, version/placement/state/mixed-mode rejection, single-use run")


if __name__ == "__main__":
    p = argparse.ArgumentParser(); p.add_argument("exe", type=Path)
    run_tests(p.parse_args().exe.resolve())
