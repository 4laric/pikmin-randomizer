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
    def run(expected, mutate=None, save=True):
        r = NativeRun(s); r.write_state(True)
        if mutate: atomic_write(r.directory / 'state.txt', mutate((r.directory / 'state.txt').read_text()))
        result = subprocess.run([exe, '--randomizer-seed', str(r.bootstrap), '--benefit-probe', *(['--save-probe'] if save else [])], capture_output=True, text=True, timeout=10)
        assert expected in result.stdout + result.stderr, result.stdout + result.stderr
        if not mutate:
            assert result.returncode == 0
            r.poll(); assert r.handshaken
        else: assert result.returncode != 0
    run('used=0 whistle=1.00 pluck=1.00')
    ids = [ITEM_IDS[n] for n in BENEFIT_ITEMS if n != HEAL] + [ITEM_IDS[WHISTLE], ITEM_IDS[PLUCK]]
    s.receive(0, ids); s.receive(0, ids)
    run('used=2 whistle=1.50 pluck=1.50')
    campaign = Path(d) / 'campaign'
    s = Session(m, d)
    run('used=0 whistle=1.50 pluck=1.50')
    # A consumed receipt without a native save must return after restarting.
    s.receive(len(ids), [ITEM_IDS[DELIVERY]])
    run('used=1 whistle=1.50 pluck=1.50', save=False)
    run('used=1 whistle=1.50 pluck=1.50')
    run('used=0 whistle=1.50 pluck=1.50')
    run('retracted benefit receipt', lambda text: text.replace('BENEFITS 2 1 0 2 2', 'BENEFITS 0 1 0 2 2'))
    run('retracted benefit receipt', lambda text: text.replace('BENEFITS 2 1 0 2 2', 'BENEFITS 2 1 0 3 2'))
    run('missing benefit state', lambda text: text.replace('BENEFITS 2 1 0 2 2 ', ''))
    (campaign / 'interrupted.tmp').write_bytes(b'incomplete write')
    run('used=0 whistle=1.50 pluck=1.50', save=False)
    latest = sorted(campaign.glob('*.sav'))[-1]
    intact = latest.read_bytes()
    for damaged in (intact[:-1], intact[:-100] + b'x' + intact[-99:]):
        latest.write_bytes(damaged)
        r = NativeRun(s); r.write_state(True)
        result = subprocess.run([exe, '--randomizer-seed', str(r.bootstrap), '--benefit-probe'], capture_output=True, text=True, timeout=10)
        assert result.returncode != 0 and 'checkpoint is damaged' in result.stderr
    latest.write_bytes(intact)
    latest.write_bytes(latest.read_bytes().replace(s.fingerprint.encode(), b'0' * 64))
    r = NativeRun(s); r.write_state(True)
    result = subprocess.run([exe, '--randomizer-seed', str(r.bootstrap), '--benefit-probe'], capture_output=True, text=True, timeout=10)
    assert result.returncode != 0 and 'checkpoint header/seed mismatch' in result.stderr
print('PASS: saved consumption, unsaved rollback, duplicate receipts, new receipts and foreign/corrupt checkpoint rejection and interrupted-write recovery')
