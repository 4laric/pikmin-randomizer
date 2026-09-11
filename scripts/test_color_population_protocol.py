"""Exercise compiled per-color observations, legacy separation and durable replay."""
from pathlib import Path
import subprocess
import sys
import tempfile
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from randomizer.catalog import ITEM_IDS, population_checks
from randomizer.seed import generate
from randomizer.session import Session
from randomizer.runner import NativeRun

for permanent in (False, True):
    for starting in ('red', 'yellow', 'blue'):
        for all_colors in (False, True):
            with tempfile.TemporaryDirectory() as d:
                m = generate('color-probe', 'ap', collection_checks=True, permanent_checks=permanent,
                             starting_color=starting, starting_flarlic=1)
                s = Session(m, d)
                if all_colors:
                    s.data['received'] = [ITEM_IDS[c + ' Onion'] for c in ('Red', 'Yellow', 'Blue') if c.lower() != starting]
                    s.save()
                r = NativeRun(s); r.write_state(True)
                result = subprocess.run([str(Path(sys.argv[1]).resolve()), '--randomizer-seed', str(r.bootstrap),
                                         '--color-population-probe'], capture_output=True, text=True, timeout=15)
                assert result.returncode == 0 and 'COLOR_POPULATION_PASS' in result.stdout, result.stdout + result.stderr
                r.poll(); assert r.handshaken
                expected = {n for n, (c, count) in population_checks(m).items() if all_colors or c.lower() == starting}
                assert set(s.data['checked']) == expected
                assert len((r.directory / 'checks.txt').read_text().splitlines()) == len(expected)
                assert Session(m, d).data['checked'] == s.data['checked']
print('PASS: 12 native cases; separate colors, locked Onions, 9/10/100 thresholds, cap 10, gating and replay')
