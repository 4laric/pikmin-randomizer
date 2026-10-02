"""Reproducible retail overworld source bundles; never a native stage launcher."""
import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path, PurePosixPath
import struct

from experimental.pikmin2_assets import archive_files, disc_files
from experimental.pikmin2_cave import tree
from experimental.pikmin2_generator_calendar import course_schedule, validate_members
from experimental.pikmin2_collision import plane, route_ini
from experimental.pikmin2_surface_physics import water_boxes
from experimental.pikmin2_surface_pocket import generators
from experimental.pikmin2_surface_topology import audit

COURSES = {'tutorial': 'Valley of Repose', 'forest': 'Awakening Wood',
           'yakushima': 'Perplexing Pool', 'last': 'Wistful Wild'}
SCHEMA = 'p2-surface-source-1'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def encoded(value):
    return (json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False,
                       allow_nan=False) + '\n').encode('utf-8')


def safe_path(name):
    if not isinstance(name, str) or not name or '\\' in name or ':' in name:
        raise ValueError('Unsafe bundle path')
    path = PurePosixPath(name)
    if path.is_absolute() or '..' in path.parts or str(path) != name:
        raise ValueError('Unsafe bundle path')
    return path


def read_member(stream, catalog, name):
    if name not in catalog:
        raise ValueError('Missing disc member: ' + name)
    offset, size = catalog[name]
    stream.seek(offset)
    data = stream.read(size)
    if len(data) != size:
        raise ValueError('Truncated disc member: ' + name)
    return data, dict(offset=offset, size=size, sha256=digest(data))


def source_generators(text):
    """Honor retail GeneratorMgr::read's declared prefix; retain dormant rows.

    Pool 20-29.txt and Wild 0-1.txt contain complete records after that prefix.
    They are source data, not active schedules, and must never be auto-enabled.
    The shared Valley parser keeps its strict whole-file count validation.
    """
    values = tree(text)
    if len(values) < 6 or values[0] != ['v0.1']:
        raise ValueError('Unsupported surface generator manager header')
    count = int(values[5])
    if count < 0 or count > len(values)-6:
        raise ValueError('Invalid or truncated declared generator count')
    if count == len(values)-6:
        return generators(text)
    # Refuse a trailing scalar/unrecognized record rather than reinterpret it
    # as a repaired count or an active actor. Raw source bytes remain preserved.
    ignored = values[6+count:]
    for row in ignored:
        if not isinstance(row, list) or len(row) < 43 or row[0] not in (['v0.1'], ['v0.2'], ['v0.3']):
            raise ValueError('Malformed dormant generator record')
    def serialize(value):
        return '{ '+ ' '.join(serialize(part) for part in value)+' }' if isinstance(value, list) else value
    prefix = ' '.join(serialize(value) for value in values[:6+count])
    result = generators(prefix)
    result.update(declared_count=count, serialized_count=len(values)-6,
                  ignored_records=[dict(file_record_index=count+i, version=row[0][0])
                                   for i, row in enumerate(ignored)],
                  ignored_reason='Retail GeneratorMgr::read consumes only its declared count')
    return result


def decode_surface(texts, course):
    """Retain source-only faces the dry-room native converter cannot accept.

    Retail Perplexing Pool has degenerate faces. Inventory them rather than
    deleting them or weakening the generic native MOD converter's validation.
    """
    grid = (texts/'grid.bin').read_bytes()
    cursor = 0
    def take(fmt):
        nonlocal cursor
        size = struct.calcsize('>'+fmt)
        if cursor+size > len(grid):
            raise ValueError('Truncated P2 grid')
        values = struct.unpack_from('>'+fmt, grid, cursor)
        cursor += size
        return values
    count, = take('I')
    if not 0 < count <= (len(grid)-cursor)//12:
        raise ValueError('Invalid surface vertex count')
    vertices = [list(take('3f')) for _ in range(count)]
    count, = take('I')
    if not 0 < count <= (len(grid)-cursor)//76:
        raise ValueError('Invalid surface triangle count')
    triangles, planes = [], []
    for _ in range(count):
        triangles.append(list(take('3I')))
        planes.append(list(take('16f')))
    if not all(math.isfinite(v) for row in vertices+planes for v in row):
        raise ValueError('Nonfinite source geometry')
    codes = (texts/'mapcode.bin').read_bytes()
    if len(codes) != 4+count or struct.unpack_from('>I', codes)[0] != count:
        raise ValueError('Mapcode count mismatch')
    degenerate = []
    for index, triangle in enumerate(triangles):
        if any(v >= len(vertices) for v in triangle):
            raise ValueError('Invalid source triangle index')
        try:
            plane(vertices, triangle)
        except ValueError:
            degenerate.append(index)
    source = (texts/'route.txt').read_text(encoding='utf-8')
    tokens = iter(' '.join(line.split('#')[0] for line in source.splitlines())
                  .replace('{', ' ').replace('}', ' ').split())
    routes = []
    try:
        count = int(next(tokens))
        if count < 0:
            raise ValueError('Negative surface route count')
        for _ in range(count):
            index, links = int(next(tokens)), int(next(tokens))
            if links < 0:
                raise ValueError('Negative surface link count')
            targets = [int(next(tokens)) for _ in range(links)]
            position = [float(next(tokens)) for _ in range(3)]
            radius = float(next(tokens))
            if index < 0 or radius < 0 or not all(math.isfinite(v) for v in position+[radius]):
                raise ValueError('Invalid surface route point')
            routes.append(dict(id=index, links=targets, position=position, radius=radius))
        if next(tokens, None) is not None:
            raise ValueError('Trailing surface route tokens')
    except StopIteration as error:
        raise ValueError('Truncated surface route') from error
    route_ini(routes)  # existing duplicate/dangling destination rejection
    return dict(source=course, vertices=vertices, triangles=triangles, planes=planes,
                mapcodes=list(codes[4:]), routes=routes, spawns=[],
                degenerate_triangles=degenerate,
                bounds={name: [fn(v[i] for v in vertices) for i in range(3)]
                        for name, fn in [('min', min), ('max', max)]},
                unconverted_acceleration_bytes=len(grid)-cursor)


