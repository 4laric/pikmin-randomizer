"""Compiled DeathLink contract: baseline, bounded pending links, induced-death exclusion and the death journal."""
import subprocess
import sys
import tempfile
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from randomizer.seed import generate
from randomizer.session import Session
from randomizer.runner import NativeRun

with tempfile.TemporaryDirectory() as d:
    m = generate('deathlink-probe', 'ap', death_link=True, death_link_pikmin=4)
    s = Session(m, d); s.bind_ap('test', 0, 1)
    # Links received before this run started form the baseline and never replay.
    s.receive_death_link(); s.receive_death_link()
    r = NativeRun(s); r.write_state(True)
    probe = subprocess.Popen([str(Path(sys.argv[1]).resolve()), '--randomizer-seed', str(r.bootstrap), '--deathlink-probe'],
                             stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    try:
        deadline = time.monotonic() + 15
        lines = []
        while time.monotonic() < deadline:
            line = probe.stdout.readline()
            if not line: break
            lines.append(line)
            if 'DEATHLINK_BASELINE' in line:
                r.poll()
                assert s.data['pikmin_deaths'] == 3, s.data
                # Five links at once: the native queue is bounded to three.
                for _ in range(5): s.receive_death_link()
                r.write_state(True)
            if 'DEATHLINK_PASS' in line or 'DEATHLINK_TIMEOUT' in line: break
        out = ''.join(lines) + probe.communicate(timeout=15)[0]
    finally:
        if probe.poll() is None: probe.kill()
    assert probe.returncode == 0 and 'DEATHLINK_PASS unit=4 applied=3' in out, out
    assert 'death-link-v1' in (r.directory / 'hello.txt').read_text()
    assert (r.directory / 'deaths.txt').read_text() == '1\n2\n3\n'
    r.poll(); assert s.data['pikmin_deaths'] == 3 and Session(m, d).data['pikmin_deaths'] == 3
    print('PASS DeathLink: baseline ignored; 5 queued links applied as 3; induced death excluded from a 3-death journal')
