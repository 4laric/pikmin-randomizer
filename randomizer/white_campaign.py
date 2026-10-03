"""Opt-in White bank and Ivory supply for an ordinary campaign.

Supply placement is engineering placement near the source landing origin.
It requires native terrain/contact and gameplay acceptance independently.
"""
import hashlib
import json
import math
import struct
from pathlib import Path

from .catalog import START_AREAS
from .purple_campaign import STAGES, add_violet, split_records


def bank_files(bank):
    bank = Path(bank)
    profile = (bank / 'p2-white.txt').read_text(encoding='ascii')
    lines = profile.splitlines()
    if len(lines) < 6 or lines[0] != 'P2_WHITE_1':
        raise ValueError('Invalid White profile')
    stats = lines[1].split()
    if (len(stats) != 10 or stats[0] != 'stats'
            or any(not math.isfinite(float(v)) or not 0 <= float(v) <= 1000 for v in stats[1:])):
        raise ValueError('Invalid White stats')
    ids = lines[2].split()
    if (len(ids) < 3 or ids[0] != 'ivory_generators' or not ids[1].isdecimal()
            or int(ids[1]) != len(ids) - 2 or not 1 <= int(ids[1]) <= 32
            or any(not v.isascii() or not v.isdecimal() or not 0 < int(v) <= 0xffffffff for v in ids[2:])
            or len(set(map(int, ids[2:]))) != len(ids) - 2):
        raise ValueError('Invalid source Ivory identity list')
    expected = {f'white_happa_{i}.mod' for i in range(3)}
    attachments = set()
    for line, name in zip(lines[3:6], ('wait', 'walk', 'attack1')):
        fields = line.split()
        if (len(fields) != 3 or fields[0] != name or not fields[1].isascii()
                or not fields[1].isdecimal() or not 1 <= int(fields[1]) <= 32
                or not math.isfinite(float(fields[2])) or not 0 < float(fields[2]) <= 1000):
            raise ValueError('Invalid White clip')
        expected.update(f'white_{name}_{i:02}.mod' for i in range(int(fields[1])))
        attachments.update((name, i) for i in range(int(fields[1])))
    seen = set()
    for line in lines[6:]:
        fields = line.split()
        if len(fields) != 15 or fields[0] != 'happa' or not fields[2].isascii() or not fields[2].isdecimal():
            raise ValueError('Invalid White attachment row')
        key = (fields[1], int(fields[2]))
        if key not in attachments or key in seen or any(not math.isfinite(float(v)) for v in fields[3:]):
            raise ValueError('Invalid White attachment identity/matrix')
        seen.add(key)
    if seen != attachments:
        raise ValueError('Incomplete White attachments')
    models = {name: (bank / name).read_bytes() for name in sorted(expected)}
    if any(not value for value in models.values()):
        raise ValueError('Empty White model')
    return models, profile


def bind_campaign_mode(session, manifest, bank, treasure_bank=None):
    marker = Path(session) / 'white-campaign.json'
    enabled = manifest.get('p2_white_campaign') is True
    if (manifest.get('p2_white_treasure_campaign') is True) != (treasure_bank is not None):
        raise ValueError('Seed-bound White treasure bank required')
    if treasure_bank is not None and not enabled:
        raise ValueError('White treasure requires natural White campaign')
    if enabled != (bank is not None):
        raise ValueError('White manifest requires its explicit --white-bank; legacy seed cannot enable it')
    if not enabled:
        if marker.exists():
            raise ValueError('Existing session requires its White bank')
        return
    if not manifest.get('p2_layout') or manifest.get('p2_purple_campaign') is not True:
        raise ValueError('White requires the seed-bound P2/Purple campaign')
    treasure_enabled = manifest.get('p2_white_treasure_campaign') is True
    if treasure_enabled and manifest.get('starting_color', 'red') != 'red':
        raise ValueError('Original Red Pod receiver requires a Red-start White treasure seed')
    if treasure_enabled:
        from .white_treasure_campaign import bank_files as treasure_files
        treasure = treasure_files(treasure_bank)
    models, profile = bank_files(bank)
    expected = {'version': 1, 'supply': 'three-ivory-landing-v1',
                'sha256': {n: hashlib.sha256(v).hexdigest()
                           for n, v in {**models, 'p2-white.txt': profile.encode('ascii')}.items()}}
    if treasure_enabled:
        expected['treasure'] = {'profile': 'dia_a_red-180-15-25-v1',
                               'sha256': {n: hashlib.sha256(v).hexdigest() for n, v in treasure.items()}}
    if marker.exists():
        if json.loads(marker.read_text(encoding='utf-8')) != expected:
            raise ValueError('White bank differs from this session')
    else:
        if any((Path(session) / 'runs').glob('*')):
            raise ValueError('White opt-in requires a fresh session')
        from .session import atomic_write
        Path(session).mkdir(parents=True, exist_ok=True)
        atomic_write(marker, json.dumps(expected, sort_keys=True) + '\n')


