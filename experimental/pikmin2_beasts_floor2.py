"""Cargo-free source staging; runtime acceptance is recorded separately by #263."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import struct
import uuid

from experimental.pikmin2_collision import attach_collision, ground_height, route_ini
from scripts.preview_pikmin2_room import generator, overlay, records
from experimental.pikmin2_generator_pose import write_position, validate_position

UNIT = 'room_cent2_4_tsuchi'
POLICY = 'P2_BEASTS_FLOOR2_PREPARE_3'
GENERATION_POLICY = 'P2_BEASTS_FLOOR2_GENERATION_1'
CARGO_FREE_CONFIG = b'P2_CARGO_FREE_1\n'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def generation_context(global_purple_count):
    """Story forest_1 floor 2 only; caller supplies the historical birth snapshot."""
    if type(global_purple_count) is not int or not 0 <= global_purple_count <= 2147483647:
        raise ValueError('Explicit nonnegative int32 global-plus-cave Purple count required')
    ids = [62000,62001] if global_purple_count < 20 else []
    return dict(schema=1,cave='forest_1',floor=2,mode='story',
                global_plus_cave_purple=global_purple_count,context_source='caller_supplied_generation_snapshot',
                native_global_population_verified=False,spawned_generators=ids,
                conversion_budgets={f'forest_1:floor2:BlackPom:{i}':5 for i in range(len(ids))},
                source_rule='Pom::Mgr::birth: story cave, zero-based floor < 2, Purple global+cave >= 20')


def source_floor(catalog):
    caves = [c for c in catalog['caves'] if c['cave_id'] == 'forest_1']
    if len(caves) != 1: raise ValueError('Expected one forest_1 definition')
    floors = [f for f in caves[0]['floors'] if f['first_floor'] <= 2 <= f['last_floor']]
    if len(floors) != 1: raise ValueError('Ambiguous floor two')
    f = floors[0]
    expected = [('BlackPom', 2, 8), ('HikariKinoko', 6, 6), ('KareOoinu_s', 2, 6)]
    actual = [(e['enemy_id'], e.get('minimum_count', e.get('target_count')), e['placement_type']) for e in f['enemies']]
    caps = f['caps']
    if actual != expected or f['treasures'] or f['gates'] or len(caps) != 1 or caps[0]['empty']:
        raise ValueError('Unexpected floor-two roster')
    egg = caps[0]['enemy']
    if (egg['enemy_id'], egg['minimum_count'], egg['placement_type']) != ('Egg', 2, 1):
        raise ValueError('Unexpected cap population')
    if any(e.get('selection_weight', 0) or e.get('carried_treasure') for e in f['enemies'] + [egg]):
        raise ValueError('Weighted or treasure-bearing roster not supported')
    p = f['parameters']
    if f['definition_index'] != 1 or p['f008'] != '1_units_cent2_tsuchi.txt' or p['f007'] != '0' or p['f010'] != '0':
        raise ValueError('Unexpected floor-two unit/exit definition')
    return f


def flower_plan(room):
    candidates = [(i, s) for i, s in enumerate(room['spawns']) if s['type'] == 8]
    if len(candidates) != 2: raise ValueError('Expected two source Violet candidates')
    result = []
    for index, (slot, s) in enumerate(candidates):
        x, y, z = s['position']
        ground = ground_height(room['vertices'], room['triangles'], x, z)
        if ground is None or abs(ground-y) > .1: raise ValueError('Source flower lacks matching ground')
        result.append(dict(generator_id=62000+index, instance_id=f'forest_1:floor2:BlackPom:{index}',
                           definition_id='forest_1:definition1:enemy:0', source_slot=slot,
                           source=s, position=[x, ground, z], yaw=s['angle'],source_yaw_applied=False,
                           implementation='Existing P1 Pom with explicit P2 Violet conversion metadata; proxy'))
    return result


def decode_no_cargo(raw,expected_flowers=2):
    if type(expected_flowers) is not int or expected_flowers not in (0,2):raise ValueError('Expected zero or two flowers')
    if len(raw)<24:raise ValueError('Truncated generator header')
    starts = [m.start() for m in re.finditer(b'    0.0v', raw)] + [len(raw)]
    entries = [raw[a:b] for a, b in zip(starts, starts[1:])]
    if raw[:4] != b'1.0v' or len(entries) != struct.unpack_from('>I', raw, 20)[0]:
        raise ValueError('Generator framing mismatch')
    allowed = {b'preview red onion', b'preview ship', b'preview red pikmin', b'preview violet 0', b'preview violet 1'}
    labels = [e[16:48].rstrip(b'\0') for e in entries]
    if any(label not in allowed for label in labels) or any(b'pr05' in e or b'50rp' in e for e in entries):
        raise ValueError('Unexpected actor or hidden cargo')
    flowers = [e for e in entries if e[16:48].startswith(b'preview violet ')]
    if len(flowers) != expected_flowers or len(entries) != 22+expected_flowers or labels.count(b'preview red pikmin') != 20 or labels.count(b'preview red onion')!=1 or labels.count(b'preview ship')!=1:
        raise ValueError('Expected twenty squad, two anchors and selected flowers')
    if [struct.unpack_from('<I', e, 8)[0] for e in flowers] != ([62000,62001] if expected_flowers else []):
        raise ValueError('Flower native identity mismatch')
    if any(e[72:80] != b'ssob\x02\x00\x00\x00' or struct.unpack_from('>I', e, 80)[0] != 69 for e in flowers):
        raise ValueError('Flower conversion metadata mismatch')
    for e in flowers:validate_position(e,struct.unpack_from('>3f',e,48))
    return dict(actors=len(entries), flowers=expected_flowers, cargo=0, allowed_receipts=[])


def prepare(assets, units, catalog_path, purple, output, *, pod=None,global_purple_count=None):
    context=generation_context(global_purple_count) if global_purple_count is not None else None
    pod_model = (pod/'pod.mod').read_bytes() if pod is not None else None
    if pod_model is not None and not pod_model: raise ValueError('Empty Research Pod model')
    catalog_raw = catalog_path.read_bytes(); catalog = json.loads(catalog_raw)
    floor = source_floor(catalog)
    imported = json.loads((units/'units.json').read_text())
    if imported['cave_id'] != 'forest_1' or imported['catalog_sha256'] != sha(catalog_raw):
        raise ValueError('Unit/catalog provenance mismatch')
    metadata = imported['units'][UNIT]; directory = units/'units'/UNIT
    if not metadata['assembly_ready'] or any(r['unreachable_sources'] for r in metadata['route_audit']):
        raise ValueError('Unit routes not ready')
    for name, digest in metadata['output_sha256'].items():
        if sha((directory/name).read_bytes()) != digest: raise ValueError('Unit hash mismatch: '+name)
    room = json.loads((directory/'collision.json').read_text()); candidates = flower_plan(room)
    flowers = candidates if context is None else [f for f in candidates if f['generator_id'] in context['spawned_generators']]
    def grounded(x, z):
        y = ground_height(room['vertices'], room['triangles'], x, z)
        if y is None: raise ValueError('Engineering anchor lacks ground')
        return [x, y, z]
    positions = dict(start=grounded(-180, -180), pod=grounded(-260, 0), ship=grounded(260, 0))
    raw = generator(assets); starts = [m.start() for m in re.finditer(b'    0.0v', raw)] + [len(raw)]
    entries = []; piki = 0
    for a, b in zip(starts, starts[1:]):
        e = bytearray(raw[a:b]); label = bytes(e[16:48]).rstrip(b'\0')
        if label in (b'preview treasure bolt', b'preview dwarf bulborb'): continue
        if label == b'preview red pikmin':
            pos = grounded(-205+(piki%5)*12, -130+(piki//5)*12); piki += 1
        else:
            key = {b'preview red onion':'pod', b'preview ship':'ship'}.get(label)
            if key is None: raise ValueError('Unknown scaffold actor')
            pos = positions[key]
        struct.pack_into('>3f', e, 48, *pos); entries.append(e)
    templates = [r for r in records(assets/'dataDir/stages/chal0/default.gen') if r[72:80] == b'ssob\x02\x00\x00\x00']
    if not templates: raise ValueError('Missing Pom template')
    for i, flower in enumerate(flowers):
        e = bytearray(templates[0]); struct.pack_into('<I', e, 8, flower['generator_id'])
        e[16:48] = f'preview violet {i}'.encode().ljust(32, b'\0')
        write_position(e,flower['position'])
        struct.pack_into('>I', e, 80, 69); entries.append(e)
    actors = b'1.0v'+struct.pack('>4fI', *positions['start'], 45, len(entries))+b''.join(entries)
    audit = decode_no_cargo(actors,len(flowers))
    for flower,e in zip(flowers,entries[-2:]):validate_position(e,flower['position'])
    stage = (assets/'dataDir/stages/chal0.ini').read_bytes()
    stage = re.sub(rb'(?m)^map_file[^\r\n]*', b'map_file courses/pikmin2room/room.mod', stage)
    stage = re.sub(rb'(?m)^navi_start[^\r\n]*', b'navi_start -180.0 -180.0', stage)
    overrides = {'dataDir/stages/chal0.ini':stage, 'dataDir/stages/chal0/default.gen':actors,
                 'dataDir/courses/pikmin2room/room.mod':attach_collision((directory/'render.mod').read_bytes(), room, cap_exits=True),
                 'dataDir/courses/pikmin2room/room.ini':route_ini(room['routes']).encode()}
    models = sorted(purple.glob('*.mod'))
    if not models or not (purple/'p2-purple.txt').is_file(): raise ValueError('Missing Purple bank')
    for path in models: overrides['dataDir/courses/pikmin2room/'+path.name] = path.read_bytes()
    if pod_model is not None: overrides['dataDir/courses/pikmin2room/pod.mod'] = pod_model
    empty = b'1.0v'+struct.pack('>4fI', *positions['start'], 45, 0)
    for path in (assets/'dataDir/stages/chal0').glob('*.gen'):
        overrides.setdefault('dataDir/stages/chal0/'+path.name, empty)
    run = output.resolve()/uuid.uuid4().hex; run.mkdir(parents=True)
    overlay(assets, run/'assets', overrides)
    (run/'p2-purple.txt').write_bytes((purple/'p2-purple.txt').read_bytes())
    (run/'p2-cargo-free.txt').write_bytes(CARGO_FREE_CONFIG)
    if pod_model is not None: (run/'p2-pod.txt').write_text('P2_POD_1\ncargo_free 0 1 1\nKochappy 0\n')
    report = dict(schema=1, policy=GENERATION_POLICY if context is not None else POLICY, cave='forest_1', floor=2, native_ready=False,
        retail_generation=False, complete_roster=False, source_definition=floor,
        catalog_sha256=sha(catalog_raw), source_sha256=imported['source_sha256'], unit=metadata,
        flowers=flowers, flower_candidates=candidates, generation_context=context,
        generation_identity=sha(json.dumps(context,sort_keys=True,separators=(',',':')).encode()) if context is not None else None,
        engineering_anchors=positions, generator_audit=audit,
        unsupported=['Egg x2 and its TamagoMushi helper/drops', 'HikariKinoko x6', 'KareOoinu_s x2', 'Descent and floor lifecycle', 'Native global population/saved generation context integration'],
        pod_enabled=pod_model is not None, pod_required_for_purple=True,
        native_blocker='Preparation is not runtime certification. Use a P2_CARGO_FREE_1-capable executable and the dedicated floor2 runtime validator; no dummy cargo permitted.',
        limitations=['One selected cent2 room with exits capped; not retail room generation.', 'Violet actors use existing P1 Pom conversion proxy, not source P2 Pom FSM/models.', 'Native conversion acceptance is separate, executable/input-hash-bound evidence.',
                     'Global population is unspecified; legacy preparation emits both flowers without certifying the birth gate.' if context is None else 'Generation population is caller-supplied; native global/save state has not been reconstructed or verified.'],
        override_sha256={k:sha(v) for k,v in sorted(overrides.items())}, purple_config_sha256=sha((run/'p2-purple.txt').read_bytes()),
        cargo_free_config_sha256=sha(CARGO_FREE_CONFIG))
    (run/'readiness.json').write_text(json.dumps(report, indent=2)+'\n')
    return run


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('assets','units','catalog','purple','output'): p.add_argument('--'+name, type=Path, required=True)
    p.add_argument('--pod',type=Path,help='Research Pod import required by native Purple initialization')
    p.add_argument('--global-purple-count',type=int,help='Explicit global-plus-cave Purple count at generation; omission retains legacy ungated preparation')
    a = p.parse_args()
    print(prepare(a.assets.resolve(), a.units.resolve(), a.catalog.resolve(), a.purple.resolve(), a.output,pod=a.pod.resolve() if a.pod else None,global_purple_count=a.global_purple_count))


if __name__ == '__main__': main()
