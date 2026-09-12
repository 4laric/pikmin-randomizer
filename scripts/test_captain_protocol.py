"""Check native movement/pluck multipliers for new and legacy receipts, including reload."""
import subprocess, sys, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from randomizer.benefits import CAPTAIN, PLUCK
from randomizer.catalog import ITEM_IDS
from randomizer.seed import generate
from randomizer.session import Session
from randomizer.runner import NativeRun
for combined in (False, True):
    for bombs in (0, 1):
        with tempfile.TemporaryDirectory() as d:
            m = generate('captain', 'ap', permanent_checks=True, combined_captain=combined, bomb_rock_weight=bombs)
            s = Session(m, d); s.bind_ap('test', 0, 1)
            for count in range(3):
                if count: s.receive(count-1, [ITEM_IDS[CAPTAIN if combined else PLUCK]])
                s = Session(m, d)
                r = NativeRun(s); r.write_state(True)
                out = subprocess.run([str(Path(sys.argv[1]).resolve()), '--randomizer-seed', str(r.bootstrap), '--benefit-probe'], capture_output=True, text=True, timeout=15)
                assert out.returncode == 0, out.stdout+out.stderr
                assert f'CAPTAIN_MOVE {1+.25*count*combined:.2f}' in out.stdout, out.stdout
                assert f'pluck={1+.25*count:.2f}' in out.stdout, out.stdout
                r.poll(); assert r.handshaken
print('PASS legacy/new captain movement and plucking, 0/1/2 receipts, bomb modes, reload')
