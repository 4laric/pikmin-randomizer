"""Native parser/getter agreement, bounds rejection and legacy stat defaults."""
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from randomizer.seed import generate
from randomizer.session import Session
from randomizer.runner import NativeRun

exe = str(Path(sys.argv[1]).resolve())
for enabled in (False, True):
    for seed in range(8):
        with TemporaryDirectory() as d:
            m = generate(str(seed), 'ap', randomize_color_stats=enabled, starting_flarlic=1)
            run = NativeRun(Session(m, d)); run.write_state(True)
            result = subprocess.run([exe, '--randomizer-seed', str(run.bootstrap), '--stats-probe'],
                                    capture_output=True, text=True, timeout=15)
            assert result.returncode == 0, result.stdout + result.stderr
            for i, color in enumerate(('blue', 'red', 'yellow')):
                p = m.get('color_stats', {}).get(color, dict(damage=100, movement=100, attack_rate=100, carry=1))
                assert f"STATS_PROBE {i} {p['damage']} {p['movement']} {p['attack_rate']} {p['carry']}" in result.stdout
            run.poll(); assert run.handshaken
for invalid in ('blue 0 100 100 1', 'blue 100 100 100 6', 'green 100 100 100 1'):
    with TemporaryDirectory() as d:
        m = generate('bad', 'ap', randomize_color_stats=True)
        run = NativeRun(Session(m, d))
        tokens = run.bootstrap.read_text().split()
        index = tokens.index('COLOR_STATS_WIDE') + 1
        tokens[index:index+5] = invalid.split()
        run.bootstrap.write_text(' '.join(tokens))
        result = subprocess.run([exe, '--randomizer-seed', str(run.bootstrap), '--stats-probe'],
                                capture_output=True, text=True, timeout=15)
        assert result.returncode == 2, result.stdout + result.stderr
print('PASS: per-color native stats, opt-out unity, strict bounds and color order')
