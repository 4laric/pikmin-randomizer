"""Complete every audited obstacle with modern and legacy native check sets."""
import sys,subprocess,tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from randomizer.seed import generate
from randomizer.catalog import ITEM_IDS,progression_pool,OBSTACLES
from randomizer.session import Session
from randomizer.runner import NativeRun
for legacy in (False,True):
    with tempfile.TemporaryDirectory() as d:
        m=generate('retired-stick','ap',permanent_checks=True,legacy_checks=legacy)
        s=Session(m,d);s.bind_ap('test',0,1)
        s.receive(0,[ITEM_IDS[n] for n in progression_pool(m)])
        r=NativeRun(s);r.write_state(True)
        out=subprocess.run([str(Path(sys.argv[1]).resolve()),'--randomizer-seed',str(r.bootstrap),'--retired-stick-probe'],capture_output=True,text=True,timeout=15)
        assert out.returncode==0 and 'RETIRED_STICK_PASS' in out.stdout,out.stdout+out.stderr
        r.poll()
        expected={n for n,row in OBSTACLES.items() if legacy or row[1]!=100}
        assert set(s.data['checked'])==expected
        assert len(expected)==(51 if legacy else 43)
        assert Session(m,d).data['checked']==s.data['checked']
print('PASS all 51 completion observations: 43 modern checks, 51 legacy checks, replay intact')
