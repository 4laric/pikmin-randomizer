"""Saved per-slot choices, independent load order and strict bootstrap failures."""
from pathlib import Path
import subprocess, sys, tempfile
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from randomizer.seed import generate
from randomizer.session import Session
from randomizer.runner import NativeRun

for case in ('valid', 'hash', 'count', 'uid', 'species', 'mask'):
    with tempfile.TemporaryDirectory() as directory:
        m = generate('slot-probe', 'ap', per_spawn_enemies=True)
        s = Session(m, directory); r = NativeRun(s); r.write_state(True)
        text = r.bootstrap.read_text()
        line = next(x for x in text.splitlines() if x.startswith('ENEMY_SLOTS '))
        fields = line.split()
        if case == 'hash': fields[1] = '0' * 64
        if case == 'count': fields[2] = '14'
        if case == 'uid': fields[3] = '1'
        if case == 'species': fields[4] = '0'
        text = text.replace(line, ' '.join(fields))
        if case == 'mask': text = text.replace('ENEMIES 0', 'ENEMIES 1')
        r.bootstrap.write_text(text)
        result = subprocess.run([str(Path(sys.argv[1]).resolve()), '--randomizer-seed', str(r.bootstrap), '--slot-probe'], capture_output=True, text=True, timeout=15)
        if case == 'valid':
            assert result.returncode == 0, result.stderr
            choices = {int(row.split()[1]): int(row.split()[2]) for row in result.stdout.splitlines() if row.startswith('SLOT_PROBE ')}
            assert choices == {row['uid']: row['actual'] for row in m['spawn_layout']['assignments']}
            r.poll(); assert r.handshaken
        else:
            assert result.returncode != 0 and not r.handshaken, case
print('PASS saved IDs/assignments, reverse load order, restored IDs, unchanged other species and five malformed bootstraps')
