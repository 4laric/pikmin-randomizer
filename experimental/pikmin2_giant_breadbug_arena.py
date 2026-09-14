"""Private original Impact Site Giant Breadbug actor arena (#220 batch 4).

Stages one P1 TEKI_Collec8 generator bound as the Giant Breadbug actor and one
P1 TEKI_Hollec12 generator as its owner-linked nest, on the original practice
map, with the batch-4 actor profile installed. The fixture writes
`giant-arena.txt` (ids + expected birth XYZ) for the native fixture to check.
"""
import hashlib
import json
import struct
import uuid
from pathlib import Path

from scripts.preview_pikmin2_room import records, generator, overlay
from experimental.pikmin2_generator_pose import write_position, validate_position
from experimental.pikmin2_uji_grounded_fixture import deterministic_births
from experimental.pikmin2_giant_breadbug_actor import install

GIANT_ID = 187001
NEST_ID = 187002
GIANT_POS = (-150., 30., 1850.)
NEST_POS = (-150., 30., 1650.)
IDS = (GIANT_ID, NEST_ID)


def prepare(assets, profile, purple, pod, output):
    if not (purple / 'p2-purple.txt').is_file() or not sorted(purple.glob('purple_*.mod')):
        raise ValueError('Missing Purple bank')
    if not (pod / 'pod.mod').is_file():
        raise ValueError('Missing Research Pod model')
    source = assets / 'dataDir/stages/practice/default.gen'
    data = source.read_bytes()
    entries = records(source)
    used = {struct.unpack_from('<I', r, 8)[0] for r in entries}
    if used.intersection(IDS):
        raise ValueError('Arena generator identity collision')
    template = generator(assets)
    starts = [i for i in range(len(template)) if template.startswith(b'    0.0v', i)]
    candidates = [template[a:(starts[i + 1] if i + 1 < len(starts) else len(template))]
                  for i, a in enumerate(starts)]
    enemy = next(r for r in candidates if r[72:76] == b'iket')
    for identity, xyz, type_byte, label in (
            (GIANT_ID, GIANT_POS, 8, 'GiantBreadbug'), (NEST_ID, NEST_POS, 12, 'GiantNest')):
        row = bytearray(enemy)
        struct.pack_into('<I', row, 8, identity)
        row[80] = type_byte
        row[16:48] = f'{label} {identity}'.encode().ljust(32, b'\0')
        write_position(row, xyz)
        validate_position(row, xyz)
        entries.append(bytes(row))
    data = data[:20] + struct.pack('>I', len(entries)) + b''.join(entries)
    run = output.resolve() / uuid.uuid4().hex
    run.mkdir(parents=True)
    overrides = {'dataDir/stages/chal0.ini': (assets / 'dataDir/stages/practice.ini').read_bytes(),
                 'dataDir/stages/chal0/default.gen': data,
                 'dataDir/courses/pikmin2room/private-arena.txt': b'Giant Breadbug actor arena\n'}
    for p in (assets / 'dataDir/stages/chal0').glob('*.gen'):
        overrides.setdefault('dataDir/stages/chal0/' + p.name, data[:20] + struct.pack('>I', 0))
    overlay(assets, run / 'assets', overrides)
    for path in sorted(purple.glob('*.mod')):
        (run / 'assets/dataDir/courses/pikmin2room' / path.name).write_bytes(path.read_bytes())
    (run / 'p2-purple.txt').write_bytes((purple / 'p2-purple.txt').read_bytes())
    (run / 'p2-pod.txt').write_text('P2_POD_1\ncargo_free 0 1 1\nKochappy 0\n', encoding='utf-8')
    (run / 'assets/dataDir/courses/pikmin2room/pod.mod').write_bytes((pod / 'pod.mod').read_bytes())
    birth = deterministic_births(run / 'assets/dataDir/stages/chal0/default.gen', list(IDS))
    install(profile, run, [(GIANT_ID, NEST_ID)])
    (run / 'p2-cargo-free.txt').write_bytes(b'P2_CARGO_FREE_1\n')
    (run / 'giant-arena.txt').write_text(
        f'{GIANT_ID} {NEST_ID}\n'
        + ' '.join(map(str, GIANT_POS)) + '\n'
        + ' '.join(map(str, NEST_POS)) + '\n', encoding='utf-8')
    preserved = {}
    for path in (assets / 'dataDir/courses/practice').rglob('*'):
        if path.is_file():
            rel = path.relative_to(assets)
            raw = path.read_bytes()
            if (run / 'assets' / rel).read_bytes() != raw:
                raise ValueError('Original map changed')
            preserved[str(rel)] = hashlib.sha256(raw).hexdigest()
    result = dict(scene='original P1 Impact Site', giant=GIANT_ID, nest=NEST_ID,
                  giant_position=GIANT_POS, nest_position=NEST_POS, birth=birth,
                  preserved=preserved, native_validated=False)
    (run / 'giant-breadbug-arena.json').write_text(json.dumps(result, indent=2) + '\n',
                                                   encoding='utf-8')
    return run
