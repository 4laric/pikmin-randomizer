"""Compiled schema-7 checks and journal/handshake test; no game assets needed."""
from pathlib import Path
import subprocess
import sys
import tempfile
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from randomizer.seed import generate
from randomizer.catalog import TOTAL_POPULATION, DELIVERY_BESTIARY
from randomizer.runner import NativeRun
from randomizer.session import Session

for shuffle in (False, True):
    with tempfile.TemporaryDirectory() as d:
        session = Session(generate('collection', 'ap', collection_checks=True, legacy_checks=True, enemy_shuffle=shuffle), d)
        run = NativeRun(session); run.write_state(True)
        result = subprocess.run([str(Path(sys.argv[1]).resolve()), '--randomizer-seed', str(run.bootstrap), '--collection-probe'],
                                capture_output=True, text=True, timeout=15)
        assert result.returncode == 0, result.stdout + result.stderr
        assert 'COLLECTION_PASS' in result.stdout
        run.poll()
        assert run.handshaken
        assert set(session.data['checked']) == set(TOTAL_POPULATION) | set(DELIVERY_BESTIARY)
        assert len((run.directory / 'checks.txt').read_text().splitlines()) == 17
print('PASS: total population through 500 at field cap 20, kill suppression, delivery gating, species and deduplication')
