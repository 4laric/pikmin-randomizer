"""Check every native species mapping and protected-spawn override."""
from pathlib import Path
import subprocess
import sys
import tempfile
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from randomizer.seed import generate
from randomizer.runner import NativeRun
from randomizer.session import Session

exe = Path(sys.argv[1]).resolve()
for mask in range(8):
    m = generate('enemy-probe', 'ap', enemy_shuffle=bool(mask))
    if mask: m['enemy_mask'] = mask
    with tempfile.TemporaryDirectory() as d:
        run = NativeRun(Session(m, d))
        run.write_state(True)
        result = subprocess.run([str(exe), '--randomizer-seed', str(run.bootstrap), '--enemy-probe'], capture_output=True, text=True, timeout=15)
        assert result.returncode == 0, result.stdout + result.stderr
        actual = {int(line.split()[1]): int(line.split()[2]) for line in result.stdout.splitlines() if line.startswith('ENEMY_MAP ')}
        expected = {i: i for i in range(35)}
        for bit, (a, b) in enumerate(((3, 31), (4, 32), (18, 19))):
            if mask & (1 << bit): expected[a], expected[b] = b, a
        assert actual == expected
        run.poll()
        assert run.handshaken
print('PASS native enemy permutations: all seven masks, opt-out, protected spawns, and all 35 type IDs')
