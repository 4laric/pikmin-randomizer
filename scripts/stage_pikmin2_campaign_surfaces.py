"""Stage a four-course native travel candidate from pinned retail surface bundles."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import struct

from experimental.pikmin2_surface_import import verify_bundle
from experimental.pikmin2_surface_collision import attach_surface_collision
from experimental.pikmin2_collision import ground_height, plane, route_ini
from experimental.pikmin2_convert import convert
from scripts.preview_pikmin2_room import overlay, records
from scripts.stage_pikmin2_surface_boot import starting_squad

COURSES = ('tutorial', 'forest', 'yakushima', 'last')
NAMES = ('Valley of Repose', 'Awakening Wood', 'Perplexing Pool', 'Wistful Wild')
WATER_COUNTS = (3, 5, 8, 2)


def stage_table():
    # Replace the P1 story table: duplicate story IDs would pick a P1 destination.
    visible = ''.join(f'new_map visible {{\n name "{name}"\n id {i}\n file stages/p2_{course}.ini\n}}\n'
                      for i, (course, name) in enumerate(zip(COURSES, NAMES)))
    # PlayerState's initialized flags and native card codec require five linked
    # slots. The fifth is invisible bookkeeping, never a travel destination.
    return (visible+'new_map hidden {\n name "Reserved native save slot"\n id 4\n file stages/p2_unused.ini\n}\n').encode('ascii')


def mapcode(code):
    # Retain slope/bald semantics; P2 walk-sound attributes fall back to solid.
    # Exact water is supplied separately, never inferred from a sound nibble.
    if type(code) is not int or not 0 <= code < 128 or code & 15 not in (0,1,2,3,5,6,7,9):
        raise ValueError('Unsupported surface mapcode')
    return (((code >> 4) & 3) << 27) | ((not (code & 64)) << 25)


def native_geometry(source):
    # A zero-area source face has no collision plane. Keep the immutable source
    # intact and explicitly map every native face back to its source face ID.
    retained = []
    omitted = []
    declared = source.get('degenerate_triangles', [])
    for i, tri in enumerate(source['triangles']):
        if any(type(v) is not int or v < 0 or v >= len(source['vertices']) for v in tri):
            raise ValueError('Invalid source triangle index')
        try:
            plane(source['vertices'], tri)
        except ValueError:
            if i not in declared:
                raise
            omitted.append(i)
        else:
            if i in declared:
                raise ValueError('Source degeneracy inventory disagrees')
            retained.append(i)
    if omitted != declared:
        raise ValueError('Source degeneracy inventory disagrees')
    return dict(source, triangles=[source['triangles'][i] for i in retained],
                mapcodes=[source['mapcodes'][i] for i in retained]), retained, omitted


def landing(generators, room, boxes):
    actors = generators['defaultgen.txt']['actors']
    ships = [a for a in actors if a.get('item') == 'onyn' and a.get('onion_index') == 4]
    onions = [a for a in actors if a.get('item') == 'onyn' and a.get('onion_index') == 1]
    if len(ships) != 1 or not onions:
        raise ValueError('Expected original ship and Red Onion landing anchors')
    ship = ships[0]['effective_position']
    onion = min(onions, key=lambda a: sum((a['effective_position'][k]-ship[k])**2 for k in (0,2)))
    x, y, z = onion['effective_position']
    floor = ground_height(room['vertices'], room['triangles'], x, z, ceiling=y+100)
    if floor is None:
        raise ValueError('Landing anchor has no native floor')
    if any(b['min'][0]-30 <= x <= b['max'][0]+30 and b['min'][2]-30 <= z <= b['max'][2]+30
           and floor <= b['surface']-3 for b in boxes):
        raise ValueError('Red squad landing anchor intersects source water')
    return [x, floor+40, z]


def squad(assets, start, generators=None):
    data = bytearray(starting_squad(assets))
    struct.pack_into('>3f', data, 4, *start)
    rows = [m.start() for m in re.finditer(b'    0.0v', data)]
    if len(rows) != 20:
        raise ValueError('Twenty-Pikmin fixture baseline missing')
    for i, offset in enumerate(rows):
        struct.pack_into('>3f', data, offset+48, start[0]-12+(i%5)*6, start[1], start[2]-9+(i//5)*6)
    if generators is not None:
        # Explicit P1 landing infrastructure adapters. Native sunset/withdrawal
        # requires a ship/Onion; this is not a port of original P2 object behavior.
        templates = records(assets/'dataDir/stages/practice/default.gen')
        if templates[1][16:24] != b'red goal' or templates[3][16:24] != b'ufo goal':
            raise ValueError('Unsupported native landing templates')
        actors = generators['defaultgen.txt']['actors']
        ship = next(a for a in actors if a.get('item')=='onyn' and a.get('onion_index')==4)
        for uid, template, position in ((1,templates[1],[start[0],start[1]-40,start[2]]),
                                        (2,templates[3],ship['effective_position'])):
            row = bytearray(template)
            struct.pack_into('>I',row,8,uid)
            struct.pack_into('>6f',row,48,*position,0,0,0)
            data.extend(row)
        struct.pack_into('>I',data,20,22)
    return bytes(data)


def prepare(assets, bundles, output):
    if set(bundles) != set(COURSES):
        raise ValueError('All four pinned courses are required')
    if output.exists():
        raise ValueError('Refusing existing staging output')
    # Validate every source before conversion or creation of a runnable overlay.
    for course, (bundle, pin) in bundles.items():
        if verify_bundle(bundle, pin)['course'] != course:
            raise ValueError('Source bundle course mismatch')
    output.mkdir(parents=True)
    overrides = {'dataDir/stages/stages.ini': stage_table()}
    records = {}
    for i, course in enumerate(COURSES):
        bundle, pin = bundles[course]
        source = json.loads((bundle/'surface-geometry.json').read_text(encoding='utf8'))
        room, retained, omitted = native_geometry(source)
        boxes = json.loads((bundle/'surface-water.json').read_text())['boxes']
        if len(boxes) != WATER_COUNTS[i]:
            raise ValueError('Course source water count mismatch')
        actors = json.loads((bundle/'surface-generators.json').read_text(encoding='utf8'))
        start = landing(actors, room, boxes)
        render = output/f'{course}-render.mod'
        convert(bundle/'arc/model.bmd', render, approximate_materials=True, bake_rigid=True, missing_normals="compute")
        model, topology = attach_surface_collision(render.read_bytes(), room, mapcode_translator=mapcode)
        course_dir = f'dataDir/courses/p2{course}/full'
        stage = (assets/'dataDir/stages/chal0.ini').read_bytes()
        stage = re.sub(rb'(?m)^map_file[^\r\n]*', f'map_file courses/p2{course}/full.mod'.encode(), stage)
        stage = re.sub(rb'(?m)^navi_start[^\r\n]*', f'navi_start {start[0]} {start[2]}'.encode(), stage)
        overrides[f'dataDir/stages/p2_{course}.ini'] = stage
        overrides[course_dir+'.mod'] = model
        overrides[course_dir+'.ini'] = route_ini(room['routes']).encode()
        water = [f'P2_SURFACE_WATER_1 {course} {len(boxes)}']
        for b in boxes:
            water.append(str(b['id'])+' '+' '.join(format(v,'.9g') for v in b['min']+b['max']+[b['surface'],0]))
        overrides[course_dir+'.water'] = ('\n'.join(water)+'\n').encode()
        gen_dir = f'dataDir/stages/p2_{course}/'
        overrides[gen_dir+'default.gen'] = squad(assets, start, actors)
        for name in ('init.gen','plants.gen','day.gen'):
            overrides[gen_dir+name] = b'1.0v'+struct.pack('>4fI',*start,0,0)
        records[course] = dict(identity=pin, stage_id=i, landing=start, source_faces=len(source['triangles']),
                               native_faces=len(retained), native_to_source_faces=retained,
                               multi_incident_edges=len(topology["multi_incident_edges"]),
                               omitted_zero_area_source_faces=omitted, water_boxes=len(boxes),
                               starting_pikmin=20, native_landing_adapters='P1 Red Onion/ship at source anchors',
                               material_fidelity='approximate', retail_actors=False)
    run = output/'run'
    run.mkdir()
    overlay(assets,run/'assets',overrides)
    record = dict(schema=1, courses=records, story_progression=False, full_campaign_accepted=False,
                  fixture_squad_per_first_visit=True, fresh_process_resume=False,
                  files={name:hashlib.sha256(data).hexdigest() for name,data in overrides.items()})
    (run/'campaign-surface-inputs.json').write_text(json.dumps(record,indent=2)+'\n')
    (run/'TRAVEL_ACCEPTANCE.txt').write_text(
        'Four-course terrain travel candidate. Retail actors and story unlocks are pending.\n'
        'Start with --experimental-pikmin2-campaign tutorial from this run directory.\n'
        'Check centered 960x540 window, live twenty-red squad and terrain movement.\n'
        'Press Enter for pause; use W/S for Go to Sunset and Space to confirm.\n'
        'Use W/S and Space in the course menu (controller main stick and A).\n'
        'Check its name/terrain, live squad and P2_SURFACE_TRAVEL log.\n'
        'Repeat a previously visited course. Preserve logs and native card saves.\n'
        'This candidate does not establish fresh-process campaign resume.\n')
    return run


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--assets',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    for course in COURSES:
        parser.add_argument('--'+course,type=Path,required=True)
        parser.add_argument('--'+course+'-identity',required=True)
    args = parser.parse_args()
    bundles = {c:(getattr(args,c).resolve(),getattr(args,c+'_identity')) for c in COURSES}
    print(prepare(args.assets.resolve(),bundles,args.output.resolve()))

