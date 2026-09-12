"""Experimental two-floor checkpoint runner; not a mid-floor world save."""
import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import subprocess
import uuid

from randomizer.session import SessionLock, atomic_write
from scripts.preview_pikmin2_emergence import prepare

SPECIES = ('blue', 'red', 'yellow', 'purple')
EXIT_TRANSITION = 42


def squad_valid(squad):
    if not isinstance(squad, list) or len(squad) > 100:
        raise ValueError('Invalid cave squad')
    for p in squad:
        if (not isinstance(p, dict) or set(p) != {'species', 'maturity'}
                or p['species'] not in SPECIES or type(p['maturity']) is not int
                or not 0 <= p['maturity'] <= 2):
            raise ValueError('Invalid cave Pikmin')


def validate(state):
    if not isinstance(state, dict) or set(state) != {'schema', 'content', 'revision', 'status', 'floor', 'squad', 'health', 'receipts'}:
        raise ValueError('Invalid cave checkpoint fields')
    if state['schema'] != 1 or type(state['schema']) is not int:
        raise ValueError('Unsupported cave checkpoint')
    if not isinstance(state['content'], str) or len(state['content']) != 64 or any(c not in '0123456789abcdef' for c in state['content']):
        raise ValueError('Invalid cave content identity')
    if type(state['revision']) is not int or not 0 <= state['revision'] <= 2:
        raise ValueError('Invalid cave revision')
    if type(state['floor']) is not int or state['floor'] not in (1, 2) or state['status'] not in ('active', 'exited', 'failed'):
        raise ValueError('Invalid cave destination')
    squad_valid(state['squad'])
    if type(state['health']) not in (int, float) or not math.isfinite(state['health']) or not 0 <= state['health'] <= 1:
        raise ValueError('Invalid captain health')
    if state['status'] != 'failed' and (not state['squad'] or state['health'] <= 0):
        raise ValueError('Living cave checkpoint needs survivors')
    if state['status'] == 'failed' and state['squad']:
        raise ValueError('Failed cave checkpoint has survivors')
    expected = state['floor'] - 1 if state['status'] == 'active' else state['floor']
    if state['revision'] != expected or (state['status'] == 'exited' and state['floor'] != 2):
        raise ValueError('Invalid cave checkpoint phase')
    if not isinstance(state['receipts'], dict) or len(state['receipts']) > 1024:
        raise ValueError('Invalid cave receipts')
    for key, value in state['receipts'].items():
        if (not isinstance(key, str) or not key or len(key) > 100
                or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_:/-' for c in key)
                or type(value) is not int or not 0 <= value <= 1000000):
            raise ValueError('Invalid cave receipt')
    if sum(state['receipts'].values()) > 2147483647:
        raise ValueError('Cave balance overflow')
    return state


def initial(content):
    return validate(dict(schema=1, content=content, revision=0, status='active', floor=1,
                         squad=[dict(species='red', maturity=0) for _ in range(20)], health=1.0, receipts={}))


def load(path, content):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result: raise ValueError('Duplicate checkpoint field')
            result[key] = value
        return result
    state = validate(json.loads(path.read_text(encoding='utf-8'), object_pairs_hook=unique))
    if state['content'] != content:
        raise ValueError('Cave assets/layout changed; preserve this save and use its original bundle')
    return state


def ledger_text(receipts):
    return 'P2_ECONOMY_1\n' + ''.join(f'{k} {v}\n' for k, v in sorted(receipts.items()))


def read_ledger(path):
    lines = path.read_text().splitlines()
    if not lines or lines.pop(0) != 'P2_ECONOMY_1': raise ValueError('Invalid cave runtime ledger')
    result = {}
    for line in lines:
        words = line.split()
        if len(words) != 2 or words[0] in result: raise ValueError('Invalid/duplicate runtime receipt')
        result[words[0]] = int(words[1])
    return result


def entry_text(state, token):
    validate(state)
    return (f'P2_CAVE_ENTRY_1\n{token}\n{state["floor"]} {state["health"]:.9g} {len(state["squad"])}\n'
            + ''.join(f'{SPECIES.index(p["species"])} {p["maturity"]}\n' for p in state['squad']))


def transition(state, token, text, receipts, allowed):
    """Validate a single native boundary event before replacing the checkpoint."""
    validate(state)
    if state['status'] != 'active': raise ValueError('Cave already ended')
    lines = text.splitlines()
    if len(lines) < 3 or lines[0] != 'P2_CAVE_TRANSFER_1' or lines[1] != token:
        raise ValueError('Stale or incomplete cave transfer')
    words = lines[2].split()
    if len(words) != 3: raise ValueError('Invalid transfer header')
    floor, health, count = int(words[0]), float(words[1]), int(words[2])
    if floor != state['floor'] or not 0 <= count <= len(state['squad']) or len(lines) != 3 + count:
        raise ValueError('Invalid transfer floor/population')
    squad = []
    for line in lines[3:]:
        words = line.split()
        if len(words) != 2: raise ValueError('Invalid transfer Pikmin')
        color, maturity = map(int, words)
        if color not in range(len(SPECIES)): raise ValueError('Invalid transfer species')
        squad.append(dict(species=SPECIES[color], maturity=maturity))
    for key, value in state['receipts'].items():
        if receipts.get(key) != value: raise ValueError('Cave receipts regressed')
    for key, value in receipts.items():
        if key not in state['receipts'] and allowed.get(key) != value:
            raise ValueError('Unexpected cave receipt/value')
    before = Counter(p['species'] for p in state['squad'])
    after = Counter(p['species'] for p in squad)
    if any(after[c] > before[c] for c in SPECIES[:3]) or after['purple'] > before['purple'] + (10 if floor == 2 else 0):
        raise ValueError('Unexpected cave species increase')
    status = 'failed' if not squad or health <= 0 else 'active' if floor == 1 else 'exited'
    if status == 'failed': squad = []
    next_state = dict(state, revision=state['revision'] + 1, status=status,
                      floor=2 if status == 'active' else floor, health=health, squad=squad, receipts=dict(receipts))
    return validate(next_state)