def surface_topology(room):
    rejected = set(room['degenerate_triangles'])
    ids = [i for i in range(len(room['triangles'])) if i not in rejected]
    report = audit(dict(room, triangles=[room['triangles'][i] for i in ids],
                        mapcodes=[room['mapcodes'][i] for i in ids]))
    for duplicate in report['duplicate_faces']:
        duplicate['triangles'] = [ids[i] for i in duplicate['triangles']]
    for edge in report['nonmanifold_edges']:
        for incident in edge['incidents']:
            incident['triangle'] = ids[incident['triangle']]
        for pair in edge['pairs']:
            pair['triangles'] = [ids[i] for i in pair['triangles']]
    compatible = report['native_conversion_approved'] and not rejected
    report.update(source_triangles=len(room['triangles']), audit_triangle_source_ids=ids,
                  degenerate_triangles=room['degenerate_triangles'],
                  source_geometry_unchanged=True, audited_triangles=len(ids),
                  topology_compatible=compatible, native_conversion_approved=False)
    report['unresolved'].append('Source audit never admits native surface conversion or water gameplay.')
    if rejected:
        report['unresolved'].append('Retail degenerate faces retained; native conversion requires an explicit policy.')
    return report


def import_surface(iso, course, output):
    """Extract geometry and schedules intact; report translation/runtime gaps.

    Raw mapcodes deliberately bypass the dry-room *translation* policy. They
    remain P2 values in an offline JSON, never become P1 collision flags.
    """
    if course not in COURSES:
        raise ValueError('Unknown overworld course')
    iso, output = Path(iso), Path(output)
    if output.exists():
        raise FileExistsError('Retain original bundle; use a new output')
    catalog = disc_files(iso)
    source, files = {}, {}
    map_root, gen_root = f'user/Kando/map/{course}/', f'user/Abe/map/{course}/'
    with iso.open('rb') as stream:
        header = stream.read(0x440)
        def read(name):
            data, source[name] = read_member(stream, catalog, name)
            return data
        for category in ('arc', 'texts'):
            for name, data in sorted(archive_files(read(map_root+category+'.szs')).items()):
                safe_path(name)
                files[f'{category}/{name}'] = data
        raw_route = read(gen_root+'route.txt')
        files['source/route.txt'] = raw_route
        files['texts/route.txt'] = raw_route.decode('cp932').encode('utf-8')
        stages = read('user/Abe/stages.txt')
        files['source/stages.txt'] = stages
        schedule = course_schedule(stages.decode('cp932'), course)
        definitions, errors, warnings = {}, [], []
        names = sorted(name for name in catalog if name.startswith(gen_root)
                       and name.endswith('.txt') and name != gen_root+'route.txt')
        if gen_root+'defaultgen.txt' not in names:
            raise ValueError('Missing default surface generators')
        validate_members(schedule, (name[len(gen_root):] for name in names))
        for name in names:
            relative = name[len(gen_root):]
            safe_path(relative)
            data = read(name)
            files['generators/'+relative] = data
            try:
                definition = source_generators(data.decode('cp932'))
                definitions[relative] = definition
                if definition.get('ignored_records'):
                    warnings.append(dict(source=relative, declared_count=definition['declared_count'],
                                         serialized_count=definition['serialized_count'],
                                         inactive_record_count=len(definition['ignored_records'])))
            except (ValueError, IndexError, TypeError, UnicodeError) as error:
                errors.append(dict(source=relative, error=str(error)))
    # Validate required source data before creating output. Failed decode leaves
    # its private partial directory, without a complete receipt; never reuse it.
    for name in ('grid.bin', 'mapcode.bin', 'waterbox.txt'):
        if 'texts/'+name not in files:
            raise ValueError('Missing surface text: ' + name)
    water = water_boxes(files['texts/waterbox.txt'].decode('cp932'))
    output.mkdir(parents=True, exist_ok=False)
    for name, data in sorted(files.items()):
        target = output / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    room = decode_surface(output/'texts', course)
    topology = surface_topology(room)
    defaults = definitions.get('defaultgen.txt', {}).get('actors', [])
    report = dict(schema=SCHEMA, course=course, name=COURSES[course],
                  vertices=len(room['vertices']), triangles=len(room['triangles']),
                  degenerate_triangles=room['degenerate_triangles'],
                  route_points=len(room['routes']), water_volumes=len(water),
                  mapcode_counts=dict(sorted(Counter(room['mapcodes']).items())),
                  entrances=[actor for actor in defaults if actor.get('item') == 'cave'],
                  landing_actors=[actor for actor in defaults if actor.get('item') == 'onyn'],
                  generator_files=len(names), generator_errors=errors, generator_warnings=warnings,
                  playable=False, native_validated=False,
                  requires=['Render conversion and material validation.',
                            'Native topology policy, collision and water integration.',
                            'Generator actor translation, day scheduling and persistent state.',
                            'Two-captain entry/return and actual-engine acceptance.'])
    artifacts = {'surface-geometry.json': room,
                 'surface-topology.json': topology,
                 'surface-water.json': dict(schema=1, boxes=water,
                                           native_consumer_implemented=False),
                 'surface-generators.json': definitions,
                 'surface-generator-calendar.json': schedule,
                 'surface-import.json': report}
    for name, value in artifacts.items():
        files[name] = encoded(value)
        (output/name).write_bytes(files[name])
    files['surface.route.ini'] = route_ini(room['routes']).encode('ascii')
    (output/'surface.route.ini').write_bytes(files['surface.route.ini'])
    receipt = dict(schema=SCHEMA, course=course,
                   disc=dict(game='GPVE01', revision=0, size=iso.stat().st_size,
                             header_sha256=digest(header)),
                   source_members=source,
                   files={name:dict(size=len(data), sha256=digest(data))
                          for name, data in sorted(files.items())})
    receipt_bytes = encoded(receipt)
    (output/'surface-receipt.json').write_bytes(receipt_bytes)
    return dict(report, identity=digest(receipt_bytes))


