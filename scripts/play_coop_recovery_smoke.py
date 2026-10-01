"""Disposable two-window online recovery smoke; rerun for a fresh campaign."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time
import uuid


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--exe', type=Path, required=True)
    p.add_argument('--assets', type=Path, default=Path(os.environ.get('APPDATA', '')) / 'PikminRandomizer/game-data/assets')
    p.add_argument('--out', type=Path, default=Path(__file__).resolve().parent / 'smoke-runs')
    p.add_argument('--hidden', action='store_true', help='Automation only; no human judgement')
    p.add_argument('--seconds', type=int, default=20, help='Play time before the disposable partner disconnects')
    a = p.parse_args()
    if not 5 <= a.seconds <= 60:
        p.error('--seconds must be 5..60')
    exe, assets = a.exe.resolve(strict=True), a.assets.resolve(strict=True)
    if not (assets / 'dataDir').is_dir():
        p.error('The game data folder is incomplete.')
    run = a.out.resolve() / uuid.uuid4().hex
    run.mkdir(parents=True)
    stage = run / 'game'
    stage.mkdir()
    for name in ('nectar.exe', 'SDL2.dll', 'libstdc++-6.dll', 'libgcc_s_seh-1.dll', 'libwinpthread-1.dll'):
        import shutil
        src = exe if name == 'nectar.exe' else exe.parent / name
        if not src.is_file():
            src = Path('C:/msys64/mingw64/bin') / name
        shutil.copy2(src, stage / name)
    env = dict(os.environ)
    for key in list(env):
        if key.startswith(('PIKMIN_', 'NECTAR_', 'BBFT_')):
            env.pop(key)
    env.update(PIKMIN_NETPLAY_STUN='none', PIKMIN_NETPLAY_ICE_BIND='127.0.0.1',
               PIKMIN_NETPLAY_UDP_BIND='127.0.0.1', PIKMIN_NETPLAY_DISCONNECT_MS='3000',
               PIKMIN_NETPLAY_BANNER_MS='10000', PIKMIN_P2_ROOM_WINDOW='960x540')
    if a.hidden:
        env.update(PIKMIN_RANDOMIZER_TEST_BACKGROUND='1', SDL_AUDIODRIVER='dummy')
    procs, logs, handles = [], [], []
    deadline = time.monotonic() + 120
    def contents(role):
        return (run / role / 'native.log').read_text(errors='replace')
    def wait(check, seconds, description):
        end = min(deadline, time.monotonic() + seconds)
        while time.monotonic() < end:
            if check():
                return
            if any(proc.poll() is not None for proc in procs):
                raise RuntimeError('A game closed before ' + description + '. See the private logs.')
            time.sleep(.1)
        raise RuntimeError('Timed out before ' + description + '. See the private logs.')
    def start(role, args):
        folder = run / role
        folder.mkdir()
        subprocess.run(['cmd', '/c', 'mklink', '/J', str(folder / 'assets'), str(assets)], check=True, capture_output=True)
        (folder / 'pikmin_settings.conf').write_text('windowMode = 0\nwindowWidth = 960\nwindowHeight = 540\n')
        local = dict(env)
        local['PIKMIN_NETPLAY_TEST_HUD_SHOT'] = str(folder)
        local['PIKMIN_STATE_HASH_LOG'] = str(folder / 'hashes.txt')
        f = (folder / 'native.log').open('w')
        handles.append(f)
        command = [str(stage / 'nectar.exe')] + args
        if a.hidden:
            command += ['--netplay-test-hidden', '--netplay-test-ticks', '10000']
        startup = subprocess.STARTUPINFO()
        startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startup.wShowWindow = 0
        proc = subprocess.Popen(command, cwd=folder, env=local, stdout=f, stderr=subprocess.STDOUT,
                                startupinfo=startup)
        procs.append(proc)
        logs.append(command)
        return proc
    result = dict(human_judgment='pending', method='scripted partner loss; no existing saves used',
                  executable_sha256=hashlib.sha256(exe.read_bytes()).hexdigest(), run=str(run))
    print('Fresh online co-op. Host: keyboard. Partner: first gamepad.')
    print('After connection, play briefly. The disposable partner will disconnect.')
    print('Read the host recovery screen: save status and what to do next should be clear.')
    try:
        host = start('host', ['--netplay-host-ice', '--netplay-code-out', str(run/'offer.txt'),
                              '--netplay-answer-in', str(run/'answer.txt'), '--netplay-input', 'keyboard'])
        wait(lambda: (run/'offer.txt').is_file(), 40, 'the host offer')
        join = start('join', ['--netplay-join-ice', '@'+str(run/'offer.txt'), '--netplay-code-out',
                              str(run/'answer.txt'), '--netplay-input', 'gamepad:0'])
        wait(lambda: all('[netplay] gekko session started' in contents(role) for role in ('host','join')), 40, 'both games connecting')
        result['both_connected'] = True
        print('Both players connected. Play now.')
        wait(lambda: all('START_STAGE' in contents(role) for role in ('host','join')), 30, 'gameplay')
        result['both_gameplay'] = True
        until = time.monotonic() + a.seconds
        wait(lambda: time.monotonic() >= until, a.seconds + 1, 'the smoke play interval')
        join.terminate()  # Only this invocation's disposable child.
        join.wait(10)
        end = time.monotonic() + 20
        while host.poll() is None and time.monotonic() < end:
            time.sleep(.1)
        text = contents('host')
        result['loss_banner'] = 'end banner: shown' in text and 'CONNECTION LOST' in text
        result['host_exit'] = host.poll()
        result['passed'] = result['loss_banner'] and host.poll() is not None
    except Exception as error:
        result.update(passed=False, error=str(error))
    finally:
        for proc in procs:
            if proc.poll() is None:
                proc.terminate()
            proc.wait(10)
        for handle in handles:
            handle.close()
        result['commands'] = logs
        (run/'result.json').write_text(json.dumps(result, indent=2))
        print('Private smoke result: ' + str(run/'result.json'))
    return 0 if result.get('passed') else 1


if __name__ == '__main__':
    raise SystemExit(main())
