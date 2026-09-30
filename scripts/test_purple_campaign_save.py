"""Exercise the real checkpoint parser/writer, without engine or retail assets."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from experimental.pikmin2_seed_bridge import build_bootstrap, resolve_layout
from randomizer.runner import NativeRun
from randomizer.seed import generate
from randomizer.session import Session


def main(exe):
    env = dict(os.environ)
    env['PATH'] = r'C:\msys64\mingw64\bin' + os.pathsep + env.get('PATH', '')
    manifest = generate('purple-checkpoint', collection_checks=True)
    layout = resolve_layout('purple-checkpoint', 'Player1', ('gen-001',), (79,))
    with tempfile.TemporaryDirectory() as directory:
        session = Session(manifest, directory)

        def run(args=(), expected=0, purple=True):
            native = NativeRun(session)
            native.write_state(True)
            text = native.bootstrap.read_text()
            native.bootstrap.write_text(text[:text.rfind('END')] + build_bootstrap(layout)
                                        + ('PURPLE 1\n' if purple else '') + 'END\n')
            result = subprocess.run([str(exe), '--randomizer-seed', str(native.bootstrap),
                                     '--purple-save-probe', *args], env=env,
                                    capture_output=True, text=True, timeout=20)
            assert result.returncode == expected, (result.stdout, result.stderr)
            return result.stdout + result.stderr

        assert 'stock=0,0,0 marker=0' in run(('--deposit', '--commit'))
        assert 'stock=1,1,1 marker=1' in run()
        assert 'stock=1,1,1 marker=1' in run(('--deposit',))
        assert 'stock=1,1,1 marker=1' in run()  # unsaved changes roll back together
        campaign = Path(directory) / 'campaign'
        (campaign / 'interrupted.tmp').write_bytes(b'incomplete')
        assert 'stock=1,1,1 marker=1' in run()
        assert 'stock=1,1,1 marker=1' in run(('--deposit', '--commit'))
        assert 'stock=2,2,2 marker=2' in run()
        latest = sorted(campaign.glob('*.sav'))[-1]
        intact = latest.read_bytes()
        latest.write_bytes(intact[:-1])
        assert 'damaged' in run(expected=2)
        latest.write_bytes(intact)
        # Options cannot silently reinterpret an opted-in checkpoint as legacy.
        assert 'mismatch' in run(expected=2, purple=False)
        # Fail the real writer after loading: its temporary path is a directory.
        assert 'cannot create campaign checkpoint' in run(('--deposit', '--fail-write', '--commit'), expected=2)
        assert latest.read_bytes() == intact
        assert 'stock=2,2,2 marker=2' in run()
    print('PASS Purple checkpoint: species/maturity, paired world, rollback, reconnect, corruption, opt-out rejection')


if __name__ == '__main__':
    main(Path(sys.argv[1]).resolve())
