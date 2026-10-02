"""Stage an ordinary White campaign; retain native Red5 pellet parameters."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import struct
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.audit_population_supply import pellet_configs
from scripts.preview_pikmin2_room import generator, records, overlay, prototype_routes, replace_embedded_routes


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def rewrite_generators(assets, retail_p2=False):
    source = generator(assets)
    starts = [m.start() for m in re.finditer(b'    0.0v', source)]
    rows = [source[a:(starts[i + 1] if i + 1 < len(starts) else len(source))] for i, a in enumerate(starts)]
    result = []
    count = 0
    for raw in rows:
        row = bytearray(raw)
        name = row[16:48].split(b'\0')[0]
        if name == b'preview dwarf bulborb':
            continue
        if row[72:76] == b'ikip':
            count += 1
            uid, xyz = count, None
        elif name == b'preview red onion':
            uid, xyz = 23, (-40, 0, 120)
        elif name == b'preview ship':
            uid, xyz = 24, (-40, 0, 0)
        elif name == b'preview treasure bolt':
            # Keep original generator model pr05. No altered retail carry/yield config.
            if row[80:84] != b'50rp':
                raise ValueError('Expected original native Red5 model')
            uid, xyz = 26, (170, 0, 200)
        else:
            raise ValueError('Unexpected generator template')
        struct.pack_into('<I', row, 8, uid)
        if xyz is not None:
            struct.pack_into('>3f', row, 48, *xyz)
        result.append(bytes(row))
    if count != 20:
        raise ValueError('Require canonical 20 original Red bodies')
    template = next(r for r in records(assets / 'dataDir/stages/chal0/default.gen') if r[72:80] == b'ssob\x02\x00\x00\x00')
    for uid, xyz, name in [(25, (-245, 0, -145), b'campaign ivory'), (27, (250, 0, 250), b'campaign violet')]:
        row = bytearray(template)
        row[16:48] = name.ljust(32, b'\0')
        struct.pack_into('<I', row, 8, uid)
        struct.pack_into('>6f', row, 48, *xyz, 0, 0, 0)
        struct.pack_into('>I', row, 80, 5 | (1 << 6))
        result.append(bytes(row))
    if retail_p2:
        ivory = next(r for r in result if struct.unpack_from('<I', r, 8)[0] == 25)
        for uid, xyz in [(28, (-245, 0, -45)), (29, (-145, 0, -145))]:
            row = bytearray(ivory)
            struct.pack_into('<I', row, 8, uid)
            struct.pack_into('>3f', row, 48, *xyz)
            result.append(bytes(row))
    return source[:20] + struct.pack('>I', len(result)) + b''.join(result)


def prepare(assets, white, purple, room, output, pod=None):
    assets, white, purple, room, output = map(Path, (assets, white, purple, room, output))
    if any(not p.is_dir() for p in (assets, white, purple, room)):
        raise ValueError('Explicit existing legal input directories required')
    if output.exists():
        raise ValueError('Fresh private output required')
    configs = assets / 'dataDir/parms/pelMgr.bin'
    retail = next(r for r in pellet_configs(configs.read_bytes()) if r['model_id'] == 'pr05')
    if (retail['carry_min'], retail['carrier_slots'], retail['matching_yield'], retail['other_yield']) != (5, 10, 5, 3):
        raise ValueError('Native retail Red5 contract changed; refuse staging')
    if pod is not None:
        pod = Path(pod)
        tokens = (pod / 'p2-pod.txt').read_text().split()
        if tokens != ['P2_POD_1', 'dia_a_red', '180', '15', '25', 'Kochappy', '2']:
            raise ValueError('Original P2 diamond descriptor required; engineering profile refused')
    data = rewrite_generators(assets, retail_p2=pod is not None)
    stage = (assets / 'dataDir/stages/practice.ini').read_bytes()
    stage = re.sub(rb'(?m)^map_file[^\r\n]*', b'map_file courses/pikmin2room/room.mod', stage)
    stage = re.sub(rb'(?m)^navi_start[^\r\n]*', b'navi_start -85.0 0.0', stage)
    routes = prototype_routes((room / 'room.ini').read_bytes())
    overrides = {'dataDir/stages/practice/default.gen': data, 'dataDir/stages/practice.ini': stage,
                 'dataDir/courses/pikmin2room/room.mod': replace_embedded_routes((room / 'room.mod').read_bytes(), routes),
                 'dataDir/courses/pikmin2room/room.ini': routes}
    empty = b'1.0v' + struct.pack('>4fI', -85, 0, 0, 45, 0)
    for file in (assets / 'dataDir/stages/practice').glob('*.gen'):
        overrides.setdefault('dataDir/stages/practice/' + file.name, empty)
    for bank in (white, purple):
        for file in bank.glob('*.mod'):
            key = 'dataDir/courses/pikmin2room/' + file.name
            if key in overrides:
                raise ValueError('Duplicate bank asset')
            overrides[key] = file.read_bytes()
    if pod is not None:
        for name in ('treasure.mod', 'pod.mod'):
            overrides['dataDir/courses/pikmin2room/' + name] = (pod / name).read_bytes()
    output.mkdir(parents=True)
    overlay(assets, output / 'assets', overrides)
    for name, bank in [('p2-white.txt', white), ('p2-purple.txt', purple)]:
        (output / name).write_bytes((bank / name).read_bytes())
    white_bindings = b'P2_WHITE_CAMPAIGN_1 3 0 25 0 28 0 29\n' if pod is not None else b'P2_WHITE_CAMPAIGN_1 1 0 25\n'
    (output / 'p2-white-campaign.txt').write_bytes(white_bindings)
    (output / 'p2-purple-campaign.txt').write_bytes(b'P2_PURPLE_CAMPAIGN_1 1 0 27\n')
    if digest(output / 'assets/dataDir/parms/pelMgr.bin') != digest(configs):
        raise ValueError('Retail config must remain byte-identical')
    files = [output / key for key in ('p2-white.txt', 'p2-purple.txt', 'p2-white-campaign.txt', 'p2-purple-campaign.txt')]
    files += [output / 'assets' / key for key in overrides]
    if pod is not None:
        (output / 'p2-pod.txt').write_bytes((pod / 'p2-pod.txt').read_bytes())
        source_hashes = [digest(pod / name) for name in ('p2-pod.txt', 'treasure.mod', 'pod.mod')]
        (output / 'p2-white-treasure-campaign.txt').write_text('P2_WHITE_TREASURE_CAMPAIGN_1 0 26 23 ' + ' '.join(source_hashes) + '\n')
        files += [output / 'p2-pod.txt', output / 'p2-white-treasure-campaign.txt']
    facts = {'schema': 1, 'issue': 1191, 'ordinary_campaign': True, 'room_preview': False,
             'stage_id': 0, 'stage': 'practice', 'original_red_uids': list(range(1, 21)), 'ivory_uid': 25, 'violet_uid': 27,
             'cargo_uid': 26, 'retail': retail, 'retail_source': str(configs.resolve()), 'retail_source_sha256': digest(configs),
             'engineering_cargo_override': False, 'P2_treasure_fidelity': False,
             'required_P2_retail': {'id': 'dia_a_red', 'value': 180, 'minimum': 15, 'maximum': 25, 'ivory_uids': [25, 28, 29], 'natural_white_target': 15, 'receiver_uid': 23, 'source_descriptor': str(pod.resolve()) if pod is not None else None, 'runtime_accepted': False} if pod is not None else None,
             'geometry': 'Inherited imported capped room with original prototype route rewrite; initial placement only, native contact/route remains acceptance gate',
             'hashes': {str(f.relative_to(output)): digest(f) for f in files},
             'runtime_accepted': False, 'sources': {k: str(p.resolve()) for k, p in [('assets', assets), ('white', white), ('purple', purple), ('room', room)]}}
    (output / 'white-campaign-inputs.json').write_text(json.dumps(facts, indent=2) + '\n')
    return output


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('assets', 'white', 'purple', 'room', 'output'):
        parser.add_argument('--' + name, required=True, type=Path)
    parser.add_argument('--pod', type=Path, help='Explicit original P2 diamond bank; absent gives additional P1 retail5 baseline')
    args = parser.parse_args()
    print(prepare(args.assets, args.white, args.purple, args.room, args.output, args.pod))
