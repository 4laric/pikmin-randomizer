"""Production-executable smoke: DeathLink handshake and an induced casualty on the starting squad."""
import _winapi, argparse, os, subprocess, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from randomizer.seed import generate
from randomizer.session import Session
from randomizer.runner import NativeRun

def main(exe, assets, output, unit=5):
    session = Session(generate('deathlink-smoke', 'ap', death_link=True, death_link_pikmin=unit), output)
    session.bind_ap('synthetic-native-smoke', 0, 1)
    run = NativeRun(session)
    _winapi.CreateJunction(str(assets.resolve()), str((run.directory / 'assets').resolve()))
    env = dict(os.environ, PIKMIN_RANDOMIZER_TEST_BACKGROUND='1', SDL_AUDIODRIVER='dummy'); env.pop('BBFT_PORT', None)
    log = run.directory / 'native.log'
    with log.open('w', encoding='utf-8') as stream:
        startup = subprocess.STARTUPINFO(); startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        process = subprocess.Popen([str(exe.resolve()), '--randomizer-seed', str(run.bootstrap.resolve())],
                                   cwd=run.directory, env=env, stdout=stream, stderr=subprocess.STDOUT, startupinfo=startup)
        try:
            def wait(marker, timeout=90):
                deadline = time.monotonic() + timeout
                while time.monotonic() < deadline:
                    if process.poll() is not None: raise AssertionError(f'native exited {process.returncode}; {log}')
                    run.poll(); run.write_state(run.handshaken)
                    text = log.read_text(encoding='utf-8', errors='replace')
                    if marker in text: return text
                    time.sleep(.1)
                raise AssertionError(f'timeout: {marker}; {log}')
            wait('START_COLOR_READY')
            assert ' death-link-v1 ' in (run.directory / 'hello.txt').read_text() + ' '
            wait('PIKMIN_WORLD_RENDERED')
            time.sleep(3)  # Let the opening reach active gameplay before the link lands.
            session.receive_death_link(); run.write_state(True)
            text = wait('DEATHLINK_APPLIED')
            line = next(l for l in text.splitlines() if 'DEATHLINK_APPLIED' in l)
            assert line.strip().endswith(f'killed={unit} pending=0'), line
            time.sleep(4)  # Dying animations finish and Piki::kill runs for the induced squad.
            run.poll()
            assert session.data['pikmin_deaths'] == 0, session.data  # Induced deaths are excluded from the journal.
            assert not (run.directory / 'deaths.txt').exists() or (run.directory / 'deaths.txt').read_text() == ''
            print(f'PASS DeathLink startup: handshake, {line.strip()}, no journaled induced deaths')
        finally:
            if process.poll() is None: process.terminate(); process.wait(10)

if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--exe', type=Path, required=True); p.add_argument('--assets', type=Path, required=True); p.add_argument('--output', type=Path, required=True); p.add_argument('--unit', type=int, default=5)
    a = p.parse_args(); a.output.mkdir(parents=True, exist_ok=True); main(a.exe, a.assets, a.output, a.unit)
