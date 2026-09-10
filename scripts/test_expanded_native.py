"""Compiled event/IPC tests, separate from native gameplay acceptance."""
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from randomizer.seed import generate
from randomizer.session import Session
from randomizer.runner import NativeRun
from randomizer.catalog import UNLOCKS, ITEM_IDS, FLARLIC, EXPANDED_NAMES


def main(exe):
    env=dict(os.environ);env.pop("BBFT_PORT",None)
    with tempfile.TemporaryDirectory() as tmp:
        session=Session(generate("probe","ap",expanded=True),Path(tmp))
        session.bind_ap("probe",0,1);run=NativeRun(session)
        log=Path(tmp)/"probe.log"
        with log.open("w") as stream:
            p=subprocess.Popen([str(exe),"--randomizer-seed",str(run.bootstrap)],env=env,stdout=stream,stderr=subprocess.STDOUT)
            try:
                granted=False
                for _ in range(150):
                    run.poll()
                    text=log.read_text()
                    if "EXPANDED_INITIAL" in text and not granted:
                        session.receive(0,[ITEM_IDS[n] for n in UNLOCKS]+[ITEM_IDS[FLARLIC]]*8)
                        granted=True
                    run.write_state(run.handshaken)
                    if p.poll() is not None:break
                    time.sleep(.05)
                p.wait(timeout=2);run.poll()
                assert p.returncode==0,log.read_text()
                assert "EXPANDED_COMPLETE" in log.read_text()
                expected={f"Population: {n} Pikmin in the field" for n in range(20,101,10)}
                expected|={"Bestiary: Dwarf Bulborb","Explore: The Forest of Hope - Land","Explore: The Forest of Hope - Scout",
                           "Explore: The Final Trial - Land","Explore: The Final Trial - Scout"}
                assert set(session.data["checked"])==expected,session.data["checked"]
                lines=(run.directory/"checks.txt").read_text().splitlines()
                assert len(lines)==len(set(lines))==len(expected)
                assert "54" in lines
            finally:
                if p.poll() is None:p.kill();p.wait()
    print("Expanded native probe passed: capacity receipts, thresholds, death/active gates, stage/ground/distance gates, dedup and IDs above bit 31")

if __name__=="__main__":main(Path(sys.argv[1]).resolve())
