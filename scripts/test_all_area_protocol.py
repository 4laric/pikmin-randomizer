"""Compiled area/color gate and new high-check-ID coverage, not physical play."""
from pathlib import Path
import subprocess
import sys
import tempfile
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from randomizer.seed import generate
from randomizer.runner import NativeRun
from randomizer.session import Session
from randomizer.catalog import POSITRON


def main(exe):
    for area in ('impact', 'forest', 'navel', 'spring', 'trial'):
        for color in ('red', 'yellow', 'blue'):
            with tempfile.TemporaryDirectory() as d:
                session = Session(generate('area-probe', 'ap', starting_area=area, starting_color=color, all_areas=True), d)
                run = NativeRun(session)
                run.write_state(True)
                result = subprocess.run([str(exe), '--randomizer-seed', str(run.bootstrap), '--area-probe'], capture_output=True, text=True, timeout=15)
                assert result.returncode == 0, result.stdout + result.stderr
                run.poll()
                assert run.handshaken
                assert len(session.data['checked']) == (3 if area == 'impact' else 1)
                if area == 'impact':
                    assert POSITRON in session.data['checked']
                    assert '57' in (run.directory / 'checks.txt').read_text().splitlines()
    print('PASS all 15 compiled area/color gate combinations and Impact IDs 55..57')


if __name__ == '__main__': main(Path(sys.argv[1]).resolve())
