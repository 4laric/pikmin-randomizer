"""Trap receipts, checkpoint/reconnect and unsaved rollback; all benefit mode combinations."""
import subprocess,sys,tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from randomizer.benefits import PROGG
from randomizer.catalog import ITEM_IDS
from randomizer.seed import generate
from randomizer.session import Session, atomic_write
from randomizer.runner import NativeRun
for bits in range(4):
    bombs,traps=bits&1,(bits>>1)&1
    for combined in (False,True):
        with tempfile.TemporaryDirectory() as d:
            m=generate('ambush','ap',permanent_checks=True,progg_trap_weight=1,bomb_trap_weight=traps,bomb_rock_weight=bombs,combined_captain=combined)
            s=Session(m,d);s.bind_ap('room',0,1)
            def run(expected,save=False,corrupt=False):
                r=NativeRun(s);r.write_state(True)
                assert f'BENEFITS {9+bombs+2*combined+4*traps}\n' in r.bootstrap.read_text()
                if corrupt:
                    state=r.directory/'state.txt'
                    atomic_write(state,state.read_text().replace('BENEFITS 0 0 0 0 0 0 0 3','BENEFITS 0 0 0 0 0 0 0 1'))
                out=subprocess.run([str(Path(sys.argv[1]).resolve()),'--randomizer-seed',str(r.bootstrap),'--benefit-probe',*(['--save-probe'] if save else [])],capture_output=True,text=True,timeout=15)
                if corrupt:
                    assert out.returncode != 0 and 'retracted benefit receipt' in out.stderr,out.stdout+out.stderr
                else:
                    assert out.returncode==0 and f'used={expected}' in out.stdout,out.stdout+out.stderr
                    r.poll();assert r.handshaken
            run(0)
            s.receive(0,[ITEM_IDS[PROGG]]*2);s.receive(0,[ITEM_IDS[PROGG]]*2)
            run(2) # unsaved effects replay on restart, like other consumables
            run(2,save=True)
            s=Session(m,d);run(0)
            s.receive(2,[ITEM_IDS[PROGG]])
            run(1,save=True);run(0);run(0,corrupt=True)
print('PASS trap duplicate receipts, Progg modes 9-16, unsaved rollback, saved consumption, reload, retraction rejection')
