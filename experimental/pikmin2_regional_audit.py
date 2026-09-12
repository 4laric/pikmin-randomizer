"""Local US-disc regional metadata audit consuming the #140 treasure ledger.

Reports stay local: names and catalog data are not redistributable assets.
Onboard regional tables are never treated as validation of a regional disc.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import struct

from experimental.pikmin2_assets import archive_files, disc_files
from experimental.pikmin2_cave import safe_name, tree
from experimental.pikmin2_pod import pellet_catalog


REGIONS = ('us', 'jpn', 'pal')
LANGUAGES = ('eng', 'fra', 'ger', 'hol', 'ita', 'jpn', 'spa')
KINDS = ('otakara', 'item', 'carcass', 'numberpellet', 'fruit')
PELLET_LIST = 'user/Abe/Pellet/us/pelletlist_us.szs'
KFES_TABLE = 'user/Matoba/challenge/kfes-stages.txt'
MAPPING_SOURCE_REVISION = '632af93787b9c95b63f0c13be32b161375ce3a96'
# src/plugProjectOgawaU/ogObjAnaDemo.cpp:12, CaveTitleMsg.
# Challenge entries in that table reuse a placeholder and are deliberately absent.
CAVE_TITLE_MESSAGES = {
    't_01': 8395, 't_02': 8399, 't_03': 8400,
    'f_01': 8396, 'f_02': 8398, 'f_03': 8401, 'f_04': 8410,
    'y_01': 8397, 'y_02': 8402, 'y_03': 8403, 'y_04': 8411,
    'l_01': 8412, 'l_02': 8413, 'l_03': 8414,
}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def bmg_index(data):
    """Read the observed BMG/MID format, rejecting ambiguous layouts.

    JMessage/data.h and resource.cpp define INF offsets, MID supplement 1
    (message number << 8 | variant), and encoding 3 (Shift-JIS).
    Text is decoded only for selected names, never for whole dialogue archives.
    """
    if len(data) < 32 or data[:8] != b'MESGbmg1':
        raise ValueError('Invalid BMG header')
    size, count = struct.unpack_from('>II', data, 8)
    if size != len(data) or data[16] not in (1, 3) or count != 3:
        raise ValueError('Unsupported BMG size, encoding or section count')
    sections = {}
    at = 32
    for _ in range(count):
        if at + 8 > size:
            raise ValueError('Truncated BMG section')
        tag, length = struct.unpack_from('>4sI', data, at)
        if tag not in (b'INF1', b'DAT1', b'MID1') or tag in sections or length < 8 or at + length > size:
            raise ValueError('Invalid BMG section')
        sections[tag] = data[at:at + length]
        at += length
    if at != size or set(sections) != {b'INF1', b'DAT1', b'MID1'}:
        raise ValueError('Incomplete BMG sections')
    info, mid, text = sections[b'INF1'], sections[b'MID1'], sections[b'DAT1'][8:]
    if len(info) < 16 or len(mid) < 16:
        raise ValueError('Truncated BMG table')
    number, stride, group = struct.unpack_from('>HHH', info, 8)
    if (stride != 8 or group != 0 or struct.unpack_from('>H', mid, 8)[0] != number
            or mid[10] != 0x10 or mid[11] != 1
            or 16 + number * stride > len(info) or 16 + number * 4 > len(mid)):
        raise ValueError('Unsupported BMG message table')
    result = {}
    previous = -1
    for index in range(number):
        key = struct.unpack_from('>I', mid, 16 + index * 4)[0]
        offset = struct.unpack_from('>I', info, 16 + index * stride)[0]
        if key <= previous or offset >= len(text):
            raise ValueError('Invalid BMG message ID or offset')
        result[key] = (text, offset, data[16])
        previous = key
    return result


def message_name(messages, number, variant=0, *, cave_presentation=False):
    key = (number << 8) | variant
    result = dict(message_number=number, variant=variant, packed_id=key)
    if key not in messages:
        return dict(result, status='missing', text=None)
    data, at, encoding = messages[key]
    result['encoding'] = encoding
    if cave_presentation:
        # JMessage::TProcessor::on_tag_ uses a five-byte header and total size.
        # Only observed, source-traced cave title presentation tags:
        # FF0001 = tagSize(u16 percent); 030004/030005 = reset/set font height.
        literal, controls = bytearray(), []
        while at < len(data) and data[at] != 0:
            if data[at] != 0x1A:
                literal.append(data[at])
                at += 1
                continue
            if at + 5 > len(data):
                raise ValueError('Truncated cave title control header')
            size = data[at + 1]
            if size < 5 or at + size > len(data):
                raise ValueError('Invalid cave title control size')
            tag = int.from_bytes(data[at + 2:at + 5], 'big')
            if (tag, size) not in ((0xFF0001, 7), (0x030004, 5), (0x030005, 7)):
                return dict(result, status='control_codes_unresolved', text=None)
            controls.append(dict(tag=tag, payload_hex=data[at + 5:at + size].hex()))
            at += size
        if at >= len(data):
            raise ValueError('Unterminated BMG cave name')
        raw = bytes(literal)
        if controls:
            result['presentation_controls'] = controls
    else:
        # Do not silently strip unreviewed control codes: payloads can contain NUL.
        end = data.find(b'\0', at)
        if end < 0:
            raise ValueError('Unterminated BMG name')
        raw = data[at:end]
    if b'\x1a' in raw:
        return dict(result, status='control_codes_unresolved', text=None)
    if encoding == 1 and not raw.isascii():
        return dict(result, status='font_encoding_unresolved', text=None)
    status = ('resolved_with_presentation_controls' if result.get('presentation_controls') else 'resolved') if raw else 'empty'
    return dict(result, status=status, text=raw.decode('shift_jis' if encoding == 3 else 'ascii'))


def catalog_delta(reference, compared):
    """Join by source ID within a pellet kind; dictionary/index are compared fields."""
    changed = []
    for name in sorted(reference.keys() & compared.keys()):
        left, right = reference[name], compared[name]
        fields = {key: dict(reference=left.get(key), compared=right.get(key))
                  for key in sorted(left.keys() | right.keys()) if left.get(key) != right.get(key)}
        if fields:
            changed.append(dict(source_id=name, fields=fields))
    return dict(reference_only=sorted(reference.keys() - compared.keys()),
                compared_only=sorted(compared.keys() - reference.keys()), changed=changed,
                order_changed=list(reference) != list(compared))


def attach_names(rows, catalogs, language_tables):
    for row in rows:
        # gamePelletList.cpp:160; mrUtil.cpp:61. Items follow all Otakara.
        offset = row['config_index'] + (len(catalogs['otakara']) if row['pellet_kind'] == 'item' else 0)
        row['display_offset'] = offset
        row['onboard_names'] = {language: message_name(table, 101 + offset)
                                for language, table in language_tables.items()}
        row['onboard_appraisal_names'] = {language: message_name(table, 101 + offset, 1)
                                          for language, table in language_tables.items()}


def verify_ledger(ledger, inventory_bytes, read):
    if ledger.get('schema') != 1 or ledger.get('disc') != 'GPVE01 revision 0':
        raise ValueError('Expected #140 schema 1 US revision 0 ledger')
    if ledger.get('inventory_sha256') != digest(inventory_bytes):
        raise ValueError('Ledger inventory provenance mismatch')
    hashes = ledger.get('source_sha256', {})
    if PELLET_LIST not in hashes or 'user/Abe/stages.txt' not in hashes:
        raise ValueError('Ledger lacks required source provenance')
    for path, expected in hashes.items():
        if digest(read(path)) != expected:
            raise ValueError('Ledger source provenance mismatch: ' + path)
    if ledger.get('reconciliation', {}).get('reconciled') is not True:
        raise ValueError('Input ledger has unresolved reconciliation')


def reconcile_entries(ledger, configs):
    """Check the consumed contract against its actual US runtime catalog.

    Keep #140's source records and classification. Do not expand unique entries
    into receipts or treat definitions beyond a generator count as active.
    """
    expected = {(kind, name) for kind in ('otakara', 'item') for name in configs[kind]}
    seen = set()
    rows = []
    for entry in ledger['entries']:
        kind, name = entry['pellet_kind'], entry['treasure_id']
        key = (kind, name)
        if key not in expected or key in seen:
            raise ValueError('Duplicate or unknown ledger catalog ID')
        seen.add(key)
        config = configs[kind][name]
        fields = {'dictionary': 'dictionary', 'value': 'money', 'weight': 'min', 'slots': 'max'}
        if (entry['config_index'] != list(configs[kind]).index(name)
                or any(type(entry[k]) is not int or entry[k] != int(config[v]) for k, v in fields.items())
                or entry['archive'] != config['archive'] or entry['model'] != config['bmd']
                or entry['unique'] != config.get('unique', 'no')):
            raise ValueError('Ledger entry differs from runtime catalog: ' + name)
        active, excluded = [], []
        for index, placement in enumerate(entry['placements']):
            if placement['treasure_id'] != name or type(placement.get('engine_loaded', True)) is not bool:
                raise ValueError('Invalid ledger placement identity or loaded flag')
            record = dict(ledger_placement_index=index, source=placement)
            (active if placement.get('engine_loaded', True) else excluded).append(record)
        if entry['classification'] not in ('campaign', 'mode_only', 'unused'):
            raise ValueError('Unknown ledger classification')
        rows.append(dict(source_id=name, pellet_kind=kind, config_index=entry['config_index'],
                         dictionary=entry['dictionary'], classification=entry['classification'],
                         campaign_scopes=entry['campaign_scopes'], mode_scopes=entry['mode_scopes'],
                         active_source_definitions=active, unloaded_generator_definitions=excluded))
    if seen != expected:
        raise ValueError('Ledger is missing runtime catalog entries')
    return rows


def kfes_references(text):
    """Read the alternate Challenge table selected by mKFesVersion.

    This records references only; it does not generate or classify cargo.
    """
    nodes = tree(text)
    if not nodes or not isinstance(nodes[0], str) or not nodes[0].isdigit() or int(nodes[0]) != len(nodes) - 1:
        raise ValueError('KFes stage count mismatch')
    paths = []
    for row in nodes[1:]:
        if (not isinstance(row, list) or len(row) < 30 or any(not isinstance(v, str) for v in row)
                or row[0] != '4' or not row[26].isdigit() or int(row[26]) < 1
                or len(row) != 29 + int(row[26])):
            raise ValueError('Unsupported KFes stage record')
        name = safe_name(row[1])
        if not name.endswith('.txt'):
            raise ValueError('Invalid KFes cave filename')
        paths.append('user/Mukki/mapunits/caveinfo/' + name)
    return set(paths)


def stage_cave_links(text):
    """Extract cave filename/tag links, not treasure counts or placement classes.

    Follow the declared table framing in gameStages.cpp CourseInfo::read.
    Keep non-retail courses and extensionless references as literal metadata.
    """
    nodes = tree(text)

    def count(value):
        if not isinstance(value, str) or not value.isascii() or not value.isdigit() or not 0 <= int(value) <= 10000:
            raise ValueError('Invalid stage table count')
        return int(value)

    if not nodes or count(nodes[0]) != len(nodes) - 1:
        raise ValueError('Stage table course count mismatch')
    result, seen_courses = [], set()
    for course_index, block in enumerate(nodes[1:]):
        if not isinstance(block, list):
            raise ValueError('Invalid stage course record')
        fields, at = {}, 0
        while at < len(block) and block[at] != 'end':
            key = block[at]
            width = 3 if key == 'start' else 1
            if (not isinstance(key, str) or key in fields or at + width >= len(block)
                    or any(not isinstance(v, str) for v in block[at + 1:at + width + 1])):
                raise ValueError('Invalid stage course header')
            fields[key] = block[at + 1:at + width + 1]
            at += width + 1
        if at == len(block) or 'name' not in fields:
            raise ValueError('Missing stage course name or header terminator')
        course = fields['name'][0]
        if course in seen_courses:
            raise ValueError('Duplicate stage course')
        seen_courses.add(course)
        at += 1
        for _ in range(2):  # Nonloop and loop tables: filename + three window fields.
            if at >= len(block):
                raise ValueError('Missing stage generator table')
            end = at + 1 + 4 * count(block[at])
            if end > len(block) or any(not isinstance(v, str) for v in block[at + 1:end]):
                raise ValueError('Truncated stage generator table')
            at = end
        if at >= len(block):
            raise ValueError('Missing stage cave table')
        cave_count = count(block[at])
        at += 1
        seen_tags = set()
        for cave_index in range(cave_count):
            if at + 3 > len(block):
                raise ValueError('Truncated stage cave table')
            tag, declared, filename = block[at:at + 3]
            if not isinstance(tag, list) or len(tag) != 1 or not isinstance(tag[0], str) or not re.fullmatch(r'[A-Za-z0-9_]{4}', tag[0]):
                raise ValueError('Invalid stage cave tag')
            if count(declared) > 255:  # CaveOtakaraInfo::read reads this as a byte.
                raise ValueError('Stage cave treasure count exceeds byte range')
            if not isinstance(filename, str):
                raise ValueError('Invalid stage cave filename')
            filename = safe_name(filename)
            # A non-retail course can register multiple tags for one filename.
            if tag[0] in seen_tags:
                raise ValueError('Duplicate cave tag within course')
            seen_tags.add(tag[0])
            result.append(dict(course_id=course, course_table_index=course_index,
                               cave_table_index=cave_index, cave_tag=tag[0], filename=filename,
                               source_path='user/Mukki/mapunits/caveinfo/' + filename))
            at += 3
        if at != len(block) - 1:
            raise ValueError('Trailing or missing stage course data')
        count(block[at])  # Declared surface treasure total; not used as a name ID.
    return result


def campaign_cave_names(links, inventory, language_tables):
    rows = []
    retail_courses = {s['id'] for s in inventory['surfaces']}
    seen_sources, seen_tags = set(), set()
    for cave in inventory['story_caves']:
        source_id, path = cave['id'], cave['source']
        if path in seen_sources or path != f'user/Mukki/mapunits/caveinfo/{source_id}.txt':
            raise ValueError('Duplicate or inconsistent campaign cave source ID')
        seen_sources.add(path)
        found = [link for link in links if link['source_path'] == path and link['course_id'] in retail_courses]
        if len(found) != 1:
            raise ValueError('Missing or ambiguous campaign cave stage link: ' + source_id)
        link = found[0]
        tag = link['cave_tag']
        if tag not in CAVE_TITLE_MESSAGES or tag in seen_tags:
            raise ValueError('Missing or duplicate campaign cave title tag: ' + tag)
        seen_tags.add(tag)
        number = CAVE_TITLE_MESSAGES[tag]
        rows.append(dict(link, source_id=source_id, message_number=number,
                         onboard_names={language: message_name(table, number, cave_presentation=True)
                                        for language, table in language_tables.items()}))
    return rows


def cave_file_classes(files, inventory, demo_references=frozenset(), stage_links=()):
    references = {}
    for cave in inventory['story_caves']:
        references.setdefault(cave['source'], []).append('campaign')
    for mode in ('challenge', 'battle'):
        for stage in inventory[mode]['stages']:
            references.setdefault(stage['cave_path'], []).append(mode)
    registered = {}
    for link in stage_links:
        registered.setdefault(link['source_path'], []).append(link)
    missing = (references.keys() | demo_references) - files.keys()
    if missing:
        raise ValueError('Missing referenced cave files: ' + ', '.join(sorted(missing)))
    return [dict(source_path=path, retail_scopes=sorted(set(references.get(path, []))),
                 classification=('retail_referenced' if path in references else
                                 'kfes_only_reference' if path in demo_references else
                                 'stage_registered_outside_retail_inventory' if path in registered else
                                 'unreferenced_status_unresolved'),
                 kfes_referenced=path in demo_references,
                 stage_table_references=registered.get(path, []),
                 filename_hint='kfes' if Path(path).name.lower().startswith('kfes_') else None)
            for path in sorted(files) if path.startswith('user/Mukki/mapunits/caveinfo/') and path.endswith('.txt')]


def build(iso, ledger_path, inventory_path, output):
    if output.exists():
        raise FileExistsError('Output must be a new private directory')
    inventory_bytes, ledger_bytes = inventory_path.read_bytes(), ledger_path.read_bytes()
    inventory, ledger = json.loads(inventory_bytes), json.loads(ledger_bytes)
    files = disc_files(iso)  # Existing parser enforces US GPVE01 revision 0.
    hashes = {}
    with iso.open('rb') as disc:
        def read(path):
            if path not in files:
                raise ValueError('Missing disc source: ' + path)
            offset, length = files[path]
            disc.seek(offset)
            data = disc.read(length)
            if len(data) != length:
                raise ValueError('Truncated disc source: ' + path)
            hashes[path] = digest(data)
            return data

        verify_ledger(ledger, inventory_bytes, read)
        catalogs, loose_deltas = {}, {}
        for region in REGIONS:
            prefix = f'user/Abe/Pellet/{region}/'
            archive = archive_files(read(prefix + f'pelletlist_{region}.szs'))
            catalogs[region], loose_deltas[region] = {}, {}
            for kind in KINDS:
                member = kind + '_config.txt'
                runtime = pellet_catalog(archive[member].decode('shift_jis'))
                catalogs[region][kind] = runtime
                path = prefix + member
                if path in files:
                    loose = pellet_catalog(read(path).decode('shift_jis'))
                    loose_deltas[region][kind] = catalog_delta(runtime, loose)
                else:
                    loose_deltas[region][kind] = dict(status='absent')
        rows = reconcile_entries(ledger, catalogs['us'])
        language_tables = {}
        for language in LANGUAGES:
            path = f'message/mesRes_{language}.szs'
            language_tables[language] = bmg_index(archive_files(read(path))['pikmin2.bmg'])
        attach_names(rows, catalogs['us'], language_tables)
        stage_links = stage_cave_links(read('user/Abe/stages.txt').decode('shift_jis'))
        named_caves = campaign_cave_names(stage_links, inventory, language_tables)
        for link in stage_links:
            link['source_file_present'] = link['source_path'] in files
            link['retail_course'] = link['course_id'] in {s['id'] for s in inventory['surfaces']}
        comparisons = {region: {kind: catalog_delta(catalogs['us'][kind], catalogs[region][kind])
                                for kind in KINDS} for region in ('jpn', 'pal')}
        cave_files = cave_file_classes(files, inventory, kfes_references(read(KFES_TABLE).decode('shift_jis')), stage_links)
    result = dict(schema=1, disc='GPVE01 revision 0', regional_runtime_validated=False,
                  mapping_source_revision=MAPPING_SOURCE_REVISION,
                  ledger_sha256=digest(ledger_bytes), inventory_sha256=digest(inventory_bytes),
                  source_sha256=hashes, entries=rows, onboard_catalog_differences=comparisons,
                  loose_config_differences=loose_deltas, cave_definitions=cave_files,
                  campaign_cave_names=named_caves, stage_cave_references=stage_links,
                  summary=dict(entries=len(rows), classifications=dict(Counter(r['classification'] for r in rows)),
                               active_source_definitions=sum(len(r['active_source_definitions']) for r in rows),
                               unloaded_generator_definitions=sum(len(r['unloaded_generator_definitions']) for r in rows),
                               campaign_cave_names=len(named_caves),
                               cave_definitions=dict(Counter(r['classification'] for r in cave_files))),
                  limitations=[
                      'Consumes #140 classifications and source definitions, not generated instances or delivery receipts.',
                      'Language archives on a US disc do not establish PAL/JPN executable or gameplay support.',
                      'Name lookups use US runtime config indexes; foreign regional runtime name joins remain unvalidated.',
                      'Unreferenced cave files and loose config differences are not automatically unused/test/demo content.',
                      'Stage registration alone does not establish an active cave entrance or retail playability.',
                      'Unrecognized controls and empty/missing messages remain unresolved; known cave sizing tags are retained separately.',
                      'Full regional disc, localized UI, physical placement and save/load validation remain open.'])
    output.mkdir(parents=True, exist_ok=False)
    (output / 'regional_audit.json').write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--iso', type=Path, required=True)
    parser.add_argument('--ledger', type=Path, required=True)
    parser.add_argument('--inventory', type=Path, default=Path('docs/PIKMIN2_CONTENT_INVENTORY.json'))
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(build(args.iso, args.ledger, args.inventory, args.output)['summary']))