def content_identity(imported, pods, purple, transitions=None):
    files = []
    for floor, unit in enumerate(('room_north_tutorial_1_snow', 'room_purple14x14_snow'), 1):
        for name in ('render.mod', 'collision.json'):
            files.append((f'floor{floor}/{name}', imported/'units'/unit/name))
    files.append(('import-manifest', imported/'manifest.json'))
    for i, pod in enumerate(pods, 1):
        for name in ('pod.mod', 'treasure.mod', 'p2-pod.txt'):
            files.append((f'pod{i}/{name}', pod/name))
    files.extend((f'purple/{p.name}', p) for p in sorted(purple.glob('*.mod')))
    files.append(('purple/config', purple/'p2-purple.txt'))
    digest = hashlib.sha256(b'P2_CAVE_LAYOUT_1:two-standalone-rooms:all-survivors:boundary-checkpoint')
    for label, path in files:
        digest.update(label.encode() + b'\0' + hashlib.sha256(path.read_bytes()).digest())
    for floor, data in sorted((transitions or {}).items()):
        digest.update(f'transition{floor}'.encode() + b'\0' + hashlib.sha256(data).digest())
    return digest.hexdigest()


def allowed_receipts(run, floor):
    words = (run/'p2-pod.txt').read_text().split()
    if len(words) != 7 or words[0] != 'P2_POD_1': raise ValueError('Unexpected Pod config')
    allowed = {f'treasure:{words[1]}': int(words[2])}
    # Native enemy generator identifiers are derived from the actual prepared file.
    from scripts.preview_pikmin2_room import records
    for row in records(run/'assets/dataDir/stages/chal0/default.gen'):
        if row[16:48].rstrip(b'\0') == b'preview dwarf bulborb':
            import struct
            allowed[f'corpse:floor{floor}:{struct.unpack_from("<I", row, 8)[0]}'] = int(words[6])
    return allowed


def run_campaign(assets, imported, pods, purple, treasure, exe, session, transitions=None):
    from experimental.pikmin2_transitions import read_transitions
    anchors = read_transitions(transitions)
    content = content_identity(imported, pods, purple, anchors)
    with SessionLock(session):
        checkpoint = session/'checkpoint.json'
        if checkpoint.exists(): state = load(checkpoint, content)
        else:
            if any(p.name != 'runner.lock' for p in session.iterdir()):
                raise ValueError('Checkpoint missing from an existing session; refusing to reset it')
            state = initial(content)
            atomic_write(checkpoint, json.dumps(state, indent=2))
        while state['status'] == 'active':
            floor = state['floor']
            run = prepare(assets, imported, treasure, session/'runs', floor=floor, pod=pods[floor-1],
                          purple=purple, violet=floor == 2, squad=state['squad'])
            token = uuid.uuid4().hex
            (run/'p2-cave-entry.txt').write_text(entry_text(state, token))
            if anchors:
                (run/'p2-cave-transition.txt').write_bytes(anchors[floor])
            (run/'p2-economy.txt').write_text(ledger_text(state['receipts']))
            allowed = allowed_receipts(run, floor)
            print(f'Emergence Cave — floor {floor}: {len(state["squad"])} Pikmin, {sum(state["receipts"].values())} Pokos.', flush=True)
            target = ('marked hole' if floor == 1 else 'marked geyser') if anchors else 'Pod'
            print(f'F6 near the {target}: descend/leave. Closing mid-floor restores this entry checkpoint.', flush=True)
            with (run/'native.log').open('w') as log:
                result = subprocess.run([str(exe), '--experimental-pikmin2-room'], cwd=run, stdout=log, stderr=subprocess.STDOUT)
            if result.returncode != EXIT_TRANSITION:
                print(f'Entry checkpoint preserved. Relaunch to resume floor {floor}. Log: {run / "native.log"}', flush=True)
                if result.returncode: raise RuntimeError(f'Native exit {result.returncode}')
                return state
            next_state = transition(state, token, (run/'p2-cave-transfer.txt').read_text(), read_ledger(run/'p2-economy.txt'), allowed)
            atomic_write(checkpoint, json.dumps(next_state, indent=2))
            state = next_state
        print(f'Cave {state["status"]}: {len(state["squad"])} survivors, {sum(state["receipts"].values())} Pokos. Result saved at {checkpoint}', flush=True)
        return state


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('assets', 'imported', 'pod1', 'pod2', 'purple', 'treasure', 'exe', 'session'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--transitions', type=Path, help='Optional floor1.txt/floor2.txt world markers; requires matching native renderer hook')
    args = parser.parse_args()
    run_campaign(args.assets.resolve(), args.imported.resolve(), [args.pod1.resolve(), args.pod2.resolve()],
                 args.purple.resolve(), args.treasure.resolve(), args.exe.resolve(), args.session.resolve(),
                 args.transitions.resolve() if args.transitions else None)
