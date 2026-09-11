"""New bestiary trigger gating and exploration-free catalog, both check-set sizes."""
import subprocess, sys, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from randomizer.seed import generate
from randomizer.catalog import NEW_BESTIARY
from randomizer.session import Session
from randomizer.runner import NativeRun
for permanent in (False, True):
    with tempfile.TemporaryDirectory() as d:
        m = generate('modern-probe', 'ap', collection_checks=True, permanent_checks=permanent)
        s = Session(m, d); r = NativeRun(s); r.write_state(True)
        result = subprocess.run([str(Path(sys.argv[1]).resolve()), '--randomizer-seed', str(r.bootstrap), '--bestiary-probe'], capture_output=True, text=True, timeout=15)
        assert result.returncode == 0 and 'BESTIARY_PASS' in result.stdout, result.stdout + result.stderr
        r.poll(); assert r.handshaken
        expected = set(NEW_BESTIARY)
        assert set(s.data['checked']) == expected, s.data['checked']
        assert len((r.directory / 'checks.txt').read_text().splitlines()) == len(expected)
        assert Session(m, d).data['checked'] == s.data['checked']
print('PASS: both modern check sets, all eleven additions, delivery/defeat gating, no landing/scout checks, journal replay/deduplication')
