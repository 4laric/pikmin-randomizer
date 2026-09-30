"""Explicit, private ordinary-campaign Purple assets and Violet supply."""
import hashlib
import json
import math
import re
import struct
from pathlib import Path

from .catalog import START_AREAS

STAGES = ('practice', 'stage1', 'stage2', 'stage3', 'last')


def bind_campaign_mode(session, manifest, bank, motion):
    """Reject reconnects that silently change species semantics or asset banks."""
    enabled = bank is not None
    if enabled != (motion is not None):
        raise ValueError('Purple campaign requires both --purple-bank and --purple-motion')
    marker = session / 'purple-campaign.json'
    if not enabled:
        if marker.exists():
            raise ValueError('This session requires its Purple campaign banks')
        return
    if not manifest.get('p2_layout'):
        raise ValueError('Purple campaign requires a P2 enemy seed')
    models, sidecars = bank_files(bank, motion)
    expected = {'version': 1, 'files': {name: hashlib.sha256(value).hexdigest()
                                      for name, value in {**models, **sidecars}.items()}}
    if marker.exists():
        if json.loads(marker.read_text(encoding='utf-8')) != expected:
            raise ValueError('Purple campaign banks differ from this session')
    else:
        if (session / 'runs').exists() and any((session / 'runs').iterdir()):
            raise ValueError('Purple opt-in requires a fresh session')
        from .session import atomic_write
        session.mkdir(parents=True, exist_ok=True)
        atomic_write(marker, json.dumps(expected, sort_keys=True) + '\n')


def split_records(data):
    starts = [m.start() for m in re.finditer(rb'(?:    |txen)0\.0v', data)]
    if (len(data) < 24 or data[:4] != b'1.0v' or not starts or starts[0] != 24
            or len(starts) != struct.unpack_from('>I', data, 20)[0]):
        raise ValueError('Unsupported campaign generator framing')
    return [data[a:b] for a, b in zip(starts, starts[1:] + [len(data)])]


def add_violet(data, template, generator_id, color=1):
    if color not in (0, 1, 2):
        raise ValueError('Invalid Violet legacy birth color')
    rows = split_records(data)
    if any(struct.unpack_from('<I', row, 8)[0] == generator_id for row in rows):
        raise ValueError('Violet generator identity already exists')
    if template[72:80] != b'ssob\x02\x00\x00\x00':
        raise ValueError('Expected version-two Boss generator template')
    # Use the landing origin from the ordinary generator, never a cave/preview origin.
    x, y, z = struct.unpack_from('>3f', data, 4)
    if not all(math.isfinite(value) for value in (x, y, z)):
        raise ValueError('Invalid landing origin')
    row = bytearray(template)
    row[:8] = b'    0.0v'
    # Generator::read uses readID (byte-swapped readInt), unlike numeric fields.
    struct.pack_into('<I', row, 8, generator_id)
    row[16:48] = b'campaign violet'.ljust(32, b'\0')
    struct.pack_into('>6f', row, 48, x + 100, y, z, 0, 0, 0)
    struct.pack_into('>I', row, 80, 5 | (color << 6))
    # Appending preserves all existing source byte offsets used by P2 enemy binding.
    return data[:20] + struct.pack('>I', len(rows) + 1) + data[24:] + bytes(row)


def bank_files(bank, motion):
    bank, motion = Path(bank), Path(motion)
    profile = (bank / 'p2-purple.txt').read_text(encoding='ascii')
    lines = profile.splitlines()
    if len(lines) < 5 or lines[0] != 'P2_PURPLE_1':
        raise ValueError('Invalid Purple profile')
    stats = lines[1].split()
    if len(stats) != 10 or stats[0] != 'stats' or any(not math.isfinite(float(v)) or not 0 <= float(v) <= 1000 for v in stats[1:]):
        raise ValueError('Invalid Purple stats')
    expected = {f'purple_happa_{i}.mod' for i in range(3)}
    attachments = set()
    for line, name in zip(lines[2:5], ('wait', 'walk', 'attack1')):
        fields = line.split()
        if len(fields) != 3 or fields[0] != name or not 1 <= int(fields[1]) <= 32 or not math.isfinite(float(fields[2])) or float(fields[2]) <= 0:
            raise ValueError('Invalid Purple clip')
        expected.update(f'purple_{name}_{i:02}.mod' for i in range(int(fields[1])))
        attachments.update((name, i) for i in range(int(fields[1])))
    seen = set()
    impact = False
    for line in lines[5:]:
        fields = line.split()
        if fields == ['impact', 'red_earthquake_v1'] and not impact:
            impact = True
            continue
        if len(fields) != 15 or fields[0] != 'happa':
            raise ValueError('Invalid Purple attachment row')
        key = (fields[1], int(fields[2]))
        if key not in attachments or key in seen or any(not math.isfinite(float(v)) for v in fields[3:]):
            raise ValueError('Invalid Purple attachment matrix')
        seen.add(key)
    if seen != attachments:
        raise ValueError('Incomplete Purple attachment bank')
    if not impact:
        profile = profile.rstrip() + '\nimpact red_earthquake_v1\n'
    from experimental.pikmin2_purple_motion import validate_profile, CLIPS
    motion_profile = validate_profile((motion / 'p2-purple-motion.txt').read_text(encoding='ascii'))
    for line, (_, count) in zip(motion_profile.splitlines()[1:3], CLIPS):
        fields = line.split()
        if len(fields) != 3 or abs(float(fields[2]) - count / 30) > 0.00001:
            raise ValueError('Invalid Purple motion duration')
    for line in motion_profile.splitlines()[1:]:
        values = line.split()[3:] if line.startswith('happa ') else line.split()[1:]
        if any(not math.isfinite(float(v)) for v in values):
            raise ValueError('Non-finite Purple motion data')
    models = {name: (bank / name).read_bytes() for name in sorted(expected)}
    models.update({f'purple_{name}_{i:02}.mod': (motion / f'purple_{name}_{i:02}.mod').read_bytes()
                   for name, count in CLIPS for i in range(count)})
    if any(not value for value in models.values()):
        raise ValueError('Empty Purple model')
    sidecars = {'p2-purple.txt': profile.encode('ascii'), 'p2-purple-motion.txt': motion_profile.encode('ascii'),
                'p2-purple-flight.txt': b'P2_PURPLE_FLIGHT_1\n'}
    return models, sidecars


