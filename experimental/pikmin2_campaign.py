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

SPECIES = ('blue', 'red', 'yellow', 'purple', 'white', 'bulbmin')
# Wire schema that first carries each species (native pc_p2_species_schema.h):
# v1 Blue/Red/Yellow/Purple, v2 + White, v3 + Bulbmin.
SPECIES_SCHEMA = {'blue': 1, 'red': 1, 'yellow': 1, 'purple': 1, 'white': 2, 'bulbmin': 3}
TRANSFER_PREFIX = 'P2_CAVE_TRANSFER_'
CHAIN_PREFIX = 'P2_CAVE_CHAIN '
EXIT_TRANSITION = 42
# Absolute floor-id ceiling, mirrors native P2CaveMaxFloors
# (pc_p2_cave_transfer.h). The supervisor additionally enforces each cave's
# own floor count through the `floors` parameter below (default 2 preserves
# the legacy Emergence loop byte-for-byte).
MAX_FLOORS = 16


def squad_valid(squad):
    if not isinstance(squad, list) or len(squad) > 100:
        raise ValueError('Invalid cave squad')
    for p in squad:
        if (not isinstance(p, dict) or set(p) != {'species', 'maturity'}
                or p['species'] not in SPECIES or type(p['maturity']) is not int
                or not 0 <= p['maturity'] <= 2):
            raise ValueError('Invalid cave Pikmin')


def validate(state, floors=2):
    if not isinstance(state, dict) or set(state) != {'schema', 'content', 'revision', 'status', 'floor', 'squad', 'health', 'receipts'}:
        raise ValueError('Invalid cave checkpoint fields')
    if type(floors) is not int or not 2 <= floors <= MAX_FLOORS:
        raise ValueError('Invalid cave floor count')
    if state['schema'] != 1 or type(state['schema']) is not int:
        raise ValueError('Unsupported cave checkpoint')
    if not isinstance(state['content'], str) or len(state['content']) != 64 or any(c not in '0123456789abcdef' for c in state['content']):
        raise ValueError('Invalid cave content identity')
    if type(state['revision']) is not int or not 0 <= state['revision'] <= floors:
        raise ValueError('Invalid cave revision')
    if type(state['floor']) is not int or not 1 <= state['floor'] <= floors or state['status'] not in ('active', 'exited', 'failed'):
        raise ValueError('Invalid cave destination')
    squad_valid(state['squad'])
    if type(state['health']) not in (int, float) or not math.isfinite(state['health']) or not 0 <= state['health'] <= 1:
        raise ValueError('Invalid captain health')
    if state['status'] != 'failed' and (not state['squad'] or state['health'] <= 0):
        raise ValueError('Living cave checkpoint needs survivors')
    if state['status'] == 'failed' and state['squad']:
        raise ValueError('Failed cave checkpoint has survivors')
    expected = state['floor'] - 1 if state['status'] == 'active' else state['floor']
    if state['revision'] != expected or (state['status'] == 'exited' and state['floor'] != floors):
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


def load(path, content, floors=2):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result: raise ValueError('Duplicate checkpoint field')
            result[key] = value
        return result
    state = validate(json.loads(path.read_text(encoding='utf-8'), object_pairs_hook=unique), floors)
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


def entry_schema(squad):
    """Earliest wire schema that can carry the whole squad (matches the native)."""
    return max([1] + [SPECIES_SCHEMA[p['species']] for p in squad])


def entry_text(state, token, floors=2):
    validate(state, floors)
    schema = entry_schema(state['squad'])
    text = (f'P2_CAVE_ENTRY_{schema}\n{token}\n{state["floor"]} {state["health"]:.9g} {len(state["squad"])}\n'
            + ''.join(f'{SPECIES.index(p["species"])} {p["maturity"]}\n' for p in state['squad']))
    if state['floor'] > 2:
        # Multi-floor identity link (issue #132): the native chained entry
        # parser consumes this; legacy readers reject it as trailing data.
        # Floors 1-2 emit byte-identical legacy text.
        text += f'{CHAIN_PREFIX}{state["floor"]} {state["revision"]}\n'
    return text


