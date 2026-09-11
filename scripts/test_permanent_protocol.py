"""Schema-8 check-set boundaries and individual permanent completion protocol."""
import subprocess
import sys
import tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from randomizer.seed import generate
from randomizer.catalog import ITEM_IDS, progression_pool, FINE_POPULATION, OBSTACLES
from randomizer.session import Session, atomic_write
from randomizer.runner import NativeRun

exe = str(Path(sys.argv[1]).resolve())
with tempfile.TemporaryDirectory() as d:
    m = generate('permanent-probe', 'ap', permanent_checks=True, progressive_color_stats=True, randomize_color_stats=True)
    s = Session(m, d); s.bind_ap('fixture', 0, 1)
    s.receive(0, [ITEM_IDS[n] for n in progression_pool(m)])
    s.collect('Population: 450 total Pikmin')
    r = NativeRun(s); r.write_state(True)
    result = subprocess.run([exe, '--randomizer-seed', str(r.bootstrap), '--permanent-probe'], capture_output=True, text=True, timeout=15)
    assert result.returncode == 0 and 'PERMANENT_PASS' in result.stdout, result.stdout + result.stderr
    r.poll(); assert r.handshaken
    assert set(s.data['checked']) == set(FINE_POPULATION) | set(OBSTACLES), s.data['checked']
    assert len((r.directory / 'checks.txt').read_text().splitlines()) == len(FINE_POPULATION) + len(OBSTACLES) - 1
    assert Session(m, d).data['checked'] == s.data['checked']
for bad in ('CHECKS 2 64 64', 'CHECKS 1 9999', 'CHECKS 9999', 'CHECKS -1', 'CHECKS 1 -1'):
    with tempfile.TemporaryDirectory() as d:
        s = Session(generate('bad', 'ap', permanent_checks=True), d)
        r = NativeRun(s)
        atomic_write(r.directory / 'state.txt', s.native_state(r.token, True).replace('CHECKS 0', bad))
        result = subprocess.run([exe, '--randomizer-seed', str(r.bootstrap)], capture_output=True, text=True, timeout=15)
        assert result.returncode != 0 and 'invalid' in result.stderr, result.stdout + result.stderr
print('PASS: >64 check restore, 19 population milestones, every obstacle instance, partial/unknown suppression, deduplication, malformed sets')
