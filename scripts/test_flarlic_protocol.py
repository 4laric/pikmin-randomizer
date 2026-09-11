"""Check configurable native capacity, legacy defaults and malformed boot rejection."""
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from randomizer.seed import generate
from randomizer.session import Session
from randomizer.runner import NativeRun
from randomizer.catalog import ITEM_IDS, FLARLIC

exe = Path(sys.argv[1]).resolve()
for initial in (None, 1, 2, 10):
    for received in (0, 10 - (initial or 2)):
        with TemporaryDirectory() as d:
            session = Session(generate('capacity', 'ap', expanded=True, starting_flarlic=initial), d)
            session.bind_ap('capacity-probe', 0, 1)
            session.receive(0, [ITEM_IDS[FLARLIC]] * received)
            run = NativeRun(session)
            run.write_state(True)
            result = subprocess.run([str(exe), '--randomizer-seed', str(run.bootstrap), '--capacity-probe'],
                                    capture_output=True, text=True, timeout=15)
            assert result.returncode == 0, result.stdout + result.stderr
            assert f'CAPACITY_PROBE {10 * ((initial or 2) + received)}' in result.stdout
            run.poll()
            assert run.handshaken
for invalid in (0, 11):
    with TemporaryDirectory() as d:
        session = Session(generate('invalid', 'ap', starting_flarlic=1), d)
        run = NativeRun(session)
        run.bootstrap.write_text(run.bootstrap.read_text().replace('STARTING_FLARLIC 1', f'STARTING_FLARLIC {invalid}'))
        result = subprocess.run([str(exe), '--randomizer-seed', str(run.bootstrap), '--capacity-probe'],
                                capture_output=True, text=True, timeout=15)
        assert result.returncode == 2 and 'invalid starting Flarlic' in result.stderr
print('PASS: initial caps, received capacity through 100, legacy handshake, invalid bounds')
