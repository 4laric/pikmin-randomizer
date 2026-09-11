"""Compiled consumable persistence and strict receipt protocol; no assets needed."""
import subprocess
import sys
import tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from randomizer.benefits import BENEFIT_ITEMS, DELIVERY, FLOWERS, HEAL, WHISTLE, PLUCK
from randomizer.catalog import ITEM_IDS
from randomizer.seed import generate
from randomizer.session import Session, atomic_write
from randomizer.runner import NativeRun

exe = str(Path(sys.argv[1]).resolve())
with tempfile.TemporaryDirectory() as d:
    m = generate('benefits', 'ap', permanent_checks=True, progressive_color_stats=True)
    s = Session(m, d); s.bind_ap('room', 0, 1)
    def run(expected, mutate=None):
        r = NativeRun(s); r.write_state(True)
        if mutate: atomic_write(r.directory / 'state.txt', mutate((r.directory / 'state.txt').read_text()))
        result = subprocess.run([exe, '--randomizer-seed', str(r.bootstrap), '--benefit-probe'], capture_output=True, text=True, timeout=10)
        assert expected in result.stdout + result.stderr, result.stdout + result.stderr
        if not mutate:
            assert result.returncode == 0
            r.poll(); assert r.handshaken
        else: assert result.returncode != 0
    run('used=0 whistle=1.00 pluck=1.00')
    ids = [ITEM_IDS[n] for n in BENEFIT_ITEMS] + [ITEM_IDS[WHISTLE], ITEM_IDS[PLUCK]]
    s.receive(0, ids); s.receive(0, ids)
    run('used=3 whistle=1.50 pluck=1.50')
    journal = Path(d) / 'benefits-used.txt'; before = journal.read_text()
    s = Session(m, d)
    run('used=0 whistle=1.50 pluck=1.50')
    assert journal.read_text() == before
    s.receive(len(ids), [ITEM_IDS[DELIVERY]])
    run('used=1 whistle=1.50 pluck=1.50')
    run('retracted benefit receipt', lambda text: text.replace('BENEFITS 2 1 1 2 2', 'BENEFITS 0 1 1 2 2'))
    run('retracted benefit receipt', lambda text: text.replace('BENEFITS 2 1 1 2 2', 'BENEFITS 2 1 1 3 2'))
    run('missing benefit state', lambda text: text.replace('BENEFITS 2 1 1 2 2 ', ''))
    journal.write_text(before.replace(s.fingerprint, '0' * 64))
    r = NativeRun(s); r.write_state(True)
    result = subprocess.run([exe, '--randomizer-seed', str(r.bootstrap), '--benefit-probe'], capture_output=True, text=True, timeout=10)
    assert result.returncode != 0 and 'invalid benefit consumption journal' in result.stderr
print('PASS: delayed receipts, upgrades, duplicates, durable consumption/relaunch, new receipt, malformed/retracted state and foreign journal rejection')
