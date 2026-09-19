"""Treasure catalog validation ledger: source placements and classifications, not cargo runtime.

Reads the local US disc catalogs and every retail placement source, then classifies
each ``otakara``/``item`` entry and reconciles the result with the counts the game
declares in ``user/Abe/stages.txt``. No disc data is copied and no runtime cargo
interface is touched.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re

from experimental.pikmin2_assets import archive_files, disc_files
from experimental.pikmin2_cave import parameters, safe_name, tree
from experimental.pikmin2_pod import pellet_catalog

COURSES = ('tutorial', 'forest', 'yakushima', 'last')
PELLET_LIST = 'user/Abe/Pellet/us/pelletlist_us.szs'
STAGES = 'user/Abe/stages.txt'
CAVEINFO = 'user/Mukki/mapunits/caveinfo/'
# include/Game/PelletList.h: PLK_Otakara = 3, PLK_Item = 4. Other managers never hold treasures.
PELLET_KINDS = {3: 'otakara', 4: 'item'}
# src/plugProjectNishimuraU/BigTreasureMgr.cpp Mgr::Mgr registers these five pellets and
# BigTreasure.cpp Obj::setupTreasure births them captured on the boss; no roster lists them.
BOSS_DROPS = {'BigTreasure': ('elec', 'fire', 'gas', 'water', 'loozy')}
DROP_MODES = {0: 'none', 1: 'pikmin_or_leader', 2: 'pikmin', 3: 'leader', 4: 'carrying_pikmin', 5: 'earthquake'}


def _int(value, low=0, high=10 ** 6):
    if not isinstance(value, str) or not re.fullmatch(r'-?\d+', value):
        raise ValueError('Expected integer token')
    number = int(value)
    if not low <= number <= high:
        raise ValueError('Integer token out of range')
    return number


def _float(value):
    if not isinstance(value, str):
        raise ValueError('Expected numeric token')
    try:
        result = float(value)
    except ValueError:
        raise ValueError('Expected numeric token') from None
    if not math.isfinite(result):
        raise ValueError('Non-finite numeric token')
    return result


def _tag(node, pattern):
    if not isinstance(node, list) or len(node) != 1 or not isinstance(node[0], str) or not re.fullmatch(pattern, node[0]):
        raise ValueError('Malformed identifier tag')
    return node[0]


def course_table(text):
    """Parse ``stages.txt`` (gameStages.cpp CourseInfo::read): generator windows, caves and declared counts."""
    nodes = tree(text)
    if not nodes:
        raise ValueError('Empty course table')
    count = _int(nodes[0], 1, 16)
    blocks = nodes[1:]
    if len(blocks) != count or any(not isinstance(block, list) for block in blocks):
        raise ValueError('Course count mismatch')
    courses = []
    for block in blocks:
        at = 0
        fields = {}
        while True:
            if at >= len(block):
                raise ValueError('Missing course header terminator')
            key = block[at]
            at += 1
            if key == 'end':
                break
            width = 3 if key == 'start' else 1
            if not isinstance(key, str) or key in fields or at + width > len(block) or any(
                    not isinstance(v, str) for v in block[at:at + width]):
                raise ValueError('Malformed course header field')
            fields[key] = block[at] if width == 1 else block[at:at + width]
            at += width
        if not {'name', 'abe_folder'} <= set(fields):
            raise ValueError('Incomplete course header')

        def rows(width, convert):
            nonlocal at
            if at >= len(block):
                raise ValueError('Missing course table count')
            number = _int(block[at], 0, 64)
            at += 1
            result = []
            for _ in range(number):
                if at + width > len(block):
                    raise ValueError('Truncated course table')
                result.append(convert(block[at:at + width]))
                at += width
            return result

        def window(row):
            name, low, high, limit = row
            return dict(file=safe_name(name), minimum_day=_int(low, 0, 10000), maximum_day=_int(high, 0, 10000),
                        day_limit=_int(limit, 0, 10000))

        def cave(row):
            tag, number, file = row
            return dict(tag=_tag(tag, r'[A-Za-z0-9_]+'), declared_treasures=_int(number, 0, 255), caveinfo=safe_name(file))

        nonloop = rows(4, window)
        loop = rows(4, window)
        caves = rows(3, cave)
        if at >= len(block):
            raise ValueError('Missing ground treasure count')
        ground = _int(block[at], 0, 255)
        at += 1
        if at != len(block):
            raise ValueError('Trailing course data')
        courses.append(dict(name=fields['name'], abe_folder=fields['abe_folder'], nonloop=nonloop, loop=loop,
                            caves=caves, declared_ground_treasures=ground))
    return courses


def _decode_code(code, otakara, items):
    """PelletMgr::OtakaraItemCode: high byte is the pellet kind, low byte the config index."""
    if code == 0:
        return None
    if code < 0:
        raise ValueError('Negative treasure item code')
    kind, index = code >> 8, code & 255
    if kind not in PELLET_KINDS:
        raise ValueError('Treasure item code names an unsupported pellet manager')
    names = otakara if kind == 3 else items
    if index >= len(names):
        raise ValueError('Treasure item code index outside catalog')
    return dict(pellet_kind=PELLET_KINDS[kind], config_index=index, treasure_id=names[index])


def _generator(block, index, otakara, items, enemies_by_id):
    """Decode one Generator::read block (RM_Disc layout) far enough to find any treasure."""
    if len(block) < 3:
        raise ValueError('Truncated generator block')
    version = int(_tag(block[0], r'v0\.\d')[-1])
    at = 1
    _int(block[at], -32768, 65535)  # reserved (readShort; the disc uses -1 for some entries)
    at += 1
    if version >= 1:
        _int(block[at], -2 ** 31, 2 ** 31 - 1)  # days till resurrection
        at += 1
    if at + 32 + 6 + 2 > len(block):
        raise ValueError('Truncated generator block')
    label = bytes(_int(v, 0, 255) for v in block[at:at + 32]).split(b'\0', 1)[0].decode('shift_jis', 'replace')
    at += 32
    position = [_float(v) for v in block[at:at + 3]]
    offset = [_float(v) for v in block[at + 3:at + 6]]
    at += 6
    kind = _tag(block[at], r'[a-z]{4}')
    object_version = int(_tag(block[at + 1], r'\d{4}'))
    at += 2
    base = dict(generator_index=index, generator_label=label, position=[p + o for p, o in zip(position, offset)],
                object_kind=kind, object_version=object_version)
    if kind == 'pelt':
        # GenPellet::doRead: manager id byte, rotation, local version, then Mgr::generatorRead index short.
        if at >= len(block) or not isinstance(block[at], list) or len(block[at]) != 6:
            raise ValueError('Malformed pellet generator')
        body = block[at]
        manager = _int(body[0], 0, 255)
        if manager not in PELLET_KINDS:
            raise ValueError('Pellet generator uses an unsupported manager')
        for value in body[1:4]:
            _float(value)
        _tag(body[4], r'\d{4}')
        names = otakara if manager == 3 else items
        config_index = _int(body[5], 0, 65535)
        if config_index >= len(names):
            raise ValueError('Pellet generator index outside catalog')
        return [dict(base, kind='loose', pellet_kind=PELLET_KINDS[manager], config_index=config_index,
                     treasure_id=names[config_index])]
    if kind == 'teki':
        # GenObjectEnemy::doRead / doReadOldVersion: versions 3-5 carry an OtakaraItemCode after the size.
        if object_version < 3:
            return []
        width = 8 if object_version >= 5 else 7
        if at + width > len(block) or any(not isinstance(v, str) for v in block[at:at + width]):
            raise ValueError('Truncated enemy generator')
        enemy_id = _int(block[at], 0, 65535)
        if enemy_id not in enemies_by_id:
            raise ValueError('Enemy generator references an unknown enemy id')
        fields = block[at + 1:at + width]
        if object_version >= 5:
            _int(fields[0], 0, 255)
            fields = fields[1:]
        count = _int(fields[0], 0, 65535)
        _float(fields[1])
        _int(fields[2], 0, 255)
        _float(fields[3])
        _float(fields[4])
        held = _decode_code(_int(fields[5], -32768, 32767), otakara, items)
        if held is None:
            return []
        return [dict(base, kind='held', enemy_id=enemies_by_id[enemy_id], enemy_count=count, **held)]
    return []


def generator_placements(text, otakara, items, enemies_by_id):
    """Find treasure pellets and enemy-held treasures in one disc generator text file."""
    nodes = tree(text)
    if len(nodes) < 5:
        raise ValueError('Missing generator manager header')
    version = _tag(nodes[0], r'v0\.[01]')
    for value in nodes[1:4]:
        _float(value)
    at = 4
    if version == 'v0.1':
        _float(nodes[at])
        at += 1
    count = _int(nodes[at], 0, 4096)
    at += 1
    blocks = nodes[at:]
    if len(blocks) < count or any(not isinstance(block, list) for block in blocks):
        raise ValueError('Generator count mismatch')
    # GeneratorMgr::read loads exactly the declared count; blocks after that are dead data
    # on the disc (last/nonloop/0-1.txt declares zero generators above twenty pellet blocks).
    result = []
    for index, block in enumerate(blocks):
        for placement in _generator(block, index, otakara, items, enemies_by_id):
            result.append(dict(placement, engine_loaded=index < count))
    return result


def _enemy_token(raw, enemy_ids):
    """TekiInfo::read: optional $ drop prefix, exact-prefix underscore split, case-insensitive enemy lookup."""
    if not isinstance(raw, str) or not re.fullmatch(r'\$?[1-9]?[A-Za-z][A-Za-z0-9_]*', raw):
        raise ValueError('Malformed enemy token')
    name = raw
    drop = 0
    if name.startswith('$'):
        name = name[1:]
        drop = 1
        if name[:1] in '123456789':
            drop = int(name[0])
            name = name[1:]
    carried = None
    for i, c in enumerate(name):
        if c == '_' and name[:i] in enemy_ids:
            carried = name[i + 1:]
            name = name[:i]
            break
    lookup = {value.lower(): value for value in enemy_ids}
    if name.lower() not in lookup:
        raise ValueError('Unknown enemy reference: ' + name)
    return lookup[name.lower()], carried, drop


def _rows(node, width):
    if not isinstance(node, list) or not node:
        raise ValueError('Missing roster block')
    count = _int(node[0], 0, 255)
    if len(node) != 1 + count * width or any(not isinstance(v, str) for v in node):
        raise ValueError('Malformed roster framing')
    return [node[1 + i * width:1 + (i + 1) * width] for i in range(count)]


def cave_placements(text, enemy_ids, cargo_ids):
    """List loose, enemy-held and cap-held treasures plus boss drops from one caveinfo definition."""
    nodes = tree(text)
    if len(nodes) < 2 or not isinstance(nodes[0], list):
        raise ValueError('Missing cave header')
    header = parameters(nodes[0])
    count = _int(nodes[1], 1, 128)
    if _int(header.get('c000', ''), 1, 128) != count:
        raise ValueError('Cave definition count mismatch')
    cursor = 2
    result = []
    for definition in range(count):
        if cursor >= len(nodes) or not isinstance(nodes[cursor], list):
            raise ValueError('Missing floor parameters')
        params = parameters(nodes[cursor])
        first, last = _int(params.get('f000', ''), 0, 127), _int(params.get('f001', ''), 0, 127)
        if first > last:
            raise ValueError('Inverted floor range')
        sections = 4 if _int(params.get('f015', '0'), 0, 255) >= 1 else 3
        cursor += 1
        if cursor + sections > len(nodes):
            raise ValueError('Missing floor roster sections')
        base = dict(definition_index=definition, first_floor=first + 1, last_floor=last + 1)
        bosses = set()

        def enemy(row, kind):
            name, carried, drop = _enemy_token(row[0], enemy_ids)
            weight, placement = _int(row[1], 0, 65535), _int(row[2], 0, 8)
            if name in BOSS_DROPS:
                bosses.add(name)
            if carried is None:
                return
            if carried not in cargo_ids:
                raise ValueError('Unknown enemy cargo: ' + carried)
            minimum = weight if placement == 6 else weight // 10
            result.append(dict(base, kind=kind, treasure_id=carried, enemy_id=name, source_token=row[0],
                               minimum_count=minimum, drop_mode=drop,
                               drop_semantics=DROP_MODES.get(drop, 'source_accepts_unmapped_mode')))

        for row in _rows(nodes[cursor], 3):
            enemy(row, 'held')
        for name, weight in _rows(nodes[cursor + 1], 2):
            if name not in cargo_ids:
                raise ValueError('Unknown treasure reference: ' + name)
            weight = _int(weight, 0, 65535)
            result.append(dict(base, kind='loose', treasure_id=name, minimum_count=weight // 10,
                               selection_weight=weight % 10))
        _rows(nodes[cursor + 2], 3)
        if sections == 4:
            node = nodes[cursor + 3]
            if not isinstance(node, list) or not node:
                raise ValueError('Missing cap block')
            at = 1
            for _ in range(_int(node[0], 0, 255)):
                if at >= len(node):
                    raise ValueError('Truncated cap record')
                empty = _int(node[at], 0, 255)
                at += 1
                if not empty:
                    if at + 3 > len(node):
                        raise ValueError('Truncated cap record')
                    enemy(node[at:at + 3], 'cap_held')
                    at += 3
            if at != len(node):
                raise ValueError('Trailing cap data')
        for boss in sorted(bosses):
            for treasure in BOSS_DROPS[boss]:
                if treasure not in cargo_ids:
                    raise ValueError('Boss drop missing from catalog: ' + treasure)
                result.append(dict(base, kind='boss_drop', treasure_id=treasure, enemy_id=boss, minimum_count=1))
        cursor += sections
    if cursor != len(nodes):
        raise ValueError('Trailing cave data')
    return result


def classify(catalog_ids, placements):
    """Classify each catalog id from its placement scopes; every id gets exactly one classification."""
    scopes = {}
    for placement in placements:
        if placement['treasure_id'] not in catalog_ids:
            raise ValueError('Placement references an unknown catalog id')
        if placement.get('engine_loaded', True):
            scopes.setdefault(placement['treasure_id'], set()).add(placement['scope'])
    result = {}
    for name in catalog_ids:
        found = scopes.get(name, set())
        campaign = sorted(scope for scope in found if scope.startswith('campaign_'))
        modes = sorted(scope for scope in found if not scope.startswith('campaign_'))
        if campaign:
            classification = 'campaign'
        elif modes:
            classification = 'mode_only'
        else:
            classification = 'unused'
        result[name] = dict(classification=classification, campaign_scopes=campaign, mode_scopes=modes)
    return result


def reconcile(courses, surface, caves, catalog_size, dictionary_numbers):
    """Compare declared course/cave treasure counts and dictionary coverage with observed placements."""
    course_rows = []
    cave_rows = []
    for course in courses:
        placed = surface.get(course['name'], [])
        loaded = sorted({p['treasure_id'] for p in placed if p['engine_loaded']})
        dead = sorted({p['treasure_id'] for p in placed if not p['engine_loaded']})
        course_rows.append(dict(course=course['name'], declared=course['declared_ground_treasures'],
                                observed=len(loaded), treasure_ids=loaded, unloaded_block_treasure_ids=dead,
                                reconciled=len(loaded) == course['declared_ground_treasures']))
        for cave in course['caves']:
            cave_id = cave['caveinfo'][:-4]
            if cave_id not in caves:
                continue
            distinct = sorted({p['treasure_id'] for p in caves[cave_id]})
            duplicates = sorted({p['treasure_id'] for p in caves[cave_id]
                                 if sum(q['treasure_id'] == p['treasure_id'] for q in caves[cave_id]) > 1})
            cave_rows.append(dict(course=course['name'], cave=cave_id, declared=cave['declared_treasures'],
                                  observed=len(distinct), treasure_ids=distinct, repeated_definitions=duplicates,
                                  reconciled=len(distinct) == cave['declared_treasures']))
    declared_total = sum(r['declared'] for r in course_rows) + sum(r['declared'] for r in cave_rows)
    numbers = sorted(dictionary_numbers)
    contiguous = numbers == list(range(1, len(numbers) + 1))
    return dict(courses=course_rows, caves=cave_rows, declared_total=declared_total, catalog_size=catalog_size,
                dictionary=dict(count=len(numbers), contiguous_from_one=contiguous, catalog_matches=len(numbers) == catalog_size),
                reconciled=all(r['reconciled'] for r in course_rows + cave_rows) and declared_total == catalog_size and contiguous)


def build(iso, inventory_path, output):
    """Produce ``treasure_ledger.json`` for the local disc; refuses an existing output directory."""
    output.mkdir(parents=True, exist_ok=False)
    inventory = json.loads(inventory_path.read_text(encoding='utf-8'))
    enemies_by_id = {}
    for enemy in inventory['enemies']:
        if type(enemy['id']) is not int or enemy['id'] in enemies_by_id:
            raise ValueError('Inventory enemy ids must be unique integers')
        enemies_by_id[enemy['id']] = enemy['internal']
    enemy_ids = set(enemies_by_id.values())
    files = disc_files(iso)
    hashes = {}
    with iso.open('rb') as disc:
        def read(path):
            if path not in files:
                raise ValueError('Missing disc source: ' + path)
            offset, size = files[path]
            disc.seek(offset)
            data = disc.read(size)
            if len(data) != size:
                raise ValueError('Truncated disc source: ' + path)
            hashes[path] = hashlib.sha256(data).hexdigest()
            return data

        archive = archive_files(read(PELLET_LIST))
        configs = {}
        for kind, member in (('otakara', 'otakara_config.txt'), ('item', 'item_config.txt')):
            configs[kind] = pellet_catalog(archive[member].decode('shift_jis'))
        otakara, items = list(configs['otakara']), list(configs['item'])
        for kind, key in (('otakara', 'us/runtime/otakara'), ('item', 'us/runtime/item')):
            recorded = inventory['catalogs'][key]['entries']
            if [(e['name'], e['dictionary']) for e in recorded] != [(n, configs[kind][n]['dictionary']) for n in configs[kind]]:
                raise ValueError('Inventory catalog differs from the disc catalog: ' + kind)
        cargo_ids = set(otakara) | set(items)
        if len(cargo_ids) != len(otakara) + len(items):
            raise ValueError('Otakara and item catalogs share a name')

        courses = [c for c in course_table(read(STAGES).decode('shift_jis')) if c['name'] in COURSES]
        if [c['name'] for c in courses] != list(COURSES):
            raise ValueError('Retail course table differs from expectation')
        placements = []
        surface = {}
        for course in courses:
            folder = course['abe_folder'] + '/'
            windows = {w['file']: w for w in course['nonloop'] + course['loop']}
            for path in sorted(p for p in files if p.startswith(folder) and p.endswith('.txt')):
                relative = path[len(folder):]
                if relative == 'route.txt':
                    continue
                for placement in generator_placements(read(path).decode('shift_jis', 'replace'), otakara, items, enemies_by_id):
                    record = dict(placement, scope='campaign_surface', course=course['name'], file=relative,
                                  day_window=windows.get(relative.split('/')[-1]) if '/' in relative else None)
                    placements.append(record)
                    surface.setdefault(course['name'], []).append(record)
        caves = {}
        story = {c['id']: c for c in inventory['story_caves']}
        mode_caves = [('challenge', s['cave_path']) for s in inventory['challenge']['stages']]
        mode_caves += [('battle', s['cave_path']) for s in inventory['battle']['stages']]
        for course in courses:
            for cave in course['caves']:
                cave_id = cave['caveinfo'][:-4]
                if cave_id not in story:
                    continue
                for placement in cave_placements(read(story[cave_id]['source']).decode('shift_jis', 'replace'), enemy_ids, cargo_ids):
                    record = dict(placement, scope='campaign_cave', course=course['name'], cave=cave_id)
                    placements.append(record)
                    caves.setdefault(cave_id, []).append(record)
        if set(caves) != set(story):
            raise ValueError('Story cave list differs between the course table and the inventory')
        for scope, path in mode_caves:
            cave_id = path.rsplit('/', 1)[-1][:-4]
            for placement in cave_placements(read(path).decode('shift_jis', 'replace'), enemy_ids, cargo_ids):
                placements.append(dict(placement, scope=scope, cave=cave_id))
    classes = classify(cargo_ids, placements)
    entries = []
    for kind, names in (('otakara', otakara), ('item', items)):
        for index, name in enumerate(names):
            config = configs[kind][name]
            entries.append(dict(treasure_id=name, pellet_kind=kind, config_index=index,
                                dictionary=_int(config['dictionary'], 1, 65535), archive=config['archive'], model=config['bmd'],
                                value=_int(config['money'], 0, 65535), weight=_int(config['min'], 0, 65535),
                                slots=_int(config['max'], 0, 65535), code=_int(config.get('code', '0'), 0, 65535),
                                unique=config.get('unique', 'no'), indirect=config.get('indirect', 'no'),
                                dynamics=config.get('dynamics'), depth=config.get('depth'),
                                **classes[name], placements=[p for p in placements if p['treasure_id'] == name]))
    dictionary = [e['dictionary'] for e in entries]
    reconciliation = reconcile(courses, surface, caves, len(entries), dictionary)
    summary = {label: sorted(e['treasure_id'] for e in entries if e['classification'] == label)
               for label in ('campaign', 'mode_only', 'unused')}
    result = dict(schema=1, disc='GPVE01 revision 0', inventory_sha256=hashlib.sha256(inventory_path.read_bytes()).hexdigest(),
                  entries=entries, classification_summary=summary, reconciliation=reconciliation, source_sha256=hashes,
                  limitations=[
                      'Placements are source definitions; they are not spawned pellets, receipts or runtime cargo.',
                      'unique=yes entries listed on several floors or generators are one collectible; repeats are recorded, not counted.',
                      'Generator blocks after the declared count are recorded with engine_loaded=false and never classify an entry.',
                      'English names are not guessed; dictionary numbers follow PelletConfigList::getPelletConfig_ByDictionaryNo.',
                      'Models, materials, carry behavior and delivery persistence are not evaluated here.'])
    (output / 'treasure_ledger.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--iso', type=Path, required=True)
    parser.add_argument('--inventory', type=Path, default=Path('docs/PIKMIN2_CONTENT_INVENTORY.json'))
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    ledger = build(args.iso, args.inventory, args.output)
    print(json.dumps(dict(entries=len(ledger['entries']), placements=sum(len(e['placements']) for e in ledger['entries']),
                          **{k: len(v) for k, v in ledger['classification_summary'].items()},
                          reconciled=ledger['reconciliation']['reconciled'])))
