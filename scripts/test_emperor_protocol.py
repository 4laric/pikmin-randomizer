"""Compiled repair gate, goal notification and durable session replay."""
import sys, tempfile, subprocess
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from randomizer.seed import generate
from randomizer.session import Session
from randomizer.runner import NativeRun
from randomizer.catalog import ITEM_IDS, REPAIR
with tempfile.TemporaryDirectory() as d:
    m = generate('emperor-probe','ap',goal_mode='emperor_bulblax')
    s = Session(m,d); s.bind_ap('test',0,1)
    s.receive(0,[ITEM_IDS[REPAIR]]*24)
    for count in (24,25):
        if count == 25: s.receive(24,[ITEM_IDS[REPAIR]])
        assert not s.goal
        r = NativeRun(s);r.write_state(True)
        out=subprocess.run([str(Path(sys.argv[1]).resolve()),'--randomizer-seed',str(r.bootstrap),'--emperor-probe'],capture_output=True,text=True,timeout=15)
        assert out.returncode==0 and 'EMPEROR_PASS' in out.stdout,out.stdout+out.stderr
        r.poll();assert s.goal == (count==25)
        assert Session(m,d).goal == s.goal
    print('PASS Emperor: 24 repairs stays locked; 25 unlocks; death signals goal; replay persists')
