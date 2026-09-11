"""Owned miniboss identities and invalid bootstrap rejection; no game assets."""
import subprocess
import sys
import tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from randomizer.seed import generate
from randomizer.session import Session
from randomizer.runner import NativeRun

for case in ('valid', 'unsupported', 'count', 'capability', 'version'):
    with tempfile.TemporaryDirectory() as folder:
        m = generate('miniboss-probe', 'ap', miniboss_enemies=True)
        s = Session(m, folder); r = NativeRun(s); r.write_state(True)
        text = r.bootstrap.read_text(encoding='utf-8')
        line = next(l for l in text.splitlines() if l.startswith('ENEMY_SLOTS '))
        fields = line.split()
        index = next(i for i in range(4, len(fields), 2) if fields[i] == '17')
        if case == 'unsupported': fields[index] = '22'
        if case == 'count': fields[index] = '24'
        text = text.replace(line, ' '.join(fields))
        if case == 'capability': text = text.replace('ENEMY_MINIBOSSES 1\n', '')
        if case == 'version': text = text.replace('ENEMY_MINIBOSSES 1', 'ENEMY_MINIBOSSES 2')
        r.bootstrap.write_text(text, encoding='utf-8')
        result = subprocess.run([str(Path(sys.argv[1]).resolve()), '--randomizer-seed', str(r.bootstrap), '--slot-probe'],
                                capture_output=True, text=True, timeout=15)
        if case == 'valid':
            assert result.returncode == 0, result.stderr
            actual = {int(l.split()[1]): int(l.split()[2]) for l in result.stdout.splitlines() if l.startswith('SLOT_PROBE ')}
            assert actual == {a['uid']: a['actual'] for a in m['spawn_layout']['assignments']}
            r.poll(); assert r.handshaken
            assert Session(m, folder).data == s.data
        else:
            assert result.returncode != 0, case
print('PASS miniboss owned identities, session handshake/recovery and four malformed adapters')
