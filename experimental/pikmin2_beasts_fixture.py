"""Private traversal/carry harness for the authored Hole of Beasts assembly."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import struct
import subprocess
import uuid

from experimental.pikmin2_collision import ground_height
from scripts.preview_pikmin2_room import generator, overlay

WALK = [(200, 0), (425, 0), (510, 0), (595, 0), (820, 0), (1020, 0)]


def placements(room):
    def grounded(x, z):
        y = ground_height(room['vertices'], room['triangles'], x, z)
        if y is None: raise ValueError('Fixture position lacks ground')
        return [x, y, z]
    result = {'start': grounded(-100, 0), 'pod': grounded(-200, 0),
              'ship': grounded(0, -200), 'cargo': grounded(1020, 0),
              'squad': [grounded(-120 + (i % 5)*12, 60 + (i // 5)*12) for i in range(20)],
              'walk': [grounded(x, z) for x, z in WALK]}
    return result


def prepare(assets, assembly, pod, output):
    manifest = json.loads((assembly/'assembly.json').read_text())
    if manifest.get('schema') != 1 or manifest.get('cave') != 'forest_1' or not manifest.get('assembled'):
        raise ValueError('Expected authored Hole of Beasts assembly')
    for name in ('room.mod', 'room.ini', 'collision.json'):
        if hashlib.sha256((assembly/name).read_bytes()).hexdigest() != manifest['output_sha256'][name]:
            raise ValueError('Assembly output hash mismatch: '+name)
    config = (pod/'p2-pod.txt').read_text().split()
    if config != ['P2_POD_1', 'dia_a_red', '180', '15', '25', 'Kochappy', '2']:
        raise ValueError('Fixture requires source Citrus economy config')
    room = json.loads((assembly/'collision.json').read_text())
    plan = placements(room)
    raw = generator(assets)
    starts = [m.start() for m in re.finditer(b'    0.0v', raw)] + [len(raw)]
    entries = []; piki = 0
    for a, b in zip(starts, starts[1:]):
        entry = bytearray(raw[a:b]); label = bytes(entry[16:48]).rstrip(b'\0')
        if label == b'preview dwarf bulborb': continue
        if label == b'preview red pikmin': pos = plan['squad'][piki]; piki += 1
        else:
            key = {b'preview red onion': 'pod', b'preview ship': 'ship', b'preview treasure bolt': 'cargo'}.get(label)
            if key is None: raise ValueError('Unexpected scaffold actor')
            pos = plan[key]
        struct.pack_into('>3f', entry, 48, *pos); entries.append(entry)
    if piki != 20 or len(entries) != 23: raise ValueError('Unexpected fixture actor counts')
    actors = b'1.0v'+struct.pack('>4fI', *plan['start'], 45, len(entries))+b''.join(entries)
    stage = (assets/'dataDir/stages/chal0.ini').read_bytes()
    stage = re.sub(rb'(?m)^map_file[^\r\n]*', b'map_file courses/pikmin2room/room.mod', stage)
    stage = re.sub(rb'(?m)^navi_start[^\r\n]*', b'navi_start -100.0 0.0', stage)
    overrides = {'dataDir/stages/chal0.ini': stage, 'dataDir/stages/chal0/default.gen': actors}
    for name in ('room.mod', 'room.ini'): overrides['dataDir/courses/pikmin2room/'+name] = (assembly/name).read_bytes()
    for name in ('pod.mod', 'treasure.mod'): overrides['dataDir/courses/pikmin2room/'+name] = (pod/name).read_bytes()
    empty = b'1.0v'+struct.pack('>4fI', *plan['start'], 45, 0)
    for path in (assets/'dataDir/stages/chal0').glob('*.gen'):
        overrides.setdefault('dataDir/stages/chal0/'+path.name, empty)
    run = output.resolve()/uuid.uuid4().hex; run.mkdir(parents=True)
    overlay(assets, run/'assets', overrides)
    (run/'p2-pod.txt').write_bytes((pod/'p2-pod.txt').read_bytes())
    (run/'p2-second-floor.txt').write_text(str(len(WALK))+'\n'+'\n'.join(f'{x} {z}' for x, z in WALK))
    probes = [plan[k] for k in ('start', 'pod', 'cargo')] + [plan['walk'][2]]
    (run/'p2-ground.txt').write_text(' '.join(str(p[1]) for p in probes))
    (run/'p2-probe-positions.txt').write_text('\n'.join(f'{p[0]} {p[2]}' for p in probes))
    report = dict(schema=1, cave='forest_1', engineering=True, retail_generation=False,
        source_assembly=manifest, placements=plan, cargo='Citrus Lump borrowed as test cargo; not retail Hole of Beasts roster',
        fixture_mode='p2-second-floor: generic waypoint/cargo-only harness, not cave floor identity',
        native_validated=False, override_sha256={k: hashlib.sha256(v).hexdigest() for k,v in sorted(overrides.items())},
        limitations=['No enemies, retail roster, lifecycle, or live save.', 'Native harness assigns transport action directly; locomotion and hauling use native physics.'])
    (run/'fixture.json').write_text(json.dumps(report, indent=2)+'\n')
    return run


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('assets', 'assembly', 'pod', 'output'): parser.add_argument('--'+name, type=Path, required=True)
    parser.add_argument('--exe', type=Path)
    args = parser.parse_args()
    run = prepare(args.assets.resolve(), args.assembly.resolve(), args.pod.resolve(), args.output)
    print(run, flush=True)
    if args.exe:
        with (run/'native.log').open('w') as log:
            result = subprocess.run([str(args.exe.resolve()), '--experimental-pikmin2-room'], cwd=run, stdout=log, stderr=subprocess.STDOUT, timeout=240)
        if result.returncode: raise SystemExit(f'Native fixture failed ({result.returncode}): {run / "native.log"}')
        if 'PASS p2 second floor:' not in (run/'native.log').read_text(): raise SystemExit('Missing cargo-only fixture completion evidence')
        report = json.loads((run/'fixture.json').read_text())
        report['native_validated'] = True
        report['validation'] = {'binary_sha256': hashlib.sha256(args.exe.read_bytes()).hexdigest(),
            'log_sha256': hashlib.sha256((run/'native.log').read_bytes()).hexdigest(),
            'mode': 'controller traversal and native delivery; direct action assignment; no per-seam cargo trace'}
        (run/'fixture.json').write_text(json.dumps(report, indent=2)+'\n')
        print('Native traversal and cargo delivery passed; see native.log', flush=True)


if __name__ == '__main__': main()
