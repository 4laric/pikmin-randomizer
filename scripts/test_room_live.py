"""Live two-slot room: real game as slot 1, headless runner as slot 2, hosted MultiServer.

Verifies against a real Archipelago server: slot authentication with slot_data, a native
check reaching the server, a remote item reaching the game, and a DeathLink Bounce from
slot 2 killing field Pikmin in slot 1's running game. Slot 2 has no executable, so its
native handshake and journals are written by this script.
"""
import argparse
import glob
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from randomizer.seed import validate
from randomizer.catalog import active_names


def wait_for(predicate, timeout, what):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        value = predicate()
        if value: return value
        time.sleep(0.25)
    raise AssertionError('timeout waiting for ' + what)


def main(args):
    out = args.room
    p1_manifest = json.loads(next(out.glob('*_P1_*.pikmin.json')).read_text(encoding='utf-8'))
    p2_manifest = json.loads(next(out.glob('*_P2_*.pikmin.json')).read_text(encoding='utf-8'))
    validate(p1_manifest); validate(p2_manifest)
    spoiler = next(out.glob('*_Spoiler.txt')).read_text(encoding='utf-8', errors='replace')
    # A slot-2 location holding a slot-1 item proves cross-slot delivery end to end.
    remote = None
    for line in spoiler.splitlines():
        m = re.match(r'(.+?) \(Player2\): (.+?) \(Player1\)$', line.strip())
        if m and m.group(1) in active_names(p2_manifest):
            remote = (m.group(1), m.group(2)); break
    assert remote, 'no Player2 location holds a Player1 item in this room'
    work = args.work; work.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, PIKMIN_RANDOMIZER_TEST_BACKGROUND='1', SDL_AUDIODRIVER='dummy', PYTHONUNBUFFERED='1'); env.pop('BBFT_PORT', None)
    root = Path(__file__).resolve().parents[1]
    procs = []
    try:
        p2 = subprocess.Popen([sys.executable, '-m', 'randomizer', 'run', str(next(out.glob('*_P2_*.pikmin.json'))), '--session-dir', str(work / 'p2'), '--server', args.server],
                              cwd=root, env=env, stdout=(work / 'p2.log').open('w'), stderr=subprocess.STDOUT)
        procs.append(p2)
        p1 = subprocess.Popen([sys.executable, '-m', 'randomizer', 'run', str(next(out.glob('*_P1_*.pikmin.json'))), '--session-dir', str(work / 'p1'), '--server', args.server,
                               '--exe', str(args.exe), '--assets', str(args.assets)], cwd=root, env=env, stdout=(work / 'p1.log').open('w'), stderr=subprocess.STDOUT)
        procs.append(p1)
        p2_run = Path(wait_for(lambda: next(iter(glob.glob(str(work / 'p2' / 'runs' / '*' / 'bootstrap.txt'))), None), 20, 'slot 2 run directory')).parent
        p1_run = Path(wait_for(lambda: next(iter(glob.glob(str(work / 'p1' / 'runs' / '*' / 'bootstrap.txt'))), None), 20, 'slot 1 run directory')).parent
        # Fake slot 2's native handshake so its runner accepts journals.
        (p2_run / 'hello.txt').write_text(' '.join(['PIKMIN_HELLO', str(p2_manifest['schema']), p2_run.name, json.loads((work / 'p2' / 'session.json').read_text())['fingerprint'] if (work / 'p2' / 'session.json').exists() else '', *p2_manifest['capabilities'], 'END']))
        fp2 = wait_for(lambda: json.loads((work / 'p2' / 'session.json').read_text()).get('fingerprint') if (work / 'p2' / 'session.json').exists() else None, 20, 'slot 2 session')
        (p2_run / 'hello.txt').write_text(' '.join(['PIKMIN_HELLO', str(p2_manifest['schema']), p2_run.name, fp2, *p2_manifest['capabilities'], 'END']))
        wait_for(lambda: json.loads((work / 'p2' / 'session.json').read_text()).get('ap_identity'), 30, 'slot 2 AP authentication')
        wait_for(lambda: 'PIKMIN_WORLD_RENDERED' in (p1_run / 'native.log').read_text(errors='replace') if (p1_run / 'native.log').exists() else False, 300, 'slot 1 world render')
        wait_for(lambda: json.loads((work / 'p1' / 'session.json').read_text()).get('ap_identity'), 30, 'slot 1 AP authentication')
        # 1. A native check from the real game reaches the server (landing exploration check).
        p1_checked = wait_for(lambda: json.loads((work / 'p1' / 'session.json').read_text())['checked'], 60, 'slot 1 native check')
        server_log = lambda: args.server_log.read_text(errors='replace') if args.server_log and args.server_log.exists() else ''
        wait_for(lambda: 'Player1' in server_log() and 'sent' in server_log(), 30, 'server to record slot 1 check')
        # 2. Slot 2 checks a location holding a slot-1 item; the game receives it.
        index = active_names(p2_manifest).index(remote[0])
        (p2_run / 'checks.txt').write_text(f'{index}\n')
        before = len(json.loads((work / 'p1' / 'session.json').read_text())['received'])
        wait_for(lambda: len(json.loads((work / 'p1' / 'session.json').read_text())['received']) > before, 30, 'slot 1 to receive the remote item')
        time.sleep(2)
        # 3. Slot 2 reaches its DeathLink threshold; the Bounce kills field Pikmin in slot 1's game.
        unit = p2_manifest['death_link_pikmin']
        (p2_run / 'deaths.txt').write_text(''.join(f'{i}\n' for i in range(1, unit + 1)))
        wait_for(lambda: json.loads((work / 'p1' / 'session.json').read_text()).get('death_links_received', 0) >= 1, 30, 'slot 1 to receive the DeathLink')
        line = wait_for(lambda: next((l for l in (p1_run / 'native.log').read_text(errors='replace').splitlines() if 'DEATHLINK_APPLIED' in l), None), 60, 'native DeathLink application')
        assert f'killed={p1_manifest["death_link_pikmin"]}' in line, line
        assert json.loads((work / 'p2' / 'session.json').read_text()).get('death_links_received', 0) == 0, 'slot 2 must not receive its own echo'
        print(f"PASS live room: both slots authenticated; slot 1 checked {p1_checked}; slot 2 sent {remote[1]} via {remote[0]}; {line.strip()}")
    finally:
        for proc in procs:
            if proc.poll() is None:
                subprocess.run(['taskkill', '/F', '/T', '/PID', str(proc.pid)], capture_output=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--room', type=Path, required=True, help='extracted AP output directory with *.pikmin.json and spoiler')
    p.add_argument('--server', default='localhost:38299')
    p.add_argument('--server-log', type=Path)
    p.add_argument('--exe', type=Path, required=True)
    p.add_argument('--assets', type=Path, required=True)
    p.add_argument('--work', type=Path, required=True)
    main(p.parse_args())