def verify_bundle(directory, expected_identity):
    """Require the consumer's pinned receipt and verify every file before use."""
    directory = Path(directory)
    receipt_path = directory/'surface-receipt.json'
    def redirected(path):
        return path.is_symlink() or path.is_junction()
    if redirected(directory) or redirected(receipt_path):
        raise ValueError('Symlinked bundle')
    data = receipt_path.read_bytes()
    if digest(data) != expected_identity:
        raise ValueError('Surface receipt differs from pinned identity')
    receipt = json.loads(data)
    if receipt.get('schema') != SCHEMA or receipt.get('course') not in COURSES:
        raise ValueError('Unsupported surface receipt')
    records = receipt.get('files')
    if not isinstance(records, dict) or not records:
        raise ValueError('Empty surface receipt')
    for name, record in records.items():
        safe_path(name)
        path = directory/name
        if any(redirected(parent) for parent in [path, *path.parents]
               if parent == directory or directory in parent.parents):
            raise ValueError('Symlinked bundle member')
        contents = path.read_bytes()
        if len(contents) != record['size'] or digest(contents) != record['sha256']:
            raise ValueError('Changed bundle member: ' + name)
    members = list(directory.rglob('*'))
    if any(redirected(path) for path in members):
        raise ValueError('Redirected surface bundle member')
    actual = {path.relative_to(directory).as_posix() for path in members if path.is_file()}
    if actual != set(records) | {'surface-receipt.json'}:
        raise ValueError('Untracked surface bundle member')
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    extract = sub.add_parser('import')
    extract.add_argument('--iso', type=Path, required=True)
    extract.add_argument('--course', choices=COURSES, required=True)
    extract.add_argument('--output', type=Path, required=True)
    verify = sub.add_parser('verify')
    verify.add_argument('--bundle', type=Path, required=True)
    verify.add_argument('--identity', required=True)
    args = parser.parse_args()
    if args.command == 'import':
        result = import_surface(args.iso, args.course, args.output)
        print(json.dumps({key: result[key] for key in
                         ('course', 'vertices', 'triangles', 'route_points',
                          'water_volumes', 'generator_files', 'generator_errors',
                          'generator_warnings', 'identity')}))
    else:
        receipt = verify_bundle(args.bundle, args.identity)
        print(json.dumps(dict(course=receipt['course'], identity=args.identity, verified=True)))


if __name__ == '__main__':
    main()
