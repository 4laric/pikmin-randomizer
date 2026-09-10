"""Hidden, silent startup/item-state smoke; not a physical carry or sunset test."""
import argparse
import os
from pathlib import Path
import subprocess
import sys
import time
import _winapi
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from randomizer.seed import generate
from randomizer.session import Session
from randomizer.runner import NativeRun
from randomizer.catalog import UNLOCKS, ITEM_IDS, REPAIR


def main(exe, assets, output, expanded=False):
    session = Session(generate("startup-smoke", "ap", expanded=expanded), output)
    session.bind_ap("synthetic-native-smoke", 0, 1)
    run = NativeRun(session)
    _winapi.CreateJunction(str(assets.resolve()), str((run.directory / "assets").resolve()))
    env = dict(os.environ, PIKMIN_RANDOMIZER_TEST_BACKGROUND="1", SDL_AUDIODRIVER="dummy")
    env.pop("BBFT_PORT", None)
    log = run.directory / "native.log"
    with log.open("w", encoding="utf-8") as stream:
        startup = subprocess.STARTUPINFO();startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        process = subprocess.Popen([str(exe.resolve()), "--randomizer-seed", str(run.bootstrap.resolve())],
                                   cwd=run.directory, env=env, stdout=stream, stderr=subprocess.STDOUT, startupinfo=startup)
        try:
            def wait(marker, timeout=60):
                deadline = time.monotonic() + timeout
                while time.monotonic() < deadline:
                    if process.poll() is not None:
                        raise AssertionError(f"native exited {process.returncode}; {log}")
                    run.poll();run.write_state(run.handshaken)
                    if marker in log.read_text(encoding="utf-8", errors="replace"): return
                    time.sleep(.1)
                raise AssertionError(f"timeout: {marker}; {log}")
            wait("PIKMIN_FOH_READY day=2 field_red=20 main_engine_ap_check=0")
            wait("PIKMIN_WORLD_RENDERED")
            wait("PIKMIN_AREA_ACCESS impact=0 forest=1 navel=0 spring=0 trial=0")
            for i, item in enumerate(UNLOCKS):
                session.receive(i, [ITEM_IDS[item]])
                if i < 2:
                    wait(f"PIKMIN_{'YELLOW' if i == 0 else 'BLUE'}_ONION_GRANTED starter=5")
            wait("PIKMIN_AREA_ACCESS impact=0 forest=1 navel=1 spring=1 trial=1")
            session.receive(5, [ITEM_IDS[REPAIR]] * 25)
            wait("GOAL: Ship repaired!")
            run.poll()
            expected = {'Population: 20 Pikmin in the field', 'Explore: The Forest of Hope - Land'} if expanded else set()
            assert set(session.data['checked']) == expected, session.data['checked']
            text = log.read_text(encoding="utf-8", errors="replace")
            for color in ("YELLOW", "BLUE"):
                assert text.count(f"PIKMIN_{color}_ONION_GRANTED starter=5") == 1
            assert 'TEST_ONLY' not in text, 'test fixtures enabled unexpectedly'
            print("PASS native startup: rendered FoH, 20 field reds, color grants, area gates, received-repair goal; expected checks only", sorted(expected))
            print(log)
        finally:
            if process.poll() is None: process.terminate();process.wait(timeout=10)
            run.write_state(False)

if __name__ == "__main__":
    p = argparse.ArgumentParser();p.add_argument("--exe", type=Path, required=True)
    p.add_argument("--assets", type=Path, required=True);p.add_argument("--output", type=Path, required=True)
    p.add_argument('--expanded', action='store_true')
    a=p.parse_args();main(a.exe,a.assets,a.output.resolve(),a.expanded)
