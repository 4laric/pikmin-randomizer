"""Compiled maturity/day-length bootstrap, handshake and strict state protocol; no assets needed."""
import subprocess
import sys
import tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from randomizer.benefits import MATURITY, DAY_LENGTH
from randomizer.catalog import ITEM_IDS
from randomizer.seed import generate
from randomizer.session import Session, atomic_write
from randomizer.runner import NativeRun

exe = str(Path(sys.argv[1]).resolve())
with tempfile.TemporaryDirectory() as d:
    m = generate('maturity', 'ap', permanent_checks=True, combined_captain=True, progressive_maturity=True, progressive_day_length=3, day_length_step=25)
    s = Session(m, d); s.bind_ap('room', 0, 1)

    def run(expected, mutate=None):
        r = NativeRun(s); r.write_state(True)
        if mutate: atomic_write(r.directory / 'state.txt', mutate((r.directory / 'state.txt').read_text()))
        result = subprocess.run([exe, '--randomizer-seed', str(r.bootstrap), '--benefit-probe'], capture_output=True, text=True, timeout=10)
        assert expected in result.stdout + result.stderr, result.stdout + result.stderr
        if not mutate:
            assert result.returncode == 0
            r.poll(); assert r.handshaken  # native capabilities match the manifest
        else: assert result.returncode != 0

    run('MATURITY_PROBE blue=0 red=0 yellow=0 day=1.00')
    ids = [ITEM_IDS[MATURITY['red']], ITEM_IDS[MATURITY['blue']], ITEM_IDS[MATURITY['blue']], ITEM_IDS[MATURITY['blue']], ITEM_IDS[DAY_LENGTH]]
    s.receive(0, ids); s.receive(0, ids)
    run('MATURITY_PROBE blue=2 red=1 yellow=0 day=1.25')
    s.receive(len(ids), [ITEM_IDS[DAY_LENGTH]] * 5)
    run('MATURITY_PROBE blue=2 red=1 yellow=0 day=1.75')
    run('invalid or retracted maturity', lambda t: t.replace('MATURITY 2 1 0', 'MATURITY 3 1 0'))
    run('missing maturity state', lambda t: t.replace(' MATURITY 2 1 0', ''))
    run('invalid or retracted day length', lambda t: t.replace('DAYLENGTH 3', 'DAYLENGTH 4'))
    run('invalid or retracted day length', lambda t: t.replace(' DAYLENGTH 3', ''))
print('PASS: maturity/day-length bootstrap, handshake, capped receipts, duplicate replay and malformed state rejection')