def transfer_schema(header):
    """Parse the P2_CAVE_TRANSFER_<schema> header the native wrote."""
    if not header.startswith(TRANSFER_PREFIX):
        raise ValueError('Stale or incomplete cave transfer')
    digits = header[len(TRANSFER_PREFIX):]
    if digits not in ('1', '2', '3'):
        raise ValueError('Unsupported cave transfer schema')
    return int(digits)


def transition(state, token, text, receipts, allowed, floors=2):
    """Validate a single native boundary event before replacing the checkpoint."""
    validate(state, floors)
    if state['status'] != 'active': raise ValueError('Cave already ended')
    lines = text.splitlines()
    if len(lines) < 3 or lines[1] != token:
        raise ValueError('Stale or incomplete cave transfer')
    schema = transfer_schema(lines[0])
    words = lines[2].split()
    if len(words) != 3: raise ValueError('Invalid transfer header')
    floor, health, count = int(words[0]), float(words[1]), int(words[2])
    if floor != state['floor'] or not 0 <= count <= len(state['squad']):
        raise ValueError('Invalid transfer floor/population')
    if floor < 1 or floor > floors:
        raise ValueError('Invalid transfer floor/population')
    body, rest = lines[3:3 + count], lines[3 + count:]
    chain_revision = None
    if rest:
        # Multi-floor identity link (issue #132): exactly one chain line
        # repeating the header floor. Anything else in the tail, including a
        # legacy reader's view of this payload, fails closed here; legacy
        # payloads have an empty tail and behave byte-identically.
        if len(rest) != 1: raise ValueError('Invalid transfer floor/population')
        words = rest[0].split()
        if len(words) != 3 or words[0] + ' ' != CHAIN_PREFIX:
            raise ValueError('Invalid transfer floor/population')
        try:
            chain_floor, chain_revision = int(words[1]), int(words[2])
        except ValueError:
            raise ValueError('Invalid transfer floor/population')
        if chain_floor != floor or chain_revision < 0:
            raise ValueError('Invalid transfer floor/population')
        if chain_revision != state['revision']:
            raise ValueError('Cave revision chain broken')
    if floor > 2 and chain_revision is None:
        # Mirror the native legacy parser, which caps unchained payloads at
        # floor 2: beyond floor 2 the chain line is mandatory, never optional.
        raise ValueError('Invalid transfer floor/population')
    squad = []
    for line in body:
        words = line.split()
        if len(words) != 2: raise ValueError('Invalid transfer Pikmin')
        color, maturity = map(int, words)
        if color not in range(len(SPECIES)): raise ValueError('Invalid transfer species')
        if SPECIES_SCHEMA[SPECIES[color]] > schema:
            raise ValueError('Cave transfer schema too old for species')
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
    status = 'failed' if not squad or health <= 0 else 'active' if floor < floors else 'exited'
    if status == 'failed': squad = []
    next_state = dict(state, revision=state['revision'] + 1, status=status,
                      floor=floor + 1 if status == 'active' else floor, health=health, squad=squad, receipts=dict(receipts))
    return validate(next_state, floors)


def content_identity(imported, pods, purple, transitions=None, snow=None, roster=None, visuals=None):
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
    if snow:
        files.extend((f'snow/{p.name}', p) for p in sorted(snow.glob('snow_*.mod')))
        files.extend((f'snow/{name}', snow/name) for name in ('snow.json', 'p2-snow.txt'))
    if roster:
        files.append(('roster/manifest', roster/'content.json'))
        files.extend((f'roster/{p.parent.name}/treasure.mod', p)
                     for p in sorted((roster/'treasures').glob('*/treasure.mod')))
    digest = hashlib.sha256(b'P2_CAVE_LAYOUT_1:two-standalone-rooms:all-survivors:boundary-checkpoint')
    if roster:
        from experimental.pikmin2_roster import POLICY
        digest.update((POLICY+':separate-cargo-instances:4+7-snow').encode('ascii'))
    for label, path in files:
        digest.update(label.encode() + b'\0' + hashlib.sha256(path.read_bytes()).digest())
    for floor, data in sorted((transitions or {}).items()):
        digest.update(f'transition{floor}'.encode() + b'\0' + hashlib.sha256(data).digest())
    for name, data in sorted((visuals or {}).items()):
        digest.update(f'transition-visual/{name}'.encode() + b'\0' + hashlib.sha256(data).digest())
    return digest.hexdigest()


