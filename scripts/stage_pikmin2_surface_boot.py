"""Stage a bounded retail Valley entrance for the native surface boot seam (#738)."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import struct

from experimental.pikmin2_surface_import import verify_bundle
from experimental.pikmin2_convert import convert
from experimental.pikmin2_collision import attach_collision, route_ini
from experimental.pikmin2_entrance_pocket import CENTER, subset, validate_probes
from experimental.pikmin2_surface_physics import surface_mapcode
from scripts.stage_pikmin2_entrance import boundary_room
from scripts.preview_pikmin2_room import generator, overlay


def stage_table(data):
    if b'stages/p2_tutorial.ini' in data:
        raise ValueError('Surface stage is already registered')
    return data + b'\nnew_map visible {\n name "P2 tutorial entrance"\n id 0\n file stages/p2_tutorial.ini\n}\n'


def starting_squad(assets):
    data = generator(assets)
    starts = [m.start() for m in re.finditer(b'    0.0v', data)] + [len(data)]
    rows = []
    for a, b in zip(starts, starts[1:]):
        row = bytearray(data[a:b])
        if row[72:76] != b'ikip':
            continue
        i = len(rows)
        struct.pack_into('>3f', row, 48, CENTER[0]-12+(i%5)*6, CENTER[1], CENTER[2]-9+(i//5)*6)
        rows.append(bytes(row))
    if len(rows) != 20:
        raise ValueError('Expected current overlay baseline of twenty Pikmin')
    return b'1.0v' + struct.pack('>4fI', CENTER[0], CENTER[1], CENTER[2], 0, 20) + b''.join(rows)


def prepare(assets, bundle, identity, output):
    receipt = verify_bundle(bundle, identity)
    if receipt['course'] != 'tutorial':
        raise ValueError('Only the audited tutorial entrance is supported')
    if output.exists():
        raise ValueError('Refusing existing staging output')
    source = json.loads((bundle/'surface-geometry.json').read_text())
    water = json.loads((bundle/'surface-water.json').read_text())
    pocket = subset(source)
    probes = validate_probes(source, pocket, water['boxes'])
    room = boundary_room(pocket)
    # Render conversion retains the whole source BMD; only the declared entrance
    # has collision. The engineering wall forbids travel into unsupported terrain.
    output.mkdir(parents=True)
    convert(bundle/'arc/model.bmd', output/'surface-render.mod', approximate_materials=True)
    model = attach_collision((output/'surface-render.mod').read_bytes(), room, mapcode_translator=surface_mapcode)
    stage = (assets/'dataDir/stages/chal0.ini').read_bytes()
    stage = re.sub(rb'(?m)^map_file[^\r\n]*', b'map_file courses/p2tutorial/entrance.mod', stage)
    stage = re.sub(rb'(?m)^navi_start[^\r\n]*', b'navi_start -190.0 1160.0', stage)
    empty = b'1.0v'+struct.pack('>4fI', *CENTER, 0, 0)
    overrides = {'dataDir/stages/stages.ini': stage_table((assets/'dataDir/stages/stages.ini').read_bytes()),
                 'dataDir/stages/p2_tutorial.ini': stage,
                 'dataDir/stages/p2_tutorial/default.gen': starting_squad(assets),
                 'dataDir/courses/p2tutorial/entrance.mod': model,
                 'dataDir/courses/p2tutorial/entrance.ini': route_ini([]).encode()}
    for name in ('init.gen', 'plants.gen', 'day.gen'):
        overrides['dataDir/stages/p2_tutorial/'+name] = empty
    run = output/'run'
    run.mkdir()
    overlay(assets, run/'assets', overrides)
    (run/'surface-water.json').write_bytes((bundle/'surface-water.json').read_bytes())
    record = dict(schema=1, course='tutorial', receipt_identity=identity, full_course=False,
                  source_triangle_ids=pocket['source_triangle_ids'], probes=probes,
                  boundary=room['engineering_boundary'], starting_pikmin=20,
                  source_water_retained=True, pocket_water_overlap=False,
                  native_water_consumer=False, generator_schedules_imported=False,
                  routes_imported=False, static_materials_approximate=True,
                  stage='stages/p2_tutorial.ini', overlay_adoption='explicit current generator() twenty-red template',
                  files={name:hashlib.sha256(data).hexdigest() for name,data in overrides.items()})
    (run/'surface-boot-inputs.json').write_text(json.dumps(record, indent=2)+'\n')
    return run


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('assets', 'bundle', 'output'):
        parser.add_argument('--'+name, type=Path, required=True)
    parser.add_argument('--identity', required=True)
    args = parser.parse_args()
    print(prepare(args.assets.resolve(), args.bundle.resolve(), args.identity, args.output.resolve()))