def add_ivory_supply(data, template, stage, color):
    """Append three real Pom records; preserve original payload bytes/UIDs."""
    if type(stage) is not int or not 0 <= stage <= 4:
        raise ValueError('Invalid campaign stage')
    x, y, z = struct.unpack_from('>3f', data, 4)
    rows = split_records(data)
    ids = [0x57485400 + stage * 3 + i for i in range(3)]
    if any(struct.unpack_from('<I', row, 8)[0] in ids for row in rows):
        raise ValueError('Reserved Ivory identity already exists')
    result = data
    for uid, (dx, dz) in zip(ids, ((-100, 100), (0, 150), (100, 100))):
        result = add_violet(result, template, uid, color)
        parts = split_records(result)
        row = bytearray(parts[-1]); row[16:48] = b'campaign ivory'.ljust(32, b'\0')
        struct.pack_into('>3f', row, 48, x + dx, y, z + dz)
        result = result[:20] + struct.pack('>I', len(parts)) + b''.join(parts[:-1]) + bytes(row)
    assert result[24:24 + len(data) - 24] == data[24:]
    return result, ids


def stage_campaign(run, assets, bank, manifest, treasure_bank=None):
    if manifest.get('p2_white_campaign') is not True:
        raise ValueError('Explicit seed White campaign required')
    treasure_enabled = manifest.get('p2_white_treasure_campaign') is True
    if treasure_enabled != (treasure_bank is not None):
        raise ValueError('Seed-bound White treasure bank required')
    if treasure_enabled and manifest.get('starting_color', 'red') != 'red':
        raise ValueError('Original Red receiver requires a Red-start treasure seed')
    models, profile = bank_files(bank)
    run, assets = Path(run).resolve(), Path(assets).resolve()
    stage = START_AREAS[manifest['profile']][0]; folder = STAGES[stage]
    base = run / 'assets'; source = base if base.exists() else assets
    key = f'dataDir/stages/{folder}/default.gen'
    data = (source / key).read_bytes()
    template = next(row for row in split_records((assets / 'dataDir/stages/chal0/default.gen').read_bytes())
                    if row[72:80] == b'ssob\x02\x00\x00\x00')
    ids = [0x57485400 + stage * 3 + i for i in range(3)]
    for path in (source / f'dataDir/stages/{folder}').glob('*.gen'):
        if any(struct.pack('<I', uid) in path.read_bytes() for uid in ids):
            raise ValueError('Reserved Ivory identity occurs in scheduled stage source')
    data, ids = add_ivory_supply(data, template, stage, {'blue': 0, 'red': 1, 'yellow': 2}[manifest.get('starting_color', 'red')])
    treasure_sidecars = {}; treasure_facts = None
    if treasure_enabled:
        from .white_treasure_campaign import bank_files as treasure_files, append_cargo, sidecars as treasure_config
        treasure = treasure_files(treasure_bank)
        cargo_uid = 0x57545200 + stage
        for path in (source / f'dataDir/stages/{folder}').glob('*.gen'):
            if any(struct.unpack_from('<I', row, 8)[0] == cargo_uid for row in split_records(path.read_bytes())):
                raise ValueError('Reserved diamond identity occurs in scheduled source')
        cargo_template = next(row for row in split_records((assets / 'dataDir/stages/chal0/default.gen').read_bytes())
                              if row[72:76] == b'tlep')
        data, cargo_uid, receiver_uid = append_cargo(data, cargo_template, stage)
        treasure_sidecars = treasure_config(treasure, stage, cargo_uid, receiver_uid)
        models = {**models, **{name: treasure[name] for name in ('treasure.mod', 'pod.mod')}}
        treasure_facts = {'source_id': 'dia_a_red', 'value': 180, 'minimum': 15, 'maximum': 25,
                          'cargo_uid': cargo_uid, 'receiver_uid': receiver_uid,
                          'receiver_source_bytes_preserved': True,
                          'placement': 'source landing origin: (-225,+250)',
                          'terrain_contact_verified': False, 'physical_delivery_accepted': False,
                          'native_SAVE_resume_accepted': False}
    overrides = {key: data, **{f'dataDir/courses/pikmin2room/{n}': v for n, v in models.items()}}
    saved = run / 'white-base-assets'
    if saved.exists():
        raise ValueError('Existing White staged base; use a fresh run')
    if base.exists():
        base.rename(saved); source = saved
    from scripts.preview_pikmin2_room import overlay
    overlay(source, base, overrides)
    lines = profile.splitlines(); lines[2] = 'ivory_generators 3 ' + ' '.join(map(str, ids))
    sidecars = {'p2-white.txt': ('\n'.join(lines) + '\n').encode('ascii'),
                'p2-white-campaign.txt': ('P2_WHITE_CAMPAIGN_1 3\n' + ''.join(f'{stage} {uid}\n' for uid in ids)).encode('ascii')}
    sidecars.update(treasure_sidecars)
    for name, value in sidecars.items():
        (run / name).write_bytes(value)
    receipt = {'version': 1, 'stage': stage, 'generators': ids, 'budget_per_bud': 5,
               'engineering_placement': 'source landing origin: (-100,+100), (0,+150), (+100,+100)',
               'terrain_contact_verified': False, 'gameplay_accepted': False,
               'sha256': {n: hashlib.sha256(v).hexdigest() for n, v in {**overrides, **sidecars}.items()}}
    if treasure_facts is not None:
        receipt['treasure'] = treasure_facts
    (run / 'white-campaign-staging.json').write_text(json.dumps(receipt, indent=2) + '\n')
    return receipt