def combat_profile(manifest):
    """Bind audited species to the seed's stable spawn-slot UID, not host type.

    Native resolves only live actors against its ENEMY_P2 mapping, so future
    stages and already defeated generators need not exist at setup time.
    """
    layout = manifest.get('p2_layout')
    if not isinstance(layout, dict) or not isinstance(layout.get('bindings'), list):
        raise ValueError('Purple combat requires P2 identity bindings')
    supported = {1: 'Kochappy', 2: 'Chappy'}
    bindings = {}
    seen = set()
    for row in layout['bindings']:
        uid_text = row.get('target')
        source = row.get('source_id')
        if not isinstance(uid_text, str) or not uid_text.isascii() or not uid_text.isdecimal():
            raise ValueError('Invalid Purple combat target UID')
        uid = int(uid_text)
        if not 0 < uid <= 0xffffffff or str(uid) != uid_text or uid in seen:
            raise ValueError('Duplicate or invalid Purple combat target UID')
        seen.add(uid)
        if type(source) is not int:
            raise ValueError('Invalid Purple combat species')
        if source in supported:
            if row.get('enum_name') != supported[source]:
                raise ValueError('Purple combat species identity mismatch')
            bindings[uid] = source
    if len(bindings) > 1024:
        raise ValueError('Too many Purple combat bindings')
    rows = [f'{uid} {source}' for uid, source in sorted(bindings.items())]
    return ('P2_PURPLE_DIRECT_2\nbindings ' + str(len(rows)) + '\n' +
            ''.join(row + '\n' for row in rows)).encode('ascii')


def stage_campaign(run, assets, bank, motion, manifest):
    """Layer over already staged P2 content without writing through a junction."""
    if not manifest.get('p2_layout'):
        raise ValueError('Purple campaign requires a P2 enemy seed')
    run, assets = Path(run).resolve(), Path(assets).resolve()
    models, sidecars = bank_files(bank, motion)
    sidecars['p2-purple-direct.txt'] = combat_profile(manifest)
    stage = START_AREAS[manifest['profile']][0]
    folder = STAGES[stage]
    base = run / 'assets'
    source = base if base.exists() else assets
    key = f'dataDir/stages/{folder}/default.gen'
    data = (source / key).read_bytes()
    template = next(row for row in split_records((assets / 'dataDir/stages/chal0/default.gen').read_bytes())
                    if row[72:80] == b'ssob\x02\x00\x00\x00')
    generator = 0x50555000 + stage
    # Check every scheduled source in the chosen stage, not just default.gen.
    for path in (source / f'dataDir/stages/{folder}').glob('*.gen'):
        if struct.pack('<I', generator) in path.read_bytes():
            raise ValueError('Reserved Violet identity occurs in stage source')
    overrides = {key: add_violet(data, template, generator, {"blue": 0, "red": 1, "yellow": 2}[manifest.get("starting_color", "red")])}
    overrides.update({f'dataDir/courses/pikmin2room/{name}': value for name, value in models.items()})
    if base.exists():
        source = run / 'purple-base-assets'
        base.rename(source)
    from scripts.preview_pikmin2_room import overlay
    overlay(source, base, overrides)
    sidecars['p2-purple-campaign.txt'] = f'P2_PURPLE_CAMPAIGN_1 1\n{stage} {generator}\n'.encode('ascii')
    for name, value in sidecars.items():
        (run / name).write_bytes(value)
    receipt = {'version': 1, 'stage': stage, 'generator': generator, 'placement': 'landing origin +100 x',
               'runtime_placement_verified': False,
               'sha256': {name: hashlib.sha256(value).hexdigest() for name, value in {**overrides, **sidecars}.items()}}
    (run / 'purple-campaign-staging.json').write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
    return receipt
