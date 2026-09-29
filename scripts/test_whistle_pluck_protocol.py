"""Compiled Whistle Pluck item bootstrap, handshake and strict state protocol; no assets needed."""
import subprocess
import sys
import tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from randomizer.benefits import WHISTLE_PLUCK
from randomizer.catalog import ITEM_IDS
from randomizer.seed import generate
from randomizer.session import Session, atomic_write
from randomizer.runner import NativeRun

exe = str(Path(sys.argv[1]).resolve())


def probe(s, expected, mutate=None):
    r = NativeRun(s); r.write_state(True)
    if mutate: atomic_write(r.directory / 'state.txt', mutate((r.directory / 'state.txt').read_text()))
    result = subprocess.run([exe, '--randomizer-seed', str(r.bootstrap), '--benefit-probe'], capture_output=True, text=True, timeout=10)
    assert expected in result.stdout + result.stderr, result.stdout + result.stderr
    if not mutate:
        assert result.returncode == 0
        r.poll(); assert r.handshaken  # native capabilities match the manifest
    else: assert result.returncode != 0


with tempfile.TemporaryDirectory() as d:
    # A seed without the item leaves the Mods setting in charge.
    old = generate('whistle', 'ap', permanent_checks=True, combined_captain=True, progressive_maturity=True)
    s = Session(old, str(Path(d) / 'old')); s.bind_ap('room', 0, 1)
    probe(s, 'WHISTLE_PLUCK_PROBE -1')

    m = generate('whistle', 'ap', permanent_checks=True, combined_captain=True, progressive_maturity=True, progressive_day_length=2, whistle_pluck_item=True)
    s = Session(m, str(Path(d) / 'new')); s.bind_ap('room', 0, 1)
    probe(s, 'WHISTLE_PLUCK_PROBE 0')
    s.receive(0, [ITEM_IDS[WHISTLE_PLUCK]]); s.receive(0, [ITEM_IDS[WHISTLE_PLUCK]])
    probe(s, 'WHISTLE_PLUCK_PROBE 1')
    probe(s, 'invalid or retracted whistle pluck', lambda t: t.replace('WHISTLEPLUCK 1', 'WHISTLEPLUCK 2'))
    probe(s, 'invalid or retracted whistle pluck', lambda t: t.replace(' WHISTLEPLUCK 1', ''))
print('PASS: whistle pluck bootstrap, handshake, receipt, duplicate replay and malformed state rejection')