def allowed_receipts(run, floor):
    words = (run/'p2-pod.txt').read_text().split()
    if len(words) != 7 or words[0] != 'P2_POD_1': raise ValueError('Unexpected Pod config')
    allowed = {f'treasure:{words[1]}': int(words[2])}
    if (run/'p2-cargo.txt').exists():
        from experimental.pikmin2_cargo import read_cargo
        allowed = {f'treasure:{row["instance"]}': row['value'] for row in read_cargo(run/'p2-cargo.txt')}
    # Native enemy generator identifiers are derived from the actual prepared file.
    from scripts.preview_pikmin2_room import records
    for row in records(run/'assets/dataDir/stages/chal0/default.gen'):
        if row[16:48].rstrip(b'\0') == b'preview dwarf bulborb':
            import struct
            allowed[f'corpse:floor{floor}:{struct.unpack_from("<I", row, 8)[0]}'] = int(words[6])
    return allowed


def run_campaign(assets, imported, pods, purple, treasure, exe, session, transitions=None, snow=None, roster=None, transition_assets=None):
    from experimental.pikmin2_transitions import read_transitions, read_visuals, install_visuals
    anchors = read_transitions(transitions)
    visuals = read_visuals(transition_assets)
    if visuals and not anchors:
        raise ValueError('Transition visuals require transition anchors')
    if roster and not snow:
        raise ValueError('Complete enemy roster requires Snow assets')
    content = content_identity(imported, pods, purple, anchors, snow, roster, visuals)
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
            if roster:
                from experimental.pikmin2_roster import install
                install(roster, run, floor, assets, imported)
            if snow:
                install_snow(snow, run)
            token = uuid.uuid4().hex
            (run/'p2-cave-entry.txt').write_text(entry_text(state, token))
            if anchors:
                (run/'p2-cave-transition.txt').write_bytes(anchors[floor])
            install_visuals(visuals, run, floor)
            (run/'p2-economy.txt').write_text(ledger_text(state['receipts']))
            allowed = allowed_receipts(run, floor)
            print(f'Emergence Cave — floor {floor}: {len(state["squad"])} Pikmin, {sum(state["receipts"].values())} Pokos.', flush=True)
            target = (('hole' if floor == 1 else 'geyser') if visuals else
                      ('marked hole' if floor == 1 else 'marked geyser')) if anchors else 'Pod'
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


def install_snow(imported, run):
    """Opt in the prepared dwarf-family actors, including an optional roster."""
    import struct
    from scripts.preview_pikmin2_room import records
    from experimental.pikmin2_enemy import install
    ids = [struct.unpack_from('<I', row, 8)[0]
           for row in records(run/'assets/dataDir/stages/chal0/default.gen')
           if row[16:48].rstrip(b'\0') == b'preview dwarf bulborb']
    if ids:
        install(imported, run, ids)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('assets', 'imported', 'pod1', 'pod2', 'purple', 'treasure', 'exe', 'session'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--transitions', type=Path, help='Optional floor1.txt/floor2.txt world markers; requires matching native renderer hook')
    parser.add_argument('--snow', type=Path, help='Opt-in source Snow Bulborb visuals on existing scaffold enemies')
    parser.add_argument('--roster', type=Path, help='All source treasures/enemy counts with deterministic engineering placements')
    parser.add_argument('--transition-assets', type=Path, help='Optional imported hole/geyser model bundle')
    args = parser.parse_args()
    run_campaign(args.assets.resolve(), args.imported.resolve(), [args.pod1.resolve(), args.pod2.resolve()],
                 args.purple.resolve(), args.treasure.resolve(), args.exe.resolve(), args.session.resolve(),
                 args.transitions.resolve() if args.transitions else None,
                 args.snow.resolve() if args.snow else None,
                 args.roster.resolve() if args.roster else None,
                 args.transition_assets.resolve() if args.transition_assets else None)
